"""Manager / leadership dashboards — team coverage, leaderboard, recent activity.

Gated on is_sales_manager(); reps use their own dashboard (field_visit/targets).
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_first_day, today

from crm_app.api import get_current_employee, is_sales_manager


def _require_manager():
	get_current_employee()
	if not is_sales_manager():
		frappe.throw(_("This view is for sales managers."), frappe.PermissionError)


@frappe.whitelist()
def get_team_overview(date=None):
	"""Team-wide snapshot for managers: today's coverage, month leaderboard, recent visits."""
	_require_manager()
	day = date or today()
	month_start = str(get_first_day(getdate(day)))

	today_visits = frappe.get_all(
		"CRM Visit",
		filters={"visit_date": day},
		fields=["name", "sales_person", "sales_person_name", "visit_status", "party_display"],
		limit=2000,
	)
	per_rep = {}
	for v in today_visits:
		r = per_rep.setdefault(v.sales_person or "—", {"sales_person_name": v.sales_person_name or "—", "count": 0})
		r["count"] += 1
	coverage = sorted(per_rep.values(), key=lambda x: x["count"], reverse=True)

	month_visits = frappe.get_all(
		"CRM Visit",
		filters={"visit_date": ["between", [month_start, day]]},
		fields=["sales_person", "sales_person_name", "visit_status"],
		limit=20000,
	)
	board = {}
	for v in month_visits:
		b = board.setdefault(
			v.sales_person or "—",
			{"sales_person_name": v.sales_person_name or "—", "visits": 0, "completed": 0},
		)
		b["visits"] += 1
		if v.visit_status == "Completed":
			b["completed"] += 1
	leaderboard = sorted(board.values(), key=lambda x: x["completed"], reverse=True)[:10]

	recent = frappe.get_all(
		"CRM Visit",
		fields=["name", "sales_person_name", "party_display", "visit_purpose", "visit_status", "visit_date"],
		order_by="modified desc",
		limit=20,
	)

	return {
		"date": day,
		"today_total": len(today_visits),
		"coverage": coverage,
		"leaderboard": leaderboard,
		"recent": recent,
	}


@frappe.whitelist()
def get_analytics() -> dict:
	"""Leadership KPIs (this month): conversion, beat adherence, attendance, expense, AR."""
	_require_manager()
	day = today()
	mstart = str(get_first_day(getdate(day)))

	# Visits + conversion (completed visits with at least one order/inquiry line)
	completed = frappe.get_all(
		"CRM Visit",
		filters={"visit_date": ["between", [mstart, day]], "visit_status": "Completed"},
		fields=["name"],
		limit=50000,
	)
	completed_names = [v.name for v in completed]
	with_orders = 0
	if completed_names:
		parents = frappe.get_all(
			"CRM Visit Order Item",
			filters={"parenttype": "CRM Visit", "parent": ["in", completed_names]},
			fields=["parent"],
			limit=100000,
		)
		with_orders = len({p.parent for p in parents})
	conversion_pct = round(with_orders / len(completed_names) * 100, 1) if completed_names else 0

	# Beat adherence (this month)
	beats = frappe.get_all(
		"CRM Beat Plan", filters={"plan_date": ["between", [mstart, day]]}, fields=["name", "sales_person", "plan_date"]
	)
	planned = visited = 0
	for b in beats:
		entries = frappe.get_all("CRM Beat Plan Entry", filters={"parent": b.name}, fields=["customer"])
		for e in entries:
			if not e.customer:
				continue
			planned += 1
			if frappe.db.exists(
				"CRM Visit",
				{"sales_person": b.sales_person, "customer": e.customer, "visit_date": b.plan_date,
				 "visit_status": ["in", ["In Progress", "Completed"]]},
			):
				visited += 1
	adherence_pct = round(visited / planned * 100, 1) if planned else 0

	# Attendance today (distinct employees with an IN today) + expense pending
	attendance_today = expense_pending = expense_pending_amount = 0
	if frappe.db.exists("DocType", "Employee Checkin"):
		ins = frappe.get_all(
			"Employee Checkin",
			filters={"log_type": "IN", "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
			fields=["employee"],
			limit=50000,
		)
		attendance_today = len({i.employee for i in ins})
	if frappe.db.exists("DocType", "Expense Claim"):
		ec = frappe.get_all(
			"Expense Claim",
			filters={"approval_status": "Draft", "docstatus": ["<", 2]},
			fields=["grand_total"],
			limit=50000,
		)
		expense_pending = len(ec)
		expense_pending_amount = flt(sum(flt(x.grand_total) for x in ec), 2)

	# Accounts receivable (outstanding)
	ar_total = ar_overdue = 0.0
	if frappe.db.exists("DocType", "Sales Invoice"):
		row = frappe.db.sql(
			"select sum(outstanding_amount) from `tabSales Invoice` where docstatus=1 and outstanding_amount>0"
		)
		ar_total = flt(row[0][0] if row and row[0] else 0, 2)
		row2 = frappe.db.sql(
			"select sum(outstanding_amount) from `tabSales Invoice` where docstatus=1 and outstanding_amount>0 and due_date < %s",
			(day,),
		)
		ar_overdue = flt(row2[0][0] if row2 and row2[0] else 0, 2)

	return {
		"period": f"{mstart} to {day}",
		"visits_completed": len(completed_names),
		"conversion_pct": conversion_pct,
		"beat_planned": planned,
		"beat_visited": visited,
		"adherence_pct": adherence_pct,
		"attendance_today": attendance_today,
		"expense_pending": expense_pending,
		"expense_pending_amount": expense_pending_amount,
		"ar_total": ar_total,
		"ar_overdue": ar_overdue,
	}
