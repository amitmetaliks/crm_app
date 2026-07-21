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
	get_current_employee()
	out = {"outstanding": 0.0, "credit_limit": 0.0, "available": 0.0, "has_limit": False}
	if not customer:
		return out

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

	# Order value for the credit check must use the REAL price, not the client's `rate`.
	# The client normally omits rate (the Sales Order prices from the list below), so
	# `qty * rate` was 0 for every line -> order_value 0 -> the gate always passed. Resolve
	# the price-list rate for any line without one so the check reflects the true value.
	def _line_value(i):
		r = flt(i.get("rate"))
		if not r and pl and _exists("Item Price"):
			r = flt(
				frappe.db.get_value(
					"Item Price", {"item_code": i["item_code"], "price_list": pl, "selling": 1}, "price_list_rate"
				)
			)
		return flt(i.get("qty")) * r

	order_value = sum(_line_value(i) for i in items)

	# Overriding the credit limit is a manager decision, not something any rep can pass as a
	# flag: `ignore_credit` is only honoured for a Sales Manager.
	from crm_app.api import is_sales_manager

	allow_ignore = bool(int(ignore_credit or 0)) and is_sales_manager()
	credit = get_credit_status(customer)
	if credit["has_limit"] and not allow_ignore:
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
