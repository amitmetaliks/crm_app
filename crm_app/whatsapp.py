"""WhatsApp Business Cloud API (Meta) integration.

Config (set on the site, NOT in code):
  bench --site <site> set-config crm_whatsapp_token "<permanent-access-token>"
  bench --site <site> set-config crm_whatsapp_phone_id "<phone-number-id>"
  bench --site <site> set-config crm_whatsapp_reminder_template "payment_reminder"

Proactive messages (e.g. payment reminders to a dealer who hasn't messaged us in 24h)
MUST use a Meta-APPROVED template. Plain text only works inside the 24h customer-reply
window. When not configured, callers fall back to free wa.me deep-links.
"""

import frappe
from frappe import _
from frappe.utils import flt

from crm_app.api import get_current_employee


def _cfg():
	return frappe.conf.get("crm_whatsapp_token"), frappe.conf.get("crm_whatsapp_phone_id")


def configured():
	t, p = _cfg()
	return bool(t and p)


@frappe.whitelist()
def is_configured():
	get_current_employee()
	return {"configured": configured()}


def _norm(phone):
	p = "".join(ch for ch in str(phone or "") if ch.isdigit())
	if len(p) == 10:
		p = "91" + p
	elif len(p) == 11 and p.startswith("0"):
		p = "91" + p[1:]
	return p


def _post(payload):
	import requests

	token, phone_id = _cfg()
	if not (token and phone_id):
		frappe.throw(_("WhatsApp API is not configured on this site."))
	url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
	r = requests.post(
		url,
		headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
		json=payload,
		timeout=20,
	)
	if r.status_code >= 300:
		frappe.log_error(title="WhatsApp send failed", message=r.text)
		frappe.throw(_("WhatsApp send failed (see error log)."))
	return r.json()


@frappe.whitelist()
def send_text(to, message):
	"""Plain text — only delivered inside the 24h customer-initiated window."""
	get_current_employee()
	to = _norm(to)
	if not to:
		frappe.throw(_("No phone number."))
	return _post({"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}})


@frappe.whitelist()
def send_template(to, template, params=None, lang="en"):
	"""Proactive message via a Meta-approved template. params = list of body variables."""
	get_current_employee()
	to = _norm(to)
	if not to:
		frappe.throw(_("No phone number."))
	import json as _json

	if isinstance(params, str):
		params = _json.loads(params or "[]")
	components = []
	if params:
		components = [{"type": "body", "parameters": [{"type": "text", "text": str(p)} for p in params]}]
	return _post(
		{
			"messaging_product": "whatsapp",
			"to": to,
			"type": "template",
			"template": {"name": template, "language": {"code": lang}, "components": components},
		}
	)


@frappe.whitelist()
def send_payment_reminder(customer):
	"""Send a dealer their outstanding via the configured reminder template."""
	get_current_employee()
	if not configured():
		frappe.throw(_("WhatsApp API not configured — use the in-app share button instead."))
	cust = frappe.db.get_value("Customer", customer, ["customer_name", "mobile_no"], as_dict=True)
	if not cust or not cust.mobile_no:
		frappe.throw(_("This customer has no mobile number on file."))
	outstanding = 0.0
	if frappe.db.exists("DocType", "Sales Invoice"):
		rows = frappe.get_all(
			"Sales Invoice",
			filters={"customer": customer, "docstatus": 1, "outstanding_amount": [">", 0]},
			fields=["outstanding_amount"],
			limit=2000,
		)
		outstanding = flt(sum(flt(r.outstanding_amount) for r in rows), 2)
	template = frappe.conf.get("crm_whatsapp_reminder_template") or "payment_reminder"
	return send_template(cust.mobile_no, template, params=[cust.customer_name, f"{outstanding:,.0f}"])
