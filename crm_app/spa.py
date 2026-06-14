"""Serve the Amit Alliance CRM single-page app.

We use a custom page renderer (instead of a www template) so the SPA entry is
served directly from the built file. This avoids Jinja PackageLoader issues with
editable installs and behaves identically in dev and production.

Note the route is ``amit-crm`` so it never collides with Frappe CRM's own SPA at
``/crm``.
"""

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer

ROUTE = "amit-crm"


class SPARenderer(BaseRenderer):
	def can_render(self) -> bool:
		return self.path == ROUTE or self.path.startswith(ROUTE + "/")

	def render(self):
		index_path = frappe.get_app_path("crm_app", "public", "frontend", "index.html")
		with open(index_path, encoding="utf-8") as f:
			html = f.read()

		# Inject the session CSRF token so the SPA can make authenticated POST requests.
		csrf = ""
		if frappe.session and frappe.session.user and frappe.session.user != "Guest":
			try:
				from frappe.sessions import get_csrf_token

				csrf = get_csrf_token()
			except Exception:
				csrf = frappe.local.session.data.get("csrf_token", "") if frappe.local.session else ""

		boot = (
			"<script>"
			f'window.csrf_token = "{csrf}";'
			f'window.frappe_user = "{frappe.session.user if frappe.session else "Guest"}";'
			"</script>"
		)
		html = html.replace("</head>", boot + "</head>")

		return self.build_response(html, headers={"Content-Type": "text/html; charset=utf-8"})
