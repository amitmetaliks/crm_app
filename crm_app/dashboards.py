"""Manager / leadership dashboards — team coverage, leaderboard, recent activity.

Gated on is_sales_manager(); reps use their own dashboard (field_visit/targets).
"""

import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, today

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
