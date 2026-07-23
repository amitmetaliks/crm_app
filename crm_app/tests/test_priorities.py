import frappe
from frappe.tests.utils import FrappeTestCase

from crm_app import priorities


class TestPriorities(FrappeTestCase):
	def test_shape_and_item_contract(self):
		# Runs as a real rep (whose priorities are computed from their own data). Skips on a
		# site with no employee-linked user.
		rep = frappe.db.get_value(
			"Employee", {"status": "Active", "user_id": ["!=", ""]}, ["name", "user_id"], as_dict=True
		)
		if not rep:
			self.skipTest("needs an Active Employee linked to a User")

		frappe.set_user(rep.user_id)
		try:
			out = priorities.get_priorities()
		finally:
			frappe.set_user("Administrator")

		self.assertIn("items", out)
		self.assertIsInstance(out["items"], list)
		self.assertIn("as_of", out)
		# Every surfaced action must be explainable and routable — no bare/opaque items.
		for it in out["items"]:
			self.assertIn(it.get("type"), ("collection", "followup", "beat"))
			self.assertTrue(it.get("reason"))
			self.assertTrue(it.get("title"))
			self.assertIn("name", it.get("route", {}))

	def test_requires_authentication(self):
		# No Employee behind the session -> the endpoint refuses (never returns another rep's work).
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				priorities.get_priorities()
		finally:
			frappe.set_user("Administrator")
