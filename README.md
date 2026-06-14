# Amit Alliance CRM (`crm_app`)

Internal, field-visit-focused CRM for Amit Alliance (TMT manufacturer), built as a custom
Frappe app on top of **Frappe CRM** (`frappe/crm`) and ERPNext.

- **Frappe CRM** (`/crm`) provides the leads/deals pipeline for inside-sales and managers.
- **`crm_app`** provides the **mobile PWA for field reps** at **`/amit-crm`** — GPS visit
  check-in/out, photo capture, orders/competitor logging, beat planning, targets, and
  payment-collection follow-up.

Sibling of the `hr_app` project; reuses its proven stack (Vue 3 + frappe-ui PWA, SPA
renderer, web-push, session/CSRF auth, upload validation, session-derived security model).

## Install (dev / Dexciss prod)

```
bench get-app crm            # Frappe CRM (branch main)
bench get-app crm_app <repo-url>
bench --site <site> install-app crm crm_app
bench --site <site> migrate
bench build --app crm_app
```

See `HANDOFF.md` for the production install guide.
