"""Scheduled reminders + the shared notify helper (in-app Notification Log + web push).

Registered as daily scheduler_events in hooks.py. All notifications are best-effort
and never raise (so a bad push can't break the scheduler).
"""

import frappe
from frappe.utils import add_days, strip_html_tags, today


def _user_for_employee(employee: str) -> str | None:
	return frappe.db.get_value("Employee", employee, "user_id") if employee else None


def notify(user: str, subject: str, body: str = "", route: str = "/amit-crm"):
	"""Create an in-app Notification Log and send a web push. Safe to call anywhere."""
	if not user or user == "Guest":
		return
	try:
		n = frappe.new_doc("Notification Log")
		n.for_user = user
		n.subject = strip_html_tags(subject or "")
		n.email_content = strip_html_tags(body or subject or "")
		n.type = "Alert"
		n.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="crm_app notify (log) failed", message=frappe.get_traceback())
	try:
		from crm_app.push import send_push_to_user

		send_push_to_user(user, subject, body or "", route)
	except Exception:
		pass


def send_beat_reminders():
	"""Morning nudge: tell each rep how many stops are on today's beat."""
	day = today()
	for bp in frappe.get_all(
		"CRM Beat Plan",
		filters={"plan_date": day, "status": ["in", ["Active", "Draft"]]},
		fields=["name", "sales_person"],
	):
		count = frappe.db.count("CRM Beat Plan Entry", {"parent": bp.name})
		if not count:
			continue
		user = _user_for_employee(bp.sales_person)
		notify(user, f"Today's beat: {count} dealer(s) to visit", "Open your beat plan to get started.", "/amit-crm/beat")


def send_followup_reminders():
	"""Remind reps about visits whose next_visit_date is today."""
	day = today()
	for v in frappe.get_all(
		"CRM Visit",
		filters={"next_visit_date": day},
		fields=["name", "sales_person", "party_display", "next_action"],
	):
		user = _user_for_employee(v.sales_person)
		notify(
			user,
			f"Follow-up due: {v.party_display}",
			v.next_action or "You planned to follow up today.",
			f"/amit-crm/visit/{v.name}",
		)


def flag_missed_visits():
	"""Flag yesterday's planned-but-not-visited beat stops to the rep."""
	yday = add_days(today(), -1)
	for bp in frappe.get_all(
		"CRM Beat Plan", filters={"plan_date": yday}, fields=["name", "sales_person"]
	):
		entries = frappe.get_all(
			"CRM Beat Plan Entry", filters={"parent": bp.name}, fields=["customer", "party_name"]
		)
		missed = []
		for e in entries:
			if not e.customer:
				continue
			visited = frappe.db.exists(
				"CRM Visit",
				{
					"sales_person": bp.sales_person,
					"customer": e.customer,
					"visit_date": yday,
					"visit_status": ["in", ["In Progress", "Completed"]],
				},
			)
			if not visited:
				missed.append(e.party_name or e.customer)
		if missed:
			user = _user_for_employee(bp.sales_person)
			notify(
				user,
				f"{len(missed)} missed visit(s) yesterday",
				", ".join(missed[:5]),
				"/amit-crm/beat",
			)
