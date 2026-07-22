"""Transactional idempotency for writes replayed by the field app.

The browser assigns a stable key before its first attempt. ``replay`` reserves that key
inside the caller's transaction before any business document is created; ``record`` stores
the response in the same transaction. A concurrent retry blocks on the unique key and then
replays the winner's response, so lost HTTP responses cannot create duplicate money or
attendance records.
"""

import frappe

DOCTYPE = "CRM Idempotency Key"

# A reservation with no response is normally a concurrent in-flight request. But if the owning
# request died AFTER a nested commit persisted the empty placeholder (e.g. a frappe.log_error
# inside the endpoint) and then rolled back its business write, the placeholder is orphaned. Without
# a reclaim window every future retry of that key would throw forever — bricking the rep's action.
# After this many seconds an empty reservation is treated as abandoned and reclaimed.
STALE_RESERVATION_SECONDS = 180


def _available() -> bool:
	try:
		return bool(frappe.db.exists("DocType", DOCTYPE))
	except Exception:
		return False


def _existing(key):
	return frappe.db.get_value(
		DOCTYPE, {"idempotency_key": key}, ["name", "employee", "response", "creation"], as_dict=True
	)


def replay(key, employee=None):
	"""Atomically reserve ``key``, or return its completed response.

	``None`` means this transaction owns the reservation and may perform the write. A response
	means another attempt already completed and the endpoint must return it verbatim.
	"""
	if not key or not _available():
		return None
	key = str(key)[:140]
	row = _existing(key)
	if not row:
		try:
			frappe.get_doc(
				{
					"doctype": DOCTYPE,
					"idempotency_key": key,
					"employee": employee,
					"response": "",
				}
			).insert(ignore_permissions=True)
			return None
		except frappe.exceptions.DuplicateEntryError:
			# The unique insert waits for the competing transaction to commit or roll back.
			# After it loses the race, the winning response is safe to read.
			row = _existing(key)

	if not row:
		frappe.throw("The request is being retried. Please try again.", frappe.TimestampMismatchError)
	if employee and row.employee and row.employee != employee:
		frappe.throw("This request key belongs to another user.", frappe.PermissionError)
	if not row.response:
		# Empty reservation. If it's fresh, a sibling request is genuinely in flight — tell the
		# client to retry shortly. If it's stale, the owning request died and left an orphan;
		# reclaim it (delete + let this transaction re-reserve) so the action isn't bricked forever.
		from frappe.utils import get_datetime, now_datetime

		age = (now_datetime() - get_datetime(row.creation)).total_seconds() if row.creation else 0
		if age <= STALE_RESERVATION_SECONDS:
			frappe.throw("This request is still being processed. Please retry shortly.", frappe.TimestampMismatchError)
		frappe.delete_doc(DOCTYPE, row.name, ignore_permissions=True, force=True)
		try:
			frappe.get_doc(
				{"doctype": DOCTYPE, "idempotency_key": key, "employee": employee, "response": ""}
			).insert(ignore_permissions=True)
		except frappe.exceptions.DuplicateEntryError:
			# Another retry reclaimed it first; fall through and let them win.
			return replay(key, employee)
		return None
	try:
		return frappe.parse_json(row.response)
	except Exception:
		return {"duplicate": True}


def record(key, method, response, employee=None):
	"""Finish a reservation with its response in the caller's transaction."""
	if not key or not _available():
		return
	key = str(key)[:140]
	row = _existing(key)
	if row:
		if employee and row.employee and row.employee != employee:
			frappe.throw("This request key belongs to another user.", frappe.PermissionError)
		frappe.db.set_value(
			DOCTYPE,
			row.name,
			{
				"method": (method or "")[:140],
				"employee": employee,
				"response": frappe.as_json(response),
			},
			update_modified=False,
		)
		return

	# Compatibility for a caller that records without first invoking replay.
	try:
		frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"idempotency_key": key,
				"method": (method or "")[:140],
				"employee": employee,
				"response": frappe.as_json(response),
			}
		).insert(ignore_permissions=True)
	except frappe.exceptions.DuplicateEntryError:
		# A concurrent path already reserved/recorded this key — that response stands.
		pass
