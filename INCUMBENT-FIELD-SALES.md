# The incumbent `field_sales` app — what it is, and what TRIAM A+ must match

**Why this file exists:** production already runs a field-sales app (`field_sales`, module
"Field Sales"). If its vendor's services are discontinued, **TRIAM A+ is the replacement**,
and this is the specification it has to meet. Everything below was read from the live
production data in the 15-Jul-2026 backup, not from a brochure.

## It is live, not legacy

| DocType | Rows | Last activity |
|---|---|---|
| **Sales Person Activity Log** | **52,416** | 15 Jul 14:38 |
| **Skip Visit** | **22,738** | 14 Jul 21:17 |
| **Beat Visit** (the core visit) | **1,628** | 15 Jul 14:25 |
| Beat Plan | 527 | 14 Jul |
| Visit Feedback | 526 | 15 Jul 13:55 |
| Must See List | 128 | 10 Jul |
| Secondary Stock | 128 | 3 Jul |
| Visit Order | 70 | 3 Jul |
| Visit Stock | 65 | 14 Jul |
| Tertiary Stock | 12 | 3 Jul |
| Visit Gift / Tertiary Sales / **TA Allowance** | **0** | never used |

**~76,000 records, 17 named rep users, in daily use since April 2026.** Real users:
`kamal.sales.aml@gmail.com` (156 feedbacks), `triam.birbhum@outlook.com` (155),
`triam.coochbihar.aml`, `triam.n24pgs`, `indrajit.amlsales`, `mithun.sales`…

## What it has that TRIAM A+ does NOT

These are the real gaps — the things that would be *lost* in a switchover:

| Their feature | Why it matters | TRIAM A+ status |
|---|---|---|
| **Tertiary sales/stock** (dealer → end customer) | The layer below secondary. TMT sells through sub-dealers. | ❌ we model primary + secondary only |
| **Territory Group / Territory Type / Group Items** | Territory hierarchy, ASM/RSM rollups | ❌ flat territory only |
| **Skip Visit** (22,738 rows!) | Rep declares *why* a planned stop was skipped. Their single most-used feature after the activity log. | ❌ we only record what happened, not what didn't |
| **Sales Person Activity Log** (52,416) | Fine-grained activity audit | ⚠️ we have visits + pings, not a unified log |
| **Rack placement feedback** (+ image) | Shelf/merchandising audit at the shop | ❌ |
| **Audio recordings** on a visit | Voice notes from the field | ❌ |
| **Gift items** on a visit | Mason/engineer gifting (SAP register has `gift_mason_engine`) | ❌ |
| **Must See List** | Priority dealers a rep must cover | ⚠️ our PJP is close but not the same idea |
| **AI insights** (per-customer, on the visit) | `ai_insights_html` / `_data` on Beat Visit | ⚠️ ours is rule-based, on a separate screen |
| **In-visit target stats** | Monthly target qty/amount + % achieved, and "average monthly potential", shown *inside* the visit | ⚠️ ours are on separate screens |
| **Primary vs Secondary customer feedback** | Two distinct feedback doctypes | ⚠️ single feedback model |
| **Beat Visit Customer Distance** | Distance from rep to dealer per visit | ✅ we have geofence + route distance |
| **Field Force Map Table** | Live force map | ✅ we have TeamMap |
| Geolocation (`map`, GeoJSON Point) | Visit stored as a GeoJSON feature | ✅ lat/lng + geofence |

## What TRIAM A+ has that they do NOT

| Ours | Evidence they lack it |
|---|---|
| **Auto-conveyance: GPS km × their own ₹3/km → Expense Claim** | Their `TA Allowance` doctype has **0 rows** — built, never used |
| **Attendance (selfie + GPS → Employee Checkin)** | Not in Field Sales at all |
| **Expense / Leave / Salary / Holidays for the rep** | Not in Field Sales |
| **Manager approvals in-app** (leave/expense/visit verify) | Not in Field Sales |
| **Offline queue + sync** | Unknown; no evidence in schema |
| **Hindi / Bengali** | Not in schema |
| **App lock (PIN/biometric)**, **web push** | Not in schema |
| **Play-Store-ready Android** with foreground-service tracking | Their app is the vendor's own |
| **Cash collection → on-account Payment Entry + WhatsApp receipt** | They have `Payment Entry Transaction` (14 rows) |
| **Route optimization / auto distance for TA** | They have distance, not optimization |

## The data that must survive a switchover

Nothing may be lost on the day the incumbent is switched off:

- `Beat Visit` (1,628) → `CRM Visit`
- `Beat Plan` (527) → `CRM Beat Plan`
- `Visit Feedback` (526) → visit outcome/notes
- `Visit Order` (70) → `CRM Visit Order Item`
- `Visit Stock` / `Secondary Stock` (65/128) → `CRM Dealer Stock`
- `Tertiary Stock` (12) → **needs a tertiary model we do not have**
- `Skip Visit` (22,738) → **needs a skip/reason model we do not have**
- `Sales Person Activity Log` (52,416) → archive or map to timeline

A migration script is only worth writing once the takeover is real — but the model gaps
above have to be closed **first**, or the history has nowhere to land.

## Verdict

TRIAM A+ is **not yet a drop-in replacement.** It is ahead on workforce (attendance,
expense, leave, salary, conveyance), platform (offline, i18n, Android, push, app lock)
and money-in (cash collection). It is behind on **tertiary sales, skip-visit, territory
hierarchy, rack placement, audio notes and gifting** — all of which their reps use today.

Closing those six gaps is what turns this from "a good app" into "a safe replacement".
