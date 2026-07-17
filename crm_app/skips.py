"""Why a planned stop did not happen.

Modelled on the incumbent's Skip Visit, but deliberately **not** a copy of it. Their
table holds 22,738 rows of which **22,721 (99.93%) are "Auto-skipped on employee
checkout"** — the system marking every unvisited stop at day's end. Reps entered a real
reason **17 times in three months**.

So we keep the half that carries information and drop the half that manufactures noise:

* **The rep's reason is stored.** It is rare and it is the only part a human knows —
  a shop shut, an owner away, a credit limit hit. That is worth a row.
* **The auto-skip is derived, never stored.** "Planned and not visited" is a fact the
  beat plan and the visit log already prove; writing 22,721 rows to restate it would bury
  the 17 real signals and make coverage *look* explained when nothing was explained.

The reason vocabulary matches theirs (Shop Closed / Owner Not Available / No Stock
Required / Credit Limit Exceeded / Location Not Accessible / Other) so their history can
migrate into this table one-for-one if the incumbent is ever switched off.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from crm_app.api import get_current_employee, is_sales_manager

REASONS = [
	"Shop Closed",
	"Owner Not Available",
	"No Stock Required",
	"Credit Limit Exceeded",
	"Location Not Accessible",
	"Other",
]


@frappe.whitelist()
def get_skip_reasons() -> list:
	return REASONS


@frappe.whitelist()
def skip_stop(customer, skip_reason, other_reason=None, skip_date=None, beat_plan=None, latitude=None, longitude=None) -> dict:
	"""Record why the rep is not visiting a planned dealer today."""
	employee = get_current_employee()
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Dealer not found."), frappe.DoesNotExistError)
	if skip_reason not in REASONS:
		frappe.throw(_("Pick a valid reason."))
	if skip_reason == "Other" and not (other_reason or "").strip():
		frappe.throw(_("Please say why this stop was skipped."))

	day = getdate(skip_date) if skip_date else getdate()

	# A rep changing his mind should correct the reason, not stack rows.
	name = frappe.db.get_value(
		"CRM Visit Skip", {"sales_person": employee, "customer": customer, "skip_date": day}, "name"
	)
	doc = frappe.get_doc("CRM Visit Skip", name) if name else frappe.new_doc("CRM Visit Skip")
	doc.sales_person = employee
	doc.customer = customer
	doc.skip_date = day
	doc.beat_plan = beat_plan
	doc.skip_reason = skip_reason
	doc.other_reason = (other_reason or "").strip() or None
	if latitude not in (None, ""):
		doc.latitude = flt(latitude)
		doc.longitude = flt(longitude)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "customer": customer, "skip_reason": skip_reason, "date": str(day)}


@frappe.whitelist()
def unskip(customer, skip_date=None) -> dict:
	"""Rep decided to visit after all."""
	employee = get_current_employee()
	day = getdate(skip_date) if skip_date else getdate()
	name = frappe.db.get_value(
		"CRM Visit Skip", {"sales_person": employee, "customer": customer, "skip_date": day}, "name"
	)
	if name:
		frappe.delete_doc("CRM Visit Skip", name, ignore_permissions=True)
		frappe.db.commit()
	return {"removed": bool(name)}


@frappe.whitelist()
def get_my_skips(skip_date=None) -> list:
	"""Skips for a day — used by the beat screen to show which stops are already excused."""
	employee = get_current_employee()
	day = getdate(skip_date) if skip_date else getdate()
	return frappe.get_all(
		"CRM Visit Skip",
		filters={"sales_person": employee, "skip_date": day},
		fields=["name", "customer", "customer_name", "skip_reason", "other_reason"],
	)


@frappe.whitelist()
def get_skip_summary(days=28, scope="mine") -> dict:
	"""What is actually stopping coverage.

	This is the point of the feature: not "17 stops were skipped", but "the shop was shut
	9 times" — a fact a manager can act on.
	"""
	employee = get_current_employee()
	frm = add_days(getdate(), -int(days))
	filters = {"skip_date": [">=", frm]}
	if not (scope == "team" and is_sales_manager()):
		filters["sales_person"] = employee

	rows = frappe.get_all(
		"CRM Visit Skip",
		filters=filters,
		fields=["skip_reason", "customer", "customer_name", "skip_date", "sales_person_name", "other_reason"],
		order_by="skip_date desc",
		limit=500,
	)
	by_reason = {}
	for r in rows:
		by_reason[r.skip_reason] = by_reason.get(r.skip_reason, 0) + 1

	# Dealers skipped again and again are the real story — a shop "closed" four times is
	# either the wrong beat day or a dealer who has quietly stopped buying.
	by_customer = {}
	for r in rows:
		c = by_customer.setdefault(
			r.customer, {"customer": r.customer, "customer_name": r.customer_name, "count": 0, "reasons": []}
		)
		c["count"] += 1
		if r.skip_reason not in c["reasons"]:
			c["reasons"].append(r.skip_reason)
	repeat = sorted([c for c in by_customer.values() if c["count"] > 1], key=lambda x: -x["count"])

	return {
		"total": len(rows),
		"days": int(days),
		"by_reason": sorted(
			[{"reason": k, "count": v} for k, v in by_reason.items()], key=lambda x: -x["count"]
		),
		"repeat_offenders": repeat[:10],
		"recent": rows[:20],
	}
