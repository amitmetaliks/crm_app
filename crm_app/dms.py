"""Dealer stock + secondary sales (the DMS half of a field CRM).

Primary sales (us → dealer) are already visible as ERPNext Sales Orders. What the
business cannot see today is what happens *after* that: how much of our material is
sitting on a dealer's floor, and how much he is actually selling onward. That blind
spot is what makes replenishment guesswork and lets a dealer quietly drift to a
competitor while his purchase numbers still look fine.

A rep records, at the shop:
  * **closing stock** per grade (ours and competitors'), and
  * **sold since last visit**, as the dealer reports it.

We then compute the same figure independently:

    implied_sold = previous_closing + primary_purchased_in_between − current_closing

If the dealer says he sold 20 MT but the arithmetic says 45 MT, that gap is the
interesting part of the visit — either the stock count is wrong, or someone is buying
elsewhere. We store both and never silently overwrite what the dealer said.

Shelf share (ours ÷ total closing) is the other number that matters: it moves before
the order numbers do.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from crm_app.api import get_current_employee, is_sales_manager


def _exists(dt):
	return bool(frappe.db.exists("DocType", dt))


def _last_check(customer, before_date, exclude=None):
	"""The previous stock check for this dealer, to measure movement against."""
	filters = {"customer": customer, "check_date": ["<", getdate(before_date)]}
	if exclude:
		filters["name"] = ["!=", exclude]
	rows = frappe.get_all(
		"CRM Dealer Stock",
		filters=filters,
		fields=["name", "check_date"],
		order_by="check_date desc",
		limit=1,
	)
	return rows[0] if rows else None


def _primary_between(customer, frm, to):
	"""MT we sold this dealer between two dates (their primary purchases from us).

	Reads Sales Orders because the site has no Delivery Notes — so this is what was
	ordered, not necessarily what landed. Stated plainly rather than hidden, since it
	makes `implied_sold` an estimate, not gospel.
	"""
	if not _exists("Sales Order") or not frm:
		return {}
	orders = frappe.get_all(
		"Sales Order",
		filters={
			"customer": customer,
			"docstatus": 1,
			"transaction_date": ["between", [getdate(frm), getdate(to)]],
		},
		pluck="name",
	)
	if not orders:
		return {}
	rows = frappe.get_all(
		"Sales Order Item",
		filters={"parent": ["in", orders]},
		fields=["item_code", "qty"],
		limit=2000,
	)
	out = {}
	for r in rows:
		out[r.item_code] = out.get(r.item_code, 0.0) + flt(r.qty)
	return out


@frappe.whitelist()
def get_last_stock(customer):
	"""Previous check for this dealer — reps re-count the same grades, so pre-fill them."""
	get_current_employee()
	last = _last_check(customer, frappe.utils.today())
	if not last:
		return {"exists": False, "items": [], "check_date": None}
	doc = frappe.get_doc("CRM Dealer Stock", last.name)
	return {
		"exists": True,
		"name": doc.name,
		"check_date": str(doc.check_date),
		"our_share_pct": doc.our_share_pct,
		"items": [
			{
				"item_code": i.item_code,
				"item_name": i.item_name,
				"brand_type": i.brand_type,
				"closing_qty_mt": i.closing_qty_mt,
			}
			for i in doc.items
		],
	}


@frappe.whitelist()
def record_stock(customer, items, check_date=None, visit=None, remarks=None) -> dict:
	"""Record a dealer's closing stock + reported secondary sales."""
	employee = get_current_employee()
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Dealer not found."), frappe.DoesNotExistError)
	if isinstance(items, str):
		items = frappe.parse_json(items)
	items = [i for i in (items or []) if (i.get("item_code") or "").strip()]
	if not items:
		frappe.throw(_("Add at least one item."))

	day = getdate(check_date) if check_date else getdate()

	# One check per dealer per day — a rep re-counting should correct, not duplicate.
	existing = frappe.db.get_value("CRM Dealer Stock", {"customer": customer, "check_date": day}, "name")
	doc = frappe.get_doc("CRM Dealer Stock", existing) if existing else frappe.new_doc("CRM Dealer Stock")
	doc.customer = customer
	doc.check_date = day
	doc.sales_person = employee
	doc.visit = visit
	doc.remarks = remarks
	doc.set("items", [])

	last = _last_check(customer, day, exclude=existing)
	primary = _primary_between(customer, last.check_date, day) if last else {}
	prev_closing = {}
	if last:
		prev = frappe.get_doc("CRM Dealer Stock", last.name)
		prev_closing = {i.item_code: flt(i.closing_qty_mt) for i in prev.items}
		doc.days_since_last_check = (day - getdate(last.check_date)).days

	for it in items:
		code = (it.get("item_code") or "").strip()
		closing = flt(it.get("closing_qty_mt"))
		implied = 0.0
		if last and it.get("brand_type", "Ours") == "Ours":
			# prev closing + what we shipped him since − what is left = what moved out
			implied = flt(prev_closing.get(code, 0) + primary.get(code, 0) - closing, 3)
			if implied < 0:
				implied = 0.0  # counted more than we can account for; not a negative sale
		doc.append(
			"items",
			{
				"item_code": code,
				"item_name": it.get("item_name") or code,
				"brand_type": it.get("brand_type") or "Ours",
				"closing_qty_mt": closing,
				"sold_qty_mt": flt(it.get("sold_qty_mt")),
				"implied_sold_mt": implied,
				"rate_per_mt": flt(it.get("rate_per_mt")),
				"remarks": it.get("remarks"),
			},
		)

	_roll_up(doc)
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"name": doc.name,
		"total_closing_mt": doc.total_closing_mt,
		"total_sold_mt": doc.total_sold_mt,
		"our_share_pct": doc.our_share_pct,
		"days_since_last_check": doc.days_since_last_check,
		"implied_total_mt": flt(sum(flt(i.implied_sold_mt) for i in doc.items), 3),
	}


def _roll_up(doc):
	ours = flt(sum(flt(i.closing_qty_mt) for i in doc.items if i.brand_type == "Ours"), 3)
	comp = flt(sum(flt(i.closing_qty_mt) for i in doc.items if i.brand_type == "Competitor"), 3)
	doc.our_closing_mt = ours
	doc.competitor_closing_mt = comp
	doc.total_closing_mt = flt(ours + comp, 3)
	doc.total_sold_mt = flt(sum(flt(i.sold_qty_mt) for i in doc.items), 3)
	doc.our_share_pct = flt(ours / (ours + comp) * 100, 2) if (ours + comp) else 0.0


@frappe.whitelist()
def get_dealer_stock_history(customer, limit=10) -> list:
	"""Stock checks for one dealer, newest first — the trend is the point."""
	get_current_employee()
	return frappe.get_all(
		"CRM Dealer Stock",
		filters={"customer": customer},
		fields=[
			"name", "check_date", "total_closing_mt", "our_closing_mt",
			"competitor_closing_mt", "our_share_pct", "total_sold_mt", "sales_person_name",
		],
		order_by="check_date desc",
		limit=int(limit),
	)


@frappe.whitelist()
def get_my_stock_checks(limit=30, scope="mine") -> list:
	"""Recent checks by this rep (or the team, for a manager)."""
	employee = get_current_employee()
	filters = {} if (scope == "team" and is_sales_manager()) else {"sales_person": employee}
	return frappe.get_all(
		"CRM Dealer Stock",
		filters=filters,
		fields=[
			"name", "customer", "customer_name", "check_date", "total_closing_mt",
			"our_share_pct", "total_sold_mt", "sales_person_name",
		],
		order_by="check_date desc, modified desc",
		limit=int(limit),
	)


@frappe.whitelist()
def get_secondary_summary(days=90, scope="mine") -> dict:
	"""Secondary sales + shelf share across the rep's dealers.

	`reported` is what dealers said; `implied` is what the stock arithmetic says. The
	gap between them is the number worth arguing about in a review meeting.
	"""
	employee = get_current_employee()
	frm = frappe.utils.add_days(getdate(), -int(days))
	filters = {"check_date": [">=", frm]}
	if not (scope == "team" and is_sales_manager()):
		filters["sales_person"] = employee

	checks = frappe.get_all(
		"CRM Dealer Stock",
		filters=filters,
		fields=["name", "customer", "customer_name", "check_date", "our_closing_mt", "competitor_closing_mt"],
		order_by="check_date desc",
		limit=500,
	)
	if not checks:
		return {"dealers": [], "reported_mt": 0, "implied_mt": 0, "our_share_pct": 0, "checks": 0}

	rows = frappe.get_all(
		"CRM Dealer Stock Item",
		filters={"parent": ["in", [c.name for c in checks]]},
		fields=["parent", "sold_qty_mt", "implied_sold_mt", "brand_type", "closing_qty_mt"],
		limit=5000,
	)
	by_check = {}
	for r in rows:
		by_check.setdefault(r.parent, []).append(r)

	dealers, reported, implied = {}, 0.0, 0.0
	ours_total = comp_total = 0.0
	for c in checks:
		its = by_check.get(c.name, [])
		rep_mt = flt(sum(flt(i.sold_qty_mt) for i in its))
		imp_mt = flt(sum(flt(i.implied_sold_mt) for i in its))
		reported += rep_mt
		implied += imp_mt
		ours_total += flt(c.our_closing_mt)
		comp_total += flt(c.competitor_closing_mt)
		d = dealers.setdefault(
			c.customer,
			{
				"customer": c.customer,
				"customer_name": c.customer_name,
				"reported_mt": 0.0,
				"implied_mt": 0.0,
				"last_check": str(c.check_date),
				"our_share_pct": 0.0,
				"checks": 0,
			},
		)
		d["reported_mt"] = flt(d["reported_mt"] + rep_mt, 3)
		d["implied_mt"] = flt(d["implied_mt"] + imp_mt, 3)
		d["checks"] += 1
		tot = flt(c.our_closing_mt) + flt(c.competitor_closing_mt)
		if tot and d["last_check"] == str(c.check_date):
			d["our_share_pct"] = flt(flt(c.our_closing_mt) / tot * 100, 2)

	out = sorted(dealers.values(), key=lambda x: x["implied_mt"], reverse=True)
	for d in out:
		d["gap_mt"] = flt(d["implied_mt"] - d["reported_mt"], 3)
	return {
		"dealers": out,
		"reported_mt": flt(reported, 3),
		"implied_mt": flt(implied, 3),
		"gap_mt": flt(implied - reported, 3),
		"our_share_pct": flt(ours_total / (ours_total + comp_total) * 100, 2) if (ours_total + comp_total) else 0,
		"checks": len(checks),
		"days": int(days),
	}
