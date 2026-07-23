"""Party lookup for field visits — unified search over ERPNext Customers and
Frappe CRM Leads/Deals, plus a customer detail view (recent visits + outstanding).

Field access is meta-guarded so the module keeps working across Frappe CRM / ERPNext
versions even if a field is renamed or absent.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime

from crm_app.api import get_current_employee, is_sales_manager


def _has(doctype: str, field: str) -> bool:
	try:
		return frappe.get_meta(doctype).has_field(field)
	except Exception:
		return False


def _exists(doctype: str) -> bool:
	return bool(frappe.db.exists("DocType", doctype))


@frappe.whitelist()
def search_parties(query=None, party_type=None, limit=20):
	"""Search dealers/customers and (if installed) CRM Leads & Deals.

	Returns a flat list of {party_type, id, label, sub, phone}.
	"""
	get_current_employee()  # auth gate
	query = (query or "").strip()
	limit = int(limit)
	results = []

	want = party_type or "all"

	if want in ("all", "Customer") and _exists("Customer"):
		results += _search_customer(query, limit)
	if want in ("all", "CRM Lead") and _exists("CRM Lead"):
		results += _search_crm("CRM Lead", query, limit)
	if want in ("all", "CRM Deal") and _exists("CRM Deal"):
		results += _search_crm("CRM Deal", query, limit)

	return results[: limit * 2]


@frappe.whitelist()
def list_my_parties(limit=800):
	"""The rep's own dealers as a flat {party_type,id,label,sub,phone} list.

	Cached by the app on load so the rep can still PICK a dealer for a visit when offline
	(the live search_parties needs a connection). Scoped to rep_customers — the dealers he
	actually deals with — so the payload stays small enough to hold on a cheap phone.
	"""
	employee = get_current_employee()
	if not _exists("Customer"):
		return []
	from crm_app.sales_attr import rep_customers

	names = list(rep_customers(employee))
	if not names:
		return []
	fields = ["name", "customer_name"]
	for f in ("customer_group", "territory", "mobile_no"):
		if _has("Customer", f):
			fields.append(f)
	rows = frappe.get_all(
		"Customer", filters={"name": ["in", names]}, fields=fields, order_by="customer_name asc", limit=int(limit)
	)
	return [
		{
			"party_type": "Customer",
			"id": r.name,
			"label": r.get("customer_name") or r.name,
			"sub": r.get("territory") or r.get("customer_group") or "",
			"phone": r.get("mobile_no") or "",
		}
		for r in rows
	]


def _search_customer(query, limit):
	filters = {"disabled": 0} if _has("Customer", "disabled") else {}
	or_filters = None
	if query:
		or_filters = [["customer_name", "like", f"%{query}%"], ["name", "like", f"%{query}%"]]
	fields = ["name", "customer_name"]
	for f in ("customer_group", "territory", "mobile_no"):
		if _has("Customer", f):
			fields.append(f)
	rows = frappe.get_all(
		"Customer",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by="modified desc",
		limit=limit,
	)
	return [
		{
			"party_type": "Customer",
			"id": r.name,
			"label": r.get("customer_name") or r.name,
			"sub": r.get("territory") or r.get("customer_group") or "",
			"phone": r.get("mobile_no") or "",
		}
		for r in rows
	]


def _search_crm(doctype, query, limit):
	meta = frappe.get_meta(doctype)
	title_field = meta.get_title_field() if meta.get_title_field() else "name"
	name_field = "lead_name" if meta.has_field("lead_name") else title_field
	org_field = "organization" if meta.has_field("organization") else None
	phone_field = "mobile_no" if meta.has_field("mobile_no") else None

	fields = ["name"]
	for f in (name_field, org_field, phone_field):
		if f and f not in fields:
			fields.append(f)

	or_filters = None
	if query:
		or_filters = [["name", "like", f"%{query}%"]]
		if name_field != "name":
			or_filters.append([name_field, "like", f"%{query}%"])
		if org_field:
			or_filters.append([org_field, "like", f"%{query}%"])

	rows = frappe.get_all(
		doctype, or_filters=or_filters, fields=fields, order_by="modified desc", limit=limit
	)
	out = []
	for r in rows:
		label = r.get(org_field) if org_field and r.get(org_field) else r.get(name_field)
		out.append(
			{
				"party_type": doctype,
				"id": r.name,
				"label": label or r.name,
				"sub": r.get(name_field) if (org_field and r.get(org_field)) else "",
				"phone": r.get(phone_field) if phone_field else "",
			}
		)
	return out


@frappe.whitelist()
def get_customer(name):
	"""Customer detail card: profile, recent visits, and current outstanding."""
	employee = get_current_employee()
	if not frappe.db.exists("Customer", name):
		frappe.throw(_("Customer not found."), frappe.DoesNotExistError)
	from crm_app.api import assert_customer_access

	assert_customer_access(employee, name)

	fields = ["name", "customer_name"]
	for f in ("customer_group", "territory", "mobile_no", "email_id", "customer_primary_address"):
		if _has("Customer", f):
			fields.append(f)
	profile = frappe.db.get_value("Customer", name, fields, as_dict=True)

	visits = frappe.get_all(
		"CRM Visit",
		filters={"party_type": "Customer", "customer": name},
		fields=["name", "visit_date", "visit_purpose", "visit_status", "outcome", "sales_person_name"],
		order_by="visit_date desc",
		limit=10,
	)

	from crm_app.geo_resolve import customer_coords

	return {
		"customer": profile,
		"visits": visits,
		"outstanding": _customer_outstanding(name),
		"geo": customer_coords(name),
	}


def _fmt_inr(n):
	n = flt(n)
	if n >= 1e7:
		return f"{n / 1e7:.2f} Cr"
	if n >= 1e5:
		return f"{n / 1e5:.2f} L"
	return f"{n:,.0f}"


def _recommended_action(name, cust_name, outstanding, balance_as_of, in_credit, balance, orders_count, days_since_order, visit_count):
	"""The single next best action for this dealer, from reliable data only.

	Priority is deliberate and explainable (money owed → a promised follow-up that's due →
	a dealer going quiet → an active dealer never visited → an advance to convert → keep
	warm) — not a score. Each carries a plain reason and a deep link into the acting screen.
	"""
	visit_route = {"name": "NewVisit", "query": {"id": name, "ptype": "Customer", "label": cust_name}}

	if flt(outstanding) > 0:
		reason = f"Outstanding ₹{_fmt_inr(outstanding)}"
		if balance_as_of:
			reason += f" · as of {balance_as_of}"
		return {"tone": "urgent", "label": "Collect payment", "reason": reason, "cta": "Collect",
			"route": {"name": "Collect", "query": {"customer": name, "label": cust_name}}}

	fu = frappe.db.get_value(
		"CRM Visit",
		{"customer": name, "next_action": ["is", "set"], "next_visit_date": ["<=", getdate()]},
		["next_action", "next_visit_date"],
		order_by="visit_date desc",
		as_dict=True,
	)
	if fu and fu.get("next_action"):
		overdue = (getdate() - getdate(fu.next_visit_date)).days
		when = "today" if overdue <= 0 else f"{overdue}d ago"
		return {"tone": "followup", "label": "Follow up", "reason": f"{fu.next_action} · was due {when}", "cta": "Visit",
			"route": {"name": "NewVisit", "query": {"id": name, "ptype": "Customer", "label": cust_name, "purpose": "Follow-up"}}}

	if orders_count and days_since_order is not None and days_since_order > 90:
		return {"tone": "warn", "label": "Win back", "reason": f"No order in {days_since_order} days", "cta": "Visit", "route": visit_route}

	if orders_count and not visit_count:
		return {"tone": "info", "label": "Introduce yourself", "reason": "Active dealer, no visit logged yet", "cta": "Visit", "route": visit_route}

	if in_credit:
		return {"tone": "info", "label": "Push an order", "reason": f"Dealer is ₹{_fmt_inr(abs(flt(balance)))} in advance", "cta": "Visit", "route": visit_route}

	return {"tone": "info", "label": "Log a visit", "reason": "Keep the relationship warm", "cta": "Visit", "route": visit_route}


@frappe.whitelist()
def get_customer_360(name):
	"""Everything a rep needs while standing outside the shop, in one call.

	Deliberately one round trip: reps open this on 3G outside a dealer's shop, so five
	chatty calls would mean five chances to hang.
	"""
	get_current_employee()
	base = get_customer(name)
	from crm_app import sap_sales

	# --- trade history (all reps, not just the caller: it is the dealer's history) ---
	orders = {"count": 0, "value": 0.0, "qty_mt": 0.0, "last_date": None}
	top_products, recent_orders, dispatches = [], [], []

	# Prefer SAP: it is where this dealer is actually invoiced. ERPNext Sales Orders are
	# a near-empty table on their site, so reading only those showed every dealer as
	# having done no business.
	sap = sap_sales.customer_sales(name) if sap_sales.available() else None
	if sap and sap["invoices"]:
		orders = {
			"count": sap["invoices"],
			"value": sap["amount"],
			"qty_mt": sap["qty"],
			"last_date": sap["last_date"],
			"source": "sap",
		}
		top_products = [
			{"item": p["item"], "qty": p["qty"], "amount": p["amount"]}
			for p in sap_sales.customer_top_products(name)
		]
		dispatches = sap_sales.customer_invoices(name, limit=5)
		recent_orders = [
			{
				"name": d["invoice_number"],
				"date": str(d["invoice_date"]),
				"amount": d["amount"],
				"qty": d["qty"],
			}
			for d in dispatches
		]
	elif _exists("Sales Order"):
		rows = frappe.get_all(
			"Sales Order",
			filters={"customer": name, "docstatus": 1},
			fields=["name", "transaction_date", "grand_total", "total_qty"],
			order_by="transaction_date desc",
			limit=200,
		)
		orders["count"] = len(rows)
		orders["value"] = flt(sum(flt(r.grand_total) for r in rows), 2)
		orders["qty_mt"] = flt(sum(flt(r.total_qty) for r in rows), 3)
		orders["last_date"] = str(rows[0].transaction_date) if rows else None
		recent_orders = [
			{
				"name": r.name,
				"date": str(r.transaction_date),
				"amount": flt(r.grand_total),
				"qty": flt(r.total_qty),
			}
			for r in rows[:5]
		]
		if rows and _exists("Sales Order Item"):
			items = frappe.get_all(
				"Sales Order Item",
				filters={"parent": ["in", [r.name for r in rows[:100]]]},
				fields=["item_code", "item_name", "qty", "amount"],
				limit=1000,
			)
			agg = {}
			for it in items:
				a = agg.setdefault(it.item_code, {"item": it.item_name or it.item_code, "qty": 0.0, "amount": 0.0})
				a["qty"] += flt(it.qty)
				a["amount"] += flt(it.amount)
			top_products = sorted(agg.values(), key=lambda x: x["amount"], reverse=True)[:5]

	# --- money owed ---
	# SAP carries the real balance; ERPNext has no invoices on their site. Unlike the
	# collections screen, a CREDIT is shown here too — on a dealer's own page that is
	# useful context, not a chase target.
	from crm_app import sap_receivables

	sap_bal = sap_receivables.customer_balance(name) if sap_receivables.available() else None
	if sap_bal:
		base["outstanding"] = sap_bal["balance"] if sap_bal["balance"] > 0 else 0.0
		base["balance"] = sap_bal["balance"]
		base["balance_as_of"] = sap_bal["as_of"]
		base["in_credit"] = sap_bal["balance"] < 0
		base["last_payment"] = sap_bal["last_paid"]
		base["payments"] = sap_receivables.customer_payments(name, limit=5)

		# The balance says how much; this says against WHICH ORDER — the question a rep
		# is actually asked at the counter. Payments carry the SAP order number, so the
		# two can be reconciled per order.
		from crm_app import sap_orders

		if sap_orders.available():
			base["order_ledger"] = sap_orders.customer_orders(name, limit=15)

	overdue = 0.0
	if not sap_bal and _exists("Sales Invoice"):
		inv = frappe.get_all(
			"Sales Invoice",
			filters={"customer": name, "docstatus": 1, "outstanding_amount": [">", 0]},
			fields=["outstanding_amount", "due_date"],
			limit=500,
		)
		td = getdate()
		overdue = flt(
			sum(flt(i.outstanding_amount) for i in inv if i.due_date and getdate(i.due_date) < td), 2
		)

	# --- relationship health ---
	visits = base["visits"]
	last_visit = visits[0]["visit_date"] if visits else None
	days_since_visit = (getdate() - getdate(last_visit)).days if last_visit else None
	days_since_order = (getdate() - getdate(orders["last_date"])).days if orders["last_date"] else None

	credit_limit = 0.0
	if _has("Customer", "credit_limit"):
		credit_limit = flt(frappe.db.get_value("Customer", name, "credit_limit"))

	visit_count = frappe.db.count("CRM Visit", {"party_type": "Customer", "customer": name})
	cust_name = base["customer"]["customer_name"] if base.get("customer") else name

	return {
		**base,
		"orders": orders,
		"recent_orders": recent_orders,
		"top_products": top_products,
		# "Where is my truck?" — the question a dealer asks at every visit, answerable
		# now that the SAP register carries LR number, truck and transporter.
		"dispatches": dispatches,
		"overdue": overdue,
		"credit_limit": credit_limit,
		"visit_count": visit_count,
		"last_visit": str(last_visit) if last_visit else None,
		"days_since_visit": days_since_visit,
		"days_since_order": days_since_order,
		# Same rule of thumb the insights module uses: quiet for a quarter = at risk.
		"at_risk": bool(days_since_order is not None and days_since_order > 90),
		# The one thing to do next at this dealer — server-computed, explainable, deep-linked.
		"next_action": _recommended_action(
			name, cust_name, base.get("outstanding"), base.get("balance_as_of"),
			base.get("in_credit"), base.get("balance"), orders["count"], days_since_order, visit_count,
		),
	}


@frappe.whitelist()
def pin_shop(customer, latitude, longitude):
	"""Save a dealer's real shop location from the rep's GPS, standing at the shop.

	This fills the ~6% of dealers whose Address carries no coordinates, and a pinned
	location outranks the billing address in geo_resolve (the shop door beats the
	accounts desk).

	Guard: a rep may pin only a dealer we CANNOT already locate. Pinning moves the
	geofence, so letting a rep re-pin an existing shop would let him relocate it to his
	own doorstep and pass every geofence check from home. Managers may re-pin.
	"""
	employee = get_current_employee()
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Customer not found."), frappe.DoesNotExistError)
	lat, lng = flt(latitude), flt(longitude)
	if not lat or not lng:
		frappe.throw(_("Could not read your location. Try again with GPS on."))
	if not _has("Customer", "custom_geo_latitude"):
		frappe.throw(_("Location fields are not installed on this site."))

	from crm_app.geo_resolve import customer_coords

	if customer_coords(customer) and not is_sales_manager():
		frappe.throw(
			_("This shop already has a location. Ask your manager to change it."),
			frappe.PermissionError,
		)

	doc = frappe.get_doc("Customer", customer)
	doc.db_set("custom_geo_latitude", lat, update_modified=False)
	doc.db_set("custom_geo_longitude", lng, update_modified=False)
	if _has("Customer", "custom_geo_pinned_by"):
		doc.db_set("custom_geo_pinned_by", employee, update_modified=False)
	if _has("Customer", "custom_geo_pinned_on"):
		doc.db_set("custom_geo_pinned_on", now_datetime(), update_modified=False)
	frappe.db.commit()
	return {"ok": True, "lat": lat, "lng": lng, "source": "pinned"}


def _customer_outstanding(customer: str) -> float:
	"""Current amount the dealer owes.

	SAP-first (positive balance = owes), because ERPNext holds 0 Sales Invoices here so the
	old Sales-Invoice sum was always ₹0 — get_customer_360 overrode it, but get_customer
	called directly still returned ₹0. Now correct at the source, with Sales Invoice as the
	fallback for a site where invoicing lands in ERPNext.
	"""
	from crm_app import sap_receivables

	if sap_receivables.available():
		bal = sap_receivables.customer_balance(customer)
		if bal is not None:
			return flt(bal.get("balance"), 2) if flt(bal.get("balance")) > 0 else 0.0
	if not _exists("Sales Invoice"):
		return 0.0
	rows = frappe.get_all(
		"Sales Invoice",
		filters={"customer": customer, "docstatus": 1, "outstanding_amount": [">", 0]},
		fields=["outstanding_amount"],
		limit=500,
	)
	return flt(sum(flt(r.outstanding_amount) for r in rows), 2)
