"""Turn captured visit orders into real ERPNext Quotations / Sales Orders.

Catalog-driven (Item + Item Price), with a credit-limit / outstanding check before
booking. Session-hardened. Guarded so it degrades cleanly where ERPNext selling
doctypes are absent.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, flt, today

from crm_app.api import get_current_employee


def _exists(dt):
	return bool(frappe.db.exists("DocType", dt))


def _default_price_list():
	pl = frappe.db.get_single_value("Selling Settings", "selling_price_list") if _exists("Selling Settings") else None
	return pl or frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")


@frappe.whitelist()
def search_items(query=None, limit=20):
	"""Search the ERPNext item catalog; include selling rate from the default price list."""
	get_current_employee()
	if not _exists("Item"):
		return []
	q = (query or "").strip()
	filters = {"disabled": 0}
	if _has("Item", "is_sales_item"):
		filters["is_sales_item"] = 1
	or_filters = None
	if q:
		or_filters = [["item_code", "like", f"%{q}%"], ["item_name", "like", f"%{q}%"]]
	items = frappe.get_all(
		"Item",
		filters=filters,
		or_filters=or_filters,
		fields=["item_code", "item_name", "stock_uom"],
		order_by="modified desc",
		limit=int(limit),
	)
	pl = _default_price_list()
	for it in items:
		rate = 0
		if pl and _exists("Item Price"):
			rate = frappe.db.get_value(
				"Item Price", {"item_code": it.item_code, "price_list": pl, "selling": 1}, "price_list_rate"
			)
		it["rate"] = flt(rate)
	return items


def _has(dt, f):
	try:
		return frappe.get_meta(dt).has_field(f)
	except Exception:
		return False


@frappe.whitelist()
def get_credit_status(customer):
	"""Outstanding + credit limit + available credit for a customer."""
	get_current_employee()
	out = {"outstanding": 0.0, "credit_limit": 0.0, "available": 0.0, "has_limit": False}
	if not customer:
		return out
	if _exists("Sales Invoice"):
		rows = frappe.get_all(
			"Sales Invoice",
			filters={"customer": customer, "docstatus": 1, "outstanding_amount": [">", 0]},
			fields=["outstanding_amount"],
			limit=2000,
		)
		out["outstanding"] = flt(sum(flt(r.outstanding_amount) for r in rows), 2)
	limit = 0
	if _exists("Customer Credit Limit"):
		limit = frappe.db.get_value("Customer Credit Limit", {"parent": customer}, "credit_limit") or 0
	if not limit and _has("Customer", "credit_limit"):
		limit = frappe.db.get_value("Customer", customer, "credit_limit") or 0
	out["credit_limit"] = flt(limit)
	out["has_limit"] = bool(limit)
	out["available"] = flt(limit - out["outstanding"], 2) if limit else 0.0
	return out


@frappe.whitelist()
def book_order(customer, items, visit=None, as_quotation=0, ignore_credit=0):
	"""Create a Draft Quotation or Sales Order for the customer from item lines.

	items: [{item_code, qty, rate?}]. Links the created doc back to the CRM Visit.
	"""
	employee = get_current_employee()
	if not _exists("Sales Order"):
		frappe.throw(_("ERPNext selling is not available on this site."))
	if isinstance(items, str):
		items = json.loads(items)
	items = [i for i in (items or []) if i.get("item_code") and flt(i.get("qty"))]
	if not items:
		frappe.throw(_("Add at least one catalog item with a quantity."))

	company = frappe.db.get_value("Customer", customer, "company") or frappe.defaults.get_global_default("company")
	pl = _default_price_list()

	# Credit check
	order_value = sum(flt(i.get("qty")) * flt(i.get("rate")) for i in items)
	credit = get_credit_status(customer)
	if credit["has_limit"] and not int(ignore_credit or 0):
		if order_value > credit["available"]:
			frappe.throw(
				_("Credit limit exceeded: order ₹{0} but only ₹{1} available (outstanding ₹{2}).").format(
					int(order_value), int(credit["available"]), int(credit["outstanding"])
				)
			)

	as_quotation = int(as_quotation or 0)
	doc = frappe.new_doc("Quotation" if as_quotation else "Sales Order")
	if as_quotation:
		doc.quotation_to = "Customer"
		doc.party_name = customer
	else:
		doc.customer = customer
	doc.company = company
	doc.transaction_date = today()
	if not as_quotation:
		doc.delivery_date = add_days(today(), 7)
	if pl and _has(doc.doctype, "selling_price_list"):
		doc.selling_price_list = pl
	for i in items:
		row = {"item_code": i["item_code"], "qty": flt(i["qty"])}
		if flt(i.get("rate")):
			row["rate"] = flt(i["rate"])
		if not as_quotation:
			row["delivery_date"] = add_days(today(), 7)
		doc.append("items", row)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)

	# Link back to the visit's order lines
	if visit and frappe.db.exists("CRM Visit", visit):
		v = frappe.get_doc("CRM Visit", visit)
		for oi in v.order_items:
			if not oi.sales_order:
				oi.sales_order = doc.name
		v.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "doctype": doc.doctype, "amount": flt(order_value, 2)}
