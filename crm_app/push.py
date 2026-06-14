"""Self-hosted Web Push (VAPID) — no third-party push service.

VAPID keys are generated once and stored in the site config. Browser push
subscriptions are stored per-user in CRM Push Subscription.

This mirrors hr_app's push implementation; the two apps keep independent
subscription stores so they can be installed/uninstalled separately.
"""

import base64
import json

import frappe


def _to_b64url_der(private_key_str: str) -> str:
	"""pywebpush expects the VAPID private key as base64url-encoded PKCS8 DER.
	Convert from PEM if needed (and leave already-DER values unchanged)."""
	if "BEGIN" not in private_key_str:
		return private_key_str
	from cryptography.hazmat.primitives import serialization

	key = serialization.load_pem_private_key(private_key_str.encode(), password=None)
	der = key.private_bytes(
		encoding=serialization.Encoding.DER,
		format=serialization.PrivateFormat.PKCS8,
		encryption_algorithm=serialization.NoEncryption(),
	)
	return base64.urlsafe_b64encode(der).rstrip(b"=").decode()


def _ensure_vapid() -> dict:
	"""Return VAPID keys, generating + persisting them on first use.

	Private key is stored as base64url PKCS8 DER (the format pywebpush needs).
	The keys are shared at the site level (crm_app reuses any keys hr_app created).
	"""
	from frappe.installer import update_site_config

	public = frappe.conf.get("vapid_public_key")
	private = frappe.conf.get("vapid_private_key")
	if public and private:
		fixed = _to_b64url_der(private)
		if fixed != private:
			update_site_config("vapid_private_key", fixed)
			private = fixed
		return {"public": public, "private": private}

	from cryptography.hazmat.primitives import serialization
	from py_vapid import Vapid01

	v = Vapid01()
	v.generate_keys()
	raw_pub = v.public_key.public_bytes(
		serialization.Encoding.X962,
		serialization.PublicFormat.UncompressedPoint,
	)
	public = base64.urlsafe_b64encode(raw_pub).rstrip(b"=").decode()
	der = v.private_key.private_bytes(
		encoding=serialization.Encoding.DER,
		format=serialization.PrivateFormat.PKCS8,
		encryption_algorithm=serialization.NoEncryption(),
	)
	private = base64.urlsafe_b64encode(der).rstrip(b"=").decode()

	update_site_config("vapid_public_key", public)
	update_site_config("vapid_private_key", private)
	return {"public": public, "private": private}


@frappe.whitelist()
def get_vapid_public_key() -> dict:
	# Per-user feature; any logged-in user may enable notifications.
	return {"public_key": _ensure_vapid()["public"]}


@frappe.whitelist()
def save_push_subscription(subscription) -> dict:
	"""Persist a browser PushSubscription for the logged-in user."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(frappe._("Login required"), frappe.PermissionError)
	if isinstance(subscription, str):
		subscription = json.loads(subscription)

	endpoint = subscription.get("endpoint")
	keys = subscription.get("keys", {})
	if not endpoint:
		frappe.throw("Invalid subscription")

	existing = frappe.db.get_value("CRM Push Subscription", {"endpoint": endpoint}, "name")
	doc = (
		frappe.get_doc("CRM Push Subscription", existing)
		if existing
		else frappe.new_doc("CRM Push Subscription")
	)
	doc.user = user
	doc.endpoint = endpoint
	doc.p256dh = keys.get("p256dh")
	doc.auth = keys.get("auth")
	doc.enabled = 1
	doc.user_agent = (frappe.request.headers.get("User-Agent") if frappe.request else "")[:140]
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def disable_push() -> dict:
	user = frappe.session.user
	for name in frappe.get_all("CRM Push Subscription", {"user": user}, pluck="name"):
		frappe.delete_doc("CRM Push Subscription", name, ignore_permissions=True, force=True)
	frappe.db.commit()
	return {"ok": True}


def send_push_to_user(user: str, title: str, body: str = "", url: str = "/amit-crm"):
	"""Send a web-push notification to all of a user's subscribed devices.

	Safe to call from server code; failures are logged, never raised.
	"""
	subs = frappe.get_all(
		"CRM Push Subscription",
		filters={"user": user, "enabled": 1},
		fields=["name", "endpoint", "p256dh", "auth"],
	)
	if not subs:
		return

	try:
		from pywebpush import WebPushException, webpush
	except Exception:
		frappe.log_error(title="pywebpush not installed", message="Install pywebpush in the bench env")
		return

	vapid = _ensure_vapid()
	payload = json.dumps({"title": title, "body": body, "url": url})
	claims = {"sub": f"mailto:{frappe.conf.get('vapid_email', 'developments@amitalliance.com')}"}

	for s in subs:
		try:
			webpush(
				subscription_info={
					"endpoint": s.endpoint,
					"keys": {"p256dh": s.p256dh, "auth": s.auth},
				},
				data=payload,
				vapid_private_key=vapid["private"],
				vapid_claims=dict(claims),
			)
		except WebPushException as e:
			status = getattr(getattr(e, "response", None), "status_code", None)
			if status in (404, 410):
				frappe.delete_doc("CRM Push Subscription", s.name, ignore_permissions=True, force=True)
			else:
				frappe.log_error(title="Web push failed", message=str(e))
		except Exception as e:
			frappe.log_error(title="Web push error", message=str(e))
	frappe.db.commit()
