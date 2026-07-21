"""Leave — balance + apply, on ERPNext/HR Leave Application. Requires `hrms`."""

import frappe
from frappe import _
from frappe.utils import getdate

from crm_app.api import get_current_employee


def _hrms_ready() -> bool:
	return bool(frappe.db.exists("DocType", "Leave Application"))


@frappe.whitelist()
def get_leave_summary() -> dict:
	employee = get_current_employee()
	balance = {}
	try:
		from hrms.api import get_leave_balance_map

		balance = get_leave_balance_map() or {}
	except Exception:
		balance = {}
	return {"employee": employee, "balance": balance, "available": _hrms_ready()}


@frappe.whitelist()
def get_leave_types() -> list:
	if not frappe.db.exists("DocType", "Leave Type"):
		return []
	return frappe.get_all("Leave Type", fields=["name"], order_by="name")


@frappe.whitelist()
def get_my_leaves(limit=30) -> list:
	employee = get_current_employee()
	if not _hrms_ready():
		return []
	return frappe.get_all(
		"Leave Application",
		filters={"employee": employee},
		fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status"],
		order_by="from_date desc",
		limit=int(limit),
	)


@frappe.whitelist()
def apply_leave(leave_type, from_date, to_date, half_day=0, description=None, idempotency_key=None) -> dict:
	employee = get_current_employee()
	if not _hrms_ready():
		frappe.throw(_("Leave is not available on this site (HR module missing)."))
	from crm_app import idempotency

	prior = idempotency.replay(idempotency_key, employee)
	if prior is not None:
		return prior
	company = frappe.db.get_value("Employee", employee, "company")
	approver = frappe.db.get_value("Employee", employee, "leave_approver")
	doc = frappe.get_doc(
		{
			"doctype": "Leave Application",
			"employee": employee,
			"leave_type": leave_type,
			"from_date": from_date,
			"to_date": to_date,
			"half_day": int(half_day or 0),
			"description": description,
			"company": company,
			"leave_approver": approver,
			"status": "Open",
			"posting_date": getdate(),
		}
	)
	doc.insert(ignore_permissions=True)
	try:
		doc.submit()
		result = {"name": doc.name, "submitted": True, "status": doc.status}
	except Exception as e:
		result = {"name": doc.name, "submitted": False, "message": str(e)}
	idempotency.record(idempotency_key, "leave.apply_leave", result, employee)
	frappe.db.commit()
	return result
