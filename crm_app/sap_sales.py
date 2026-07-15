"""The real sales data: the SAP Sales Register synced into Frappe as **AML Sales Register**.

Amit Metaliks invoices in SAP, not in this ERPNext. A sync lands the SAP sales register
here — 3,782 lines / 1,347 invoices / **₹219 crore** in six weeks — while ERPNext itself
holds 47 Sales Orders worth ~₹22 lakh. Anything that reads only ERPNext is therefore
reading noise, which is exactly what targets, KRA, Customer 360 and insights were doing
before this module existed.

Two joins make it usable, and both are exact — no name matching, no guessing:

  * ``sales_employee_code`` → ``Employee.name``            (10002138 → Debasish Samaddar)
  * ``soldtoparty_code``    → ``Customer.custom_customer_sap_code``  (a field their setup
    already carries, on 1308 of 1970 customers)

Known limits, deliberately visible rather than smoothed over:

  * **No receivables.** This is an invoice register, not a debtors ledger — there is no
    outstanding/paid column. Collections cannot be built on it.
  * **Coverage is partial.** 139 of 276 SAP parties currently resolve to a Customer, and
    8 of 22 SAP employee codes to an Employee. Unmatched rows are real business we simply
    cannot attribute; ``coverage()`` reports that honestly instead of hiding it.
  * **Freshness is not ours to guarantee.** The sync is someone else's job; ``last_synced``
    exposes it so a stale feed shows up as a date rather than as quietly shrinking numbers.
"""

import frappe
from frappe.utils import flt, getdate

DOCTYPE = "AML Sales Register"


def available() -> bool:
	"""Whether this site has the SAP feed at all (crm-dev and a fresh site will not)."""
	return bool(frappe.db.exists("DocType", DOCTYPE))


def _customer_sap_codes(customer):
	"""SAP codes for a Customer. A dealer can carry only one, but treat it as a set so a
	future many-to-one mapping does not need a rewrite here."""
	if not frappe.get_meta("Customer").has_field("custom_customer_sap_code"):
		return []
	code = frappe.db.get_value("Customer", customer, "custom_customer_sap_code")
	return [code] if code else []


def rep_sales(employee, frm, to) -> dict:
	"""{amount, qty, invoices} invoiced by this rep in SAP between two dates."""
	if not available() or not employee:
		return {"amount": 0.0, "qty": 0.0, "invoices": 0}
	rows = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(invoice_amount), 0) AS amount,
		       COALESCE(SUM(sales_order_qty), 0) AS qty,
		       COUNT(DISTINCT invoice_number) AS invoices
		FROM `tab{DOCTYPE}`
		WHERE sales_employee_code = %(emp)s
		  AND invoice_date BETWEEN %(frm)s AND %(to)s
		""",
		{"emp": employee, "frm": getdate(frm), "to": getdate(to)},
		as_dict=True,
	)
	r = rows[0] if rows else {}
	return {
		"amount": flt(r.get("amount"), 2),
		"qty": flt(r.get("qty"), 3),
		"invoices": int(r.get("invoices") or 0),
	}


def customer_sales(customer, frm=None, to=None, limit_months=12) -> dict:
	"""What this dealer actually bought, per SAP."""
	empty = {"amount": 0.0, "qty": 0.0, "invoices": 0, "last_date": None}
	if not available():
		return empty
	codes = _customer_sap_codes(customer)
	if not codes:
		return empty
	cond, params = "", {"codes": tuple(codes)}
	if frm and to:
		cond = "AND invoice_date BETWEEN %(frm)s AND %(to)s"
		params.update({"frm": getdate(frm), "to": getdate(to)})
	rows = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(invoice_amount), 0) AS amount,
		       COALESCE(SUM(sales_order_qty), 0) AS qty,
		       COUNT(DISTINCT invoice_number) AS invoices,
		       MAX(invoice_date) AS last_date
		FROM `tab{DOCTYPE}`
		WHERE soldtoparty_code IN %(codes)s {cond}
		""",
		params,
		as_dict=True,
	)
	r = rows[0] if rows else {}
	return {
		"amount": flt(r.get("amount"), 2),
		"qty": flt(r.get("qty"), 3),
		"invoices": int(r.get("invoices") or 0),
		"last_date": str(r["last_date"]) if r.get("last_date") else None,
	}


def customer_invoices(customer, limit=5) -> list:
	"""Recent SAP invoices for a dealer — including dispatch, which is the thing a dealer
	actually asks about at the counter ("where is my truck?")."""
	if not available():
		return []
	codes = _customer_sap_codes(customer)
	if not codes:
		return []
	return frappe.db.sql(
		f"""
		SELECT invoice_number, invoice_date, delivery_date,
		       ROUND(SUM(invoice_amount), 2) AS amount, ROUND(SUM(sales_order_qty), 3) AS qty,
		       MAX(lr_number) AS lr_number, MAX(truck_no) AS truck_no,
		       MAX(transporter_name) AS transporter, MAX(sales_employee_name) AS rep
		FROM `tab{DOCTYPE}`
		WHERE soldtoparty_code IN %(codes)s
		GROUP BY invoice_number, invoice_date, delivery_date
		ORDER BY invoice_date DESC
		LIMIT %(limit)s
		""",
		{"codes": tuple(codes), "limit": int(limit)},
		as_dict=True,
	)


def customer_top_products(customer, limit=5) -> list:
	"""Real materials this dealer buys (TMT BAR 12 MM, TRIAM A+ …), by value."""
	if not available():
		return []
	codes = _customer_sap_codes(customer)
	if not codes:
		return []
	rows = frappe.db.sql(
		f"""
		SELECT material_description AS item, ROUND(SUM(sales_order_qty), 3) AS qty,
		       ROUND(SUM(invoice_amount), 2) AS amount
		FROM `tab{DOCTYPE}`
		WHERE soldtoparty_code IN %(codes)s AND COALESCE(material_description, '') != ''
		GROUP BY material_description
		ORDER BY SUM(invoice_amount) DESC
		LIMIT %(limit)s
		""",
		{"codes": tuple(codes), "limit": int(limit)},
		as_dict=True,
	)
	return rows


def rep_top_products(employee, frm, to, limit=5) -> list:
	if not available() or not employee:
		return []
	return frappe.db.sql(
		f"""
		SELECT material_description AS item, ROUND(SUM(sales_order_qty), 3) AS qty,
		       ROUND(SUM(invoice_amount), 2) AS amount
		FROM `tab{DOCTYPE}`
		WHERE sales_employee_code = %(emp)s AND invoice_date BETWEEN %(frm)s AND %(to)s
		  AND COALESCE(material_description, '') != ''
		GROUP BY material_description
		ORDER BY SUM(invoice_amount) DESC
		LIMIT %(limit)s
		""",
		{"emp": employee, "frm": getdate(frm), "to": getdate(to), "limit": int(limit)},
		as_dict=True,
	)


def rep_customers(employee) -> set:
	"""Customers this rep has actually invoiced, mapped back to Frappe Customer names."""
	if not available() or not employee:
		return set()
	codes = frappe.db.sql_list(
		f"""SELECT DISTINCT soldtoparty_code FROM `tab{DOCTYPE}`
		    WHERE sales_employee_code = %s AND COALESCE(soldtoparty_code, '') != ''""",
		employee,
	)
	if not codes:
		return set()
	return set(
		frappe.get_all(
			"Customer", filters={"custom_customer_sap_code": ["in", codes]}, pluck="name"
		)
	)


@frappe.whitelist()
def last_synced() -> dict:
	"""How current the SAP feed is.

	Surfaced deliberately: if the sync stops, every number downstream quietly shrinks,
	and a rep would think he had a bad month rather than a stale feed.
	"""
	from crm_app.api import get_current_employee

	get_current_employee()
	if not available():
		return {"available": False}
	row = frappe.db.sql(
		f"SELECT MAX(invoice_date) AS last_date, COUNT(*) AS rows_ FROM `tab{DOCTYPE}`", as_dict=True
	)[0]
	last = row.get("last_date")
	days = (getdate() - getdate(last)).days if last else None
	return {
		"available": True,
		"last_invoice_date": str(last) if last else None,
		"days_behind": days,
		"rows": int(row.get("rows_") or 0),
		"stale": bool(days is not None and days > 7),
	}


@frappe.whitelist()
def coverage() -> dict:
	"""How much of the SAP business we can actually attribute.

	Reported rather than hidden: unmatched parties/reps are real sales that will never
	show up against a dealer or a target, and someone should know the size of that.
	"""
	from crm_app.api import get_current_employee

	get_current_employee()
	if not available():
		return {"available": False}
	parties = frappe.db.sql(
		f"""SELECT COUNT(DISTINCT r.soldtoparty_code) AS total,
		           COUNT(DISTINCT c.name) AS matched
		    FROM `tab{DOCTYPE}` r
		    LEFT JOIN `tabCustomer` c ON c.custom_customer_sap_code = r.soldtoparty_code""",
		as_dict=True,
	)[0]
	reps = frappe.db.sql(
		f"""SELECT COUNT(DISTINCT r.sales_employee_code) AS total,
		           COUNT(DISTINCT e.name) AS matched
		    FROM `tab{DOCTYPE}` r
		    LEFT JOIN `tabEmployee` e ON e.name = r.sales_employee_code
		    WHERE COALESCE(r.sales_employee_code, '') != ''""",
		as_dict=True,
	)[0]
	return {
		"available": True,
		"parties_total": int(parties.total or 0),
		"parties_matched": int(parties.matched or 0),
		"reps_total": int(reps.total or 0),
		"reps_matched": int(reps.matched or 0),
	}
