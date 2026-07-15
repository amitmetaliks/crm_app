# Play Store route — TRIAM A+ (chosen distribution method)

The app is distributed via **Google Play**, not as a PWA/sideloaded APK. Cost: **one-time $25**
Google developer fee (no recurring fee). For your own reps, the **Internal testing** track is
best — fast, no full public review, up to 100 testers via a link — then promote to Production
(or Managed Google Play for org-only listing) when the pilot is done.

Everything technical is already built: two GitHub Actions workflows + a privacy page.

> **Foreground location only — by design.** The app does **not** request
> `ACCESS_BACKGROUND_LOCATION`. That permission triggers Google's Permissions Declaration
> review (form + video demo + written justification) and is one of the most common rejection
> causes, especially for workforce-tracking apps. Location is captured while the app is open
> and at every check-in/check-out, which covers the field-visit use case. Both Android
> workflows **fail the build** if background location ever reappears in the manifest.
> Trade-off accepted: no tracking while the phone is pocketed with the app closed, and no
> native mock-location (fake GPS) detection — geofencing and photo watermarking still apply.

## Step 1 — Create the signing keystore (once)
1. GitHub → **Actions → "Create Android Keystore" → Run workflow**. Enter a keystore
   password and key password (write them down — you need them for every future build).
2. Open the finished run → **Artifacts** → download **`triam-upload-keystore`**
   (keep `triam-upload.jks` somewhere safe — backup it; losing it complicates updates).
3. GitHub → **Settings → Secrets and variables → Actions → New repository secret**, add:
   - `ANDROID_KEYSTORE_BASE64` → paste the contents of `triam-upload.jks.b64`
   - `ANDROID_STORE_PASSWORD` → your keystore password
   - `ANDROID_KEY_ALIAS` → `triam-upload` (or what you chose)
   - `ANDROID_KEY_PASSWORD` → your key password

## Step 2 — Build the release bundle
GitHub → **Actions → "Build Android Release (AAB for Play Store)" → Run workflow**.
Download the **`triam-aplus-release`** artifact → it contains **`app-release.aab`**
(upload this to Play) and an APK. (Version code auto-increments each run.)

## Step 3 — Google Play Console
1. Create a developer account at https://play.google.com/console (**$25 one-time**).
2. **Create app** → name "TRIAM A+", app/free, default language English.
3. Use **Testing → Internal testing** → create a release → **upload `app-release.aab`**.
   - Accept **Play App Signing** (Google holds the signing key; our keystore is the upload key).
4. Add testers' emails (your reps) → share the opt-in link → they install from Play & get auto-updates.

## Step 4 — Required declarations (Play asks for these)
- **Privacy policy URL**: `https://<your-site>/triam-privacy` (page already built & served;
  it states location is collected **only while the app is open** — matches the manifest).
- **Data safety form** — answer exactly:
  | Question | Answer |
  |---|---|
  | Location — collected? | **Yes** → *Approximate + Precise location* |
  | Location — purpose | **App functionality** (verify dealer visits, travel distance) |
  | Photos — collected? | **Yes** → purpose: **App functionality** (attendance selfie, visit photos) |
  | Personal info | **Yes** → Name, Email, Phone → **App functionality** |
  | Data shared with third parties? | **No** |
  | Data encrypted in transit? | **Yes** (HTTPS) |
  | Can users request deletion? | **Yes** — via their employer/HR (internal app) |
- **Background location**: **not applicable — we do not request it.** No declaration form,
  no video demo needed. This is the main reason review should be routine.
- Content rating questionnaire + target audience (adults / business).

## Notes
- For production, set `frontend/capacitor.config.json` → `server.url` to your prod URL before building.
- Same keystore must be reused for all updates — keep it safe.
