"""Dev-only seeding + verification helpers for crm-dev (NOT used in production).

Run e.g.:  bench --site crm-dev execute crm_app.dev_seed.verify
"""

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
