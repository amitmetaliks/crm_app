"""Payment collection — chase what's owed, and record what the rep actually collects.

Two halves:

* ``get_my_collections`` reads ERPNext Sales Invoices (submitted, outstanding > 0).
  **On their site this is empty**: invoicing happens outside ERPNext (0 Sales Invoices),
  so nothing here has anything to show until invoices land. Left intact for the day they do.
* ``record_payment`` is what actually matters today. 50 of their 51 receipts are
  customer money taken **on account** (₹12.1 L over 6 months, 88% cash) with no invoice
  to allocate against. So a rep's receipt is written the same way: an on-account
  Payment Entry mirroring ``ACC-PAY-*`` — mode Cash, paid_to the company cash account,
  the whole amount unallocated.

Receipts are created as **drafts** by default: a rep saying he took ₹50,000 in cash
should not hit the general ledger before accounts confirm the money physically arrived.
Set ``crm_autosubmit_payments: 1`` in site config to submit on the spot instead.
"""

import base64

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from crm_app.api import get_current_employee, has_field, is_sales_manager, validate_upload
from crm_app.sales_attr import rep_customers


def _exists(dt):
	return bool(frappe.db.exists("DocType", dt))


def _my_customers(employee, scope):
	"""The dealers this rep may chase."""
	# The assigned-sales-person field is ours; on a site where our migrate has not run
	# (e.g. a freshly restored production DB) filtering on it raises Unknown column.
	if scope == "team" and is_sales_manager():
		cust_filter = {}
	elif has_field("Customer", "custom_assigned_sales_person"):
		cust_filter = {"custom_assigned_sales_person": employee}
	else:
		cust_filter = {"name": ["in", list(rep_customers(employee)) or [""]]}
	return frappe.get_all("Customer", filters=cust_filter, fields=["name", "customer_name"])


@frappe.whitelist()
def get_my_collections(scope="mine"):
	"""What the rep's dealers owe.

	**SAP first.** They invoice in SAP, so ERPNext holds 0 Sales Invoices and the old
	path here could only ever return ₹0 — a permanently empty collections screen. The
	Sales Invoice path stays as the fallback for sites without the SAP feed, and for the
	day invoicing moves here.
	"""
	employee = get_current_employee()
	from crm_app import sap_receivables

	if sap_receivables.available():
		customers = _my_customers(employee, scope)
		if not customers:
			return {"total": 0.0, "overdue": 0.0, "customers": [], "source": "sap"}
		owed = sap_receivables.outstanding_for([c.name for c in customers])
		rows = sorted(owed.values(), key=lambda r: r["outstanding"], reverse=True)
		for r in rows:
			# SAP sends a balance, not an open-item list, so there is no invoice-level
			# ageing to derive "overdue" from. Reporting 0 is honest; inventing a due
			# date from the last posting would be a guess a rep might act on.
			r["overdue"] = 0.0
			r["invoices"] = 0
			r["oldest_due"] = None
		return {
			"total": flt(sum(r["outstanding"] for r in rows), 2),
			"overdue": 0.0,
			"customers": rows,
			"source": "sap",
			"no_ageing": True,
		}

	if not _exists("Sales Invoice"):
		return {"total": 0.0, "overdue": 0.0, "customers": []}

	customers = _my_customers(employee, scope)
	if not customers:
		return {"total": 0.0, "overdue": 0.0, "customers": []}

	by_name = {c.name: c.customer_name for c in customers}
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={
			"customer": ["in", list(by_name.keys())],
			"docstatus": 1,
			"outstanding_amount": [">", 0],
		},
		fields=["name", "customer", "outstanding_amount", "due_date"],
		limit=5000,
	)

	agg = {}
	td = getdate(today())
	total = 0.0
	overdue_total = 0.0
	for inv in invoices:
		amt = flt(inv.outstanding_amount)
		total += amt
		is_overdue = inv.due_date and getdate(inv.due_date) < td
		if is_overdue:
			overdue_total += amt
		row = agg.setdefault(
			inv.customer,
			{
				"customer": inv.customer,
				"customer_name": by_name.get(inv.customer, inv.customer),
				"outstanding": 0.0,
				"overdue": 0.0,
				"invoices": 0,
				"oldest_due": None,
			},
		)
		row["outstanding"] += amt
		row["invoices"] += 1
		if is_overdue:
			row["overdue"] += amt
		if inv.due_date and (row["oldest_due"] is None or getdate(inv.due_date) < getdate(row["oldest_due"])):
			row["oldest_due"] = str(inv.due_date)

	rows = sorted(agg.values(), key=lambda r: r["outstanding"], reverse=True)
	for r in rows:
		r["outstanding"] = flt(r["outstanding"], 2)
		r["overdue"] = flt(r["overdue"], 2)
	return {"total": flt(total, 2), "overdue": flt(overdue_total, 2), "customers": rows}


# ---------------------------------------------------------------------------
# Cash / cheque collection at the dealer
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_payment_modes() -> list:
	"""Enabled Modes of Payment, cash first (88% of their receipts are cash)."""
	if not _exists("Mode of Payment"):
		return []
	rows = frappe.get_all("Mode of Payment", filters={"enabled": 1}, fields=["name", "type"])
	return sorted(rows, key=lambda r: (r.type != "Cash", r.name))


def _paid_to_account(company: str, mode: str) -> str | None:
	"""The account the money lands in: the mode's own account, else the company default."""
	acc = frappe.db.get_value(
		"Mode of Payment Account", {"parent": mode, "company": company}, "default_account"
	)
	if acc:
		return acc
	kind = frappe.db.get_value("Mode of Payment", mode, "type")
	if kind == "Cash":
		return frappe.db.get_value("Company", company, "default_cash_account")
	return frappe.db.get_value("Company", company, "default_bank_account") or frappe.db.get_value(
		"Company", company, "default_cash_account"
	)


def _account_meta(account: str):
	"""Currency + type straight off the Account, avoiding ERPNext's whitelisted
	get_account_details() (which permission-checks Payment Entry — see record_payment)."""
	return frappe.db.get_value("Account", account, ["account_currency", "account_type"], as_dict=True)


def _company_for(customer: str, employee: str) -> str | None:
	"""Which entity is receiving this money.

	It is the company that SOLD, not the rep's payroll company — the group runs several
	entities (AML / AMPL / NISPL / TIPL) and a rep employed by one may collect for
	another. Order: the dealer's own party account → their last order → their last
	receipt → the rep's company.
	"""
	co = frappe.db.get_value("Party Account", {"parenttype": "Customer", "parent": customer}, "company")
	if co:
		return co
	if _exists("Sales Order"):
		co = frappe.db.get_value(
			"Sales Order", {"customer": customer, "docstatus": 1}, "company", order_by="transaction_date desc"
		)
		if co:
			return co
	co = frappe.db.get_value(
		"Payment Entry",
		{"party_type": "Customer", "party": customer, "docstatus": 1},
		"company",
		order_by="posting_date desc",
	)
	return co or frappe.db.get_value("Employee", employee, "company")


def _receivable_account(customer: str, company: str) -> str | None:
	"""The dealer's receivable account.

	1710 of their 1970 customers carry their own Party Account, so ERPNext resolves it.
	No company here has a ``default_receivable_account``, and AML alone has 12 Receivable
	accounts, so auto-picking one would be a guess about someone's books — we ask instead.
	``crm_receivable_account`` in site config can name the fallback (theirs would be
	'16120000 - SD - TMT - AML', which 48 of 50 real receipts use).
	"""
	from erpnext.accounts.party import get_party_account

	acc = get_party_account("Customer", customer, company)
	if acc:
		return acc
	cfg = frappe.conf.get("crm_receivable_account")
	if cfg and frappe.db.exists("Account", {"name": cfg, "company": company, "is_group": 0}):
		return cfg
	accounts = frappe.get_all(
		"Account", filters={"company": company, "account_type": "Receivable", "is_group": 0}, pluck="name"
	)
	return accounts[0] if len(accounts) == 1 else None


@frappe.whitelist()
def record_payment(
	customer,
	amount,
	mode_of_payment="Cash",
	reference_no=None,
	reference_date=None,
	remarks=None,
	photo_base64=None,
	photo_filename=None,
	latitude=None,
	longitude=None,
) -> dict:
	"""Record money collected from a dealer as an on-account Payment Entry.

	Mirrors their existing receipts exactly: Receive / Customer / fully unallocated,
	because there are no invoices to allocate against.
	"""
	employee = get_current_employee()
	if not _exists("Payment Entry"):
		frappe.throw(_("Payments are not available on this site."))
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Customer not found."), frappe.DoesNotExistError)
	amt = flt(amount)
	if amt <= 0:
		frappe.throw(_("Enter the amount collected."))

	company = _company_for(customer, employee)
	if not company:
		frappe.throw(_("Could not work out which company this dealer belongs to. Ask accounts."))

	paid_to = _paid_to_account(company, mode_of_payment)
	if not paid_to:
		frappe.throw(
			_("No account is set for {0} in {1}. Ask accounts to set it on the Mode of Payment.").format(
				mode_of_payment, company
			)
		)

	paid_from = _receivable_account(customer, company)
	if not paid_from:
		frappe.throw(
			_(
				"No receivable account is set for this dealer in {0}. Ask accounts to set the "
				"dealer's Accounts Receivable, or set 'default_receivable_account' on the company."
			).format(company)
		)

	# Supply each account's currency AND type up front. ERPNext only reaches for
	# get_account_details() when one of them is missing — and that helper is whitelisted,
	# so it runs its own has_permission("Payment Entry", throw=True), which insert's
	# ignore_permissions does NOT bypass. A field rep has no Payment Entry role, so
	# filling these here is what lets him record a receipt without us loosening
	# permissions on an accounting doctype.
	frm = _account_meta(paid_from)
	to = _account_meta(paid_to)

	doc = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"company": company,
			"posting_date": getdate(),
			"mode_of_payment": mode_of_payment,
			"party_type": "Customer",
			"party": customer,
			"party_account": paid_from,
			"paid_from": paid_from,
			"paid_from_account_currency": frm.account_currency,
			"paid_from_account_type": frm.account_type,
			"paid_to": paid_to,
			"paid_to_account_currency": to.account_currency,
			"paid_to_account_type": to.account_type,
			"paid_amount": amt,
			"received_amount": amt,
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"reference_no": reference_no,
			"reference_date": getdate(reference_date) if reference_date else None,
			"remarks": remarks or f"Collected in the field by {frappe.db.get_value('Employee', employee, 'employee_name')}",
		}
	)

	meta = frappe.get_meta("Payment Entry")
	if meta.has_field("custom_collected_by"):
		doc.custom_collected_by = employee
	if latitude not in (None, "") and meta.has_field("custom_collected_lat"):
		doc.custom_collected_lat = flt(latitude)
		doc.custom_collected_lng = flt(longitude)

	doc.insert(ignore_permissions=True)

	if photo_base64:
		content = base64.b64decode(photo_base64.split(",")[-1])
		validate_upload(photo_filename or "receipt.jpg", content, images_only=True, max_mb=8)
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": photo_filename or "receipt.jpg",
				"attached_to_doctype": doc.doctype,
				"attached_to_name": doc.name,
				"content": content,
				"is_private": 1,
			}
		).insert(ignore_permissions=True)

	submitted = False
	if frappe.conf.get("crm_autosubmit_payments"):
		try:
			doc.submit()
			submitted = True
		except Exception:
			pass
	frappe.db.commit()

	return {
		"name": doc.name,
		"amount": amt,
		"customer": customer,
		"mode": mode_of_payment,
		"date": str(getdate()),
		"submitted": submitted,
		# Draft = recorded, pending verification by accounts. Say so plainly.
		"status": "Submitted" if submitted else "Recorded — pending verification by accounts",
	}


@frappe.whitelist()
def get_my_receipts(limit=30) -> list:
	"""Receipts this rep collected (identified by custom_collected_by, a Link field:
	it is NULL on every pre-existing Payment Entry, unlike a numeric field which would
	backfill to 0 and match the whole table)."""
	employee = get_current_employee()
	if not _exists("Payment Entry") or not frappe.get_meta("Payment Entry").has_field("custom_collected_by"):
		return []
	return frappe.get_all(
		"Payment Entry",
		filters={"custom_collected_by": employee, "docstatus": ["<", 2]},
		fields=["name", "posting_date", "party", "paid_amount", "mode_of_payment", "docstatus"],
		order_by="creation desc",
		limit=int(limit),
	)
