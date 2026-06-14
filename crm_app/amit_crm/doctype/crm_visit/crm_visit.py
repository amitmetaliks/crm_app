import frappe
from frappe.model.document import Document
from frappe.utils import time_diff_in_seconds


class CRMVisit(Document):
	def validate(self):
		self._set_party_display()
		self._compute_duration()

	def _set_party_display(self):
		"""Human-readable party label used in lists and the desk title column."""
		label = ""
		if self.party_type == "Customer" and self.customer:
			label = frappe.db.get_value("Customer", self.customer, "customer_name") or self.customer
		elif self.party_type == "CRM Lead" and self.crm_lead:
			label = frappe.db.get_value("CRM Lead", self.crm_lead, "lead_name") or self.crm_lead
		elif self.party_type == "CRM Deal" and self.crm_deal:
			org = frappe.db.get_value("CRM Deal", self.crm_deal, "organization")
			label = org or self.crm_deal
		elif self.party_type == "Prospect":
			label = self.prospect_name or "Prospect"
		self.party_display = (label or "")[:140]

	def _compute_duration(self):
		if self.check_in_time and self.check_out_time:
			secs = time_diff_in_seconds(self.check_out_time, self.check_in_time)
			self.duration_minutes = int(max(0, round(secs / 60)))
		elif not self.check_out_time:
			self.duration_minutes = 0
