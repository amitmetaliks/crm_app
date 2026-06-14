app_name = "crm_app"
app_title = "Amit Alliance CRM"
app_publisher = "Amit Alliance (Amit Metaliks Limited)"
app_description = "Amit Alliance CRM — field-visit CRM PWA built on Frappe CRM"
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

# Row-level visibility: reps see only their own visits; sales managers see all.
permission_query_conditions = {
	"CRM Visit": "crm_app.permissions.crm_visit_query",
}

# Scheduled background tasks (missed-visit + follow-up reminders) are added in Phase 4:
# scheduler_events = {
# 	"cron": {"*/5 * * * *": ["crm_app.tasks.send_due_reminders"]},
# 	"daily": ["crm_app.tasks.flag_missed_visits"],
# }
