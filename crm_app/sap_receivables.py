"""Real receivables: what each dealer owes, from the SAP payment feed.

This is the number a collections screen exists for, and for most of this project it was
unreachable — ERPNext holds 0 Sales Invoices, so "outstanding" was always ₹0. It turns
out SAP syncs it in as **`tabSAP Payment`** (app `sap_app`): 1,677 rows, 283 customers,
current to the day of the backup.

**Read `cust_bal` carefully — it is not a per-row figure.** SAP writes the customer's
running balance *as of that posting date* onto every payment line. One dealer had 42
distinct values ranging −₹43.7L to +₹38.1L across 92 rows; rows sharing a posting date
share the same balance. So the current outstanding is the balance on the **latest**
posting, not a SUM, not the first row we happen to read. Summing it would produce a
number wrong by orders of magnitude — on a screen a rep uses to ask a dealer for money.

**Sign convention**, verified across all 283 customers on real data:

    positive  = dealer owes us     90 customers, ₹23.23 Cr
    negative  = advance / credit   97 customers, ₹17.52 Cr
    zero      = settled            98 customers

That distribution is what a real debtors book looks like, which is the evidence the
convention is right.

Field names are raw SAP: ``kunnr`` customer, ``name1`` its name, ``dmbtr`` amount,
``cust_bal`` balance, ``budat`` posting date, ``belnr`` document, ``shkzg`` debit/credit
(H = credit, the 1,662 receipts), ``blart`` document type (DZ = customer payment).

Limits worth stating: there is **no invoice-level ageing here** — SAP sends a balance,
not an open-item list — so "overdue" cannot be computed, only "owed". And the feed is
someone else's to keep alive; ``last_synced`` exposes its date rather than letting a
stale feed quietly shrink every number.
"""

import frappe
from frappe.utils import flt, getdate

DOCTYPE = "SAP Payment"


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
	return _table_exists(DOCTYPE)


def _sap_code(customer):
	from crm_app.api import has_field

	if not has_field("Customer", "custom_customer_sap_code"):
		return None
	return frappe.db.get_value("Customer", customer, "custom_customer_sap_code")


def _latest_balances(codes=None) -> dict:
	"""``{sap_code: {balance, as_of, last_paid, name}}`` from each customer's LAST posting.

	The window function does the "latest row per customer" pick in one pass; a
	correlated subquery over 1,677 rows × 283 customers would be needlessly slow and,
	worse, tempts a GROUP BY that silently mixes balances from different dates.
	"""
	if not available():
		return {}
	cond, params = "", {}
	if codes:
		cond = "WHERE kunnr IN %(codes)s"
		params["codes"] = tuple(codes)
	rows = frappe.db.sql(
		f"""
		SELECT kunnr, name1, cust_bal, budat, dmbtr, belnr FROM (
			SELECT kunnr, name1, cust_bal, budat, dmbtr, belnr,
			       ROW_NUMBER() OVER (PARTITION BY kunnr ORDER BY budat DESC, belnr DESC) AS rn
			FROM `tab{DOCTYPE}` {cond}
		) x WHERE rn = 1
		""",
		params,
		as_dict=True,
	)
	return {
		r.kunnr: {
			"balance": flt(r.cust_bal, 2),
			"as_of": str(r.budat) if r.budat else None,
			"last_paid": flt(r.dmbtr, 2),
			"last_doc": r.belnr,
			"sap_name": r.name1,
		}
		for r in rows
	}


def customer_balance(customer) -> dict | None:
	"""Current balance for one dealer, or None if SAP does not know them."""
	code = _sap_code(customer)
	if not code:
		return None
	return _latest_balances([code]).get(code)


def customer_payments(customer, limit=10) -> list:
	"""Recent receipts from this dealer — what a rep needs when a dealer says 'I paid'."""
	if not available():
		return []
	code = _sap_code(customer)
	if not code:
		return []
	return frappe.db.sql(
		f"""
		SELECT belnr AS document, budat AS date, ROUND(dmbtr, 2) AS amount,
		       ROUND(cust_bal, 2) AS balance_after, blart AS doc_type
		FROM `tab{DOCTYPE}` WHERE kunnr = %(code)s
		ORDER BY budat DESC, belnr DESC LIMIT %(limit)s
		""",
		{"code": code, "limit": int(limit)},
		as_dict=True,
	)


def outstanding_for(customers) -> dict:
	"""``{customer: balance_info}`` for dealers that owe us (positive balance only).

	Credits are deliberately excluded from *collections*: a rep chasing a dealer who is
	₹17 lakh in advance would be an embarrassment. The credit is still visible on the
	dealer's own 360 screen, where it is information rather than a to-do.
	"""
	from crm_app.api import has_field

	if not available() or not customers or not has_field("Customer", "custom_customer_sap_code"):
		return {}
	rows = frappe.get_all(
		"Customer",
		filters={"name": ["in", list(customers)], "custom_customer_sap_code": ["!=", ""]},
		fields=["name", "customer_name", "custom_customer_sap_code"],
	)
	by_code = {r.custom_customer_sap_code: r for r in rows if r.custom_customer_sap_code}
	if not by_code:
		return {}
	balances = _latest_balances(list(by_code.keys()))
	out = {}
	for code, bal in balances.items():
		cust = by_code.get(code)
		if not cust or bal["balance"] <= 0:
			continue
		out[cust.name] = {
			"customer": cust.name,
			"customer_name": cust.customer_name,
			"outstanding": bal["balance"],
			"as_of": bal["as_of"],
			"last_paid": bal["last_paid"],
			"sap_code": code,
		}
	return out


@frappe.whitelist()
def last_synced() -> dict:
	"""Freshness of the payment feed, surfaced so a stalled sync shows as a date."""
	from crm_app.api import get_current_employee

	get_current_employee()
	if not available():
		return {"available": False}
	row = frappe.db.sql(
		f"SELECT MAX(budat) AS last_date, COUNT(*) AS rows_, COUNT(DISTINCT kunnr) AS customers FROM `tab{DOCTYPE}`",
		as_dict=True,
	)[0]
	last = row.get("last_date")
	days = (getdate() - getdate(last)).days if last else None
	return {
		"available": True,
		"last_posting_date": str(last) if last else None,
		"days_behind": days,
		"rows": int(row.get("rows_") or 0),
		"customers": int(row.get("customers") or 0),
		"stale": bool(days is not None and days > 7),
	}
