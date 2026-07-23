import frappe
from frappe.tests.utils import FrappeTestCase

from crm_app import customers

# A name that has no CRM Visit rows, so the follow-up branch (rule 2) is a deterministic miss
# and the other rules are exercised in isolation.
NONE = "TEST-NO-SUCH-DEALER"


class TestCustomerNextAction(FrappeTestCase):
	def test_owes_money_recommends_collect(self):
		na = customers._recommended_action(NONE, "X Dealer", 15000, "2026-06-01", False, 15000, 5, 10, 2)
		self.assertEqual(na["cta"], "Collect")
		self.assertEqual(na["tone"], "urgent")
		self.assertEqual(na["route"]["name"], "Collect")

	def test_quiet_active_dealer_recommends_winback(self):
		na = customers._recommended_action(NONE, "X", 0, None, False, 0, 3, 120, 5)
		self.assertEqual(na["label"], "Win back")
		self.assertEqual(na["route"]["name"], "NewVisit")

	def test_active_never_visited_recommends_introduce(self):
		na = customers._recommended_action(NONE, "X", 0, None, False, 0, 4, 10, 0)
		self.assertEqual(na["label"], "Introduce yourself")

	def test_in_credit_recommends_push_order(self):
		na = customers._recommended_action(NONE, "X", 0, None, True, -50000, 0, None, 3)
		self.assertEqual(na["label"], "Push an order")

	def test_default_recommends_log_visit(self):
		na = customers._recommended_action(NONE, "X", 0, None, False, 0, 0, None, 3)
		self.assertEqual(na["label"], "Log a visit")
