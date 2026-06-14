"""Party lookup for field visits — unified search over ERPNext Customers and
Frappe CRM Leads/Deals, plus a customer detail view (recent visits + outstanding).

Field access is meta-guarded so the module keeps working across Frappe CRM / ERPNext
versions even if a field is renamed or absent.
"""

import frappe
from frappe import _
from frappe.utils import flt

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
	get_current_employee()
	if not frappe.db.exists("Customer", name):
		frappe.throw(_("Customer not found."), frappe.DoesNotExistError)

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

	return {
		"customer": profile,
		"visits": visits,
		"outstanding": _customer_outstanding(name),
	}


def _customer_outstanding(customer: str) -> float:
	"""Total submitted, unpaid Sales Invoice amount for the customer."""
	if not _exists("Sales Invoice"):
		return 0.0
	rows = frappe.get_all(
		"Sales Invoice",
		filters={"customer": customer, "docstatus": 1, "outstanding_amount": [">", 0]},
		fields=["outstanding_amount"],
		limit=500,
	)
	return flt(sum(flt(r.outstanding_amount) for r in rows), 2)
