import base64
from io import BytesIO

import frappe
from frappe.tests.utils import FrappeTestCase

from crm_app import field_visit


def _png_data_uri():
	from PIL import Image

	buf = BytesIO()
	Image.new("RGB", (8, 8), (200, 100, 50)).save(buf, "PNG")
	return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class TestVisitPhotoByRef(FrappeTestCase):
	def setUp(self):
		self.rep = frappe.db.get_value(
			"Employee", {"status": "Active", "user_id": ["!=", ""]}, ["name", "user_id"], as_dict=True
		)
		self.cust = frappe.db.get_value("Customer", {}, "name")
		if not self.rep or not self.cust:
			self.skipTest("needs an Active Employee-user and a Customer")
		self.ref = "test-photo-ref-" + frappe.generate_hash(length=8)
		self.visit = frappe.get_doc(
			{
				"doctype": "CRM Visit",
				"sales_person": self.rep.name,
				"party_type": "Customer",
				"customer": self.cust,
				"visit_date": frappe.utils.today(),
				"visit_status": "Completed",
				"client_ref": self.ref,
			}
		).insert(ignore_permissions=True)

	def test_attaches_once_and_is_replay_safe(self):
		img = _png_data_uri()
		frappe.set_user(self.rep.user_id)
		try:
			r1 = field_visit.add_visit_photo_by_ref(self.ref, img, idempotency_key="tpk-1")
			c1 = len(frappe.get_doc("CRM Visit", self.visit.name).photos)
			# Same key -> the queue retried a committed-but-lost response; must NOT double-attach.
			r2 = field_visit.add_visit_photo_by_ref(self.ref, img, idempotency_key="tpk-1")
			c2 = len(frappe.get_doc("CRM Visit", self.visit.name).photos)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(c1, 1)
		self.assertEqual(c2, 1)
		self.assertEqual(r1.get("image"), r2.get("image"))

	def test_unknown_ref_fails_cleanly(self):
		frappe.set_user(self.rep.user_id)
		try:
			with self.assertRaises(frappe.exceptions.ValidationError):
				field_visit.add_visit_photo_by_ref("no-such-ref-xyz", _png_data_uri())
		finally:
			frappe.set_user("Administrator")
