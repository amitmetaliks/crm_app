# TRIAM A+ — Pilot Test Checklist

**App link:** https://hrdev.34-93-148-147.sslip.io/amit-crm
**Login:** your normal company email + password (same as ERP).
**Duration:** 1 week · **Reps:** 2–3 · **This is a TEST copy — nothing here touches live data.**

---

## First — install it on your phone (2 minutes)

1. Open the link above in **Chrome** (Android).
2. Tap the **⋮** menu → **Add to Home screen** / **Install app**.
3. Open it from the home screen icon (looks like a normal app).
4. When it asks, **Allow Location** and **Allow Camera**. Both are required.

> If the logo or screen looks stale, close the app fully and reopen (clears old cache).

---

## Daily use — do these as part of your normal day

| # | Do this | What to check |
|---|---|---|
| 1 | **Attendance check-in** (selfie + GPS) at day start | Photo saves, location correct |
| 2 | **See today's beat** (your planned dealer stops) | Right dealers listed |
| 3 | **Start a visit** at a dealer → GPS check-in | Marks you at the correct shop |
| 4 | **Add photo** of shop/stock | Uploads without failing |
| 5 | **Log an order / inquiry** (grade + tonnage) | Saves correctly |
| 6 | **Log competitor info** (brand, rate) | Saves correctly |
| 7 | **Check out** of the visit | Duration looks right |
| 8 | **Submit one expense** (with bill photo) | Reaches your manager |
| 9 | **Check Home / KRA screen** | Your numbers look believable |
| 10 | **Attendance check-out** at day end | Saves |

**Managers also test:** pending approvals (leave/expense), team dashboard, live team map, analytics.

---

## Please report these things (this is the important part)

Send a **WhatsApp message or screenshot** for anything below:

- ❌ **Anything that fails, freezes, or shows an error** — screenshot it
- 📍 **Wrong GPS** — says you're somewhere you're not, or won't check in at a dealer
- 🐢 **Slow screens** — anything taking more than ~5 seconds
- 📵 **What happens with no network / weak signal** — inside a warehouse, on the highway
- 🔢 **Wrong numbers** — sales, targets, outstanding that don't match reality
- 😕 **Anything confusing** — a button you couldn't find, a word that's unclear
- 🔋 **Battery drain** — if the phone drains much faster than usual

> **No issue is too small.** "The text was too small to read" is a real finding.

---

## Known / expected in this test

- **Visit history starts empty** — it's a fresh test database. Normal.
- **WhatsApp** opens your normal WhatsApp to send (tap-to-send). Normal.
- **This is the test server** — orders logged here do **not** become real Sales Orders in production.
- Android app (APK) is **not** part of this pilot — we test the phone web app first.

---

## After the week

Collect all findings → fixes get made → then we install on production and roll out wider.
