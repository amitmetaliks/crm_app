"""The manager's dashboard — the business, not the activity log.

``dashboards.get_analytics`` answers "did my reps move today": visits completed, beat
adherence, who checked in. Useful, but it is a supervisor's report card. It never touches
the numbers the business is actually run on — it predates the SAP work and reads none of
it.

This module answers the questions a sales head actually opens an app for:

  * **How much did we sell, and who sold it** — from the live SAP register (₹513 Cr of
    real invoices), not from the 47 ERPNext Sales Orders.
  * **Who owes us money** — from the SAP payment feed, positive balances only.
  * **Which dealers are slipping** — quiet for 90+ days, ranked by what they used to buy,
    because a big dealer going quiet matters more than a small one.
  * **Is the plan being followed** — PJP coverage, and skips *with a reason* kept separate
    from stops simply ignored.
  * **Are we holding the shelf** — our share of dealer stock, from the DMS checks.

Two design rules, both learned the hard way on this project:

**Attribution is reported, never assumed.** Only 13 of 28 SAP rep codes resolve to an
Employee and 218 of 466 dealer codes to a Customer. Unattributed sales are real money the
leaderboard cannot show, so ``coverage`` surfaces the gap instead of quietly dropping it.
A leaderboard that silently omits half the business is worse than no leaderboard.

**Feed health is on the dashboard, not buried.** If a sync stalls, every number here
shrinks and the month looks bad. ``feeds`` carries each source's last date so a stale
pipe reads as a stale pipe.
"""

import frappe
from frappe.utils import add_days, flt, get_first_day, getdate, today

from crm_app.api import get_current_employee, has_field, is_sales_manager
from crm_app.dashboards import _require_manager


def _team_employees():
	"""Active employees who could be selling. Kept broad on purpose: the SAP register is
	the source of truth for who actually invoiced, so filtering harder here would only
	hide reps whose Sales Person record is incomplete."""
	return frappe.get_all(
		"Employee", filters={"status": "Active"}, fields=["name", "employee_name"], limit=5000
	)


def _mgr_inr(n):
	n = flt(n)
	if n >= 1e7:
		return f"{n / 1e7:.2f} Cr"
	if n >= 1e5:
		return f"{n / 1e5:.2f} L"
	return f"{n:,.0f}"


def _manager_exceptions(out, frm_d, to_d):
	"""The control-tower feed: everything that needs the manager's attention, ranked by
	severity, each with a plain reason and a drill-down into the underlying records. Built
	from values already computed for the dashboard plus a couple of targeted queries — no new
	data sources, no scores.
	"""
	day = getdate(today())
	ex = []

	# Pending approvals — a manager-only blocker on the team's reimbursements.
	pend = out.get("pending_approvals", 0)
	if pend:
		ex.append({"type": "approvals", "severity": "high", "title": f"{pend} approval(s) waiting",
			"detail": "Clear the team's blocked reimbursements", "route": {"name": "Approvals"}})

	# Biggest outstanding dealers — real money to chase, drills into the dealer.
	rec = out.get("receivables", {})
	if rec.get("available"):
		for r in (rec.get("top") or [])[:2]:
			ex.append({"type": "collection", "severity": "high", "title": r["customer_name"],
				"detail": f"Outstanding ₹{_mgr_inr(r['outstanding'])}", "value": r["outstanding"],
				"route": {"name": "CustomerDetail", "params": {"name": r["customer"]}}})

	# Stale SAP feed — every number understates reality until it syncs.
	for label, feed in (("Sales", out.get("feeds", {}).get("sales", {})), ("Payments", out.get("feeds", {}).get("payments", {}))):
		if feed.get("available") and feed.get("stale"):
			db = feed.get("days_behind")
			ex.append({"type": "feed", "severity": "high",
				"title": f"{label} feed is {db} days behind" if db is not None else f"{label} feed is stale",
				"detail": "Dashboard numbers may understate reality until it syncs", "route": None})

	# Target gap vs how much of the period has elapsed.
	tgt = out.get("target", {})
	if flt(tgt.get("amount")):
		total_days = max(1, (getdate(to_d) - getdate(frm_d)).days + 1)
		elapsed = min(total_days, max(1, (day - getdate(frm_d)).days + 1))
		pace = round(elapsed / total_days * 100)
		pct = flt(tgt.get("amount_pct"))
		if pace - pct >= 10:
			ex.append({"type": "target", "severity": "medium",
				"title": f"Team at {round(pct)}% of target, pace expects {pace}%",
				"detail": f"{round(pace - pct)} points behind for the period", "route": {"name": "Analytics"}})

	# Planned beat stops today not visited yet (team-wide).
	beats = frappe.get_all("CRM Beat Plan", filters={"plan_date": day}, fields=["name", "sales_person"])
	if beats:
		sp = {b.name: b.sales_person for b in beats}
		entries = frappe.get_all(
			"CRM Beat Plan Entry", filters={"parent": ["in", list(sp)], "customer": ["is", "set"]}, fields=["parent", "customer"]
		)
		done = {
			(v.sales_person, v.customer)
			for v in frappe.get_all(
				"CRM Visit", filters={"visit_date": day, "visit_status": ["in", ["In Progress", "Completed"]]},
				fields=["sales_person", "customer"], limit=5000,
			)
		}
		missed = sum(1 for e in entries if (sp.get(e.parent), e.customer) not in done)
		if missed:
			ex.append({"type": "missed_visits", "severity": "medium", "title": f"{missed} planned stop(s) not visited yet",
				"detail": "Across the team's beats today", "route": {"name": "Beat"}})

	# Dealers going quiet — biggest lifetime value first.
	try:
		risk = get_at_risk_dealers(days=90, limit=2)
	except Exception:
		risk = []
	for r in risk:
		ex.append({"type": "at_risk", "severity": "medium", "title": r["customer_name"],
			"detail": f"No purchase in {r['days_quiet']}d · ₹{_mgr_inr(r['lifetime_value'])} lifetime",
			"route": {"name": "CustomerDetail", "params": {"name": r["customer"]}}})

	# Attribution gap — sales the leaderboard cannot show (data-trust, low severity).
	cq = out.get("coverage_quality", {})
	if cq.get("available") and cq.get("reps_total"):
		unmapped = cq["reps_total"] - cq.get("reps_matched", 0)
		if unmapped > 0:
			ex.append({"type": "attribution", "severity": "low", "title": f"{unmapped} rep code(s) not mapped",
				"detail": "Their sales aren't on the leaderboard", "route": None})

	rank = {"high": 0, "medium": 1, "low": 2}
	ex.sort(key=lambda x: rank.get(x["severity"], 3))
	return ex


@frappe.whitelist()
def get_manager_dashboard(period="mtd") -> dict:
	"""One call, because a manager opens this on a phone between meetings."""
	_require_manager()
	from crm_app import sap_receivables, sap_sales

	to_d = getdate()
	if period == "mtd":
		frm_d = get_first_day(to_d)
	elif period == "30d":
		frm_d = add_days(to_d, -29)
	elif period == "90d":
		frm_d = add_days(to_d, -89)
	else:
		frm_d = get_first_day(to_d)

	out = {"period": period, "from_date": str(frm_d), "to_date": str(to_d)}

	# ── Sales, from the live SAP register ────────────────────────────────────
	sales = {"amount": 0.0, "qty_mt": 0.0, "invoices": 0, "available": False}
	leaderboard = []
	if sap_sales.available():
		sales["available"] = True
		emps = _team_employees()
		by_name = {e.name: e.employee_name for e in emps}
		board = sap_sales.rep_leaderboard(frm_d, to_d)  # one GROUP BY, not one query per employee
		for e in emps:
			r = board.get(e.name)
			if not r or not r["invoices"]:
				continue
			sales["amount"] += r["amount"]
			sales["qty_mt"] += r["qty"]
			sales["invoices"] += r["invoices"]
			leaderboard.append(
				{
					"employee": e.name,
					"employee_name": by_name.get(e.name, e.name),
					"amount": r["amount"],
					"qty_mt": r["qty"],
					"invoices": r["invoices"],
				}
			)
		leaderboard.sort(key=lambda x: x["amount"], reverse=True)
		sales["amount"] = flt(sales["amount"], 2)
		sales["qty_mt"] = flt(sales["qty_mt"], 3)

		# What the leaderboard CANNOT show: invoiced under a rep code we cannot map.
		t = sap_sales.which()
		c = sap_sales.COLS[t]
		total = frappe.db.sql(
			f"""SELECT COALESCE(SUM({c['amount']}), 0) FROM `tab{t}`
			    WHERE {c['date']} BETWEEN %s AND %s""",
			(frm_d, to_d),
		)[0][0]
		sales["all_invoiced"] = flt(total, 2)
		sales["unattributed"] = flt(flt(total) - sales["amount"], 2)
		sales["attributed_pct"] = flt(sales["amount"] / flt(total) * 100, 1) if flt(total) else 0.0

	out["sales"] = sales
	out["leaderboard"] = leaderboard[:15]

	# ── Targets, so the sales number has something to mean ───────────────────
	target_amount = target_qty = 0.0
	if frappe.db.exists("DocType", "CRM Sales Target"):
		for t in frappe.get_all(
			"CRM Sales Target",
			filters={"from_date": ["<=", to_d], "to_date": [">=", frm_d]},
			fields=["target_amount", "target_qty_mt"],
			limit=500,
		):
			target_amount += flt(t.target_amount)
			target_qty += flt(t.target_qty_mt)
	# Achievement % is measured against ALL invoicing (all_invoiced), not just the half we can
	# attribute to a mapped rep code — otherwise a team that hit target reads as ~50% purely
	# because the other half is under unmapped codes. attributed_pct (above) keeps the
	# attribution quality visible separately.
	achieved_for_target = flt(sales.get("all_invoiced", sales["amount"]))
	out["target"] = {
		"amount": flt(target_amount, 2),
		"qty_mt": flt(target_qty, 3),
		"amount_pct": flt(achieved_for_target / target_amount * 100, 1) if target_amount else 0.0,
	}

	# ── Money owed ───────────────────────────────────────────────────────────
	receivables = {"available": False, "total": 0.0, "dealers": 0, "top": []}
	if sap_receivables.available():
		names = frappe.get_all("Customer", pluck="name", limit=5000)
		owed = sap_receivables.outstanding_for(names)
		rows = sorted(owed.values(), key=lambda r: r["outstanding"], reverse=True)
		receivables = {
			"available": True,
			"total": flt(sum(r["outstanding"] for r in rows), 2),
			"dealers": len(rows),
			"top": rows[:8],
			# SAP sends a balance, not open items — there is no ageing to compute.
			"no_ageing": True,
		}
	out["receivables"] = receivables

	# ── Coverage: is the plan being followed ─────────────────────────────────
	visits = frappe.db.count(
		"CRM Visit", {"visit_date": ["between", [frm_d, to_d]], "visit_status": "Completed"}
	)
	skips = 0
	if frappe.db.exists("DocType", "CRM Visit Skip"):
		skips = frappe.db.count("CRM Visit Skip", {"skip_date": ["between", [frm_d, to_d]]})
	active_reps = len(
		{
			v.sales_person
			for v in frappe.get_all(
				"CRM Visit",
				filters={"visit_date": ["between", [frm_d, to_d]]},
				fields=["sales_person"],
				limit=5000,
			)
		}
	)
	out["coverage"] = {
		"visits": visits,
		"skips_with_reason": skips,
		"active_reps": active_reps,
		"dealers_visited": len(
			{
				v.customer
				for v in frappe.get_all(
					"CRM Visit",
					filters={"visit_date": ["between", [frm_d, to_d]], "customer": ["!=", ""]},
					fields=["customer"],
					limit=5000,
				)
				if v.customer
			}
		),
	}

	# ── Shelf share, from the dealer stock checks ────────────────────────────
	shelf = {"available": False}
	if frappe.db.exists("DocType", "CRM Dealer Stock"):
		checks = frappe.get_all(
			"CRM Dealer Stock",
			filters={"check_date": ["between", [frm_d, to_d]]},
			fields=["our_closing_mt", "competitor_closing_mt"],
			limit=1000,
		)
		if checks:
			ours = flt(sum(flt(c.our_closing_mt) for c in checks))
			comp = flt(sum(flt(c.competitor_closing_mt) for c in checks))
			shelf = {
				"available": True,
				"checks": len(checks),
				"our_share_pct": flt(ours / (ours + comp) * 100, 1) if (ours + comp) else 0.0,
				"our_mt": flt(ours, 3),
				"competitor_mt": flt(comp, 3),
			}
	out["shelf"] = shelf

	# ── Pending approvals: the manager's own to-do ────────────────────────────
	pending = 0
	if frappe.db.exists("DocType", "Expense Claim"):
		pending = frappe.db.count(
			"Expense Claim", {"approval_status": "Draft", "docstatus": ["<", 2]}
		)
	out["pending_approvals"] = pending

	# ── Feed health, on the dashboard rather than buried ──────────────────────
	out["feeds"] = {
		"sales": sap_sales.last_synced() if sap_sales.available() else {"available": False},
		"payments": sap_receivables.last_synced() if sap_receivables.available() else {"available": False},
	}
	out["coverage_quality"] = sap_sales.coverage() if sap_sales.available() else {"available": False}

	# The control-tower feed: ranked, drill-down exceptions built from the values above.
	out["exceptions"] = _manager_exceptions(out, frm_d, to_d)
	return out


@frappe.whitelist()
def get_at_risk_dealers(days=90, limit=15) -> list:
	"""Dealers who have gone quiet, biggest first.

	Ranked by what they USED to buy, not alphabetically: a ₹2 Cr dealer going silent is a
	different problem from a ₹2 L one, and a list that does not say which is which just
	becomes noise a manager scrolls past.
	"""
	_require_manager()
	from crm_app import sap_sales

	if not sap_sales.available():
		return []
	t = sap_sales.which()
	c = sap_sales.COLS[t]
	cutoff = add_days(getdate(), -int(days))

	rows = frappe.db.sql(
		f"""
		SELECT r.{c['cust']} AS sap_code, MAX(r.{c['date']}) AS last_invoice,
		       SUM({c['amount']}) AS lifetime_value, COUNT(DISTINCT r.{c['inv']}) AS invoices
		FROM `tab{t}` r
		WHERE COALESCE(r.{c['cust']}, '') != ''
		GROUP BY r.{c['cust']}
		HAVING MAX(r.{c['date']}) < %(cutoff)s
		ORDER BY SUM({c['amount']}) DESC
		LIMIT %(limit)s
		""",
		{"cutoff": cutoff, "limit": int(limit) * 3},
		as_dict=True,
	)
	if not rows:
		return []

	# Map back to Customers so the manager can open the dealer, not a SAP code.
	# custom_customer_sap_code is a custom field: on a site that has the SAP register but
	# not that field (they are independent), filtering on it raises "Unknown column" and
	# takes the whole dashboard down — the same trap as Address.latitude. Guard it.
	if not has_field("Customer", "custom_customer_sap_code"):
		return []
	custs = frappe.get_all(
		"Customer",
		filters={"custom_customer_sap_code": ["in", [r.sap_code for r in rows]]},
		fields=["name", "customer_name", "custom_customer_sap_code"],
	)
	by_code = {c.custom_customer_sap_code: c for c in custs}

	out = []
	today_d = getdate()
	for r in rows:
		cust = by_code.get(r.sap_code)
		if not cust:
			continue  # SAP party we cannot resolve — counted in coverage(), not shown here
		out.append(
			{
				"customer": cust.name,
				"customer_name": cust.customer_name,
				"last_invoice": str(r.last_invoice),
				"days_quiet": (today_d - getdate(r.last_invoice)).days,
				"lifetime_value": flt(r.lifetime_value, 2),
				"invoices": int(r.invoices or 0),
			}
		)
		if len(out) >= int(limit):
			break
	return out
