"""Rep 'Today's priorities' — a ranked, explainable next-best-action feed.

Answers "what should I do next?" from RELIABLE CRM data only, never invented scores:

  1. Collections   — dealers who owe money (SAP receivable balance), biggest first.
  2. Follow-ups    — a next action the rep PROMISED whose date has arrived
                     (CRM Visit.next_action + next_visit_date), not already handled today.
  3. Beat stops    — planned stops for today not yet visited.

Every item carries a plain-language reason and a deep link into the screen that acts on it.
Priority is the insertion order (money owed, then overdue follow-ups, then today's beat) — a
deliberate, explainable ordering, not a black-box score. Everything is scoped to the logged-in
rep's own dealers/visits, so nothing leaks across reps or territories.
"""

import frappe
from frappe.utils import add_days, flt, getdate, today

from crm_app.api import get_current_employee


def _inr(n):
	n = flt(n)
	if n >= 1e7:
		return f"{n / 1e7:.2f} Cr"
	if n >= 1e5:
		return f"{n / 1e5:.2f} L"
	return f"{n:,.0f}"


def _names(customers):
	"""{name: customer_name} for a set of Customers, in one query."""
	if not customers:
		return {}
	return {
		r.name: (r.customer_name or r.name)
		for r in frappe.get_all("Customer", filters={"name": ["in", list(customers)]}, fields=["name", "customer_name"])
	}


@frappe.whitelist()
def get_priorities(limit=8):
	"""Ranked next-best-actions for the logged-in rep."""
	emp = get_current_employee()
	day = getdate(today())
	limit = int(limit)
	items = []

	from crm_app.sales_attr import rep_customers

	mine = rep_customers(emp)

	# Dealers already visited today — used to suppress follow-up / beat noise for stops done.
	visited_today = set(
		frappe.get_all(
			"CRM Visit",
			filters={
				"sales_person": emp,
				"visit_date": day,
				"visit_status": ["in", ["In Progress", "Completed"]],
			},
			pluck="customer",
		)
	)

	# 1) Collections — biggest outstanding first (SAP receivables, positive balances only).
	from crm_app import sap_receivables

	if mine and sap_receivables.available():
		owed = sap_receivables.outstanding_for(mine)
		for r in sorted(owed.values(), key=lambda x: x["outstanding"], reverse=True)[:3]:
			items.append(
				{
					"type": "collection",
					"severity": "high" if r["outstanding"] >= 100000 else "medium",
					"title": r["customer_name"],
					"reason": f"Owes ₹{_inr(r['outstanding'])}",
					"cta": "Collect",
					"route": {"name": "Collect", "query": {"customer": r["customer"], "label": r["customer_name"]}},
				}
			)

	# 2) Follow-ups due — the rep promised a next action and the date has arrived (look back 30d
	#    so an old promise still surfaces). Latest promise per dealer, and skip dealers done today.
	fu = frappe.get_all(
		"CRM Visit",
		filters={
			"sales_person": emp,
			"next_visit_date": ["between", [add_days(day, -30), day]],
			"next_action": ["is", "set"],
			"customer": ["is", "set"],
		},
		fields=["customer", "next_action", "next_visit_date"],
		order_by="visit_date desc",
	)
	fu_seen = set()
	fu_rows = []
	for v in fu:
		if v.customer in fu_seen or v.customer in visited_today:
			continue
		fu_seen.add(v.customer)
		fu_rows.append(v)
		if len(fu_rows) >= 3:
			break
	fu_names = _names(fu_seen)
	# Most overdue first.
	for v in sorted(fu_rows, key=lambda x: getdate(x.next_visit_date)):
		overdue = (day - getdate(v.next_visit_date)).days
		when = "today" if overdue <= 0 else f"{overdue}d overdue"
		items.append(
			{
				"type": "followup",
				"severity": "high" if overdue >= 3 else "medium",
				"title": fu_names.get(v.customer) or v.customer,
				"reason": f"{v.next_action} · due {when}",
				"cta": "Visit",
				"route": {
					"name": "NewVisit",
					"query": {"id": v.customer, "ptype": "Customer", "label": fu_names.get(v.customer) or v.customer, "purpose": "Follow-up"},
				},
			}
		)

	# 3) Pending beat stops today — planned but not visited yet.
	beat_name = frappe.db.get_value("CRM Beat Plan", {"sales_person": emp, "plan_date": day}, "name")
	if beat_name:
		stops = frappe.get_all(
			"CRM Beat Plan Entry", filters={"parent": beat_name, "customer": ["is", "set"]}, fields=["customer"]
		)
		pending = [s.customer for s in stops if s.customer not in visited_today and s.customer not in fu_seen]
		beat_names = _names(pending[:3])
		for c in pending[:3]:
			items.append(
				{
					"type": "beat",
					"severity": "medium",
					"title": beat_names.get(c) or c,
					"reason": "On today's beat, not visited yet",
					"cta": "Visit",
					"route": {"name": "NewVisit", "query": {"id": c, "ptype": "Customer", "label": beat_names.get(c) or c}},
				}
			)

	return {"items": items[:limit], "as_of": str(day), "available": True}
