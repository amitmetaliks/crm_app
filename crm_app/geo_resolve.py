"""Resolve dealer/customer coordinates from MULTIPLE signals.

Why this exists: the app originally read only ``Customer.custom_geo_latitude`` — a field
this app added. On the real site that field is empty for **all 1970 customers**, while
**1843 of them** have genuine coordinates on their linked ERPNext **Address**
(``Address.latitude/longitude``, joined through ``Dynamic Link``). So geofence
validation silently never fired and route optimization had no stops to order.

Resolution order (first hit wins):

  1. ``Customer.custom_geo_latitude/longitude`` — set when a rep pins the shop from the
     app; treated as most authoritative because it is the shop door, not the billing desk.
  2. Linked **Address**: primary → shipping → most recently modified.

Mirrors the multi-signal approach in ``sales_attr.py``: read the data where the business
actually keeps it, rather than requiring a backfill before anything works.
"""

import frappe
from frappe.utils import flt

_ADDR_SQL = """
	SELECT dl.link_name AS customer, a.name AS address, a.latitude, a.longitude,
	       a.city, a.address_line1, a.is_primary_address, a.is_shipping_address
	FROM `tabAddress` a
	JOIN `tabDynamic Link` dl ON dl.parent = a.name AND dl.parenttype = 'Address'
	WHERE dl.link_doctype = 'Customer' AND dl.link_name IN %(names)s
	  AND COALESCE(a.latitude, 0) <> 0 AND COALESCE(a.longitude, 0) <> 0
	ORDER BY a.is_primary_address DESC, a.is_shipping_address DESC, a.modified DESC
"""


def _has_custom_geo() -> bool:
	return frappe.db.exists("DocType", "Customer") and frappe.get_meta("Customer").has_field(
		"custom_geo_latitude"
	)


def _from_custom(names):
	"""{customer: coords} for shops a rep has pinned from the app."""
	if not _has_custom_geo():
		return {}
	rows = frappe.get_all(
		"Customer",
		filters={"name": ["in", names]},
		fields=["name", "custom_geo_latitude", "custom_geo_longitude"],
	)
	out = {}
	for r in rows:
		lat, lng = flt(r.custom_geo_latitude), flt(r.custom_geo_longitude)
		if lat and lng:
			out[r.name] = {"lat": lat, "lng": lng, "source": "pinned", "address": None, "city": None}
	return out


def _from_address(names):
	"""{customer: coords} from the linked ERPNext Address (where the real data lives)."""
	if not frappe.db.exists("DocType", "Address"):
		return {}
	rows = frappe.db.sql(_ADDR_SQL, {"names": tuple(names)}, as_dict=True)
	out = {}
	for r in rows:
		# ORDER BY already ranks primary > shipping > newest, so keep the first per customer.
		if r.customer in out:
			continue
		out[r.customer] = {
			"lat": flt(r.latitude),
			"lng": flt(r.longitude),
			"source": "address",
			"address": r.address,
			"city": r.city,
		}
	return out


def coords_for(names) -> dict:
	"""Batch resolve. ``{customer: {lat, lng, source, address, city}}`` — misses omitted."""
	names = [n for n in (names or []) if n]
	if not names:
		return {}
	resolved = _from_address(names)
	resolved.update(_from_custom(names))  # a rep's pin beats the billing address
	return resolved


def customer_coords(name):
	"""Coordinates for one customer, or None if we genuinely have none."""
	return coords_for([name]).get(name)
