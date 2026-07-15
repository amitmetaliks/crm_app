# TRIAM A+ CRM (`crm_app`) — Production Install Guide (for Dexciss)

An **internal field-sales CRM + workforce app** built as a custom Frappe app on top of
**Frappe CRM** (`frappe/crm`) and ERPNext/HR. Reps use a mobile app at **`/amit-crm`**
(PWA; an optional native Android build also exists). All custom logic lives in `crm_app`
— **ERPNext, Frappe HR and Frappe CRM core are not modified.**

## Prerequisites (on the target bench / site)

- **Frappe Framework v16**, **ERPNext v16**
- **Frappe HR (`hrms`) v16** — required for attendance, expense, leave, salary
  (writes to Employee Checkin / Expense Claim / Leave Application / Salary Slip).
- **Frappe CRM** — `frappe/crm`, branch **`main`** (v1.x; supports v16)
- Python package **`pywebpush`** (declared in `crm_app/pyproject.toml`; auto-installed)

### Status on `amitalliance.dexciss.tech` (verified 2026-06-19)

**All prerequisites are already installed on production — only `crm_app` remains.**

| Dependency | Prod status | Evidence |
|---|---|---|
| frappe / erpnext | ✅ installed | assets serve `200` |
| **hrms** (Frappe HR) | ✅ installed | `/hr/dashboard` → `200` |
| **Frappe CRM** | ✅ **installed** | `/crm` + `/crm/leads` → `403` (route exists, login required); `/assets/crm/frontend/index.html` → `200` |
| **crm_app** (TRIAM A+) | ❌ not yet | `/amit-crm` + `/assets/crm_app/...` → `404` |

Dev reference build runs **Frappe CRM 1.73.2** (= latest upstream release, 11 Jun 2026).

## Install

Since `crm` and `hrms` are already installed on production, **only steps 2 and 4 below are needed there**
(steps 1 and 3a are for a fresh bench).

```bash
# 1. Frappe CRM — ALREADY INSTALLED on amitalliance.dexciss.tech; skip there.
bench get-app crm --branch main

# 2. This app
bench get-app crm_app https://github.com/amitmetaliks/crm_app.git --branch main

# 3a. Install crm on the site — ALREADY DONE on amitalliance.dexciss.tech; skip there.
bench --site <site> install-app crm
# 3b. Install this app (crm + hrms must already be installed)
bench --site <site> install-app crm_app

# 4. Migrate + build + restart  (migrate creates all doctypes + custom fields)
bench --site <site> migrate
bench build --app crm_app
bench --site <site> clear-cache
bench restart
```

The committed pre-built frontend is served as-is; to rebuild: `cd apps/crm_app/frontend && yarn install && yarn build`.

## What it adds (all server-side; created automatically by migrate)

- **DocTypes** (module “Amit CRM”): CRM Visit (+ children Photo / Order Item / Competitor),
  CRM Beat Plan (+ Entry), CRM Sales Target, CRM Push Subscription, **CRM Location Ping**.
- **Custom Fields** (idempotent via `after_migrate`):
  - **Customer** & **CRM Lead** — geo lat/long, dealer category, assigned sales person, last visit date.
  - **Employee Checkin** — check-in selfie + address (field attendance).
- **Modules / features**: field visits (GPS + photo watermark + **geofence** validation),
  beat planning (primary/secondary, route optimization), targets & **KRA scorecards**,
  collections, leads/deals, **attendance (selfie+GPS → Employee Checkin)**, **expense
  (→ Expense Claim)**, **leave / salary / holidays**, **manager approvals** (leave/expense/
  visit verify), **analytics + smart insights** (churn, forecast), **activity timeline**,
  **order → Quotation/Sales Order** (catalog + credit-limit check), **location tracking +
  auto distance**, **WhatsApp** share, offline sync, web push, app PIN/biometric lock.
- **PWA** at `/amit-crm` (renderer `crm_app.spa.SPARenderer`); privacy page at `/triam-privacy`.
- **Scheduler** (daily): beat reminders, follow-up reminders, missed-visit flags.
- **Row-level security**: reps see only their own rows; `Sales Manager` / `Sales Master Manager`
  / `System Manager` see the whole team.

## Optional config

- **Web Push**: VAPID keys auto-generate on first use (no setup).
- **Hands-free WhatsApp** (otherwise free tap-to-send is used): see `WHATSAPP-SETUP.md`, then
  `bench --site <site> set-config crm_whatsapp_token / crm_whatsapp_phone_id / crm_whatsapp_reminder_template`.

## Roles
- Field reps: any user with an **active Employee linked to their User** can use the app
  (identity comes from the session, not roles). `Sales User` adds desk visibility (optional).
- Managers: add **`Sales Manager`** for team dashboards/approvals/analytics.

## Post-install verification
1. `https://<site>/crm` loads Frappe CRM. `https://<site>/amit-crm` loads TRIAM A+ login.
2. Sign in as an employee user → Start a visit (GPS check-in, photo, order, check-out) → Attendance check-in.
3. (Optional) `bench --site <site> set-config allow_tests true && bench --site <site> run-tests --app crm_app`

## Notes
- Native Android app + Play Store are **client-side** (see `NATIVE-SETUP.md` / `PLAY-STORE-SETUP.md`) —
  not part of this server install; the app just needs to point at this site's URL.
- Targets/Collections/Insights read ERPNext **Sales Orders / Sales Invoices** for dealers whose
  `custom_assigned_sales_person` is set.
- Clean uninstall: `bench --site <site> uninstall-app crm_app`.
