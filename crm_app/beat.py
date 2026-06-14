"""Beat / route planning — the dealers a rep plans to visit on a given day.

Visited status is derived live: an entry counts as visited when a CRM Visit for
that customer by this rep exists on the plan date. Session-hardened like the rest
of crm_app (employee from session; ignore_permissions writes on own beats).
"""

import json

import frappe
from frappe import _
from frappe.utils import today

from crm_app.api import get_current_employee, is_sales_manager


def _parse(v):
	if v is None or v == "":
		return []
	if isinstance(v, list):
		return v
	try:
		return json.loads(v)
	except (ValueError, TypeError):
		return []


def _require_access(name, employee):
	owner = frappe.db.get_value("CRM Beat Plan", name, "sales_person")
	if not owner:
		frappe.throw(_("Beat plan not found."), frappe.DoesNotExistError)
	if owner != employee and not is_sales_manager():
		frappe.throw(_("You do not have access to this beat plan."), frappe.PermissionError)


@frappe.whitelist()
def save_beat(name=None, plan_date=None, title=None, entries=None, status="Active", beat_type="Primary", territory=None, week_of=None):
	"""Create or replace a beat plan's stops for the session rep."""
	employee = get_current_employee()
	if name:
		_require_access(name, employee)
		doc = frappe.get_doc("CRM Beat Plan", name)
	else:
		doc = frappe.new_doc("CRM Beat Plan")
		doc.sales_person = employee

	doc.plan_date = plan_date or today()
	doc.title = title
	doc.beat_type = beat_type or "Primary"
	doc.territory = territory
	doc.week_of = week_of or None
	doc.status = status or "Active"
	doc.entries = []
	for row in _parse(entries):
		doc.append(
			"entries",
			{
				"party_type": row.get("party_type") or "Customer",
				"customer": row.get("customer") if (row.get("party_type") or "Customer") == "Customer" else None,
				"crm_lead": row.get("crm_lead") if row.get("party_type") == "CRM Lead" else None,
				"party_name": row.get("party_name"),
				"area": row.get("area"),
				"planned_time": row.get("planned_time"),
				"notes": row.get("notes"),
			},
		)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}


def _mark_visited(doc):
	"""Annotate each entry with whether a matching visit happened on plan_date."""
	planned = 0
	visited = 0
	rows = []
	for e in doc.entries:
		planned += 1
		vname = None
		if e.customer:
			vname = frappe.db.get_value(
				"CRM Visit",
				{
					"sales_person": doc.sales_person,
					"customer": e.customer,
					"visit_date": doc.plan_date,
					"visit_status": ["in", ["In Progress", "Completed"]],
				},
				"name",
			)
		is_visited = bool(vname)
		if is_visited:
			visited += 1
		rows.append(
			{
				"party_type": e.party_type,
				"customer": e.customer,
				"crm_lead": e.crm_lead,
				"party_name": e.party_name or e.customer,
				"area": e.area,
				"planned_time": e.planned_time,
				"visited": is_visited,
				"visit": vname,
				"notes": e.notes,
			}
		)
	return rows, planned, visited


@frappe.whitelist()
def get_my_beat(plan_date=None):
	"""The session rep's beat for a date (defaults to today) with live coverage."""
	employee = get_current_employee()
	plan_date = plan_date or today()
	name = frappe.db.get_value(
		"CRM Beat Plan", {"sales_person": employee, "plan_date": plan_date}, "name"
	)
	if not name:
		return {"exists": False, "plan_date": plan_date, "entries": [], "planned": 0, "visited": 0}
	doc = frappe.get_doc("CRM Beat Plan", name)
	rows, planned, visited = _mark_visited(doc)
	return {
		"exists": True,
		"name": name,
		"plan_date": plan_date,
		"title": doc.title,
		"status": doc.status,
		"beat_type": doc.beat_type,
		"territory": doc.territory,
		"entries": rows,
		"planned": planned,
		"visited": visited,
	}


@frappe.whitelist()
def get_beats(scope="mine", limit=60):
	"""List recent beat plans (mine, or whole team for managers)."""
	employee = get_current_employee()
	filters = {} if (scope == "team" and is_sales_manager()) else {"sales_person": employee}
	beats = frappe.get_all(
		"CRM Beat Plan",
		filters=filters,
		fields=["name", "plan_date", "title", "status", "sales_person_name"],
		order_by="plan_date desc",
		limit=int(limit),
	)
	# attach coverage counts
	for b in beats:
		doc = frappe.get_doc("CRM Beat Plan", b.name)
		_, planned, visited = _mark_visited(doc)
		b["planned"] = planned
		b["visited"] = visited
	return beats
