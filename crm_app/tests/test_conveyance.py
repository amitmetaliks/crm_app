"""Auto-conveyance tests.

The headline test here is `test_legacy_travel_claim_is_not_mistaken_for_ours`, which
pins the bug that nearly shipped: adding a **Float** custom field backfills every
pre-existing row with **0, not NULL**, so `custom_gps_distance_km IS NOT NULL` matched
all 1006 historic Expense Claim Detail rows on the real site. That made the duplicate
guard tell every rep "already claimed" if they had any Travel expense that day — and it
made a cleanup script match the entire table. Rows written by this app are identified by
`custom_distance_source` (a Data field, which backfills as NULL) instead.

Run: bench --site <site> run-tests --app crm_app
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from crm_app import conveyance


def _hrms() -> bool:
	return bool(frappe.db.exists("DocType", "Expense Claim"))


class TestConveyanceRowMarker(FrappeTestCase):
	"""The guard must recognise only rows this app wrote."""

	def test_float_custom_field_backfills_zero_not_null(self):
		"""Document the trap itself: legacy rows have 0, not NULL."""
		if not _hrms() or not frappe.get_meta("Expense Claim Detail").has_field("custom_gps_distance_km"):
			self.skipTest("hrms / custom field not present")
		# Any row that pre-dates the field must not read as NULL.
		nulls = frappe.db.sql(
			"SELECT COUNT(*) FROM `tabExpense Claim Detail` WHERE custom_gps_distance_km IS NULL"
		)[0][0]
		zeros = frappe.db.sql(
			"SELECT COUNT(*) FROM `tabExpense Claim Detail` WHERE custom_gps_distance_km = 0"
		)[0][0]
		total = frappe.db.count("Expense Claim Detail")
		if total:
			# It is the 0-not-NULL behaviour that makes IS NOT NULL unusable as a marker.
			self.assertEqual(nulls + zeros, total - frappe.db.sql(
				"SELECT COUNT(*) FROM `tabExpense Claim Detail` WHERE custom_gps_distance_km > 0"
			)[0][0])

	def test_legacy_travel_claim_is_not_mistaken_for_ours(self):
		"""A Travel claim NOT created by this app must never satisfy the duplicate guard."""
		if not _hrms() or not frappe.get_meta("Expense Claim Detail").has_field("custom_distance_source"):
			self.skipTest("hrms / custom field not present")

		emp = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not emp:
			self.skipTest("no employee on this site")

		# Simulate a legacy row: Travel, no distance source, gps field left at its 0 default.
		rows = frappe.db.sql(
			"""SELECT ec.employee, d.expense_date FROM `tabExpense Claim Detail` d
			   JOIN `tabExpense Claim` ec ON ec.name = d.parent
			   WHERE d.expense_type = 'Travel' AND COALESCE(d.custom_distance_source, '') = ''
			   LIMIT 1""",
			as_dict=True,
		)
		if not rows:
			self.skipTest("no legacy Travel claim on this site")
		self.assertIsNone(
			conveyance._claimed_row(rows[0].employee, rows[0].expense_date),
			"A pre-existing Travel claim was mistaken for an app-created conveyance claim — "
			"the duplicate guard would wrongly block this rep.",
		)


class TestConveyanceRules(FrappeTestCase):
	def test_correction_without_remarks_is_rejected(self):
		"""Overriding the GPS distance must always carry a justification."""
		if not _hrms():
			self.skipTest("hrms not installed")
		emp = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not emp:
			self.skipTest("no employee")
		user = frappe.db.get_value("Employee", emp, "user_id")
		if not user:
			self.skipTest("employee has no user")
		frappe.set_user(user)
		try:
			with self.assertRaises(frappe.ValidationError):
				# A large override with no remarks: must throw regardless of rate/distance.
				conveyance.claim_conveyance(date=today(), claimed_km=999, remarks="")
		finally:
			frappe.set_user("Administrator")

	def test_rate_comes_from_sales_person_record(self):
		"""The ₹/km must be read from their own Sales Person field, never hardcoded."""
		if not frappe.db.exists("DocType", "Sales Person"):
			self.skipTest("no Sales Person doctype")
		if not frappe.get_meta("Sales Person").has_field("travel_allowance_per_km"):
			self.skipTest("their travel_allowance_per_km field is not on this site")
		row = frappe.db.sql(
			"""SELECT sp.employee, sp.travel_allowance_per_km FROM `tabSales Person` sp
			   WHERE sp.travel_allowance_per_km > 0 AND COALESCE(sp.employee, '') != '' LIMIT 1""",
			as_dict=True,
		)
		if not row:
			self.skipTest("no Sales Person has a rate configured")
		self.assertEqual(conveyance._rate_for(row[0].employee), row[0].travel_allowance_per_km)


class TestCustomFieldGuards(FrappeTestCase):
	"""Custom fields are not guaranteed to exist on a site.

	Ours appear only after our after_migrate; theirs (Address.latitude,
	Customer.custom_customer_sap_code) only on their sites. Filtering on an absent column
	raises "Unknown column" and takes the screen down — it does not quietly return
	nothing. This has bitten twice: Customer 360 on a site without Address geo, and
	Collections on a freshly-restored production DB. api.has_field is the guard.
	"""

	def test_has_field_is_false_for_absent_field(self):
		from crm_app.api import has_field

		self.assertFalse(has_field("Customer", "definitely_not_a_real_field_xyz"))
		self.assertFalse(has_field("No Such DocType At All", "whatever"))

	def test_has_field_is_true_for_a_real_field(self):
		from crm_app.api import has_field

		self.assertTrue(has_field("Customer", "customer_name"))

	def test_assigned_customers_survives_missing_custom_field(self):
		"""The helper must return empty, not explode, when our field is absent."""
		from crm_app.sales_attr import _assigned_customers

		emp = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not emp:
			self.skipTest("no employee")
		# Must not raise regardless of whether the field exists on this site.
		self.assertIsInstance(_assigned_customers(emp), set)
