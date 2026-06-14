"""Foreground location tracking + auto distance (for travel allowance).

PWA limitation (documented): location is only captured while the app is OPEN — pings
on an interval plus at each visit/check-in. Day distance is the haversine sum of the
day's points. True always-on background tracking needs a native wrapper.
"""

import frappe
from frappe.utils import flt, getdate, now_datetime, today

from crm_app.api import get_current_employee, is_sales_manager


def _haversine_km(a, b):
	import math

	R = 6371.0
	p1, p2 = math.radians(a[0]), math.radians(b[0])
	dp, dl = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
	h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
	return 2 * R * math.asin(math.sqrt(h))


@frappe.whitelist()
def record_ping(latitude, longitude, accuracy=None, source="ping"):
	"""Store a foreground location ping for the session rep."""
	emp = get_current_employee()
	if latitude in (None, "") or longitude in (None, ""):
		return {"ok": False}
	frappe.get_doc(
		{
			"doctype": "CRM Location Ping",
			"sales_person": emp,
			"time": now_datetime(),
			"latitude": flt(latitude),
			"longitude": flt(longitude),
			"accuracy": flt(accuracy) if accuracy not in (None, "") else None,
			"source": source,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


def _day_points(emp, day):
	return frappe.get_all(
		"CRM Location Ping",
		filters={"sales_person": emp, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
		fields=["time", "latitude", "longitude"],
		order_by="time asc",
		limit=5000,
	)


def _distance_km(points):
	dist = 0.0
	prev = None
	for p in points:
		if p.latitude is None or p.longitude is None:
			continue
		cur = (flt(p.latitude), flt(p.longitude))
		if prev:
			dist += _haversine_km(prev, cur)
		prev = cur
	return flt(dist, 2)


@frappe.whitelist()
def get_day_route(date=None, employee=None):
	"""Day route + total distance (km) for a rep. Managers may pass an employee."""
	me = get_current_employee()
	day = date or today()
	emp = me
	if employee and is_sales_manager():
		emp = employee
	points = _day_points(emp, day)
	stops = frappe.get_all(
		"CRM Visit",
		filters={"sales_person": emp, "visit_date": day},
		fields=["name", "party_display", "check_in_time", "check_in_latitude", "check_in_longitude", "visit_status"],
		order_by="check_in_time asc",
	)
	return {
		"date": day,
		"employee": emp,
		"distance_km": _distance_km(points),
		"points": len(points),
		"stops": stops,
	}


@frappe.whitelist()
def get_team_distance(date=None):
	"""Per-rep distance for the day (managers)."""
	get_current_employee()
	if not is_sales_manager():
		frappe.throw(frappe._("Managers only."), frappe.PermissionError)
	day = date or today()
	reps = frappe.get_all(
		"CRM Location Ping",
		filters={"time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
		fields=["sales_person"],
		group_by="sales_person",
	)
	out = []
	for r in reps:
		pts = _day_points(r.sales_person, day)
		out.append(
			{
				"sales_person": r.sales_person,
				"sales_person_name": frappe.db.get_value("Employee", r.sales_person, "employee_name"),
				"distance_km": _distance_km(pts),
			}
		)
	return sorted(out, key=lambda x: x["distance_km"], reverse=True)
