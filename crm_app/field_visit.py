"""Field Visit API — the heart of the CRM.

All endpoints derive the acting sales person from the session (`get_current_employee`)
and never trust an `employee`/`sales_person` value from the request. Reads are scoped
to the session employee (managers see the whole team); writes on the rep's own visits
use `ignore_permissions=True` after an explicit access check, so the app does not depend
on the user holding a particular Frappe role.
"""

import base64
import json

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from crm_app.api import get_current_employee, is_sales_manager, validate_upload

VISIT_FIELDS = [
	"name",
	"sales_person",
	"sales_person_name",
	"visit_date",
	"planned_date",
	"party_type",
	"customer",
	"crm_lead",
	"crm_deal",
	"prospect_name",
	"party_display",
	"contact_name",
	"contact_phone",
	"visit_purpose",
	"visit_status",
	"outcome",
	"check_in_time",
	"check_in_latitude",
	"check_in_longitude",
	"check_in_address",
	"check_out_time",
	"check_out_latitude",
	"check_out_longitude",
	"duration_minutes",
	"notes",
	"next_action",
	"next_visit_date",
	"modified",
]


def _parse(value):
	"""Accept a JSON string or an already-decoded list/dict from the request."""
	if value is None or value == "":
		return None
	if isinstance(value, (list, dict)):
		return value
	try:
		return json.loads(value)
	except (ValueError, TypeError):
		return value


def _require_access(name: str, employee: str):
	"""Raise unless the current user owns the visit or is a sales manager."""
	owner_emp = frappe.db.get_value("CRM Visit", name, "sales_person")
	if not owner_emp:
		frappe.throw(_("Visit not found."), frappe.DoesNotExistError)
	if owner_emp != employee and not is_sales_manager():
		frappe.throw(_("You do not have access to this visit."), frappe.PermissionError)


def _apply_party(doc, party_type, customer, crm_lead, crm_deal, prospect_name):
	doc.party_type = party_type or "Customer"
	doc.customer = customer if doc.party_type == "Customer" else None
	doc.crm_lead = crm_lead if doc.party_type == "CRM Lead" else None
	doc.crm_deal = crm_deal if doc.party_type == "CRM Deal" else None
	doc.prospect_name = prospect_name if doc.party_type == "Prospect" else None


# ── create / check-in ───────────────────────────────────────────────────────


@frappe.whitelist()
def start_visit(
	party_type="Customer",
	customer=None,
	crm_lead=None,
	crm_deal=None,
	prospect_name=None,
	visit_purpose="Follow-up",
	contact_name=None,
	contact_phone=None,
	latitude=None,
	longitude=None,
	address=None,
	planned_visit=None,
):
	"""Begin a visit: creates a CRM Visit in 'In Progress' with the GPS check-in stamped now.

	`planned_visit` (optional) is the name of an existing Planned visit to convert in place
	(used by beat planning) instead of creating a new record.
	"""
	employee = get_current_employee()

	if planned_visit:
		_require_access(planned_visit, employee)
		doc = frappe.get_doc("CRM Visit", planned_visit)
	else:
		doc = frappe.new_doc("CRM Visit")
		doc.sales_person = employee
		doc.visit_date = frappe.utils.today()

	_apply_party(doc, party_type, customer, crm_lead, crm_deal, prospect_name)
	doc.visit_purpose = visit_purpose or doc.visit_purpose or "Follow-up"
	if contact_name is not None:
		doc.contact_name = contact_name
	if contact_phone is not None:
		doc.contact_phone = contact_phone
	doc.visit_status = "In Progress"
	doc.check_in_time = now_datetime()
	if latitude not in (None, ""):
		doc.check_in_latitude = flt(latitude)
	if longitude not in (None, ""):
		doc.check_in_longitude = flt(longitude)
	if address:
		doc.check_in_address = address
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "visit_status": doc.visit_status, "check_in_time": doc.check_in_time}


@frappe.whitelist()
def check_out(name, latitude=None, longitude=None):
	"""Stamp the GPS check-out, mark the visit Completed, and compute its duration."""
	employee = get_current_employee()
	_require_access(name, employee)
	doc = frappe.get_doc("CRM Visit", name)
	doc.check_out_time = now_datetime()
	if latitude not in (None, ""):
		doc.check_out_latitude = flt(latitude)
	if longitude not in (None, ""):
		doc.check_out_longitude = flt(longitude)
	if doc.visit_status in ("Planned", "In Progress"):
		doc.visit_status = "Completed"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "visit_status": doc.visit_status, "duration_minutes": doc.duration_minutes}


@frappe.whitelist()
def save_visit(
	name=None,
	party_type="Customer",
	customer=None,
	crm_lead=None,
	crm_deal=None,
	prospect_name=None,
	visit_purpose="Follow-up",
	visit_status=None,
	contact_name=None,
	contact_phone=None,
	visit_date=None,
	planned_date=None,
	notes=None,
	outcome=None,
	next_action=None,
	next_visit_date=None,
	order_items=None,
	competitors=None,
):
	"""Create or update a visit's details (everything except photos, which stream
	separately via add_photo). `order_items`/`competitors` replace the child rows."""
	employee = get_current_employee()
	if name:
		_require_access(name, employee)
		doc = frappe.get_doc("CRM Visit", name)
	else:
		doc = frappe.new_doc("CRM Visit")
		doc.sales_person = employee
		doc.visit_date = visit_date or frappe.utils.today()

	_apply_party(doc, party_type, customer, crm_lead, crm_deal, prospect_name)
	doc.visit_purpose = visit_purpose or doc.visit_purpose or "Follow-up"
	if visit_status:
		doc.visit_status = visit_status
	if planned_date:
		doc.planned_date = planned_date
	for field, value in (
		("contact_name", contact_name),
		("contact_phone", contact_phone),
		("notes", notes),
		("outcome", outcome),
		("next_action", next_action),
		("next_visit_date", next_visit_date),
	):
		if value is not None:
			doc.set(field, value)

	orders = _parse(order_items)
	if orders is not None:
		doc.order_items = []
		for row in orders:
			doc.append("order_items", _clean_order_row(row))

	comps = _parse(competitors)
	if comps is not None:
		doc.competitors = []
		for row in comps:
			doc.append("competitors", _clean_competitor_row(row))

	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "visit_status": doc.visit_status}


def _clean_order_row(row: dict) -> dict:
	return {
		"order_type": row.get("order_type") or "Inquiry",
		"product": row.get("product"),
		"grade": row.get("grade"),
		"quantity_mt": flt(row.get("quantity_mt")),
		"rate_per_mt": flt(row.get("rate_per_mt")),
		"expected_value": flt(row.get("expected_value")),
		"expected_close_date": row.get("expected_close_date") or None,
		"remarks": row.get("remarks"),
	}


def _clean_competitor_row(row: dict) -> dict:
	return {
		"competitor_brand": row.get("competitor_brand"),
		"product_grade": row.get("product_grade"),
		"price_per_mt": flt(row.get("price_per_mt")),
		"stock_status": row.get("stock_status"),
		"remarks": row.get("remarks"),
	}


@frappe.whitelist()
def add_photo(name, content_base64, filename=None, caption=None, latitude=None, longitude=None):
	"""Validate + store a visit photo and append it to the visit's photo grid."""
	employee = get_current_employee()
	_require_access(name, employee)

	raw = content_base64.split(",")[-1] if content_base64 else ""
	content = base64.b64decode(raw)
	fname = filename or "visit-photo.jpg"
	validate_upload(fname, content, images_only=True, max_mb=8)

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": fname,
			"attached_to_doctype": "CRM Visit",
			"attached_to_name": name,
			"content": content,
			"is_private": 1,
		}
	).insert(ignore_permissions=True)

	doc = frappe.get_doc("CRM Visit", name)
	doc.append(
		"photos",
		{
			"image": file_doc.file_url,
			"caption": caption,
			"captured_at": now_datetime(),
			"latitude": flt(latitude) if latitude not in (None, "") else None,
			"longitude": flt(longitude) if longitude not in (None, "") else None,
		},
	)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "image": file_doc.file_url}


# ── reads ───────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_my_visits(scope="mine", status=None, search=None, limit=100):
	"""List visits. scope='mine' → the session rep's visits; scope='team' → whole
	team (managers only, falls back to 'mine' for non-managers)."""
	employee = get_current_employee()
	filters = {}
	if scope == "team" and is_sales_manager():
		pass
	else:
		filters["sales_person"] = employee
	if status:
		filters["visit_status"] = status

	or_filters = None
	if search:
		or_filters = [
			["party_display", "like", f"%{search}%"],
			["contact_name", "like", f"%{search}%"],
			["name", "like", f"%{search}%"],
		]

	return frappe.get_all(
		"CRM Visit",
		filters=filters,
		or_filters=or_filters,
		fields=VISIT_FIELDS,
		order_by="visit_date desc, modified desc",
		limit=int(limit),
	)


@frappe.whitelist()
def get_visit(name):
	"""Full visit detail incl. photos, order/inquiry rows, and competitor rows."""
	employee = get_current_employee()
	_require_access(name, employee)
	doc = frappe.get_doc("CRM Visit", name)
	return {
		"visit": {f: doc.get(f) for f in VISIT_FIELDS if f != "modified"},
		"photos": [
			{
				"image": p.image,
				"caption": p.caption,
				"captured_at": p.captured_at,
				"latitude": p.latitude,
				"longitude": p.longitude,
			}
			for p in doc.photos
		],
		"order_items": [
			{
				"order_type": o.order_type,
				"product": o.product,
				"grade": o.grade,
				"quantity_mt": o.quantity_mt,
				"rate_per_mt": o.rate_per_mt,
				"expected_value": o.expected_value,
				"expected_close_date": o.expected_close_date,
				"remarks": o.remarks,
				"sales_order": o.sales_order,
			}
			for o in doc.order_items
		],
		"competitors": [
			{
				"competitor_brand": c.competitor_brand,
				"product_grade": c.product_grade,
				"price_per_mt": c.price_per_mt,
				"stock_status": c.stock_status,
				"remarks": c.remarks,
			}
			for c in doc.competitors
		],
	}


@frappe.whitelist()
def cancel_visit(name, reason=None):
	employee = get_current_employee()
	_require_access(name, employee)
	doc = frappe.get_doc("CRM Visit", name)
	doc.visit_status = "Cancelled"
	if reason:
		doc.notes = ((doc.notes or "") + f"\n[Cancelled] {reason}").strip()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "visit_status": doc.visit_status}
