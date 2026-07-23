import frappe
from frappe.tests.utils import FrappeTestCase

from crm_app import customers


class TestDealerCategory(FrappeTestCase):
	def setUp(self):
		self.user = frappe.db.get_value("Employee", {"status": "Active", "user_id": ["!=", ""]}, "user_id")
		if not self.user:
			self.skipTest("needs an Active Employee-user")

	def test_categories_shape_and_filter(self):
		frappe.set_user(self.user)
		try:
			cats = customers.dealer_categories()
			self.assertIn("field", cats)
			self.assertIn("categories", cats)
			if not cats["categories"]:
				self.skipTest("no categorised dealers on this site")
			chosen = cats["categories"][0]
			res = customers.search_parties(query="", party_type="", limit=15, category=chosen)
			# A category filter narrows to Customers only, all in the chosen category.
			self.assertTrue(res)
			self.assertTrue(all(r["party_type"] == "Customer" for r in res))
			self.assertTrue(all(r.get("category") == chosen for r in res))
		finally:
			frappe.set_user("Administrator")
