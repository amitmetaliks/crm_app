app_name = "crm_app"
app_title = "TRIAM A+ CRM"
app_publisher = "Amit Alliance (Amit Metaliks Limited)"
app_description = "TRIAM A+ CRM — field-visit CRM PWA built on Frappe CRM"
app_email = "developments@amitalliance.com"
app_license = "mit"

# ─────────────────────────────────────────────────────────────────────────────
# Amit Alliance CRM (crm_app) configuration
# ─────────────────────────────────────────────────────────────────────────────

# Serve the Vue PWA via a custom renderer (reads public/frontend/index.html).
# Handles /amit-crm and all client-side deep links (/amit-crm/*).
page_renderer = ["crm_app.spa.SPARenderer"]

# Create/refresh custom fields (on Customer / CRM Lead) on every migrate (idempotent).
after_migrate = "crm_app.setup.after_migrate"

# Row-level visibility: reps see only their own rows; sales managers see all.
permission_query_conditions = {
	"CRM Visit": "crm_app.permissions.crm_visit_query",
	"CRM Beat Plan": "crm_app.permissions.crm_beat_plan_query",
	"CRM Sales Target": "crm_app.permissions.crm_sales_target_query",
}

# Scheduled background tasks: daily beat/follow-up reminders + missed-visit flags.
scheduler_events = {
	"daily": [
		# Build today's beat from each rep's PJP first, so the reminder that follows has
		# something to talk about.
		"crm_app.pjp.auto_generate_daily_beats",
		"crm_app.tasks.send_beat_reminders",
		"crm_app.tasks.send_followup_reminders",
		"crm_app.tasks.flag_missed_visits",
	],
}
