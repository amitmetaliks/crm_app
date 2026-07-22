import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from crm_app import idempotency


class TestIdempotencyReservation(FrappeTestCase):
	def test_replay_reserves_then_returns_recorded_response(self):
		key = "test-" + uuid.uuid4().hex

		self.assertIsNone(idempotency.replay(key))
		row = frappe.db.get_value(
			"CRM Idempotency Key",
			{"idempotency_key": key},
			["name", "response"],
			as_dict=True,
		)
		self.assertTrue(row)
		self.assertFalse(row.response)

		result = {"name": "TEST-DOC", "amount": 1250}
		idempotency.record(key, "test.write", result)

		self.assertEqual(idempotency.replay(key), result)
		self.assertEqual(
			frappe.db.get_value("CRM Idempotency Key", row.name, "method"),
			"test.write",
		)

	def test_fresh_empty_reservation_blocks_a_concurrent_retry(self):
		# A sibling attempt that finds a FRESH empty reservation must be told to retry, not
		# repeat the write. (Same-transaction stand-in for the cross-request lock/block.)
		key = "test-" + uuid.uuid4().hex
		self.assertIsNone(idempotency.replay(key))
		with self.assertRaises(frappe.TimestampMismatchError):
			idempotency.replay(key)

	def test_key_is_scoped_to_the_recording_employee(self):
		# The core security property: user B replaying user A's key is denied, never handed
		# A's response or document name. `employee` is a Link, so use two real Employee rows
		# (skip where the test site has fewer than two).
		emps = frappe.get_all("Employee", pluck="name", limit=2)
		if len(emps) < 2:
			self.skipTest("needs two Employee records")
		a, b = emps[0], emps[1]
		key = "test-" + uuid.uuid4().hex
		self.assertIsNone(idempotency.replay(key, employee=a))
		idempotency.record(key, "test.write", {"name": "A-DOC"}, employee=a)

		# The rightful owner replays their own response.
		self.assertEqual(idempotency.replay(key, employee=a), {"name": "A-DOC"})
		# A different employee is refused.
		with self.assertRaises(frappe.PermissionError):
			idempotency.replay(key, employee=b)
