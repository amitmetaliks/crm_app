"""Manager approvals — Leave + Expense (hrms) and field-visit verification.

Gates on the real approver relationship (leave_approver / expense_approver) or the
sales-manager role. Respects an active Frappe Workflow if configured, else does a
guarded status change. Notifies the employee (in-app + push).
"""

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from crm_app.api import get_current_employee, is_sales_manager


def _hrms_ready() -> bool:
	return bool(frappe.db.exists("DocType", "Leave Application"))


def _add_conveyance_context(expenses):
	"""Attach GPS-vs-claimed distance to auto-conveyance claims, so the approver can see
	at a glance whether the rep overrode the measured route (and why).

	Only rows written by crm_app carry ``custom_distance_source``; note that
	``custom_gps_distance_km`` is 0 (not NULL) on every pre-existing row, so it must
	never be used to detect our rows. See conveyance.py.
	"""
	if not expenses:
		return
	meta = frappe.get_meta("Expense Claim Detail")
	if not meta.has_field("custom_distance_source"):
		return
	rows = frappe.get_all(
		"Expense Claim Detail",
		filters={"parent": ["in", [e.name for e in expenses]], "custom_distance_source": ["!=", ""]},
		fields=[
			"parent", "amount", "description", "custom_gps_distance_km",
			"custom_distance_travelled", "custom_distance_source",
		],
	)
	by_parent = {r.parent: r for r in rows}
	for e in expenses:
		r = by_parent.get(e.name)
		if not r:
			continue
		gps = flt(r.custom_gps_distance_km)
		try:
			claimed = flt(r.custom_distance_travelled)
		except (TypeError, ValueError):
			claimed = gps
		e["conveyance"] = {
			"gps_km": gps,
			"claimed_km": claimed,
			"source": r.custom_distance_source,
			"corrected": r.custom_distance_source == "Rep corrected",
			"extra_km": flt(claimed - gps, 2),
			"description": r.description,
		}


@frappe.whitelist()
def get_pending_approvals() -> dict:
	"""Items awaiting the current user: leave, expense, and team visits to verify."""
	get_current_employee()
	user = frappe.session.user
	leaves, expenses = [], []
	if _hrms_ready():
		leaves = frappe.get_all(
			"Leave Application",
			filters={"leave_approver": user, "status": "Open", "docstatus": 1},
			fields=["name", "employee_name", "leave_type", "from_date", "to_date", "total_leave_days", "description"],
			order_by="from_date asc",
		)
		expenses = frappe.get_all(
			"Expense Claim",
			filters={"expense_approver": user, "approval_status": "Draft", "docstatus": ["<", 2]},
			fields=["name", "employee_name", "posting_date", "grand_total", "total_claimed_amount"],
			order_by="posting_date asc",
		)
		_add_conveyance_context(expenses)

	visits = []
	if is_sales_manager():
		visits = frappe.get_all(
			"CRM Visit",
			filters={"verified": 0, "visit_status": "Completed"},
			fields=["name", "sales_person_name", "party_display", "visit_purpose", "visit_date"],
			order_by="visit_date desc",
			limit=25,
		)

	return {"leaves": leaves, "expenses": expenses, "visits": visits, "count": len(leaves) + len(expenses)}


def _active_workflow(doctype):
	return frappe.db.exists("Workflow", {"document_type": doctype, "is_active": 1})


def _apply_workflow_action(doc, action):
	from frappe.model.workflow import apply_workflow, get_transitions

	target = "approve" if action == "approve" else "reject"
	for t in get_transitions(doc):
		if target in (t.get("action") or "").lower():
			apply_workflow(doc, t.get("action"))
			return True
	return False


@frappe.whitelist()
def act_on_approval(doctype, name, action, reason=None) -> dict:
	if action not in ("approve", "reject"):
		frappe.throw(_("Invalid action."))
	if doctype not in ("Leave Application", "Expense Claim"):
		frappe.throw(_("Unsupported approval type."))
	get_current_employee()
	user = frappe.session.user

	approver_field = "leave_approver" if doctype == "Leave Application" else "expense_approver"
	approver = frappe.db.get_value(doctype, name, approver_field)
	if approver != user and not is_sales_manager():
		frappe.throw(_("You are not the approver for this item."), frappe.PermissionError)

	doc = frappe.get_doc(doctype, name)
	if _active_workflow(doctype):
		if reason and doctype == "Expense Claim" and doc.meta.has_field("remark"):
			doc.remark = reason
		if not _apply_workflow_action(doc, action):
			frappe.throw(_("No matching workflow action from the current state."))
	elif doctype == "Leave Application":
		if doc.docstatus != 1 or doc.status != "Open":
			frappe.throw(_("This leave application is already {0}.").format(doc.status))
		doc.status = "Approved" if action == "approve" else "Rejected"
		doc.save(ignore_permissions=True)
	else:
		if doc.approval_status != "Draft":
			frappe.throw(_("This expense claim is already {0}.").format(doc.approval_status))
		doc.approval_status = "Approved" if action == "approve" else "Rejected"
		if reason:
			doc.remark = reason
		doc.save(ignore_permissions=True)

	_notify_employee(doctype, name, action, reason)
	frappe.db.commit()
	return {"name": name, "action": action}


def _notify_employee(doctype, name, action, reason):
	try:
		employee = frappe.db.get_value(doctype, name, "employee")
		emp_user = frappe.db.get_value("Employee", employee, "user_id")
		if not emp_user:
			return
		from crm_app.tasks import notify

		verb = "approved" if action == "approve" else "rejected"
		notify(emp_user, f"Your {doctype} {name} was {verb}", reason or "", "/amit-crm/notifications")
	except Exception:
		frappe.log_error(title="crm approval notify failed", message=frappe.get_traceback())


@frappe.whitelist()
def verify_visit(name) -> dict:
	"""Manager marks a completed field visit as verified."""
	get_current_employee()
	if not is_sales_manager():
		frappe.throw(_("Only sales managers can verify visits."), frappe.PermissionError)
	doc = frappe.get_doc("CRM Visit", name)
	doc.verified = 1
	doc.verified_by = frappe.session.user
	doc.verified_on = now_datetime()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": name, "verified": True}
