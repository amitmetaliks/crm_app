"""PJP — permanent journey plan, and whether it is actually being followed.

A beat plan answers "who do I see today". A PJP answers the harder question: "which
dealers does this rep owe a visit, how often, and is he keeping to it?" It is the
difference between a rep choosing his day and the company deciding coverage.

Model: a repeating cycle (weekly / fortnightly / monthly) of *dealer → week of cycle →
weekday*. The cycle position is computed from ``cycle_start_date``, so the rotation
holds indefinitely without anyone regenerating anything.

Today's beat is *derived* from the PJP rather than typed again — ``generate_beat``
creates (or tops up) the CRM Beat Plan for a date. It never deletes stops a rep added
himself: the plan is a floor, not a cage.

Coverage is measured honestly — planned stops that turned into a real visit, vs those
that did not.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, today

from crm_app.api import get_current_employee, is_sales_manager

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _active_pjp(employee):
	name = frappe.db.get_value(
		"CRM PJP", {"sales_person": employee, "status": "Active"}, "name", order_by="modified desc"
	)
	return frappe.get_doc("CRM PJP", name) if name else None


def _cycle_week(pjp, day):
	"""Which week of the rotation `day` falls in (1-based)."""
	weeks = int(pjp.cycle_weeks or 1)
	if weeks <= 1:
		return 1
	start = getdate(pjp.cycle_start_date)
	delta_weeks = ((getdate(day) - start).days) // 7
	return (delta_weeks % weeks) + 1


def _due_entries(pjp, day):
	"""PJP stops due on `day`."""
	wd = WEEKDAYS[getdate(day).weekday()]
	wk = _cycle_week(pjp, day)
	return [e for e in pjp.entries if e.weekday == wd and int(e.week_no or 1) == wk]


@frappe.whitelist()
def get_my_pjp() -> dict:
	"""The rep's plan, plus what it means for today."""
	employee = get_current_employee()
	pjp = _active_pjp(employee)
	if not pjp:
		return {"exists": False, "entries": [], "today": []}
	day = getdate()
	due = _due_entries(pjp, day)
	return {
		"exists": True,
		"name": pjp.name,
		"title": pjp.title,
		"cycle_weeks": int(pjp.cycle_weeks or 1),
		"cycle_week_now": _cycle_week(pjp, day),
		"total_stops": len(pjp.entries),
		"entries": [
			{
				"customer": e.customer,
				"customer_name": e.customer_name or e.customer,
				"weekday": e.weekday,
				"week_no": e.week_no,
				"beat_type": e.beat_type,
				"area": e.area,
			}
			for e in pjp.entries
		],
		"today": [{"customer": e.customer, "customer_name": e.customer_name or e.customer, "beat_type": e.beat_type} for e in due],
	}


@frappe.whitelist()
def generate_beat(plan_date=None, employee=None) -> dict:
	"""Create/top-up the beat plan for a date from the PJP.

	Additive on purpose: stops the rep added by hand survive, because the PJP is the
	company's floor for coverage, not a replacement for his judgement on the day.
	"""
	me = get_current_employee()
	employee = employee if (employee and is_sales_manager()) else me
	day = getdate(plan_date) if plan_date else getdate()

	pjp = _active_pjp(employee)
	if not pjp:
		return {"created": 0, "reason": "no active PJP"}
	due = _due_entries(pjp, day)
	if not due:
		return {"created": 0, "reason": "nothing due on this day"}

	name = frappe.db.get_value("CRM Beat Plan", {"sales_person": employee, "plan_date": day}, "name")
	if name:
		doc = frappe.get_doc("CRM Beat Plan", name)
	else:
		doc = frappe.new_doc("CRM Beat Plan")
		doc.sales_person = employee
		doc.plan_date = day
		doc.title = pjp.title
		doc.status = "Active"
		# beat_type lives on the plan, not the stop — a day is a primary or a secondary
		# beat. Take the majority of what is due rather than inventing a per-stop field.
		doc.beat_type = _dominant_type(due)
		doc.territory = next((e.area for e in due if e.area), None)

	added = _append_stops(doc, due)
	if added or not name:
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	return {"created": added, "beat_plan": doc.name, "due": len(due), "date": str(day)}


def _dominant_type(entries):
	"""Primary unless the day is mostly secondary stops."""
	sec = sum(1 for e in entries if (e.beat_type or "Primary") == "Secondary")
	return "Secondary" if sec > len(entries) / 2 else "Primary"


def _append_stops(doc, due):
	"""Add PJP stops the plan does not already carry. Returns how many were added."""
	existing = {e.customer for e in doc.entries if e.customer}
	added = 0
	for e in due:
		if e.customer in existing:
			continue
		doc.append(
			"entries",
			{
				"party_type": "Customer",
				"customer": e.customer,
				"party_name": e.customer_name or e.customer,
				"area": e.area,
			},
		)
		added += 1
	return added


@frappe.whitelist()
def get_coverage(from_date=None, to_date=None, employee=None) -> dict:
	"""Did the planned stops actually get visited?

	Counts a stop as covered when a CRM Visit exists for that dealer on that date —
	the visit itself, not a tick on the beat plan, because ticking is free.
	"""
	me = get_current_employee()
	employee = employee if (employee and is_sales_manager()) else me
	to_d = getdate(to_date) if to_date else getdate()
	frm_d = getdate(from_date) if from_date else add_days(to_d, -27)

	pjp = _active_pjp(employee)
	if not pjp:
		return {"exists": False, "planned": 0, "covered": 0, "pct": 0, "missed": []}

	planned, covered, missed = 0, 0, []
	d = frm_d
	while d <= to_d:
		for e in _due_entries(pjp, d):
			planned += 1
			hit = frappe.db.exists(
				"CRM Visit",
				{
					"sales_person": employee,
					"customer": e.customer,
					"visit_date": d,
					"visit_status": ["in", ["Completed", "In Progress"]],
				},
			)
			if hit:
				covered += 1
			elif d < getdate():  # today is still in play — do not call it missed yet
				missed.append(
					{"customer": e.customer, "customer_name": e.customer_name or e.customer, "date": str(d)}
				)
		d = add_days(d, 1)

	return {
		"exists": True,
		"from_date": str(frm_d),
		"to_date": str(to_d),
		"planned": planned,
		"covered": covered,
		"pct": flt(covered / planned * 100, 1) if planned else 0.0,
		"missed": missed[:50],
		"missed_count": len(missed),
	}


@frappe.whitelist()
def upsert_pjp(sales_person, title, cycle_weeks, cycle_start_date, entries, name=None) -> dict:
	"""Managers set a rep's journey plan."""
	get_current_employee()
	if not is_sales_manager():
		frappe.throw(_("Only sales managers can set a journey plan."), frappe.PermissionError)
	if isinstance(entries, str):
		entries = frappe.parse_json(entries)

	doc = frappe.get_doc("CRM PJP", name) if name else frappe.new_doc("CRM PJP")
	doc.sales_person = sales_person
	doc.title = title
	doc.cycle_weeks = str(cycle_weeks or 1)
	doc.cycle_start_date = getdate(cycle_start_date)
	doc.status = "Active"
	doc.set("entries", [])
	for e in entries or []:
		if not e.get("customer") or not e.get("weekday"):
			continue
		doc.append(
			"entries",
			{
				"customer": e["customer"],
				"weekday": e["weekday"],
				"week_no": int(e.get("week_no") or 1),
				"beat_type": e.get("beat_type") or "Primary",
				"area": e.get("area"),
			},
		)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "stops": len(doc.entries)}


def auto_generate_daily_beats():
	"""Scheduler: build today's beat for every rep with an active PJP.

	Failures are per-rep and swallowed: one rep's bad plan must not stop the rest of the
	sales force getting their day.
	"""
	day = getdate(today())
	made = 0
	for name in frappe.get_all("CRM PJP", filters={"status": "Active"}, pluck="sales_person"):
		try:
			res = generate_beat_for(name, day)
			made += res.get("created", 0)
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"PJP beat generation failed for {name}")
	return {"stops_added": made}


def generate_beat_for(employee, day):
	"""Internal (scheduler) variant: no session, so it takes the employee explicitly."""
	pjp = _active_pjp(employee)
	if not pjp:
		return {"created": 0}
	due = _due_entries(pjp, day)
	if not due:
		return {"created": 0}
	name = frappe.db.get_value("CRM Beat Plan", {"sales_person": employee, "plan_date": day}, "name")
	if name:
		doc = frappe.get_doc("CRM Beat Plan", name)
	else:
		doc = frappe.new_doc("CRM Beat Plan")
		doc.sales_person = employee
		doc.plan_date = day
		doc.title = pjp.title
		doc.status = "Active"
		doc.beat_type = _dominant_type(due)
		doc.territory = next((e.area for e in due if e.area), None)
	added = _append_stops(doc, due)
	if added or not name:
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	return {"created": added}
