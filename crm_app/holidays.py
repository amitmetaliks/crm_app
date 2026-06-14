"""Holiday list for the logged-in employee."""

import frappe
from frappe.utils import getdate

from crm_app.api import get_current_employee


def _clean(text):
	from frappe.utils import strip_html_tags

	return strip_html_tags(text or "").strip()


@frappe.whitelist()
def get_holidays() -> dict:
	employee = get_current_employee()
	company = frappe.db.get_value("Employee", employee, "company")
	holiday_list = frappe.db.get_value("Employee", employee, "holiday_list") or (
		frappe.db.get_value("Company", company, "default_holiday_list") if company else None
	)
	if not holiday_list or not frappe.db.exists("DocType", "Holiday"):
		return {"holiday_list": None, "holidays": [], "upcoming": []}

	rows = frappe.get_all(
		"Holiday",
		filters={"parent": holiday_list},
		fields=["holiday_date", "description", "weekly_off"],
		order_by="holiday_date asc",
	)
	today = getdate()
	holidays = [
		{"date": str(r.holiday_date), "description": _clean(r.description), "weekly_off": bool(r.weekly_off)}
		for r in rows
	]
	upcoming = [h for h in holidays if getdate(h["date"]) >= today and not h["weekly_off"]][:10]
	return {"holiday_list": holiday_list, "holidays": holidays, "upcoming": upcoming}
