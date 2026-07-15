import frappe
from frappe import _
from frappe.model.document import Document


class CRMPJP(Document):
	def validate(self):
		weeks = int(self.cycle_weeks or 1)
		for e in self.entries:
			wk = int(e.week_no or 1)
			# A stop parked in week 3 of a 2-week cycle would simply never come due —
			# it would look planned and silently never be visited.
			if wk < 1 or wk > weeks:
				frappe.throw(
					_("Row {0}: week {1} is outside this {2}-week cycle.").format(e.idx, wk, weeks)
				)
