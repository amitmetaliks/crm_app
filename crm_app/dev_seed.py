"""Dev-only seeding + verification helpers for crm-dev (NOT used in production).

Run e.g.:  bench --site crm-dev execute crm_app.dev_seed.verify
"""

import base64

import frappe

TEST_USER = "fieldrep@crmtest.local"
TEST_PW = "FieldRep@2026"


def _ensure_company():
	name = frappe.db.get_value("Company", {}, "name")
	if name:
		return name
	# On a fresh ERPNext site (no setup wizard) the default Warehouse Types the
	# Company creation relies on may be missing — create the ones it needs.
	for wt in ("Transit",):
		if not frappe.db.exists("Warehouse Type", wt):
			frappe.get_doc({"doctype": "Warehouse Type", "name": wt}).insert(ignore_permissions=True)
	doc = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": "Amit Alliance",
			"abbr": "AA",
			"default_currency": "INR",
			"country": "India",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


def _root(doctype):
	return frappe.db.get_value(doctype, {"is_group": 0}, "name") or frappe.db.get_value(
		doctype, {}, "name"
	)


def _ensure_user_employee():
	if not frappe.db.exists("User", TEST_USER):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": TEST_USER,
				"first_name": "Field",
				"last_name": "Rep",
				"send_welcome_email": 0,
				"new_password": TEST_PW,
				"roles": [{"role": "Sales User"}],
			}
		).insert(ignore_permissions=True)

	emp = frappe.db.get_value("Employee", {"user_id": TEST_USER}, "name")
	if not emp:
		company = _ensure_company()
		for g in ("Male", "Female"):
			if not frappe.db.exists("Gender", g):
				frappe.get_doc({"doctype": "Gender", "gender": g}).insert(ignore_permissions=True)
		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Field",
				"last_name": "Rep",
				"employee_name": "Field Rep",
				"user_id": TEST_USER,
				"company": company,
				"status": "Active",
				"gender": "Male",
				"date_of_birth": "1995-01-01",
				"date_of_joining": "2024-01-01",
			}
		).insert(ignore_permissions=True)
		emp = doc.name
	frappe.db.commit()
	return emp


def seed_demo():
	"""Create a test rep + a few dealers with categories/geo. Idempotent."""
	emp = _ensure_user_employee()
	cg = _root("Customer Group")
	terr = _root("Territory")
	dealers = [
		("Sharma Steel Traders", "Dealer", 22.5726, 88.3639),
		("Verma Build Mart", "Distributor", 22.5958, 88.4042),
		("Ganesh Hardware & Steel", "Sub-Dealer", 22.5448, 88.3426),
	]
	names = []
	for nm, cat, lat, lng in dealers:
		existing = frappe.db.get_value("Customer", {"customer_name": nm}, "name")
		if existing:
			names.append(existing)
			continue
		c = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": nm,
				"customer_type": "Company",
				"customer_group": cg,
				"territory": terr,
			}
		).insert(ignore_permissions=True)
		c.db_set("custom_dealer_category", cat)
		c.db_set("custom_geo_latitude", lat)
		c.db_set("custom_geo_longitude", lng)
		c.db_set("custom_assigned_sales_person", emp)
		names.append(c.name)
	frappe.db.commit()
	return {"employee": emp, "customers": names}


def seed_phase3():
	"""Seed a beat plan (today, 3 dealers) + a monthly sales target for the test rep."""
	seeded = seed_demo()
	emp = seeded["employee"]
	custs = seeded["customers"]
	from frappe.utils import get_first_day, get_last_day, today

	# Beat plan for today
	if not frappe.db.exists("CRM Beat Plan", {"sales_person": emp, "plan_date": today()}):
		bp = frappe.new_doc("CRM Beat Plan")
		bp.sales_person = emp
		bp.plan_date = today()
		bp.title = "Kolkata North beat"
		bp.status = "Active"
		for cn in custs:
			bp.append("entries", {"party_type": "Customer", "customer": cn, "area": "Kolkata"})
		bp.insert(ignore_permissions=True)

	# Monthly target
	fd, ld = str(get_first_day(today())), str(get_last_day(today()))
	if not frappe.db.exists("CRM Sales Target", {"sales_person": emp, "from_date": fd}):
		tg = frappe.new_doc("CRM Sales Target")
		tg.sales_person = emp
		tg.period_label = "This Month"
		tg.from_date = fd
		tg.to_date = ld
		tg.target_amount = 5000000
		tg.target_qty_mt = 100
		tg.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"employee": emp, "customers": custs}


MGR_USER = "salesmgr@crmtest.local"


def _ensure_manager():
	if not frappe.db.exists("User", MGR_USER):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": MGR_USER,
				"first_name": "Sales",
				"last_name": "Manager",
				"send_welcome_email": 0,
				"new_password": TEST_PW,
				"roles": [{"role": "Sales Manager"}, {"role": "Sales User"}],
			}
		).insert(ignore_permissions=True)
	emp = frappe.db.get_value("Employee", {"user_id": MGR_USER}, "name")
	if not emp:
		company = _ensure_company()
		for g in ("Male", "Female"):
			if not frappe.db.exists("Gender", g):
				frappe.get_doc({"doctype": "Gender", "gender": g}).insert(ignore_permissions=True)
		emp = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Sales",
				"last_name": "Manager",
				"employee_name": "Sales Manager",
				"user_id": MGR_USER,
				"company": company,
				"status": "Active",
				"gender": "Male",
				"date_of_birth": "1985-01-01",
				"date_of_joining": "2020-01-01",
			}
		).insert(ignore_permissions=True).name
	frappe.db.commit()
	return emp


def verify4():
	"""Exercise leads + manager dashboard + scheduler tasks."""
	out = {}
	_ensure_manager()

	# leads as the rep
	frappe.set_user(TEST_USER)
	try:
		from crm_app import leads

		created = leads.create_lead(lead_name="Test Builder Pvt Ltd", organization="Test Builder Pvt Ltd", mobile_no="9811122233")
		out["lead_created"] = created.get("name")
		out["my_leads"] = len(leads.get_leads())
		out["my_deals"] = len(leads.get_deals())
	finally:
		frappe.set_user("Administrator")

	# manager dashboard
	frappe.set_user(MGR_USER)
	try:
		from crm_app import dashboards

		ov = dashboards.get_team_overview()
		out["team_today_total"] = ov.get("today_total")
		out["team_leaderboard"] = len(ov.get("leaderboard", []))
		out["team_recent"] = len(ov.get("recent", []))
	finally:
		frappe.set_user("Administrator")

	# scheduler tasks should run without error
	from crm_app import tasks

	tasks.send_beat_reminders()
	tasks.send_followup_reminders()
	tasks.flag_missed_visits()
	out["scheduler"] = "ran"
	frappe.db.commit()
	return out


def verify7():
	"""Exercise the enterprise round: attendance (selfie+GPS), expense/leave/salary/holiday
	reads, manager approvals + analytics. Needs hrms installed."""
	from io import BytesIO

	from PIL import Image

	_ensure_manager()
	buf = BytesIO()
	Image.new("RGB", (8, 8), (40, 60, 90)).save(buf, format="PNG")
	selfie = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

	out = {}
	frappe.set_user(TEST_USER)
	try:
		from crm_app import attendance, expense, holidays, leave, salary

		ci = attendance.check_in_out(latitude=22.5726, longitude=88.3639, selfie_base64=selfie, address="Kolkata")
		out["checkin"] = {"log_type": ci.get("log_type"), "name": ci.get("name")}
		ov = attendance.get_attendance_overview()
		out["attendance_next"] = ov.get("next_action")
		out["attendance_logs_today"] = len(ov.get("logs_today", []))
		out["expense_types"] = len(expense.get_expense_types())
		out["my_expenses"] = len(expense.get_my_expenses())
		out["leave_types"] = len(leave.get_leave_types())
		out["my_leaves"] = len(leave.get_my_leaves())
		out["salary_slips"] = len(salary.get_my_salary_slips())
		out["holidays"] = len(holidays.get_holidays().get("holidays", []))

		# offline one-shot visit submit
		from crm_app import field_visit

		cust = frappe.db.get_value("Customer", {}, "name")
		payload = {
			"client_ref": "verify7-ref-1",
			"party_type": "Customer",
			"customer": cust,
			"visit_purpose": "Order Booking",
			"check_in_time": frappe.utils.now(),
			"check_out_time": frappe.utils.now(),
			"notes": "offline submit test",
			"order_items": [{"order_type": "Firm Order", "grade": "Fe 550D", "quantity_mt": 10}],
			"competitors": [],
			"photos": [],
		}
		import json as _json

		r1 = field_visit.submit_full_visit(_json.dumps(payload))
		r2 = field_visit.submit_full_visit(_json.dumps(payload))  # replay → should dedupe
		out["offline_visit"] = r1.get("name")
		out["offline_dedupe"] = bool(r2.get("duplicate"))
	finally:
		frappe.set_user("Administrator")

	frappe.set_user(MGR_USER)
	try:
		from crm_app import approvals, dashboards

		pend = approvals.get_pending_approvals()
		out["approvals_count"] = pend.get("count")
		out["visits_to_verify"] = len(pend.get("visits", []))
		an = dashboards.get_analytics()
		out["analytics"] = {
			"conversion_pct": an.get("conversion_pct"),
			"adherence_pct": an.get("adherence_pct"),
			"attendance_today": an.get("attendance_today"),
			"ar_total": an.get("ar_total"),
		}
	finally:
		frappe.set_user("Administrator")
	frappe.db.commit()
	return out


def verify8():
	"""Exercise the SFA backend (home summary, KRA, timeline, top products, series)."""
	seed_phase3()
	emp = _ensure_user_employee()
	tname = frappe.db.get_value("CRM Sales Target", {"sales_person": emp}, "name")
	if tname:
		frappe.db.set_value(
			"CRM Sales Target",
			tname,
			{"target_visits": 40, "target_productive_calls": 25, "target_new_customers": 5, "collection_ratio_target": 95},
		)
	frappe.db.commit()

	out = {}
	frappe.set_user(TEST_USER)
	try:
		from crm_app import sfa

		h = sfa.get_home_summary()
		out["home_keys"] = sorted(h.keys())
		out["strike_rate"] = h["visits"]["strike_rate"]
		out["order_value"] = h["order_summary"]["value"]
		out["beat"] = h["beat"]
		out["kra"] = [(k["label"], k["pct"]) for k in sfa.get_kra()]
		out["timeline_items"] = len(sfa.get_activity_timeline()["items"])
		out["top_products"] = len(sfa.get_top_products()["items"])
		out["series_days"] = len(sfa.get_productivity_series()["series"])
	finally:
		frappe.set_user("Administrator")
	return out


def verify9():
	"""Exercise Phase 9: tracking/distance, credit, item search, geofence on check-in."""
	seed_demo()
	emp = _ensure_user_employee()
	cust = frappe.db.get_value("Customer", {"custom_assigned_sales_person": emp}, "name") or frappe.db.get_value("Customer", {}, "name")
	out = {}
	frappe.set_user(TEST_USER)
	try:
		from crm_app import field_visit, orders, tracking

		tracking.record_ping(22.5726, 88.3639, 10, "test")
		tracking.record_ping(22.5958, 88.4042, 10, "test")
		r = tracking.get_day_route()
		out["distance_km"] = r["distance_km"]
		out["route_stops"] = len(r["stops"])
		out["credit"] = orders.get_credit_status(cust)
		out["items_found"] = len(orders.search_items(""))
		st = field_visit.start_visit(party_type="Customer", customer=cust, latitude=22.5726, longitude=88.3639)
		out["geofence_within"] = st.get("within_geofence")
		out["geofence_dist_m"] = st.get("distance_m")
	finally:
		frappe.set_user("Administrator")
	return out


def verify10():
	"""Exercise route optimization + smart insights."""
	seed_phase3()
	out = {}
	frappe.set_user(TEST_USER)
	try:
		from crm_app import beat, insights

		opt = beat.optimize_beat(start_lat=22.57, start_lng=88.36)
		out["opt_stops"] = len(opt["stops"])
		out["opt_km"] = opt["total_km"]
		out["churn"] = len(insights.churn_risk())
		f = insights.sales_forecast()
		out["forecast"] = f["forecast"]
		out["hist_months"] = len(f["history"])
	finally:
		frappe.set_user("Administrator")
	return out


def diagnose_sales():
	"""Read-only: how do Sales Orders attribute to a salesperson on this site?"""
	out = {}
	out["sales_orders_total"] = frappe.db.count("Sales Order", {"docstatus": ["<", 2]})
	out["customers_total"] = frappe.db.count("Customer")
	out["customers_with_assigned_rep"] = frappe.db.count("Customer", {"custom_assigned_sales_person": ["is", "set"]})

	so = frappe.db.get_value("Sales Order", {"docstatus": ["<", 2]}, "name", order_by="modified desc")
	if so:
		d = frappe.get_doc("Sales Order", so)
		m = d.meta
		out["sample_so"] = so
		out["so_customer"] = d.customer
		out["so_owner"] = d.owner
		out["so_territory"] = getattr(d, "territory", None) if m.has_field("territory") else None
		out["so_has_sales_person_field"] = m.has_field("sales_person")
		out["so_sales_person_field"] = getattr(d, "sales_person", None) if m.has_field("sales_person") else None
		team = []
		if m.has_field("sales_team"):
			for r in d.get("sales_team") or []:
				team.append(r.sales_person)
		out["so_sales_team"] = team
		# what the SO's customer has for our field
		out["so_customer_assigned_rep"] = frappe.db.get_value("Customer", d.customer, "custom_assigned_sales_person")

	out["has_sales_person_doctype"] = bool(frappe.db.exists("DocType", "Sales Person"))
	if out["has_sales_person_doctype"]:
		out["sales_person_count"] = frappe.db.count("Sales Person")
		spm = frappe.get_meta("Sales Person")
		out["sales_person_has_employee_field"] = spm.has_field("employee")
		fields = ["name"] + (["employee"] if spm.has_field("employee") else [])
		out["sample_sales_persons"] = frappe.get_all("Sales Person", fields=fields, limit=5)
	return out


def verify_sales_fix(user_email="mukulmishra@amitmetaliks.com"):
	"""Confirm real Sales Orders now attribute to a rep (by owner/sales-team/assigned)."""
	from crm_app.sales_attr import rep_customers, rep_sales

	emp = frappe.db.get_value("Employee", {"user_id": user_email}, "name")
	out = {"user": user_email, "employee": emp}
	if emp:
		out["rep_sales_FY"] = rep_sales(emp, "2025-04-01", "2027-03-31")
		out["rep_customers"] = len(rep_customers(emp))
	return out


def verify_realdata():
	"""Read-only smoke test against a real-data site (e.g. realtest). Safe — no writes."""
	out = {"customers_total": frappe.db.count("Customer")}
	for dt in ["CRM Visit", "CRM Beat Plan", "CRM Sales Target", "CRM Lead"]:
		out["dt:" + dt] = 1 if frappe.db.exists("DocType", dt) else 0
	out["custom_field_on_customer"] = 1 if frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "custom_assigned_sales_person"}) else 0

	emp = frappe.db.get_value(
		"Employee",
		{"status": "Active", "user_id": ["is", "set"]},
		["name", "user_id"],
		as_dict=True,
		order_by="modified desc",
	)
	if emp:
		frappe.set_user(emp.user_id)
		try:
			from crm_app import customers, field_visit

			out["sample_employee"] = emp.user_id
			out["search_parties_count"] = len(customers.search_parties(query="", limit=10))
			out["my_visits_count"] = len(field_visit.get_my_visits())
		except Exception as e:
			out["error"] = str(e)
		finally:
			frappe.set_user("Administrator")
	return out


def verify3():
	"""Exercise beat/targets/collections as the test rep."""
	seed_phase3()
	frappe.set_user(TEST_USER)
	try:
		from crm_app import beat, collections, targets

		out = {}
		b = beat.get_my_beat()
		out["beat_planned"] = b.get("planned")
		out["beat_visited"] = b.get("visited")
		out["beat_entries"] = len(b.get("entries", []))
		tg = targets.get_my_targets()
		out["targets"] = len(tg)
		if tg:
			out["target_amount_pct"] = tg[0].get("amount_pct")
			out["target_achieved_amount"] = tg[0].get("achieved_amount")
		col = collections.get_my_collections()
		out["collections_total"] = col.get("total")
		out["collections_customers"] = len(col.get("customers", []))
	finally:
		frappe.set_user("Administrator")
	return out


def verify():
	"""Exercise the Phase 1 backend end-to-end as the test rep. Returns a report dict."""
	out = {}
	for dt in [
		"CRM Visit",
		"CRM Visit Photo",
		"CRM Visit Order Item",
		"CRM Visit Competitor",
		"CRM Push Subscription",
	]:
		out["doctype:" + dt] = 1 if frappe.db.exists("DocType", dt) else 0

	out["custom_fields_customer"] = frappe.get_all(
		"Custom Field", filters={"dt": "Customer", "fieldname": ["like", "custom_%"]}, pluck="fieldname"
	)
	out["custom_fields_crm_lead"] = frappe.get_all(
		"Custom Field", filters={"dt": "CRM Lead", "fieldname": ["like", "custom_%"]}, pluck="fieldname"
	)

	seeded = seed_demo()
	cust = seeded["customers"][0]

	frappe.set_user(TEST_USER)
	try:
		from crm_app import customers as customers_api
		from crm_app import field_visit

		started = field_visit.start_visit(
			party_type="Customer",
			customer=cust,
			visit_purpose="Follow-up",
			contact_name="Mr. Sharma",
			contact_phone="9800000000",
			latitude=22.5726,
			longitude=88.3639,
			address="Burrabazar, Kolkata",
		)
		name = started["name"]

		field_visit.save_visit(
			name=name,
			party_type="Customer",
			customer=cust,
			visit_purpose="Order Booking",
			notes="Discussed Q2 requirement; positive.",
			outcome="Order Received",
			next_action="Send quotation for 25 MT Fe 500D",
			order_items=[
				{
					"order_type": "Firm Order",
					"product": "TMT Bar",
					"grade": "Fe 500D",
					"quantity_mt": 25,
					"rate_per_mt": 52000,
					"expected_value": 1300000,
				}
			],
			competitors=[
				{"competitor_brand": "Tata Tiscon", "price_per_mt": 53500, "stock_status": "In Stock"}
			],
		)
		co = field_visit.check_out(name=name, latitude=22.5728, longitude=88.3641)
		detail = field_visit.get_visit(name)
		mine = field_visit.get_my_visits()
		parties = customers_api.search_parties(query="")
		cust_card = customers_api.get_customer(cust)
	finally:
		frappe.set_user("Administrator")

	out["visit_name"] = name
	out["checkout_status"] = co.get("visit_status")
	out["duration_minutes"] = co.get("duration_minutes")
	out["detail_party_display"] = detail["visit"].get("party_display")
	out["detail_order_rows"] = len(detail["order_items"])
	out["detail_competitor_rows"] = len(detail["competitors"])
	out["my_visits_count"] = len(mine)
	out["search_parties_count"] = len(parties)
	out["customer_card_visits"] = len(cust_card["visits"])
	frappe.db.commit()
	return out
