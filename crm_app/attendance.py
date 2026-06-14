"""Field attendance — selfie + GPS check-in/out → ERPNext/HR Employee Checkin.

Field reps mark attendance from their phone (no office machine): a selfie + GPS at
day-start (IN) and day-end (OUT). This writes genuine **Employee Checkin** records so
it flows into HR/payroll. The selfie is stored as a private File and referenced from a
custom field. Requires `hrms` (Employee Checkin); guarded so a migrate never breaks.
"""

import base64

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime

from crm_app.api import get_current_employee, validate_upload

DEVICE_ID = "TRIAM A+ CRM PWA"


def _hrms_ready() -> bool:
	return bool(frappe.db.exists("DocType", "Employee Checkin"))


@frappe.whitelist()
def check_in_out(latitude=None, longitude=None, selfie_base64=None, address=None, log_type=None) -> dict:
	"""Record an Employee Checkin (auto-toggles IN/OUT) with GPS + a selfie."""
	employee = get_current_employee()
	if not _hrms_ready():
		frappe.throw(_("Attendance is not available on this site (HR module missing)."))

	if not log_type:
		today = getdate()
		last = frappe.get_all(
			"Employee Checkin",
			filters={"employee": employee, "time": ["between", [f"{today} 00:00:00", f"{today} 23:59:59"]]},
			fields=["log_type"],
			order_by="time desc",
			limit=1,
		)
		log_type = "OUT" if (last and last[0].log_type == "IN") else "IN"

	doc = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"log_type": log_type,
			"time": now_datetime(),
			"device_id": DEVICE_ID,
			"latitude": flt(latitude) if latitude not in (None, "") else None,
			"longitude": flt(longitude) if longitude not in (None, "") else None,
		}
	)
	if address and doc.meta.has_field("custom_check_in_address"):
		doc.custom_check_in_address = address
	doc.insert(ignore_permissions=True)

	# Attach the selfie (optional) and link it from the custom field.
	if selfie_base64:
		content = base64.b64decode(selfie_base64.split(",")[-1])
		validate_upload("selfie.jpg", content, images_only=True, max_mb=6)
		f = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"checkin-{doc.name}.jpg",
				"attached_to_doctype": "Employee Checkin",
				"attached_to_name": doc.name,
				"content": content,
				"is_private": 1,
			}
		).insert(ignore_permissions=True)
		if doc.meta.has_field("custom_selfie"):
			doc.db_set("custom_selfie", f.file_url)

	frappe.db.commit()
	return {"name": doc.name, "log_type": doc.log_type, "time": doc.time}


@frappe.whitelist()
def get_attendance_overview() -> dict:
	"""Today's check-in state + recent check-ins for the logged-in employee."""
	employee = get_current_employee()
	if not _hrms_ready():
		return {"available": False, "next_action": "IN", "logs_today": [], "recent": []}

	today = getdate()
	logs_today = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": ["between", [f"{today} 00:00:00", f"{today} 23:59:59"]]},
		fields=["name", "time", "log_type", "latitude", "longitude"],
		order_by="time asc",
	)
	recent = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee},
		fields=["name", "time", "log_type"],
		order_by="time desc",
		limit=10,
	)
	last = logs_today[-1] if logs_today else None
	next_action = "OUT" if (last and last.log_type == "IN") else "IN"
	first_in = next((x for x in logs_today if x.log_type == "IN"), None)
	last_out = next((x for x in reversed(logs_today) if x.log_type == "OUT"), None)
	return {
		"available": True,
		"next_action": next_action,
		"checked_in": next_action == "OUT",
		"first_in": first_in.time if first_in else None,
		"last_out": last_out.time if last_out else None,
		"logs_today": logs_today,
		"recent": recent,
	}
