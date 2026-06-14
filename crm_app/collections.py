"""Payment-collection follow-up — outstanding invoices for the rep's dealers.

Reads ERPNext Sales Invoices (submitted, outstanding > 0) for customers assigned to
the rep, grouped by customer. Used to drive "Payment Collection" field visits.
"""

import frappe
from frappe.utils import flt, getdate, today

from crm_app.api import get_current_employee, is_sales_manager


def _exists(dt):
	return bool(frappe.db.exists("DocType", dt))


@frappe.whitelist()
def get_my_collections(scope="mine"):
	"""Outstanding amount per dealer for the session rep's assigned customers."""
	employee = get_current_employee()
	if not _exists("Sales Invoice"):
		return {"total": 0.0, "overdue": 0.0, "customers": []}

	cust_filter = {} if (scope == "team" and is_sales_manager()) else {"custom_assigned_sales_person": employee}
	customers = frappe.get_all("Customer", filters=cust_filter, fields=["name", "customer_name"])
	if not customers:
		return {"total": 0.0, "overdue": 0.0, "customers": []}

	by_name = {c.name: c.customer_name for c in customers}
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={
			"customer": ["in", list(by_name.keys())],
			"docstatus": 1,
			"outstanding_amount": [">", 0],
		},
		fields=["name", "customer", "outstanding_amount", "due_date"],
		limit=5000,
	)

	agg = {}
	td = getdate(today())
	total = 0.0
	overdue_total = 0.0
	for inv in invoices:
		amt = flt(inv.outstanding_amount)
		total += amt
		is_overdue = inv.due_date and getdate(inv.due_date) < td
		if is_overdue:
			overdue_total += amt
		row = agg.setdefault(
			inv.customer,
			{
				"customer": inv.customer,
				"customer_name": by_name.get(inv.customer, inv.customer),
				"outstanding": 0.0,
				"overdue": 0.0,
				"invoices": 0,
				"oldest_due": None,
			},
		)
		row["outstanding"] += amt
		row["invoices"] += 1
		if is_overdue:
			row["overdue"] += amt
		if inv.due_date and (row["oldest_due"] is None or getdate(inv.due_date) < getdate(row["oldest_due"])):
			row["oldest_due"] = str(inv.due_date)

	rows = sorted(agg.values(), key=lambda r: r["outstanding"], reverse=True)
	for r in rows:
		r["outstanding"] = flt(r["outstanding"], 2)
		r["overdue"] = flt(r["overdue"], 2)
	return {"total": flt(total, 2), "overdue": flt(overdue_total, 2), "customers": rows}
