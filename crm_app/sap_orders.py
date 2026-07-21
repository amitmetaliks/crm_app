"""Order-level payment reconciliation: what was ordered, what was paid, what is due.

The balance in ``sap_receivables`` answers "how much does this dealer owe in total".
This module answers the question a rep is actually asked across the counter: **"which
order is this payment against, and what is still due on it?"**

It works because the payment feed carries the SAP order number:

    SAP Payment.vbel2  ->  SAP Sales Register.aubel

Verified on real data: ``vbel2`` is filled on **1,623 of 1,677 payments (97%)** and
matches the register for **700 of 722 orders (97%)**. So per order:

    due = invoiced (SUM invamt on the register) - paid (SUM dmbtr on the payments)

**The one thing that must never be got wrong here.** The two feeds do not cover the
same period:

    orders   2025-03-26 -> 2026-07-14   (11,500 rows)
    payments 2026-05-14 -> 2026-07-14   ( 1,677 rows)

**1,171 orders worth ₹211 crore predate the payment feed.** Their payments are simply
not in the data — almost all of them are settled. Reporting them as "unpaid" would send
a rep to a dealer's counter to demand crores for an order closed a year ago. So orders
placed before the feed begins are reported as **unknown**, never as due, and the cutoff
is derived from the data rather than hard-coded, so it corrects itself as the feed grows.

The ledger balance stays the authority on the total; this is the breakdown beneath it.
"""

import frappe
from frappe.utils import flt, getdate

PAY = "SAP Payment"
REG = "SAP Sales Register"


def _table_exists(table: str) -> bool:
	"""Does the physical table exist and hold rows?

	NOT frappe.db.exists("DocType", ...) and NOT frappe.db.count(): the SAP feeds arrive
	as TABLES from the production restore, while their DocType definitions live in
	`sap_app`, which is not installed on this bench. Both of those checks therefore
	answer "no" for data that is demonstrably present — which silently sent sales back to
	the DEAD AML register and reported receivables as zero on the very site that has
	1,677 payment rows. A read needs the table, not the controller class.
	"""
	try:
		return bool(frappe.db.sql(f"SELECT 1 FROM `tab{table}` LIMIT 1"))
	except Exception:
		return False


def available() -> bool:
	return _table_exists(PAY) and _table_exists(REG)


def _feed_start():
	"""First posting date in the payment feed.

	Derived, not hard-coded: as SAP backfills or the feed ages, the honest cutoff moves
	with it and nothing here needs editing.
	"""
	if not available():
		return None
	d = frappe.db.sql(f"SELECT MIN(budat) FROM `tab{PAY}`")[0][0]
	return getdate(d) if d else None


def _sap_code(customer):
	from crm_app.api import has_field

	if not has_field("Customer", "custom_customer_sap_code"):
		return None
	return frappe.db.get_value("Customer", customer, "custom_customer_sap_code")


def customer_orders(customer, limit=25) -> dict:
	"""Per-order ledger for a dealer: ordered vs paid vs due.

	``status`` is one of:
	  * ``paid``    — settled (within a rupee, to absorb rounding)
	  * ``part``    — partly paid, the rest genuinely due
	  * ``due``     — nothing received, and the order is inside the payment window
	  * ``unknown`` — order predates the payment feed; we cannot see its payments and
	                  must not claim it is unpaid
	"""
	empty = {"orders": [], "due": 0.0, "unknown": 0.0, "feed_start": None}
	if not available():
		return empty
	code = _sap_code(customer)
	if not code:
		return empty

	start = _feed_start()
	rows = frappe.db.sql(
		f"""
		SELECT o.aubel AS order_no, o.ordered_on, o.invoiced, o.qty,
		       COALESCE(p.paid, 0) AS paid, p.last_paid_on
		FROM (
			SELECT aubel, MIN(audat) AS ordered_on, SUM(invamt) AS invoiced,
			       -- fkimg is a VARCHAR holding '10.000 ' (trailing space); summing it
			       -- raw makes MySQL coerce per-row and quietly lose the decimals.
			       SUM(CAST(TRIM(fkimg) AS DECIMAL(18, 3))) AS qty
			FROM `tab{REG}` WHERE kunag = %(code)s AND COALESCE(aubel, '') != ''
			GROUP BY aubel
		) o
		LEFT JOIN (
			SELECT vbel2, SUM(dmbtr) AS paid, MAX(budat) AS last_paid_on
			FROM `tab{PAY}` WHERE kunnr = %(code)s AND COALESCE(vbel2, '') != ''
			GROUP BY vbel2
		) p ON p.vbel2 = o.aubel
		ORDER BY o.ordered_on DESC
		LIMIT %(limit)s
		""",
		{"code": code, "limit": int(limit)},
		as_dict=True,
	)

	out, due_total, unknown_total = [], 0.0, 0.0
	for r in rows:
		invoiced = flt(r.invoiced, 2)
		paid = flt(r.paid, 2)
		balance = flt(invoiced - paid, 2)
		before_feed = bool(start and r.ordered_on and getdate(r.ordered_on) < start)

		if paid <= 0 and before_feed:
			status = "unknown"  # its payments predate the feed — silence, not an accusation
			unknown_total += invoiced
		elif paid <= 0:
			status = "due"
			due_total += balance
		elif balance <= 1:
			status = "paid"
		else:
			status = "part"
			due_total += balance

		out.append(
			{
				"order_no": r.order_no,
				"ordered_on": str(r.ordered_on) if r.ordered_on else None,
				"invoiced": invoiced,
				"paid": paid,
				"balance": balance if status in ("due", "part") else 0.0,
				"qty": flt(r.qty, 3),
				"last_paid_on": str(r.last_paid_on) if r.last_paid_on else None,
				"status": status,
			}
		)

	return {
		"orders": out,
		"due": flt(due_total, 2),
		"unknown": flt(unknown_total, 2),
		"feed_start": str(start) if start else None,
		"counts": {
			s: sum(1 for o in out if o["status"] == s) for s in ("paid", "part", "due", "unknown")
		},
	}


@frappe.whitelist()
def get_customer_orders(customer, limit=25) -> dict:
	from crm_app.api import assert_customer_access, get_current_employee

	assert_customer_access(get_current_employee(), customer)
	return customer_orders(customer, limit=limit)


@frappe.whitelist()
def get_order_payments(order_no) -> list:
	"""Every payment posted against one order — the evidence behind the due figure."""
	from crm_app.api import assert_customer_access, get_current_employee, has_field

	employee = get_current_employee()
	if not available():
		return []
	# Gate on the dealer this order belongs to (resolved from the payment feed), so a rep
	# can't pull another rep's dealer's payment ledger by walking order numbers.
	if has_field("Customer", "custom_customer_sap_code"):
		kunnr = frappe.db.sql(f"SELECT kunnr FROM `tab{PAY}` WHERE vbel2 = %s LIMIT 1", order_no)
		if kunnr and kunnr[0][0]:
			cust = frappe.db.get_value("Customer", {"custom_customer_sap_code": kunnr[0][0]}, "name")
			if cust:
				assert_customer_access(employee, cust)
	return frappe.db.sql(
		f"""
		SELECT belnr AS document, budat AS date, ROUND(dmbtr, 2) AS amount, blart AS doc_type
		FROM `tab{PAY}` WHERE vbel2 = %s ORDER BY budat DESC, belnr DESC LIMIT 20
		""",
		order_no,
		as_dict=True,
	)
