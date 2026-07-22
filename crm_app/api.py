"""
crm_app public API.

SECURITY RULE (enforced in every endpoint across crm_app):
  1. The acting sales person is ALWAYS derived from the logged-in session
     (`frappe.session.user`) via `get_current_employee()` — never taken from a
     request parameter.
  2. Reads of own data use session-scoped filters; writes on employee-owned data
     use `ignore_permissions=True` AFTER the session check (the app must not
     depend on the user holding a particular Frappe role — most field staff only
     have minimal roles).
  3. Manager/leadership views gate on a real relationship (reports_to / role),
     not on a free-form id supplied by the caller.

Endpoints are reachable at /api/method/crm_app.api.<function_name>.
"""

import frappe
from frappe import _


def get_current_employee() -> str:
	"""Return the Active Employee linked to the logged-in user, or raise.

	Never trust an `employee` value from the request — always resolve it here.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "status": "Active"},
		"name",
	)
	if not employee:
		frappe.throw(
			_("No active Employee record is linked to your user account."),
			frappe.PermissionError,
		)
	return employee


def is_sales_manager(user: str | None = None) -> bool:
	"""True for users who may see the whole team's field activity."""
	roles = frappe.get_roles(user or frappe.session.user)
	return any(r in roles for r in ("Sales Manager", "Sales Master Manager", "System Manager"))


def owns_customer(employee: str, customer: str) -> bool:
	"""May this rep act on / see this dealer's private data (balances, ledger, receipts)?

	True when the caller is a manager; the dealer is attributed to this rep (rep_customers —
	SAP-invoiced, explicitly assigned, or ordered); OR the dealer is not explicitly assigned
	to anyone. The last clause keeps new/unassigned dealers open — today EVERY dealer is
	unassigned, so this is a no-op that costs the pilot nothing, and it tightens automatically
	into a real cross-rep control as ``custom_assigned_sales_person`` gets populated. A rep is
	blocked only from a dealer explicitly assigned to a DIFFERENT rep whom he never invoiced.
	"""
	if not customer:
		return False
	if is_sales_manager():
		return True
	if has_field("Customer", "custom_assigned_sales_person"):
		assigned = frappe.db.get_value("Customer", customer, "custom_assigned_sales_person")
		if not assigned or assigned == employee:
			return True
		from crm_app.sales_attr import rep_customers

		return customer in rep_customers(employee)
	# No assignment model on this site — ownership can't be scoped, so don't pretend to.
	return True


def assert_customer_access(employee: str, customer: str):
	"""Guard a dealer-scoped read/write; raises PermissionError if the rep may not touch it."""
	if not owns_customer(employee, customer):
		frappe.throw(_("This dealer is assigned to a different sales person."), frappe.PermissionError)


def has_field(doctype: str, fieldname: str) -> bool:
	"""Does this SITE have that field?

	Custom fields are not a given. Ours (``custom_assigned_sales_person``,
	``custom_geo_latitude``…) only exist after our ``after_migrate`` has run, and theirs
	(``Address.latitude``, ``Customer.custom_customer_sap_code``) only exist on their
	sites. Filtering on an absent column does not return nothing — it raises
	``Unknown column`` and takes the whole screen down. This has bitten twice:
	Customer 360 on a site without Address geo, and Collections on a freshly-restored
	production database before migrate.

	Guard every query that touches a custom field with this.
	"""
	try:
		if not frappe.db.exists("DocType", doctype):
			return False
		return bool(frappe.get_meta(doctype).has_field(fieldname))
	except Exception:
		return False


# ── upload safety ─────────────────────────────────────────────────────────────

# Extensions that can host/execute scripts — never accept these as uploads.
DANGEROUS_EXT = {
	"exe", "bat", "cmd", "sh", "js", "mjs", "html", "htm", "svg", "xhtml", "php",
	"phtml", "py", "pl", "rb", "jar", "com", "msi", "dll", "scr", "vbs", "ps1", "jsp", "asp", "aspx",
}
IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif", "heic", "heif", "bmp"}


def validate_upload(filename: str, content: bytes, images_only: bool = False, max_mb: int = 10):
	"""Reject empty/oversized/unsafe uploads. Call before persisting any File."""
	size = len(content or b"")
	if size == 0:
		frappe.throw(_("The file appears to be empty."))
	if size > max_mb * 1024 * 1024:
		frappe.throw(_("File is too large (max {0} MB).").format(max_mb))
	ext = filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else ""
	if ext in DANGEROUS_EXT:
		frappe.throw(_("This file type is not allowed for security reasons."))
	if images_only and ext not in IMAGE_EXT:
		frappe.throw(_("Please upload an image file (JPG, PNG, or WebP)."))

	# Don't trust the extension — inspect the actual bytes (a renamed .exe must fail).
	head = content[:512]
	if head[:2] == b"MZ" or head[:4] == b"\x7fELF" or head[:4] == b"\xca\xfe\xba\xbe":
		frappe.throw(_("Executable files are not allowed."))
	sniff = head.lstrip().lower()
	if sniff.startswith((b"<!doctype html", b"<html", b"<svg", b"<?php", b"<script", b"#!/")):
		frappe.throw(_("This file type is not allowed for security reasons."))
	if images_only:
		# Signature check (works without any library) — defeats a renamed file.
		is_webp = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
		known = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"BM")
		if not (is_webp or any(head.startswith(sig) for sig in known)):
			frappe.throw(_("That doesn't look like a valid image — please upload a real photo."))
		# Deeper decode with Pillow when available (don't block uploads if it isn't).
		try:
			from io import BytesIO

			from PIL import Image

			Image.open(BytesIO(content)).verify()
		except ImportError:
			pass
		except Exception:
			frappe.throw(_("That image appears to be corrupted — please try another."))


@frappe.whitelist()
def ping() -> dict:
	"""Liveness check (no auth required beyond being routed through Frappe)."""
	return {"ok": True, "app": "crm_app", "user": frappe.session.user}


@frappe.whitelist(allow_guest=True)
def asset_manifest() -> dict:
	"""Return the built Vite asset manifest so the service worker can precache every route
	chunk (whole-app offline). Served via /api/method because Frappe's static handler serves
	/assets/** only for whitelisted extensions — a .json there 404s, silently disabling the
	precache. The manifest is just public chunk filenames, so allow_guest is safe.
	"""
	import json
	import os

	path = os.path.join(frappe.get_app_path("crm_app"), "public", "frontend", "manifest.json")
	try:
		with open(path, encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return {}


@frappe.whitelist()
def whoami() -> dict:
	"""Identify the current user and their employee profile."""
	employee = get_current_employee()
	emp = frappe.db.get_value(
		"Employee",
		employee,
		[
			"name",
			"employee_name",
			"designation",
			"department",
			"company",
			"image",
			"user_id",
			"company_email",
			"cell_number",
			"date_of_joining",
		],
		as_dict=True,
	)
	return {
		"user": frappe.session.user,
		"employee": emp,
		"is_sales_manager": is_sales_manager(),
		"is_system_manager": "System Manager" in frappe.get_roles(frappe.session.user),
	}
