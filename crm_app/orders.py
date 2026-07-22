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
	"""Outstanding + credit limit + available credit for a customer.

	Outstanding comes from the SAP receivable feed, NOT ERPNext Sales Invoices: this
	business invoices in SAP, so `tabSales Invoice` holds 0 rows and the old path reported
	every dealer as owing ₹0 — which silently disabled the credit gate in book_order. The
	SAP balance (positive = owes) is the real exposure; a credit balance is clamped to 0
	owed. Sales Invoice stays as the fallback for a site where invoicing lands in ERPNext.
	"""
	employee = get_current_employee()
	out = {"outstanding": 0.0, "credit_limit": 0.0, "available": 0.0, "has_limit": False}
	if not customer:
		return out
	from crm_app.api import assert_customer_access

	assert_customer_access(employee, customer)

	outstanding = None
	from crm_app import sap_receivables

	if sap_receivables.available():
		bal = sap_receivables.customer_balance(customer)
		if bal is not None:
			# positive = owes us; negative = in advance (no exposure) -> 0 owed
			outstanding = max(0.0, flt(bal.get("balance"), 2))
	if outstanding is None and _exists("Sales Invoice"):
		rows = frappe.get_all(
			"Sales Invoice",
			filters={"customer": customer, "docstatus": 1, "outstanding_amount": [">", 0]},
			fields=["outstanding_amount"],
			limit=2000,
		)
		outstanding = flt(sum(flt(r.outstanding_amount) for r in rows), 2)
	out["outstanding"] = flt(outstanding or 0.0, 2)
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

	items: [{item_code, qty}]. Price is always resolved on the server; browser-provided
	rates are display hints only and are never trusted for credit or order value.
	"""
	employee = get_current_employee()
	if not _exists("Sales Order"):
		frappe.throw(_("ERPNext selling is not available on this site."))
	from crm_app.api import assert_customer_access

	assert_customer_access(employee, customer)
	if isinstance(items, str):
		items = json.loads(items)
	items = [i for i in (items or []) if i.get("item_code") and flt(i.get("qty"))]
	if not items:
		frappe.throw(_("Add at least one catalog item with a quantity."))

	company = frappe.db.get_value("Customer", customer, "company") or frappe.defaults.get_global_default("company")
	pl = _default_price_list()

	def _server_rate(item_code):
		"""Resolve a selling rate from ERPNext-owned data, never request JSON."""
		rate = 0
		if pl and _exists("Item Price"):
			rate = flt(
				frappe.db.get_value(
					"Item Price", {"item_code": item_code, "price_list": pl, "selling": 1}, "price_list_rate"
				)
			)
		if not rate and _exists("Item"):
			master = frappe.db.get_value(
				"Item", item_code, ["standard_rate", "valuation_rate"], as_dict=True
			) or {}
			rate = flt(master.get("standard_rate") or master.get("valuation_rate"))
		return rate

	server_items = []
	for item in items:
		rate = _server_rate(item["item_code"])
		if rate <= 0:
			frappe.throw(
				_("No selling price is configured for item {0}. Ask a manager to update the ERPNext price list.").format(
					frappe.bold(item["item_code"])
				)
			)
		server_items.append({"item_code": item["item_code"], "qty": flt(item["qty"]), "rate": rate})

	order_value = sum(item["qty"] * item["rate"] for item in server_items)

	# Overriding the credit limit is a manager decision, not something any rep can pass as a
	# flag: `ignore_credit` is only honoured for a Sales Manager.
	from crm_app.api import is_sales_manager

	allow_ignore = bool(int(ignore_credit or 0)) and is_sales_manager()
	credit = get_credit_status(customer)
	if credit["has_limit"] and not allow_ignore:
		if order_value <= 0:
			# Could not value any line — do NOT treat that as "₹0, within limit" (the old
			# bypass). Make the rep price it or get a manager override.
			frappe.throw(
				_("Couldn't price this order to check the credit limit — enter a rate on each line, or ask a manager to override.")
			)
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
	for i in server_items:
		row = {"item_code": i["item_code"], "qty": i["qty"], "rate": i["rate"]}
		if not as_quotation:
			row["delivery_date"] = add_days(today(), 7)
		doc.append("items", row)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)

	# Link back to the visit's order lines
	if visit and frappe.db.exists("CRM Visit", visit):
		v = frappe.get_doc("CRM Visit", visit)
		if not is_sales_manager() and v.sales_person != employee:
			frappe.throw(_("You do not have access to this visit."), frappe.PermissionError)
		if v.party_type != "Customer" or v.customer != customer:
			frappe.throw(_("The selected visit belongs to a different customer."))
		for oi in v.order_items:
			if not oi.sales_order:
				oi.sales_order = doc.name
		v.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "doctype": doc.doctype, "amount": flt(order_value, 2)}
