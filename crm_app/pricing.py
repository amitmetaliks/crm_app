"""Active sales schemes / offers — surfaced from ERPNext Pricing Rules so reps can
see and quote current discounts/schemes during a visit.
"""

import frappe
from frappe.utils import flt, getdate, today

from crm_app.api import get_current_employee


def _summary(r):
	kind = (r.get("rate_or_discount") or "").strip()
	if kind == "Discount Percentage" and r.get("discount_percentage"):
		offer = f"{flt(r.discount_percentage):g}% off"
	elif kind == "Discount Amount" and r.get("discount_amount"):
		offer = f"₹{flt(r.discount_amount):g} off"
	elif kind == "Rate" and r.get("rate"):
		offer = f"₹{flt(r.rate):g} rate"
	else:
		offer = kind or "Offer"
	if r.get("min_qty"):
		offer += f" (min {flt(r.min_qty):g})"
	return offer


@frappe.whitelist()
def get_schemes(limit=80):
	"""Active selling Pricing Rules valid today, with a friendly summary."""
	get_current_employee()
	if not frappe.db.exists("DocType", "Pricing Rule"):
		return []
	meta = frappe.get_meta("Pricing Rule")
	wanted = [
		"title", "valid_from", "valid_upto", "rate_or_discount", "discount_percentage",
		"discount_amount", "rate", "min_qty", "max_qty", "apply_on", "applicable_for", "priority",
	]
	fields = ["name"] + [f for f in wanted if meta.has_field(f)]
	filters = {"disable": 0}
	if meta.has_field("selling"):
		filters["selling"] = 1
	rules = frappe.get_all("Pricing Rule", filters=filters, fields=fields, order_by="modified desc", limit=300)
	td = getdate(today())
	out = []
	for r in rules:
		if r.get("valid_from") and getdate(r.valid_from) > td:
			continue
		if r.get("valid_upto") and getdate(r.valid_upto) < td:
			continue
		out.append(
			{
				"name": r.name,
				"title": r.get("title") or r.name,
				"offer": _summary(r),
				"apply_on": r.get("apply_on"),
				"valid_upto": str(r.valid_upto) if r.get("valid_upto") else None,
			}
		)
	return out[: int(limit)]
