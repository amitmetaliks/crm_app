"""Row-level visibility (permission_query_conditions) for crm_app doctypes.

Registered in hooks.py from Phase 1 onward. Each function returns a SQL WHERE
fragment (or "" for no filter, "1=0" for deny-all). Sales managers see the whole
team; everyone else sees only the rows tied to their own Employee.
"""

import frappe


def _own_employee(user: str, doctype: str, field: str = "sales_person") -> str:
	from crm_app.api import is_sales_manager

	if is_sales_manager(user):
		return ""
	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	if not employee:
		return "1=0"
	return f"`tab{doctype}`.`{field}` = {frappe.db.escape(employee)}"


def crm_visit_query(user: str | None = None) -> str:
	"""Reps see only their own visits; sales managers see the whole team."""
	return _own_employee(user or frappe.session.user, "CRM Visit", "sales_person")
