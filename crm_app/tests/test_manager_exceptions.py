import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_first_day, get_last_day, getdate, today

from crm_app import manager


class TestManagerExceptions(FrappeTestCase):
	def test_ranking_and_drilldown_from_dashboard_values(self):
		# Feed a representative dashboard payload; the DB-backed branches (beat, at-risk) add
		# nothing on a clean test site, so the mock-driven exceptions are deterministic.
		out = {
			"pending_approvals": 3,
			"receivables": {
				"available": True,
				"total": 5000000,
				"dealers": 2,
				"top": [
					{"customer": "C1", "customer_name": "Dealer One", "outstanding": 3000000},
					{"customer": "C2", "customer_name": "Dealer Two", "outstanding": 2000000},
				],
			},
			"feeds": {
				"sales": {"available": True, "stale": True, "days_behind": 9},
				"payments": {"available": True, "stale": False},
			},
			"target": {"amount": 1000000, "amount_pct": 10.0},
			"coverage_quality": {"available": True, "reps_total": 28, "reps_matched": 13},
		}
		frm = get_first_day(getdate(today()))
		to = get_last_day(frm)
		ex = manager._manager_exceptions(out, frm, to)

		types = [e["type"] for e in ex]
		self.assertIn("approvals", types)
		self.assertIn("collection", types)  # biggest debtor surfaced
		self.assertIn("feed", types)  # stale sales feed surfaced (payments not stale -> not)
		self.assertIn("attribution", types)

		# Ranked: every high before every medium before every low.
		rank = {"high": 0, "medium": 1, "low": 2}
		sevs = [rank[e["severity"]] for e in ex]
		self.assertEqual(sevs, sorted(sevs))

		# A collection exception drills into the dealer and carries the amount.
		col = next(e for e in ex if e["type"] == "collection")
		self.assertEqual(col["route"]["name"], "CustomerDetail")
		self.assertTrue(col.get("value"))

		# Only the stale feed is flagged, not the healthy one.
		self.assertEqual(len([e for e in ex if e["type"] == "feed"]), 1)
