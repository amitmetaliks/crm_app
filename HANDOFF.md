# TRIAM A+ CRM (`crm_app`) — Production Install Guide (for Dexciss)

This is an **internal field-visit CRM** built as a custom Frappe app on top of
**Frappe CRM** (`frappe/crm`). It adds a mobile PWA for sales reps at `/amit-crm`
(GPS visit check-in/out, photos, orders, competitor intel, beat planning, targets,
collections) plus manager dashboards. It does **not** modify ERPNext or Frappe CRM
core — all logic lives in `crm_app`.

## Prerequisites (on the target bench)

- **Frappe Framework v16**, **ERPNext v16**
- **Frappe CRM** — `frappe/crm`, branch **`main`** (v1.x; supports v16)
- Python package **`pywebpush`** (declared in `crm_app/pyproject.toml`; installed automatically with the app)

## Install

```bash
# 1. Frappe CRM (if not already installed)
bench get-app crm --branch main

# 2. This app
bench get-app crm_app https://github.com/<account>/crm_app.git --branch main

# 3. Install both on the site (order matters: crm before crm_app)
bench --site <site> install-app crm
bench --site <site> install-app crm_app

# 4. Migrate + build assets
bench --site <site> migrate
bench build --app crm_app
bench --site <site> clear-cache
bench restart
```

## What it adds

- **DocTypes** (module “Amit CRM”): CRM Visit (+ child Photo / Order Item / Competitor),
  CRM Beat Plan (+ Entry), CRM Sales Target, CRM Push Subscription.
- **Custom Fields** on **Customer** and **CRM Lead** (idempotent, via `after_migrate`):
  geo lat/long, dealer category, assigned sales person, last visit date.
- **PWA** served at **`/amit-crm`** (custom page renderer `crm_app.spa.SPARenderer`).
  Frontend assets are pre-built into `crm_app/crm_app/public/frontend` and committed.
  If you prefer to rebuild: `cd apps/crm_app/frontend && yarn install && yarn build`.
- **Scheduler** (daily): beat reminders, follow-up reminders, missed-visit flags.
- **Web Push** (self-hosted VAPID; keys auto-generated into site config on first use).
- **Row-level security**: reps see only their own visits/beats/targets; users with the
  `Sales Manager` (or `System Manager`) role see the whole team.

## Roles

- Field reps: any user with an **active Employee record linked to their User** can record
  visits (the app derives identity from the session, not from roles). Giving them the
  `Sales User` role makes the desk doctypes visible too (optional — the PWA works without it).
- Managers: add the **`Sales Manager`** role to unlock Team dashboards and team-wide views.

## Post-install verification

1. Open `https://<site>/crm` → Frappe CRM loads (leads/deals).
2. Open `https://<site>/amit-crm` → TRIAM A+ login; sign in as an employee user.
3. Start a visit → GPS check-in, add a photo, log an order, check out.
4. (Optional) `bench --site <site> set-config allow_tests true && bench --site <site> run-tests --app crm_app`

## Notes

- Targets/Collections read **ERPNext Sales Orders / Sales Invoices** for dealers whose
  `custom_assigned_sales_person` is set — assign dealers to reps to populate these.
- Field visits link to an ERPNext **Customer**, a Frappe CRM **Lead/Deal**, or a free-text
  **Prospect**, so converting a lead later keeps the visit history attached.
- Uninstall is clean: `bench --site <site> uninstall-app crm_app`.
