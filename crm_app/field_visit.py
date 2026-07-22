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
	"within_geofence",
	"check_in_distance_m",
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


def _haversine_m(lat1, lng1, lat2, lng2):
	import math

	R = 6371000
	p1, p2 = math.radians(lat1), math.radians(lat2)
	dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
	a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
	return 2 * R * math.asin(math.sqrt(a))


def _geofence(party_type, customer, lat, lng, radius_m=None):
	"""Return (within(0/1), distance_m) vs the dealer's location, or (None, None).

	Coordinates come from geo_resolve, which also reads the linked ERPNext Address —
	that is where 1843 of 1970 real dealers actually have coordinates. Reading only our
	own custom field (empty on every real customer) made this check silently no-op.

	Radius defaults to 300 m but is configurable via ``crm_geofence_radius_m`` in site config
	— many dealers' Address is a billing/accounts office, not the shop, so a site may need a
	wider tolerance to avoid false 'outside geofence' flags.
	"""
	if radius_m is None:
		radius_m = flt(frappe.conf.get("crm_geofence_radius_m")) or 300
	if party_type != "Customer" or not customer or lat in (None, "") or lng in (None, ""):
		return (None, None)
	from crm_app.geo_resolve import customer_coords

	g = customer_coords(customer)
	if not g:
		return (None, None)
	d = _haversine_m(flt(lat), flt(lng), g["lat"], g["lng"])
	return (1 if d <= radius_m else 0, int(d))


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
	within, dist = _geofence(doc.party_type, doc.customer, latitude, longitude)
	if within is not None:
		doc.within_geofence = within
		doc.check_in_distance_m = dist
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {
		"name": doc.name,
		"visit_status": doc.visit_status,
		"check_in_time": doc.check_in_time,
		"within_geofence": doc.within_geofence,
		"distance_m": doc.check_in_distance_m,
	}


@frappe.whitelist()
def check_out(name, latitude=None, longitude=None):
	"""Stamp the GPS check-out, mark the visit Completed, and compute its duration."""
	employee = get_current_employee()
	_require_access(name, employee)
	doc = frappe.get_doc("CRM Visit", name)
	# Precondition guards: a Cancelled/Missed visit must not receive a check-out, and a visit
	# with no check-in produces a meaningless (0-clamped) duration — surface that instead of
	# silently recording it.
	if doc.visit_status in ("Cancelled", "Missed"):
		frappe.throw(_("This visit was {0} — it can't be checked out.").format(doc.visit_status))
	if not doc.check_in_time:
		frappe.throw(_("Please check in before checking out."))
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
def submit_full_visit(payload):
	"""Create a COMPLETE visit in one call (party, check-in/out, notes, orders,
	competitors, photos[]). Used by the offline queue so a whole visit syncs at once.
	Idempotent-ish: a client_ref dedupes replays."""
	employee = get_current_employee()
	data = _parse(payload) or {}

	client_ref = data.get("client_ref")
	visit_name = data.get("visit_name")

	# Replay safety for the whole submission. The offline queue retries a write whose response
	# was lost; keyed on the stable client_ref, a retry returns the prior result instead of
	# re-running — which on the UPDATE path below would otherwise re-attach every photo again.
	from crm_app import idempotency

	if client_ref:
		prior = idempotency.replay(client_ref, employee)
		if prior is not None:
			return prior

	# Update the visit that was created online at check-in, if its name was passed and it is
	# ours — this is what stops an online check-in followed by an OFFLINE check-out from
	# creating a SECOND visit. Otherwise dedupe replays by client_ref; otherwise create fresh.
	is_update = False
	if (
		visit_name
		and frappe.db.exists("CRM Visit", visit_name)
		and frappe.db.get_value("CRM Visit", visit_name, "sales_person") == employee
	):
		doc = frappe.get_doc("CRM Visit", visit_name)
		# Replace ONLY the child tables the payload actually carries, so a partial payload
		# can't silently wipe order lines/competitors captured elsewhere on the visit.
		if data.get("order_items") is not None:
			doc.set("order_items", [])
		if data.get("competitors") is not None:
			doc.set("competitors", [])
		is_update = True
	elif client_ref:
		existing = frappe.db.get_value("CRM Visit", {"sales_person": employee, "client_ref": client_ref}, "name")
		if existing:
			return {"name": existing, "duplicate": True}
		doc = frappe.new_doc("CRM Visit")
		doc.sales_person = employee
	else:
		doc = frappe.new_doc("CRM Visit")
		doc.sales_person = employee
	doc.visit_date = data.get("visit_date") or doc.get("visit_date") or frappe.utils.today()
	_apply_party(
		doc, data.get("party_type"), data.get("customer"), data.get("crm_lead"),
		data.get("crm_deal"), data.get("prospect_name"),
	)
	for f in ("visit_purpose", "contact_name", "contact_phone", "notes", "outcome", "next_action", "next_visit_date"):
		if data.get(f) is not None:
			doc.set(f, data.get(f))
	doc.visit_purpose = doc.visit_purpose or "Follow-up"
	doc.visit_status = data.get("visit_status") or "Completed"
	if data.get("check_in_time"):
		doc.check_in_time = data["check_in_time"]
		doc.check_in_latitude = flt(data.get("check_in_latitude")) if data.get("check_in_latitude") not in (None, "") else None
		doc.check_in_longitude = flt(data.get("check_in_longitude")) if data.get("check_in_longitude") not in (None, "") else None
		within, dist = _geofence(doc.party_type, doc.customer, data.get("check_in_latitude"), data.get("check_in_longitude"))
		if within is not None:
			doc.within_geofence = within
			doc.check_in_distance_m = dist
	if data.get("check_out_time"):
		doc.check_out_time = data["check_out_time"]
		doc.check_out_latitude = flt(data.get("check_out_latitude")) if data.get("check_out_latitude") not in (None, "") else None
		doc.check_out_longitude = flt(data.get("check_out_longitude")) if data.get("check_out_longitude") not in (None, "") else None
	if doc.meta.has_field("client_ref"):
		doc.client_ref = client_ref
	for row in data.get("order_items") or []:
		doc.append("order_items", _clean_order_row(row))
	for row in data.get("competitors") or []:
		doc.append("competitors", _clean_competitor_row(row))
	if is_update:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)

	for ph in data.get("photos") or []:
		b64 = ph.get("content_base64") if isinstance(ph, dict) else ph
		if not b64:
			continue
		try:
			content = base64.b64decode(b64.split(",")[-1])
			validate_upload("visit.jpg", content, images_only=True, max_mb=8)
			f = frappe.get_doc(
				{"doctype": "File", "file_name": f"visit-{doc.name}-{len(doc.photos)}.jpg",
				 "attached_to_doctype": "CRM Visit", "attached_to_name": doc.name, "content": content, "is_private": 1}
			).insert(ignore_permissions=True)
			doc.append("photos", {"image": f.file_url, "captured_at": now_datetime()})
		except Exception:
			frappe.log_error(title="offline visit photo failed", message=frappe.get_traceback())
	if doc.photos:
		doc.save(ignore_permissions=True)
	result = {"name": doc.name, "updated": is_update}
	# Remember this submission so a queue retry replays it instead of re-attaching photos.
	idempotency.record(client_ref, "field_visit.submit_full_visit", result, employee)
	frappe.db.commit()
	return result


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
