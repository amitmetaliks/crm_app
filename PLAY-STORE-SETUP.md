# Play Store route — TRIAM A+ (chosen distribution method)

The app is distributed via **Google Play**, not as a PWA/sideloaded APK. Cost: **one-time $25**
Google developer fee (no recurring fee). For your own reps, the **Internal testing** track is
best — fast, no full public review, up to 100 testers via a link — then promote to Production
(or Managed Google Play for org-only listing) when the pilot is done.

Everything technical is already built: two GitHub Actions workflows + a privacy page.

> **Foreground SERVICE location — by design; no background-location permission.**
> The app records the rep's route **with the screen off** using a location **foreground
> service** with a permanent notification ("TRIAM A+ — on duty"), started at attendance
> check-in and stopped at check-out. Android grants this with only `ACCESS_FINE_LOCATION`:
> *"Your app is running a foreground service... Your app retains access when it's placed in
> the background, such as when the user ... turns their device's display off."*
> ([Android docs](https://developer.android.com/develop/sensors-and-location/location/permissions))
>
> So the app does **not** request `ACCESS_BACKGROUND_LOCATION`, which would trigger Google's
> Permissions Declaration review (form + video demo + justification) — a common rejection
> cause for workforce apps, **with no exemption for private/enterprise or testing tracks**.
> The `background-geolocation` library declares that permission itself, so
> `scripts/patch-android-manifest.sh` strips it with `tools:node="remove"`, and
> `scripts/verify-android-manifest.sh` **fails the build** if it survives into the *merged*
> manifest.

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
- **Foreground service declaration** (apps targeting Android 14+): Play asks you to declare
  each foreground service type. Declare **Location**, with this use case:
  > *"Internal field-sales app. While a sales representative is on duty (between their
  > attendance check-in and check-out), the app records their dealer-visit route to verify
  > visits and compute travel distance for reimbursement. A permanent notification is shown
  > for the whole time recording is active. Recording stops at check-out."*
  This is a lighter declaration than background location and is normally approved for
  workforce/route apps. Play may ask for a short screen recording of the flow.
- Content rating questionnaire + target audience (adults / business).

## Notes
- For production, set `frontend/capacitor.config.json` → `server.url` to your prod URL before building.
- Same keystore must be reused for all updates — keep it safe.
