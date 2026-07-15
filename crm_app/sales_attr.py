"""Attribute ERPNext Sales Orders / Customers to a rep using MULTIPLE signals, so
real orders reflect regardless of how the org records them:

  1. ERPNext Sales Team -> Sales Person (linked to the Employee)
  2. The order's creator (owner) -> the Employee's user
  3. Our Customer.custom_assigned_sales_person field

Shared by targets / sfa / insights so attribution is consistent everywhere.
"""

import frappe
from frappe.utils import flt


def _sales_persons_for(employee):
	if frappe.db.exists("DocType", "Sales Person") and frappe.get_meta("Sales Person").has_field("employee"):
		return frappe.get_all("Sales Person", filters={"employee": employee}, pluck="name")
	return []


def _team_sales_orders(sales_persons):
	if not sales_persons or not frappe.db.exists("DocType", "Sales Team"):
		return set()
	rows = frappe.get_all(
		"Sales Team",
		filters={"parenttype": "Sales Order", "sales_person": ["in", sales_persons]},
		fields=["parent"],
		limit=100000,
	)
	return {r.parent for r in rows}


def _attributes_so(so, employee, user, assigned_customers, team_sos):
	return (
		so.name in team_sos
		or so.customer in assigned_customers
		or (user and so.owner == user)
	)


def rep_sales(employee, frm, to):
	"""{amount, qty, orders} attributed to the rep in [frm, to].

	**Prefers the SAP Sales Register**, because that is where the business actually
	invoices: ₹219 crore of real invoices against ~₹22 lakh of ERPNext Sales Orders on
	their site, and SAP carries the rep's employee code on every line, so attribution is
	read rather than inferred. The ERPNext path below stays as the fallback for sites
	without the SAP feed (crm-dev, a fresh install) and for the day orders are raised here.
	"""
	from crm_app import sap_sales

	if employee and sap_sales.available():
		sap = sap_sales.rep_sales(employee, frm, to)
		if sap["invoices"]:
			return {"amount": sap["amount"], "qty": sap["qty"], "orders": sap["invoices"], "source": "sap"}

	if not employee or not frappe.db.exists("DocType", "Sales Order"):
		return {"amount": 0.0, "qty": 0.0, "orders": 0}
	user = frappe.db.get_value("Employee", employee, "user_id")
	assigned = set(frappe.get_all("Customer", filters={"custom_assigned_sales_person": employee}, pluck="name"))
	team_sos = _team_sales_orders(_sales_persons_for(employee))
	sos = frappe.get_all(
		"Sales Order",
		filters={"transaction_date": ["between", [frm, to]], "docstatus": ["<", 2]},
		fields=["name", "customer", "owner", "base_net_total", "total_qty"],
		limit=100000,
	)
	amount = qty = 0.0
	cnt = 0
	for so in sos:
		if _attributes_so(so, employee, user, assigned, team_sos):
			amount += flt(so.base_net_total)
			qty += flt(so.total_qty)
			cnt += 1
	return {"amount": flt(amount, 2), "qty": flt(qty, 3), "orders": cnt}


def rep_customers(employee):
	"""Set of Customer names attributed to the rep (SAP invoices + assigned + orders)."""
	from crm_app import sap_sales

	custs = set(frappe.get_all("Customer", filters={"custom_assigned_sales_person": employee}, pluck="name"))
	# Whoever he actually invoiced in SAP is the strongest signal of "his" dealer.
	custs.update(sap_sales.rep_customers(employee))
	if not frappe.db.exists("DocType", "Sales Order"):
		return custs
	user = frappe.db.get_value("Employee", employee, "user_id")
	if user:
		custs.update(frappe.get_all("Sales Order", filters={"owner": user, "docstatus": ["<", 2]}, pluck="customer"))
	sps = _sales_persons_for(employee)
	team_sos = _team_sales_orders(sps)
	if team_sos:
		custs.update(
			frappe.get_all("Sales Order", filters={"name": ["in", list(team_sos)]}, pluck="customer")
		)
	custs.discard(None)
	return custs
