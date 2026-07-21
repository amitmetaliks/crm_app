"""Auto conveyance (travel allowance) from the GPS route.

The company already had the policy pieces in ERPNext but nothing ever connected them:

  * ``Sales Person.travel_allowance_per_km``      — the rate (₹3.00/km on their site)
  * ``Expense Claim Detail.custom_distance_travelled`` — their distance field, which was
    filled on 0 of 513 Travel claims.

This module joins them to the app's GPS trail: distance × rate → a pre-filled **Travel**
Expense Claim that flows through the normal approval path.

Honest limitation (surfaced in the UI): the GPS distance is a haversine sum of the day's
pings, so it follows straight lines between points and **under-reads real road distance**.
The rep may therefore correct the distance, but only *with remarks* (and optionally a
photo). Both numbers are stored, so the approver always sees GPS vs claimed.
"""

import base64

import frappe
from frappe import _
from frappe.utils import flt, getdate

from crm_app.api import get_current_employee, validate_upload
from crm_app.sales_attr import _sales_persons_for
from crm_app.tracking import _day_points, _distance_km

EXPENSE_TYPE = "Travel"
#: Difference beyond which a correction must be justified.
TOLERANCE_KM = 0.5


def _hrms_ready() -> bool:
	return bool(frappe.db.exists("DocType", "Expense Claim"))


def _rate_for(employee) -> float:
	"""₹/km for this rep: their Sales Person rate, else a site-wide default."""
	for sp in _sales_persons_for(employee):
		if frappe.get_meta("Sales Person").has_field("travel_allowance_per_km"):
			rate = flt(frappe.db.get_value("Sales Person", sp, "travel_allowance_per_km"))
			if rate > 0:
				return rate
	# Fallback for reps with no Sales Person / no rate set (15 of 36 on their site).
	return flt(frappe.conf.get("crm_conveyance_rate_per_km") or 0)


def _claimed_row(employee, day):
	"""An existing conveyance claim *from this app* for that day, if any.

	Identified by ``custom_distance_source``, NOT by ``custom_gps_distance_km``: adding a
	Float custom field backfills every pre-existing row with **0, not NULL**, so an
	``IS NOT NULL`` test matches the whole table (all 1,005 historic claims on their
	site). A Data field backfills as NULL, so only rows this module wrote are matched.
	"""
	meta = frappe.get_meta("Expense Claim Detail")
	if not meta.has_field("custom_distance_source"):
		return None
	rows = frappe.db.sql(
		"""
		SELECT ec.name, ec.approval_status, ec.status, d.amount, d.custom_gps_distance_km
		FROM `tabExpense Claim Detail` d
		JOIN `tabExpense Claim` ec ON ec.name = d.parent
		WHERE ec.employee = %s AND d.expense_date = %s AND d.expense_type = %s
		  AND COALESCE(d.custom_distance_source, '') != '' AND ec.docstatus < 2
		LIMIT 1
		""",
		(employee, day, EXPENSE_TYPE),
		as_dict=True,
	)
	return rows[0] if rows else None


@frappe.whitelist()
def get_today_conveyance(date=None) -> dict:
	"""GPS distance, rate and payable conveyance for the session rep on `date`."""
	employee = get_current_employee()
	day = getdate(date) if date else getdate()
	gps_km = _distance_km(_day_points(employee, day))
	rate = _rate_for(employee)
	existing = _claimed_row(employee, day) if _hrms_ready() else None
	return {
		"date": str(day),
		"gps_km": gps_km,
		"rate_per_km": rate,
		"amount": flt(gps_km * rate, 2),
		"available": bool(_hrms_ready() and rate > 0),
		"rate_missing": rate <= 0,
		"claimed": bool(existing),
		"claim": existing or None,
		# The rep sees this, so nobody is surprised by a short reading.
		"note": "GPS measures straight lines between points, so it can read a little "
		"short of the road distance. Correct it below if needed.",
	}


@frappe.whitelist()
def claim_conveyance(date=None, claimed_km=None, remarks=None, attachment_base64=None, attachment_filename=None) -> dict:
	"""Create + submit a Travel claim for the day's distance.

	`claimed_km` (optional) overrides the GPS reading — allowed only with `remarks`.
	"""
	employee = get_current_employee()
	if not _hrms_ready():
		frappe.throw(_("Expense claims are not available on this site (HR module missing)."))
	day = getdate(date) if date else getdate()

	if _claimed_row(employee, day):
		frappe.throw(_("Conveyance for {0} is already claimed.").format(day))

	gps_km = _distance_km(_day_points(employee, day))
	rate = _rate_for(employee)
	if rate <= 0:
		frappe.throw(_("No travel allowance rate is set for you. Ask HR to set 'Travel Allowance Per Km' on your Sales Person record."))

	final_km = flt(claimed_km) if claimed_km not in (None, "") else gps_km
	if final_km <= 0:
		frappe.throw(_("No distance recorded for {0}.").format(day))

	corrected = abs(final_km - gps_km) > TOLERANCE_KM
	remarks = (remarks or "").strip()
	if corrected and not remarks:
		frappe.throw(_("Please add remarks explaining the corrected distance."))

	amount = flt(final_km * rate, 2)
	company = frappe.db.get_value("Employee", employee, "company")
	desc = f"Conveyance {day}: {final_km:g} km × ₹{rate:g}/km"
	if corrected:
		desc += f" (GPS recorded {gps_km:g} km; rep corrected). Remarks: {remarks}"
	elif remarks:
		desc += f". Remarks: {remarks}"

	row = {
		"expense_type": EXPENSE_TYPE,
		"expense_date": str(day),
		"description": desc,
		"amount": amount,
		"sanctioned_amount": amount,
	}
	meta = frappe.get_meta("Expense Claim Detail")
	if meta.has_field("custom_gps_distance_km"):
		row["custom_gps_distance_km"] = gps_km
	if meta.has_field("custom_distance_source"):
		row["custom_distance_source"] = "Rep corrected" if corrected else "GPS auto"
	# Their pre-existing field (Data). Only set it if the site actually has it.
	if meta.has_field("custom_distance_travelled"):
		row["custom_distance_travelled"] = f"{final_km:g}"

	doc = frappe.get_doc(
		{
			"doctype": "Expense Claim",
			"employee": employee,
			"company": company,
			"posting_date": getdate(),
			"currency": frappe.db.get_value("Company", company, "default_currency") if company else None,
			"exchange_rate": 1.0,
			"payable_account": frappe.db.get_value("Company", company, "default_expense_claim_payable_account")
			if company
			else None,
			"expense_approver": frappe.db.get_value("Employee", employee, "expense_approver"),
			"expenses": [row],
		}
	)
	doc.insert(ignore_permissions=True)

	if attachment_base64:
		content = base64.b64decode(attachment_base64.split(",")[-1])
		validate_upload(attachment_filename or "conveyance.jpg", content, images_only=True, max_mb=8)
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": attachment_filename or "conveyance.jpg",
				"attached_to_doctype": doc.doctype,
				"attached_to_name": doc.name,
				"content": content,
				"is_private": 1,
			}
		).insert(ignore_permissions=True)

	submit_error = None
	try:
		doc.submit()
		frappe.db.commit()
		submitted = True
	except Exception as e:
		# Leave the claim as a draft rather than failing the whole call, but DON'T swallow the
		# reason: log it and hand it back, so a claim that silently didn't submit (missing
		# approver / payable account on a customised site) is diagnosable, not an orphan.
		frappe.db.commit()
		submitted = False
		submit_error = str(e)
		frappe.log_error(title="Conveyance claim submit failed", message=frappe.get_traceback())

	return {
		"name": doc.name,
		"submitted": submitted,
		"message": submit_error,
		"km": final_km,
		"gps_km": gps_km,
		"rate_per_km": rate,
		"amount": amount,
		"corrected": corrected,
	}
