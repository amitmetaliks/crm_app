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
from frappe.utils import add_to_date, flt, now_datetime

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


# send_text / send_template are INTERNAL helpers — deliberately NOT @frappe.whitelist().
#
# Whitelisting them let any logged-in employee POST an arbitrary recipient AND arbitrary
# body/template to Meta on the company's paid WhatsApp account: spam, phishing from the
# company number, and uncapped cost, with no product feature using them (the app sends
# rep-to-dealer messages via free wa.me deep links, and dunning via send_payment_reminder
# below, which builds its own content from a Customer record).
#
# So these stay as building blocks that only trusted server-side callers may use. Any
# future feature that needs a free send must expose its OWN whitelisted endpoint that
# validates the recipient against a known party and constructs the message itself.
def send_text(to, message):
	"""Plain text — only delivered inside the 24h customer-initiated window. INTERNAL."""
	to = _norm(to)
	if not to:
		frappe.throw(_("No phone number."))
	return _post({"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}})


def send_template(to, template, params=None, lang="en"):
	"""Proactive message via a Meta-approved template. params = body variables. INTERNAL."""
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


# Minimum gap between two reminders to the SAME dealer, in hours. A dealer messaged twice
# in an afternoon (a double tap, or two reps) is a real complaint waiting to happen and a
# wasted paid template; override per-site with `crm_reminder_min_gap_hours` if needed.
REMINDER_MIN_GAP_HOURS = 12


@frappe.whitelist()
def send_payment_reminder(customer):
	"""Send a dealer their REAL outstanding (from SAP) via the approved reminder template.

	This is a paid, proactive message from the company's number, so it is fenced in:

	  * amount comes from the SAP receivable balance — NOT ERPNext Sales Invoices, which
	    hold ₹0 on this business (invoicing lives in SAP), so the old code messaged every
	    dealer "outstanding: 0";
	  * refuses to send when the balance is zero, a credit, or unknown — a "you owe ₹0"
	    dunning message is worse than none;
	  * a rep may only remind a dealer that is actually theirs; managers may remind anyone;
	  * one reminder per dealer per `REMINDER_MIN_GAP_HOURS`, so a double-tap or two reps
	    can't spam the dealer or the paid quota;
	  * every send is logged with who sent it and the amount.
	"""
	from crm_app import sap_receivables
	from crm_app.api import is_sales_manager

	employee = get_current_employee()
	if not configured():
		frappe.throw(_("WhatsApp API not configured — use the in-app share button instead."))
	cust = frappe.db.get_value("Customer", customer, ["customer_name", "mobile_no"], as_dict=True)
	if not cust:
		frappe.throw(_("Unknown customer."))
	if not cust.mobile_no:
		frappe.throw(_("This customer has no mobile number on file."))

	# Ownership: a rep may only dun their own dealers; a manager may dun anyone.
	if not is_sales_manager():
		from crm_app import sap_sales

		if customer not in sap_sales.rep_customers(employee):
			frappe.throw(_("You can only send a reminder to a dealer in your own territory."))

	# Real balance, from SAP. Refuse anything that isn't a genuine positive due.
	bal = sap_receivables.customer_balance(customer)
	outstanding = flt(bal.get("balance")) if bal else 0.0
	if not bal:
		frappe.throw(_("No receivable balance is available for this dealer yet — cannot send a reminder."))
	if outstanding <= 0:
		frappe.throw(_("This dealer has nothing outstanding ({0}) — no reminder sent.").format(f"₹{outstanding:,.0f}"))

	# Rate-limit / duplicate-prevention per dealer.
	gap = flt(frappe.conf.get("crm_reminder_min_gap_hours") or REMINDER_MIN_GAP_HOURS)
	if gap > 0 and frappe.db.exists("DocType", "CRM Payment Reminder Log"):
		since = add_to_date(now_datetime(), hours=-gap)
		recent = frappe.db.get_value(
			"CRM Payment Reminder Log",
			{"customer": customer, "sent_at": [">=", since]},
			["sent_at"],
		)
		if recent:
			frappe.throw(_("A reminder was already sent to this dealer recently. Please wait before sending another."))

	template = frappe.conf.get("crm_whatsapp_reminder_template") or "payment_reminder"
	resp = send_template(cust.mobile_no, template, params=[cust.customer_name, f"{outstanding:,.0f}"])

	# Record the send (who, how much) — best-effort; a logging miss must not fail the send.
	if frappe.db.exists("DocType", "CRM Payment Reminder Log"):
		try:
			frappe.get_doc(
				{
					"doctype": "CRM Payment Reminder Log",
					"customer": customer,
					"employee": employee,
					"amount": outstanding,
					"mobile_no": cust.mobile_no,
					"sent_at": now_datetime(),
				}
			).insert(ignore_permissions=True)
			frappe.db.commit()
		except Exception:
			frappe.log_error(title="Payment reminder log failed", message=frappe.get_traceback())

	return {"sent": True, "outstanding": outstanding, "as_of": bal.get("as_of")}
