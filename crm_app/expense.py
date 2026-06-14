"""Field expense claims → ERPNext/HR Expense Claim (TA/DA, fuel, food, lodging…).

Reps file claims with photo receipts from the app; they flow into the real Expense
Claim with the normal approval + reimbursement path. Requires `hrms`.
"""

import base64
import json

import frappe
from frappe import _
from frappe.utils import flt, getdate

from crm_app.api import get_current_employee, validate_upload


def _hrms_ready() -> bool:
	return bool(frappe.db.exists("DocType", "Expense Claim"))


@frappe.whitelist()
def get_expense_types() -> list:
	if not frappe.db.exists("DocType", "Expense Claim Type"):
		return []
	return frappe.get_all("Expense Claim Type", fields=["name"], order_by="name")


@frappe.whitelist()
def get_my_expenses(limit=40) -> list:
	employee = get_current_employee()
	if not _hrms_ready():
		return []
	return frappe.get_all(
		"Expense Claim",
		filters={"employee": employee},
		fields=["name", "posting_date", "status", "approval_status", "grand_total", "total_claimed_amount"],
		order_by="posting_date desc",
		limit=int(limit),
	)


def _attach(doc, b64, filename):
	content = base64.b64decode(b64.split(",")[-1])
	validate_upload(filename or "receipt.jpg", content, images_only=True, max_mb=8)
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename or "receipt.jpg",
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"content": content,
			"is_private": 1,
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def create_expense_claim(items, receipt_base64=None, receipt_filename=None) -> dict:
	"""Create + submit an Expense Claim for the logged-in employee."""
	employee = get_current_employee()
	if not _hrms_ready():
		frappe.throw(_("Expense claims are not available on this site (HR module missing)."))
	company = frappe.db.get_value("Employee", employee, "company")
	if isinstance(items, str):
		items = json.loads(items)
	if not items:
		frappe.throw(_("Add at least one expense line."))

	expenses = []
	for it in items:
		amt = flt(it.get("amount"))
		expenses.append(
			{
				"expense_type": it.get("expense_type"),
				"expense_date": it.get("expense_date") or str(getdate()),
				"description": it.get("description"),
				"amount": amt,
				"sanctioned_amount": amt,
			}
		)

	approver = frappe.db.get_value("Employee", employee, "expense_approver")
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
			"expense_approver": approver,
			"expenses": expenses,
		}
	)
	doc.insert(ignore_permissions=True)
	if receipt_base64:
		_attach(doc, receipt_base64, receipt_filename)
	try:
		doc.submit()
		frappe.db.commit()
		return {"name": doc.name, "submitted": True}
	except Exception as e:
		frappe.db.commit()
		return {"name": doc.name, "submitted": False, "message": str(e)}


@frappe.whitelist()
def get_expense_claim(name) -> dict:
	employee = get_current_employee()
	owner = frappe.db.get_value("Expense Claim", name, "employee")
	if owner != employee:
		frappe.throw(_("You do not have access to this claim."), frappe.PermissionError)
	doc = frappe.get_doc("Expense Claim", name)
	return {
		"name": doc.name,
		"posting_date": doc.posting_date,
		"status": doc.status,
		"approval_status": doc.approval_status,
		"grand_total": doc.grand_total,
		"total_claimed_amount": doc.total_claimed_amount,
		"expenses": [
			{
				"expense_type": e.expense_type,
				"expense_date": e.expense_date,
				"description": e.description,
				"amount": e.amount,
				"sanctioned_amount": e.sanctioned_amount,
			}
			for e in doc.expenses
		],
	}
