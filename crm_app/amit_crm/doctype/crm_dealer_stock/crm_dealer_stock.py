import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CRMDealerStock(Document):
	def validate(self):
		# Roll totals up here too, not only in dms.record_stock: a stock check edited
		# from the desk must leave the same numbers as one saved from the app.
		ours = flt(sum(flt(i.closing_qty_mt) for i in self.items if i.brand_type == "Ours"), 3)
		comp = flt(sum(flt(i.closing_qty_mt) for i in self.items if i.brand_type == "Competitor"), 3)
		self.our_closing_mt = ours
		self.competitor_closing_mt = comp
		self.total_closing_mt = flt(ours + comp, 3)
		self.total_sold_mt = flt(sum(flt(i.sold_qty_mt) for i in self.items), 3)
		self.our_share_pct = flt(ours / (ours + comp) * 100, 2) if (ours + comp) else 0.0
