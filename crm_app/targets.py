"""Sales targets vs achievement.

Achievement is computed live from ERPNext Sales Orders for the dealers assigned to
the rep (Customer.custom_assigned_sales_person), within the target period. On a site
without Sales Orders yet, achievement is simply 0.
"""

import frappe
from frappe.utils import flt

from crm_app.api import get_current_employee, is_sales_manager


def _exists(dt):
	return bool(frappe.db.exists("DocType", dt))


def _achievement(employee, from_date, to_date):
	"""Sum of submitted/draft Sales Orders in [from,to] for the rep's dealers."""
	if not _exists("Sales Order"):
		return {"amount": 0.0, "qty_mt": 0.0, "orders": 0}
	customers = frappe.get_all(
		"Customer", filters={"custom_assigned_sales_person": employee}, pluck="name"
	)
	if not customers:
		return {"amount": 0.0, "qty_mt": 0.0, "orders": 0}
	rows = frappe.get_all(
		"Sales Order",
		filters={
			"customer": ["in", customers],
			"transaction_date": ["between", [from_date, to_date]],
			"docstatus": ["<", 2],
		},
		fields=["base_net_total", "total_qty"],
		limit=5000,
	)
	return {
		"amount": flt(sum(flt(r.base_net_total) for r in rows), 2),
		"qty_mt": flt(sum(flt(r.total_qty) for r in rows), 3),
		"orders": len(rows),
	}


@frappe.whitelist()
def get_my_targets(scope="mine"):
	"""Targets for the session rep (or whole team for managers) with live achievement."""
	employee = get_current_employee()
	filters = {} if (scope == "team" and is_sales_manager()) else {"sales_person": employee}
	targets = frappe.get_all(
		"CRM Sales Target",
		filters=filters,
		fields=[
			"name", "sales_person", "sales_person_name", "period_label",
			"from_date", "to_date", "target_amount", "target_qty_mt",
		],
		order_by="from_date desc",
		limit=60,
	)
	for t in targets:
		ach = _achievement(t.sales_person, t.from_date, t.to_date)
		t["achieved_amount"] = ach["amount"]
		t["achieved_qty_mt"] = ach["qty_mt"]
		t["order_count"] = ach["orders"]
		t["amount_pct"] = round(ach["amount"] / t.target_amount * 100, 1) if t.target_amount else 0
		t["qty_pct"] = round(ach["qty_mt"] / t.target_qty_mt * 100, 1) if t.target_qty_mt else 0
	return targets


@frappe.whitelist()
def upsert_target(sales_person, period_label, from_date, to_date, target_amount=0, target_qty_mt=0, name=None):
	"""Managers create/update targets for reps."""
	get_current_employee()
	if not is_sales_manager():
		frappe.throw("Only sales managers can set targets.", frappe.PermissionError)
	doc = frappe.get_doc("CRM Sales Target", name) if name else frappe.new_doc("CRM Sales Target")
	doc.sales_person = sales_person
	doc.period_label = period_label
	doc.from_date = from_date
	doc.to_date = to_date
	doc.target_amount = flt(target_amount)
	doc.target_qty_mt = flt(target_qty_mt)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}
