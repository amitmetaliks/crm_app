"""The real sales data: the SAP sales register synced into Frappe.

**There are two generations of this feed, and picking the wrong one is a real bug.**

    SAP Sales Register   11,500 rows   2025-05-12 -> 2026-07-14   ₹513 Cr   LIVE
    AML Sales Register    3,782 rows   2026-04-01 -> 2026-05-11   ₹219 Cr   DEAD since 11 May

This module originally read the AML table — it was the only one on the dev copy. On the
real database that is two months stale: Rahul Ghosh's achievement reads **₹15.36 Cr**
from AML against **₹27.41 Cr** of live truth. Reps would be judged on numbers ~44% short
and two months old. So the live register wins wherever it exists, and AML remains as the
fallback for a site that only carries the old generation.

**The two generations do not use the same codes.** The live one zero-pads:

    live:  salempcode        '0010000675'  -> Employee '10000675'   (TRIM LEADING '0')
    old:   sales_employee_code '10000675'  -> Employee '10000675'   (as-is)

Customer codes need no trimming in either (`kunag` matches `custom_customer_sap_code`).

Column map, live vs old — nothing is a guess, each was checked for population:

    invoice no    vbeln            invoice_number
    invoice date  fkdat            invoice_date
    customer      kunag            soldtoparty_code
    rep code      salempcode       sales_employee_code
    rep name      salempname       sales_employee_name
    material      arktx            material_description
    quantity      fkimg (VARCHAR!) sales_order_qty
    amount        invamt           invoice_amount
    order no      aubel            sales_order_no
    truck         zzvehregno       truck_no
    delivery date deldate          delivery_date

Beware ``fkimg``: it is a VARCHAR holding '41.360 ' with a trailing space, so it must be
CAST, not summed raw. The ``sal_emp_code`` / ``zzveh_reg_no`` / ``del_date`` variants
exist in the schema but are empty on every row — the live columns are the ones above.

Limits, stated rather than smoothed over: there is **no receivables column here** (that
is ``sap_receivables``), only **13 of 28** live rep codes currently resolve to an
Employee and **218 of 466** parties to a Customer, so unattributed business is real —
``coverage()`` reports it instead of hiding it.
"""

import frappe
from frappe.utils import flt, getdate

LIVE = "SAP Sales Register"
OLD = "AML Sales Register"


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


def _table():
	"""The live register if this site has it, else the old generation, else None."""
	if _table_exists(LIVE):
		return LIVE
	if _table_exists(OLD):
		return OLD
	return None


#: Column names per generation. Keyed by table so a caller never has to care which.
COLS = {
	LIVE: {
		"inv": "vbeln", "date": "fkdat", "cust": "kunag", "rep": "salempcode",
		"rep_name": "salempname", "material": "arktx", "qty": "CAST(TRIM(fkimg) AS DECIMAL(18,3))",
		"amount": "invamt", "order": "aubel", "truck": "zzvehregno", "del_date": "deldate",
		"lr": "NULL", "transporter": "NULL",
		# The live feed zero-pads the employee code; the Employee id does not.
		"rep_match": "TRIM(LEADING '0' FROM salempcode)",
	},
	OLD: {
		"inv": "invoice_number", "date": "invoice_date", "cust": "soldtoparty_code",
		"rep": "sales_employee_code", "rep_name": "sales_employee_name",
		"material": "material_description", "qty": "sales_order_qty",
		"amount": "invoice_amount", "order": "sales_order_no", "truck": "truck_no",
		"del_date": "delivery_date", "lr": "lr_number", "transporter": "transporter_name",
		"rep_match": "sales_employee_code",
	},
}


def available() -> bool:
	return _table() is not None


def which() -> str | None:
	"""Which generation this site is reading — surfaced in last_synced()."""
	return _table()


def _customer_sap_codes(customer):
	from crm_app.api import has_field

	if not has_field("Customer", "custom_customer_sap_code"):
		return []
	code = frappe.db.get_value("Customer", customer, "custom_customer_sap_code")
	return [code] if code else []


def rep_sales(employee, frm, to) -> dict:
	"""{amount, qty, invoices} invoiced by this rep between two dates."""
	t = _table()
	if not t or not employee:
		return {"amount": 0.0, "qty": 0.0, "invoices": 0}
	c = COLS[t]
	rows = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM({c['amount']}), 0) AS amount,
		       COALESCE(SUM({c['qty']}), 0) AS qty,
		       COUNT(DISTINCT {c['inv']}) AS invoices
		FROM `tab{t}`
		WHERE {c['rep_match']} = %(emp)s AND {c['date']} BETWEEN %(frm)s AND %(to)s
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


def customer_sales(customer, frm=None, to=None) -> dict:
	"""What this dealer actually bought."""
	empty = {"amount": 0.0, "qty": 0.0, "invoices": 0, "last_date": None}
	t = _table()
	if not t:
		return empty
	codes = _customer_sap_codes(customer)
	if not codes:
		return empty
	c = COLS[t]
	cond, params = "", {"codes": tuple(codes)}
	if frm and to:
		cond = f"AND {c['date']} BETWEEN %(frm)s AND %(to)s"
		params.update({"frm": getdate(frm), "to": getdate(to)})
	rows = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM({c['amount']}), 0) AS amount,
		       COALESCE(SUM({c['qty']}), 0) AS qty,
		       COUNT(DISTINCT {c['inv']}) AS invoices,
		       MAX({c['date']}) AS last_date
		FROM `tab{t}` WHERE {c['cust']} IN %(codes)s {cond}
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
	"""Recent invoices with dispatch — "where is my truck", the counter question."""
	t = _table()
	if not t:
		return []
	codes = _customer_sap_codes(customer)
	if not codes:
		return []
	c = COLS[t]
	return frappe.db.sql(
		f"""
		SELECT {c['inv']} AS invoice_number, {c['date']} AS invoice_date,
		       MAX({c['del_date']}) AS delivery_date,
		       ROUND(SUM({c['amount']}), 2) AS amount, ROUND(SUM({c['qty']}), 3) AS qty,
		       MAX({c['lr']}) AS lr_number, MAX({c['truck']}) AS truck_no,
		       MAX({c['transporter']}) AS transporter, MAX({c['rep_name']}) AS rep
		FROM `tab{t}` WHERE {c['cust']} IN %(codes)s
		GROUP BY {c['inv']}, {c['date']}
		ORDER BY {c['date']} DESC LIMIT %(limit)s
		""",
		{"codes": tuple(codes), "limit": int(limit)},
		as_dict=True,
	)


def customer_top_products(customer, limit=5) -> list:
	t = _table()
	if not t:
		return []
	codes = _customer_sap_codes(customer)
	if not codes:
		return []
	c = COLS[t]
	return frappe.db.sql(
		f"""
		SELECT {c['material']} AS item, ROUND(SUM({c['qty']}), 3) AS qty,
		       ROUND(SUM({c['amount']}), 2) AS amount
		FROM `tab{t}`
		WHERE {c['cust']} IN %(codes)s AND COALESCE({c['material']}, '') != ''
		GROUP BY {c['material']} ORDER BY SUM({c['amount']}) DESC LIMIT %(limit)s
		""",
		{"codes": tuple(codes), "limit": int(limit)},
		as_dict=True,
	)


def rep_top_products(employee, frm, to, limit=5) -> list:
	t = _table()
	if not t or not employee:
		return []
	c = COLS[t]
	return frappe.db.sql(
		f"""
		SELECT {c['material']} AS item, ROUND(SUM({c['qty']}), 3) AS qty,
		       ROUND(SUM({c['amount']}), 2) AS amount
		FROM `tab{t}`
		WHERE {c['rep_match']} = %(emp)s AND {c['date']} BETWEEN %(frm)s AND %(to)s
		  AND COALESCE({c['material']}, '') != ''
		GROUP BY {c['material']} ORDER BY SUM({c['amount']}) DESC LIMIT %(limit)s
		""",
		{"emp": employee, "frm": getdate(frm), "to": getdate(to), "limit": int(limit)},
		as_dict=True,
	)


def rep_customers(employee) -> set:
	"""Customers this rep has actually invoiced, mapped back to Frappe Customer names."""
	from crm_app.api import has_field

	t = _table()
	if not t or not employee or not has_field("Customer", "custom_customer_sap_code"):
		return set()
	c = COLS[t]
	codes = frappe.db.sql_list(
		f"""SELECT DISTINCT {c['cust']} FROM `tab{t}`
		    WHERE {c['rep_match']} = %s AND COALESCE({c['cust']}, '') != ''""",
		employee,
	)
	if not codes:
		return set()
	return set(
		frappe.get_all("Customer", filters={"custom_customer_sap_code": ["in", codes]}, pluck="name")
	)


@frappe.whitelist()
def last_synced() -> dict:
	"""How current the feed is, and WHICH generation we are reading.

	The generation is reported because the difference is not cosmetic: the old table
	stopped on 11 May, and a site silently reading it would show every rep two months
	short without anything looking broken.
	"""
	from crm_app.api import get_current_employee

	get_current_employee()
	t = _table()
	if not t:
		return {"available": False}
	c = COLS[t]
	row = frappe.db.sql(
		f"SELECT MAX({c['date']}) AS last_date, COUNT(*) AS rows_ FROM `tab{t}`", as_dict=True
	)[0]
	last = row.get("last_date")
	days = (getdate() - getdate(last)).days if last else None
	return {
		"available": True,
		"source": t,
		"generation": "live" if t == LIVE else "legacy",
		"last_invoice_date": str(last) if last else None,
		"days_behind": days,
		"rows": int(row.get("rows_") or 0),
		"stale": bool(days is not None and days > 7),
	}


@frappe.whitelist()
def coverage() -> dict:
	"""How much of the SAP business we can actually attribute — reported, not hidden."""
	from crm_app.api import get_current_employee

	get_current_employee()
	t = _table()
	if not t:
		return {"available": False}
	c = COLS[t]
	parties = frappe.db.sql(
		f"""SELECT COUNT(DISTINCT r.{c['cust']}) AS total, COUNT(DISTINCT cu.name) AS matched
		    FROM `tab{t}` r
		    LEFT JOIN `tabCustomer` cu ON cu.custom_customer_sap_code = r.{c['cust']}""",
		as_dict=True,
	)[0]
	reps = frappe.db.sql(
		f"""SELECT COUNT(DISTINCT x.code) AS total, COUNT(DISTINCT e.name) AS matched FROM
		    (SELECT DISTINCT {c['rep_match']} AS code FROM `tab{t}`
		     WHERE COALESCE({c['rep']}, '') != '') x
		    LEFT JOIN `tabEmployee` e ON e.name = x.code""",
		as_dict=True,
	)[0]
	return {
		"available": True,
		"source": t,
		"parties_total": int(parties.total or 0),
		"parties_matched": int(parties.matched or 0),
		"reps_total": int(reps.total or 0),
		"reps_matched": int(reps.matched or 0),
	}


# ── Bulk helpers ─────────────────────────────────────────────────────────────
# Per-customer lookups are fine on a dealer page; they are not fine across a book of
# 2,000 dealers. churn_risk was running two queries PER customer — 40,000 round trips for
# a manager — so these answer the same questions in one.


def _codes_for(customers) -> dict:
	"""``{sap_code: customer_name}`` for a list of Customers."""
	from crm_app.api import has_field

	if not customers or not has_field("Customer", "custom_customer_sap_code"):
		return {}
	rows = frappe.get_all(
		"Customer",
		filters={"name": ["in", list(customers)], "custom_customer_sap_code": ["!=", ""]},
		fields=["name", "custom_customer_sap_code"],
		limit=20000,
	)
	return {r.custom_customer_sap_code: r.name for r in rows if r.custom_customer_sap_code}


def last_invoice_dates(customers) -> dict:
	"""``{customer: last_invoice_date}`` — one query for the whole book."""
	t = _table()
	by_code = _codes_for(customers)
	if not t or not by_code:
		return {}
	c = COLS[t]
	rows = frappe.db.sql(
		f"""SELECT {c['cust']} AS code, MAX({c['date']}) AS last_date
		    FROM `tab{t}` WHERE {c['cust']} IN %(codes)s GROUP BY {c['cust']}""",
		{"codes": tuple(by_code.keys())},
		as_dict=True,
	)
	return {by_code[r.code]: r.last_date for r in rows if r.code in by_code and r.last_date}


def monthly_totals(customers, months=4) -> list:
	"""``[{label, value}]`` invoiced per calendar month — one query, not one per month."""
	from frappe.utils import add_months, get_first_day, get_last_day

	t = _table()
	by_code = _codes_for(customers)
	base = getdate()
	spans = []
	for i in range(int(months) - 1, -1, -1):
		ms = get_first_day(add_months(base, -i))
		spans.append((ms, get_last_day(ms), ms.strftime("%b")))
	if not t or not by_code:
		return [{"label": lbl, "value": 0.0} for _, _, lbl in spans]

	c = COLS[t]
	rows = frappe.db.sql(
		f"""SELECT DATE_FORMAT({c['date']}, '%%Y-%%m') AS ym, SUM({c['amount']}) AS amount
		    FROM `tab{t}`
		    WHERE {c['cust']} IN %(codes)s AND {c['date']} BETWEEN %(frm)s AND %(to)s
		    GROUP BY ym""",
		{"codes": tuple(by_code.keys()), "frm": spans[0][0], "to": spans[-1][1]},
		as_dict=True,
	)
	by_ym = {r.ym: flt(r.amount, 2) for r in rows}
	return [{"label": lbl, "value": by_ym.get(ms.strftime("%Y-%m"), 0.0)} for ms, _, lbl in spans]
