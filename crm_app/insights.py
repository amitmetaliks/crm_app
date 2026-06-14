"""Smart insights — churn-risk dealers + sales forecast.

Rule-based / statistical (computed from CRM Visits + ERPNext Sales Orders) — not an
LLM. Honest, explainable, and free. Session-hardened.
"""

import frappe
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, today

from crm_app.api import get_current_employee, is_sales_manager


def _assigned(emp, scope):
	flt_ = {} if (scope == "team" and is_sales_manager()) else {"custom_assigned_sales_person": emp}
	return frappe.get_all("Customer", filters=flt_, fields=["name", "customer_name"], limit=5000)


@frappe.whitelist()
def churn_risk(days=30, scope="mine"):
	"""Assigned dealers with no visit/order in the last <days> — ranked by inactivity."""
	emp = get_current_employee()
	days = int(days)
	cutoff = getdate(add_days(today(), -days))
	has_so = frappe.db.exists("DocType", "Sales Order")
	out = []
	for c in _assigned(emp, scope):
		last_visit = frappe.db.get_value(
			"CRM Visit",
			{"customer": c.name, "visit_status": ["in", ["Completed", "In Progress"]]},
			"visit_date",
			order_by="visit_date desc",
		)
		last_order = None
		if has_so:
			last_order = frappe.db.get_value(
				"Sales Order", {"customer": c.name, "docstatus": ["<", 2]}, "transaction_date", order_by="transaction_date desc"
			)
		dates = [getdate(d) for d in (last_visit, last_order) if d]
		last_activity = max(dates) if dates else None
		if last_activity is None or last_activity < cutoff:
			days_since = (getdate(today()) - last_activity).days if last_activity else None
			out.append(
				{
					"customer": c.name,
					"customer_name": c.customer_name,
					"last_activity": str(last_activity) if last_activity else None,
					"days_since": days_since,
				}
			)
	out.sort(key=lambda x: (x["days_since"] is not None, -(x["days_since"] or 10 ** 6)))
	return out[:50]


@frappe.whitelist()
def sales_forecast(months=4, scope="mine"):
	"""Monthly Sales Order totals for the last <months> + next-month forecast (avg of last 3)."""
	emp = get_current_employee()
	months = int(months)
	if not frappe.db.exists("DocType", "Sales Order"):
		return {"history": [], "forecast": 0, "available": False}
	custs = [c.name for c in _assigned(emp, scope)]
	if not custs:
		return {"history": [], "forecast": 0, "available": True}

	hist = []
	base = getdate(today())
	for i in range(months - 1, -1, -1):
		mstart = get_first_day(add_months(base, -i))
		mend = get_last_day(mstart)
		rows = frappe.get_all(
			"Sales Order",
			filters={"customer": ["in", custs], "transaction_date": ["between", [str(mstart), str(mend)]], "docstatus": ["<", 2]},
			fields=["base_net_total"],
			limit=10000,
		)
		hist.append({"label": mstart.strftime("%b"), "value": flt(sum(flt(r.base_net_total) for r in rows), 2)})

	vals = [h["value"] for h in hist]
	last3 = vals[-3:] if vals else []
	forecast = flt(sum(last3) / len(last3), 2) if last3 else 0
	return {"history": hist, "forecast": forecast, "available": True}
