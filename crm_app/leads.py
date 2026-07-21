"""Thin, version-tolerant wrappers over Frappe CRM's CRM Lead / CRM Deal for the
inside-sales experience in our PWA. All field access is meta-guarded so it keeps
working across Frappe CRM versions.
"""

import frappe
from frappe import _

from crm_app.api import get_current_employee, is_sales_manager


def _exists(dt):
	return bool(frappe.db.exists("DocType", dt))


def _has(dt, f):
	try:
		return frappe.get_meta(dt).has_field(f)
	except Exception:
		return False


def _list_fields(dt, wanted):
	return ["name"] + [f for f in wanted if _has(dt, f)]


@frappe.whitelist()
def get_leads(scope="mine", status=None, search=None, limit=100):
	"""List CRM Leads. Reps see their own (lead_owner); managers can see all."""
	get_current_employee()
	if not _exists("CRM Lead"):
		return []
	fields = _list_fields("CRM Lead", ["lead_name", "organization", "status", "mobile_no", "email", "lead_owner", "modified"])
	filters = {}
	if not (scope == "team" and is_sales_manager()) and _has("CRM Lead", "lead_owner"):
		filters["lead_owner"] = frappe.session.user
	if status and _has("CRM Lead", "status"):
		filters["status"] = status
	or_filters = None
	if search:
		or_filters = [["name", "like", f"%{search}%"]]
		for f in ("lead_name", "organization", "mobile_no"):
			if _has("CRM Lead", f):
				or_filters.append([f, "like", f"%{search}%"])
	return frappe.get_all(
		"CRM Lead", filters=filters, or_filters=or_filters, fields=fields,
		order_by="modified desc", limit=int(limit)
	)


@frappe.whitelist()
def get_deals(scope="mine", status=None, search=None, limit=100):
	"""List CRM Deals. Reps see their own (deal_owner); managers can see all."""
	get_current_employee()
	if not _exists("CRM Deal"):
		return []
	fields = _list_fields("CRM Deal", ["organization", "lead_name", "status", "mobile_no", "email", "deal_owner", "modified"])
	filters = {}
	if not (scope == "team" and is_sales_manager()) and _has("CRM Deal", "deal_owner"):
		filters["deal_owner"] = frappe.session.user
	if status and _has("CRM Deal", "status"):
		filters["status"] = status
	or_filters = None
	if search:
		or_filters = [["name", "like", f"%{search}%"]]
		for f in ("organization", "lead_name", "mobile_no"):
			if _has("CRM Deal", f):
				or_filters.append([f, "like", f"%{search}%"])
	return frappe.get_all(
		"CRM Deal", filters=filters, or_filters=or_filters, fields=fields,
		order_by="modified desc", limit=int(limit)
	)


@frappe.whitelist()
def create_lead(lead_name=None, organization=None, mobile_no=None, email=None, source=None, territory=None, notes=None, idempotency_key=None):
	"""Create a CRM Lead owned by the current user (inside-sales capture)."""
	employee = get_current_employee()
	if not _exists("CRM Lead"):
		frappe.throw(_("Frappe CRM is not installed on this site."))
	from crm_app import idempotency

	prior = idempotency.replay(idempotency_key, employee)
	if prior is not None:
		return prior

	doc = frappe.new_doc("CRM Lead")
	name = (lead_name or organization or "New Lead").strip()
	if _has("CRM Lead", "first_name"):
		doc.first_name = name
	if _has("CRM Lead", "lead_name"):
		doc.lead_name = name
	for field, value in (
		("organization", organization),
		("mobile_no", mobile_no),
		("email", email),
		("email_id", email),
		("source", source),
		("territory", territory),
		("notes", notes),
	):
		if value and _has("CRM Lead", field):
			doc.set(field, value)
	if _has("CRM Lead", "lead_owner"):
		doc.lead_owner = frappe.session.user
	# Pick a safe, non-"Lost" status (a Lost status triggers a mandatory lost-reason
	# check). Prefer "New"; otherwise leave it for Frappe CRM's own default.
	if _has("CRM Lead", "status") and _exists("CRM Lead Status"):
		st = None
		if frappe.db.exists("CRM Lead Status", "New"):
			st = "New"
		elif _has("CRM Lead Status", "type"):
			st = frappe.db.get_value("CRM Lead Status", {"type": ["!=", "Lost"]}, "name")
		if st:
			doc.status = st
	doc.insert(ignore_permissions=True)
	result = {"name": doc.name, "lead_name": name}
	idempotency.record(idempotency_key, "leads.create_lead", result, employee)
	frappe.db.commit()
	return result


@frappe.whitelist()
def convert_lead(lead):
	"""Best-effort: convert a CRM Lead to a Deal using Frappe CRM's own method."""
	get_current_employee()
	try:
		from crm.fcrm.doctype.crm_lead.crm_lead import convert_to_deal

		deal = convert_to_deal(lead=lead)
		frappe.db.commit()
		return {"ok": True, "deal": deal}
	except Exception as e:
		frappe.log_error(title="convert_lead failed", message=str(e))
		frappe.throw(_("Could not convert this lead automatically. Please convert it in the CRM."))
