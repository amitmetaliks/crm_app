"""Idempotent setup for crm_app, run on every `bench migrate` via the
`after_migrate` hook.

Custom Fields on stock doctypes (Customer, CRM Lead) — geo coordinates, territory,
dealer category, last-visit date, assigned sales person — are added in Phase 1 here
via `create_custom_fields` (idempotent), guarded by a doctype-existence check so a
migrate never fails if Frappe CRM / ERPNext is not yet installed on the site.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():
	_install_custom_fields()
	frappe.db.commit()


def _install_custom_fields():
	# Field-sales context added to the dealer/customer + lead master records.
	# Self-chained via insert_after so the group stays together at the end of the form.
	geo_fields = [
		{
			"fieldname": "custom_field_sales_section",
			"fieldtype": "Section Break",
			"label": "Field Sales",
			"collapsible": 1,
		},
		{
			"fieldname": "custom_geo_latitude",
			"fieldtype": "Float",
			"label": "Geo Latitude",
			"precision": "6",
			"insert_after": "custom_field_sales_section",
		},
		{
			"fieldname": "custom_geo_longitude",
			"fieldtype": "Float",
			"label": "Geo Longitude",
			"precision": "6",
			"insert_after": "custom_geo_latitude",
		},
		{
			"fieldname": "custom_dealer_category",
			"fieldtype": "Select",
			"label": "Dealer Category",
			"options": "\nDistributor\nDealer\nSub-Dealer\nRetailer\nBuilder / Contractor\nProject\nArchitect / Engineer",
			"insert_after": "custom_geo_longitude",
		},
		{
			"fieldname": "custom_assigned_sales_person",
			"fieldtype": "Link",
			"label": "Assigned Sales Person",
			"options": "Employee",
			"insert_after": "custom_dealer_category",
		},
		{
			"fieldname": "custom_last_visit_date",
			"fieldtype": "Date",
			"label": "Last Visit Date",
			"read_only": 1,
			"insert_after": "custom_assigned_sales_person",
		},
	]

	# Selfie + address on Employee Checkin (field attendance). Only applied where
	# hrms is installed (guarded by the existence filter below).
	checkin_fields = [
		{
			"fieldname": "custom_selfie",
			"fieldtype": "Attach Image",
			"label": "Check-in Selfie",
			"insert_after": "device_id",
		},
		{
			"fieldname": "custom_check_in_address",
			"fieldtype": "Small Text",
			"label": "Check-in Address",
			"insert_after": "custom_selfie",
		},
	]

	custom_fields: dict[str, list[dict]] = {
		"Customer": geo_fields,
		"CRM Lead": geo_fields,
		"Employee Checkin": checkin_fields,
	}

	to_install = {dt: fields for dt, fields in custom_fields.items() if frappe.db.exists("DocType", dt)}
	if to_install:
		create_custom_fields(to_install, ignore_validate=True)
