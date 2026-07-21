"""Smart insights — churn-risk dealers + sales forecast.

Rule-based / statistical (computed from CRM Visits + ERPNext Sales Orders) — not an
LLM. Honest, explainable, and free. Session-hardened.
"""

import frappe
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, today

from crm_app.api import get_current_employee, is_sales_manager


def _assigned(emp, scope):
	if scope == "team" and is_sales_manager():
		return frappe.get_all("Customer", fields=["name", "customer_name"], limit=20000)
	from crm_app.sales_attr import rep_customers

	names = rep_customers(emp)
	if not names:
		return []
	return frappe.get_all("Customer", filters={"name": ["in", list(names)]}, fields=["name", "customer_name"], limit=20000)


@frappe.whitelist()
def churn_risk(days=30, scope="mine"):
	"""Assigned dealers with no visit or purchase in the last <days>, worst first.

	"Purchase" means the SAP register, not ERPNext Sales Orders. That distinction is the
	whole feature: their site has ~47 Sales Orders against 11,500 SAP invoice lines, so
	reading ERPNext made almost every dealer look dormant and the list meaningless.
	"""
	emp = get_current_employee()
	from crm_app import sap_sales

	days = int(days)
	cutoff = getdate(add_days(today(), -days))
	dealers = _assigned(emp, scope)
	if not dealers:
		return []
	names = [c.name for c in dealers]

	# Two batched lookups instead of two queries per dealer (40,000 round trips for a
	# manager's book).
	last_orders = sap_sales.last_invoice_dates(names)
	last_visits = {}
	for v in frappe.get_all(
		"CRM Visit",
		filters={"customer": ["in", names], "visit_status": ["in", ["Completed", "In Progress"]]},
		fields=["customer", "visit_date"],
		order_by="visit_date asc",
		limit=50000,
	):
		if v.customer:
			last_visits[v.customer] = v.visit_date  # ascending, so the last write wins

	# Fall back to ERPNext Sales Orders only where SAP knows nothing about the dealer.
	so_dates = {}
	if frappe.db.exists("DocType", "Sales Order"):
		missing = [n for n in names if n not in last_orders]
		if missing:
			for so in frappe.get_all(
				"Sales Order",
				filters={"customer": ["in", missing], "docstatus": ["<", 2]},
				fields=["customer", "transaction_date"],
				order_by="transaction_date asc",
				limit=50000,
			):
				so_dates[so.customer] = so.transaction_date

	out = []
	todayd = getdate(today())
	for c in dealers:
		dates = [
			getdate(d)
			for d in (last_visits.get(c.name), last_orders.get(c.name), so_dates.get(c.name))
			if d
		]
		last_activity = max(dates) if dates else None
		if last_activity is None or last_activity < cutoff:
			out.append(
				{
					"customer": c.name,
					"customer_name": c.customer_name,
					"last_activity": str(last_activity) if last_activity else None,
					"days_since": (todayd - last_activity).days if last_activity else None,
				}
			)

	# CHURN means a dealer who used to buy and stopped. Dealers with no recorded activity
	# at all are a different thing — an unmapped SAP code, a prospect never converted, a
	# dead record — and there are ~1,800 of them here. The previous sort put those FIRST,
	# so the list was 50 blank rows and the dealers actually slipping never appeared.
	# Known-quiet first, longest silence at the top; the never-active tail follows.
	known = [r for r in out if r["days_since"] is not None]
	never = [r for r in out if r["days_since"] is None]
	known.sort(key=lambda x: -x["days_since"])
	for r in never:
		r["no_history"] = True
	return (known + never)[:50]


@frappe.whitelist()
def sales_forecast(months=4, scope="mine"):
	"""Invoiced per month for the last <months>, plus next month (average of the last 3).

	Reads the SAP register where present. Forecasting from ERPNext Sales Orders on their
	site meant projecting next month off ~₹22 lakh of orders while ₹513 crore of real
	invoicing sat in the table next door.
	"""
	emp = get_current_employee()
	from crm_app import sap_sales

	months = int(months)
	custs = [c.name for c in _assigned(emp, scope)]
	if not custs:
		return {"history": [], "forecast": 0, "available": True, "source": None}

	if sap_sales.available():
		hist = sap_sales.monthly_totals(custs, months)
		source = "sap"
	elif frappe.db.exists("DocType", "Sales Order"):
		hist = []
		base = getdate(today())
		for i in range(months - 1, -1, -1):
			mstart = get_first_day(add_months(base, -i))
			mend = get_last_day(mstart)
			rows = frappe.get_all(
				"Sales Order",
				filters={
					"customer": ["in", custs],
					"transaction_date": ["between", [str(mstart), str(mend)]],
					"docstatus": ["<", 2],
				},
				fields=["base_net_total"],
				limit=10000,
			)
			hist.append(
				{"label": mstart.strftime("%b"), "value": flt(sum(flt(r.base_net_total) for r in rows), 2)}
			)
		source = "erpnext"
	else:
		return {"history": [], "forecast": 0, "available": False, "source": None}

	# The last bucket is the current, still-accumulating month (the SAP feed also ends
	# mid-month), so averaging it into the forecast biases next month LOW. Keep it visible in
	# history but flag it partial, and forecast off the completed months only.
	if hist:
		hist[-1]["partial"] = True
	vals = [h["value"] for h in hist]
	complete = vals[:-1] if len(vals) > 1 else vals
	last3 = complete[-3:] if complete else []
	forecast = flt(sum(last3) / len(last3), 2) if last3 else 0
	return {"history": hist, "forecast": forecast, "available": True, "source": source}
