"""SFA depth — home summary, KRA scorecard, activity timeline, product mix, and
productivity series. Powers the rich dashboard that matches a field-sales app.

All session-hardened; managers may pass an employee for timeline/scope where noted.
Productivity model: a Completed visit with >=1 order line = Productive; Completed with
none = Zero-Order; Cancelled/Missed = Skipped. Strike rate = Productive / Completed.
"""

import frappe
from frappe.utils import flt, get_first_day, getdate, add_days, today

from crm_app.api import get_current_employee, is_sales_manager


def _hrms(dt):
	return bool(frappe.db.exists("DocType", dt))


def _visits(emp, frm, to):
	return frappe.get_all(
		"CRM Visit",
		filters={"sales_person": emp, "visit_date": ["between", [frm, to]]},
		fields=["name", "visit_status", "visit_date", "party_display", "check_in_time"],
		order_by="check_in_time asc",
	)


def _names_with_orders(names):
	if not names:
		return set()
	rows = frappe.get_all("CRM Visit Order Item", filters={"parent": ["in", names]}, fields=["parent"])
	return {r.parent for r in rows}


def _order_agg(names):
	if not names:
		return {"orders": 0, "value": 0.0, "qty": 0.0, "avg": 0.0}
	rows = frappe.get_all(
		"CRM Visit Order Item", filters={"parent": ["in", names]}, fields=["expected_value", "quantity_mt"]
	)
	value = flt(sum(flt(r.expected_value) for r in rows), 2)
	return {
		"orders": len(rows),
		"value": value,
		"qty": flt(sum(flt(r.quantity_mt) for r in rows), 3),
		"avg": flt(value / len(rows), 2) if rows else 0.0,
	}


def _achievement(emp, frm, to):
	from crm_app.sales_attr import rep_sales

	return rep_sales(emp, frm, to)


def _attendance_state(emp, day):
	state = {"checked_in": False, "first_in": None, "last_out": None}
	if not _hrms("Employee Checkin"):
		return state
	logs = frappe.get_all(
		"Employee Checkin",
		filters={"employee": emp, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
		fields=["time", "log_type"],
		order_by="time asc",
	)
	if logs:
		state["first_in"] = next((x.time for x in logs if x.log_type == "IN"), None)
		state["last_out"] = next((x.time for x in reversed(logs) if x.log_type == "OUT"), None)
		state["checked_in"] = logs[-1].log_type == "IN"
	return state


def _beat_today(emp, day):
	name = frappe.db.get_value("CRM Beat Plan", {"sales_person": emp, "plan_date": day}, "name")
	if not name:
		return {"planned": 0, "visited": 0}
	entries = frappe.get_all("CRM Beat Plan Entry", filters={"parent": name}, fields=["customer"])
	planned = visited = 0
	for e in entries:
		if not e.customer:
			continue
		planned += 1
		if frappe.db.exists(
			"CRM Visit",
			{"sales_person": emp, "customer": e.customer, "visit_date": day,
			 "visit_status": ["in", ["In Progress", "Completed"]]},
		):
			visited += 1
	return {"planned": planned, "visited": visited}


def _expense(emp, day, mstart):
	out = {"today": 0.0, "month": 0.0}
	if not _hrms("Expense Claim"):
		return out
	rows = frappe.get_all(
		"Expense Claim",
		filters={"employee": emp, "posting_date": ["between", [mstart, day]], "docstatus": ["<", 2]},
		fields=["posting_date", "total_claimed_amount"],
		limit=2000,
	)
	out["month"] = flt(sum(flt(r.total_claimed_amount) for r in rows), 2)
	out["today"] = flt(sum(flt(r.total_claimed_amount) for r in rows if str(r.posting_date) == str(day)), 2)
	return out


def _new_retailers(emp, mstart, day):
	return frappe.db.count(
		"Customer",
		{"custom_assigned_sales_person": emp, "creation": ["between", [f"{mstart} 00:00:00", f"{day} 23:59:59"]]},
	)


@frappe.whitelist()
def get_home_summary():
	"""Everything the home dashboard needs for the logged-in rep, for today + this month."""
	emp = get_current_employee()
	day = today()
	mstart = str(get_first_day(getdate(day)))

	visits = _visits(emp, day, day)
	names = [v.name for v in visits]
	completed = [v for v in visits if v.visit_status == "Completed"]
	completed_names = [v.name for v in completed]
	with_orders = _names_with_orders(completed_names)
	productive = len([n for n in completed_names if n in with_orders])
	zero_order = len(completed_names) - productive
	in_progress = len([v for v in visits if v.visit_status == "In Progress"])
	skipped = len([v for v in visits if v.visit_status in ("Cancelled", "Missed")])
	strike = round(productive / len(completed_names) * 100, 1) if completed_names else 0

	ach = _achievement(emp, mstart, day)
	tgt = frappe.db.get_value(
		"CRM Sales Target",
		{"sales_person": emp, "from_date": ["<=", day], "to_date": [">=", day]},
		["target_amount", "target_qty_mt"],
		as_dict=True,
	) or {}

	return {
		"date": day,
		"employee_name": frappe.db.get_value("Employee", emp, "employee_name"),
		"attendance": _attendance_state(emp, day),
		"beat": _beat_today(emp, day),
		"visits": {
			"total": len(visits),
			"completed": len(completed),
			"in_progress": in_progress,
			"productive": productive,
			"zero_order": zero_order,
			"skipped": skipped,
			"strike_rate": strike,
		},
		"order_summary": _order_agg(names),
		"sales_target": {
			"target": flt(tgt.get("target_amount")) if tgt else 0,
			"achieved": ach["amount"],
			"pct": round(ach["amount"] / tgt["target_amount"] * 100, 1) if tgt.get("target_amount") else 0,
			"orders": ach["orders"],
		},
		"expense": _expense(emp, day, mstart),
		"new_retailers": _new_retailers(emp, mstart, day),
	}


@frappe.whitelist()
def get_kra():
	"""KRA scorecard for the month: 5 KRAs with achieved/target/%."""
	emp = get_current_employee()
	day = today()
	mstart = str(get_first_day(getdate(day)))

	tgt = frappe.db.get_value(
		"CRM Sales Target",
		{"sales_person": emp, "from_date": ["<=", day], "to_date": [">=", day]},
		["target_amount", "target_visits", "target_productive_calls", "target_new_customers", "collection_ratio_target"],
		as_dict=True,
	) or {}

	visits = _visits(emp, mstart, day)
	completed = [v for v in visits if v.visit_status == "Completed"]
	completed_names = [v.name for v in completed]
	with_orders = _names_with_orders(completed_names)
	productive = len([n for n in completed_names if n in with_orders])
	ach = _achievement(emp, mstart, day)

	# Collection ratio: paid vs billed (this month, rep's customers)
	coll_ratio = 0.0
	if _hrms("Sales Invoice"):
		custs = frappe.get_all("Customer", filters={"custom_assigned_sales_person": emp}, pluck="name")
		if custs:
			inv = frappe.get_all(
				"Sales Invoice",
				filters={"customer": ["in", custs], "posting_date": ["between", [mstart, day]], "docstatus": 1},
				fields=["grand_total", "outstanding_amount"],
				limit=5000,
			)
			billed = sum(flt(i.grand_total) for i in inv)
			paid = sum(flt(i.grand_total) - flt(i.outstanding_amount) for i in inv)
			coll_ratio = round(paid / billed * 100, 1) if billed else 0.0

	def kra(label, achieved, target, unit=""):
		t = flt(target)
		return {
			"label": label,
			"achieved": achieved,
			"target": t,
			"unit": unit,
			"pct": round(flt(achieved) / t * 100, 1) if t else 0,
			"has_target": bool(t),
		}

	return [
		kra("Sales Achievement", ach["amount"], tgt.get("target_amount"), "₹"),
		kra("Visit Completion", len(completed), tgt.get("target_visits")),
		kra("Productive Calls", productive, tgt.get("target_productive_calls")),
		kra("Collection Ratio", coll_ratio, tgt.get("collection_ratio_target") or 95, "%"),
		kra("New Customer Acquisition", _new_retailers(emp, mstart, day), tgt.get("target_new_customers")),
	]


@frappe.whitelist()
def get_activity_timeline(date=None, employee=None):
	"""Chronological day feed: check-ins + visits (+orders) for a rep."""
	me = get_current_employee()
	day = date or today()
	emp = me
	if employee and is_sales_manager():
		emp = employee

	items = []
	if _hrms("Employee Checkin"):
		for c in frappe.get_all(
			"Employee Checkin",
			filters={"employee": emp, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
			fields=["time", "log_type"],
			order_by="time asc",
		):
			items.append({"time": str(c.time), "type": "attendance", "title": f"Checked {c.log_type}", "subtitle": ""})

	for v in frappe.get_all(
		"CRM Visit",
		filters={"sales_person": emp, "visit_date": day},
		fields=["name", "party_display", "visit_purpose", "visit_status", "check_in_time", "check_out_time"],
		order_by="check_in_time asc",
	):
		items.append(
			{
				"time": str(v.check_in_time or f"{day} 00:00:00"),
				"type": "visit",
				"title": v.party_display or v.name,
				"subtitle": f"{v.visit_purpose} · {v.visit_status}",
				"ref": v.name,
			}
		)

	items.sort(key=lambda x: x["time"])
	return {"date": day, "employee": emp, "items": items}


@frappe.whitelist()
def get_top_products(scope="mine"):
	"""Top-selling products this month by captured order value (donut data)."""
	emp = get_current_employee()
	day = today()
	mstart = str(get_first_day(getdate(day)))

	vfilters = {"visit_date": ["between", [mstart, day]]}
	if not (scope == "team" and is_sales_manager()):
		vfilters["sales_person"] = emp
	vnames = frappe.get_all("CRM Visit", filters=vfilters, pluck="name", limit=20000)
	if not vnames:
		return {"items": [], "total": 0}
	rows = frappe.get_all(
		"CRM Visit Order Item",
		filters={"parent": ["in", vnames]},
		fields=["grade", "product", "expected_value"],
		limit=50000,
	)
	agg = {}
	for r in rows:
		key = r.product or r.grade or "Other"
		agg[key] = agg.get(key, 0) + flt(r.expected_value)
	total = sum(agg.values())
	ordered = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
	top = ordered[:5]
	others = sum(v for _, v in ordered[5:])
	items = [{"name": k, "value": flt(v, 2), "pct": round(v / total * 100, 1) if total else 0} for k, v in top]
	if others:
		items.append({"name": "Others", "value": flt(others, 2), "pct": round(others / total * 100, 1) if total else 0})
	return {"items": items, "total": flt(total, 2)}


@frappe.whitelist()
def get_productivity_series():
	"""Last 7 days completed-visit counts (for the daily/weekly chart)."""
	emp = get_current_employee()
	day = getdate(today())
	series = []
	for i in range(6, -1, -1):
		d = add_days(day, -i)
		cnt = frappe.db.count("CRM Visit", {"sales_person": emp, "visit_date": str(d), "visit_status": "Completed"})
		series.append({"date": str(d), "label": getdate(d).strftime("%a"), "achieved": cnt})
	return {"series": series}
