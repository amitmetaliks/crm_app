"""Salary slips — list / detail / PDF, own slips only. Requires `hrms`."""

import base64

import frappe
from frappe import _

from crm_app.api import get_current_employee


def _hrms_ready() -> bool:
	return bool(frappe.db.exists("DocType", "Salary Slip"))


def _assert_owner(name):
	employee = get_current_employee()
	if frappe.db.get_value("Salary Slip", name, "employee") != employee:
		frappe.throw(_("You do not have access to this salary slip."), frappe.PermissionError)


@frappe.whitelist()
def get_my_salary_slips(limit=24) -> list:
	employee = get_current_employee()
	if not _hrms_ready():
		return []
	return frappe.get_all(
		"Salary Slip",
		filters={"employee": employee, "docstatus": ["<", 2]},
		fields=["name", "start_date", "end_date", "posting_date", "gross_pay", "total_deduction", "net_pay", "status"],
		order_by="end_date desc",
		limit=int(limit),
	)


@frappe.whitelist()
def get_salary_slip(name) -> dict:
	_assert_owner(name)
	doc = frappe.get_doc("Salary Slip", name)
	return {
		"name": doc.name,
		"start_date": doc.start_date,
		"end_date": doc.end_date,
		"posting_date": doc.posting_date,
		"gross_pay": doc.gross_pay,
		"total_deduction": doc.total_deduction,
		"net_pay": doc.net_pay,
		"currency": getattr(doc, "currency", None),
		"earnings": [{"component": e.salary_component, "amount": e.amount} for e in doc.earnings],
		"deductions": [{"component": d.salary_component, "amount": d.amount} for d in doc.deductions],
	}


@frappe.whitelist()
def download_salary_slip_pdf(name) -> dict:
	_assert_owner(name)
	from frappe.utils.pdf import get_pdf

	html = frappe.get_print("Salary Slip", name)
	pdf = get_pdf(html)
	return {"name": name, "filename": f"{name}.pdf", "content_base64": base64.b64encode(pdf).decode()}
