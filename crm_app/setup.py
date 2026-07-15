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
		# Audit for a rep-pinned shop location. Pinning moves the geofence, so it must be
		# attributable — otherwise a rep could quietly relocate a dealer to his doorstep.
		{
			"fieldname": "custom_geo_pinned_by",
			"fieldtype": "Link",
			"label": "Shop Pinned By",
			"options": "Employee",
			"read_only": 1,
			"insert_after": "custom_last_visit_date",
		},
		{
			"fieldname": "custom_geo_pinned_on",
			"fieldtype": "Datetime",
			"label": "Shop Pinned On",
			"read_only": 1,
			"insert_after": "custom_geo_pinned_by",
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

	# Auto-conveyance audit trail on the expense line: what GPS actually measured, and
	# whether the rep overrode it. The approver can then compare against the claimed
	# distance instead of taking it on trust.
	#
	# NOTE: their site already has its own `custom_distance_travelled` (Data) field on
	# this doctype. It is deliberately NOT declared here — create_custom_fields would
	# rewrite an existing field's properties, and that field belongs to their setup, not
	# ours. conveyance.py fills it only when the site actually has it.
	expense_detail_fields = [
		{
			"fieldname": "custom_gps_distance_km",
			"fieldtype": "Float",
			"label": "GPS Distance (km)",
			"precision": "2",
			"read_only": 1,
			"insert_after": "description",
		},
		{
			"fieldname": "custom_distance_source",
			"fieldtype": "Data",
			"label": "Distance Source",
			"read_only": 1,
			"insert_after": "custom_gps_distance_km",
		},
	]

	# Field-collection audit on the receipt: who took the money and where they stood.
	# custom_collected_by is a Link (NULL on every pre-existing Payment Entry), which is
	# what lets us identify app-created receipts — a Float would backfill to 0 and match
	# the entire table. See conveyance.py.
	payment_fields = [
		{
			"fieldname": "custom_collected_by",
			"fieldtype": "Link",
			"label": "Collected By (Field)",
			"options": "Employee",
			"read_only": 1,
			"insert_after": "mode_of_payment",
		},
		{
			"fieldname": "custom_collected_lat",
			"fieldtype": "Float",
			"label": "Collected Latitude",
			"precision": "6",
			"read_only": 1,
			"insert_after": "custom_collected_by",
		},
		{
			"fieldname": "custom_collected_lng",
			"fieldtype": "Float",
			"label": "Collected Longitude",
			"precision": "6",
			"read_only": 1,
			"insert_after": "custom_collected_lat",
		},
	]

	custom_fields: dict[str, list[dict]] = {
		"Customer": geo_fields,
		"CRM Lead": geo_fields,
		"Employee Checkin": checkin_fields,
		"Expense Claim Detail": expense_detail_fields,
		"Payment Entry": payment_fields,
	}

	to_install = {dt: fields for dt, fields in custom_fields.items() if frappe.db.exists("DocType", dt)}
	if to_install:
		create_custom_fields(to_install, ignore_validate=True)
