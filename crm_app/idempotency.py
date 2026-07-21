"""Server-side idempotency for the offline queue.

The rep app queues writes in IndexedDB and replays them when the network returns
(`frontend/src/data/offline.js`). One replay case is genuinely dangerous: the request
COMMITTED on the server but its RESPONSE was lost (dropped connection, timeout after the
DB write). The client can't tell that from a request that never arrived, so it retries —
and without a guard the retry creates a SECOND attendance punch or a SECOND expense claim.
A duplicate expense claim is duplicate money; a duplicate check-in corrupts the day.

Visits already dedupe on their own `client_ref` field. This module is the general
equivalent for endpoints whose target is a stock HRMS doctype (Employee Checkin, Expense
Claim) we don't want to add custom fields to: the client mints a stable key ONCE, before
the first attempt, and reuses it on every retry; the server records key -> response in a
tiny `CRM Idempotency Key` row that COMMITS in the same transaction as the business write.
So either both persist or neither does — exactly the property that makes the retry safe.

Degrades gracefully: on a bench where the doctype hasn't been migrated yet, `replay`
returns None and `record` is a no-op, so the endpoints behave as before (no idempotency,
but no crash) — the same defensive stance the rest of this app takes toward optional data.
"""

import frappe

DOCTYPE = "CRM Idempotency Key"


def _available() -> bool:
	try:
		return bool(frappe.db.exists("DocType", DOCTYPE))
	except Exception:
		return False


def replay(key):
	"""If this key was already processed, return the stored response; else None.

	A non-None return means "already done, don't do it again" — the caller must return it
	verbatim instead of repeating its write.
	"""
	if not key or not _available():
		return None
	resp = frappe.db.get_value(DOCTYPE, {"idempotency_key": str(key)}, "response")
	if resp is None:
		return None
	try:
		return frappe.parse_json(resp)
	except Exception:
		# The write definitely happened; we just can't reconstruct the payload.
		return {"duplicate": True}


def record(key, method, response, employee=None):
	"""Persist key -> response. NOT committed here: it rides the caller's own commit so the
	marker and the business write land together (or roll back together)."""
	if not key or not _available():
		return
	if frappe.db.exists(DOCTYPE, {"idempotency_key": str(key)}):
		return
	try:
		frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"idempotency_key": str(key)[:140],
				"method": (method or "")[:140],
				"employee": employee,
				"response": frappe.as_json(response),
			}
		).insert(ignore_permissions=True)
	except frappe.exceptions.DuplicateEntryError:
		# A concurrent request beat us to the same key — that request's response stands.
		pass
