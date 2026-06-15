# Play Store route (optional) — TRIAM A+

Use this only if you want the app on Google Play (easier install + auto-updates) instead
of / in addition to internal sideloading. Cost: **one-time $25** Google developer fee
(no recurring fee). For your own reps, the **Internal testing** track is best — fast, no
full public review, up to 100 testers via a link.

Everything technical is already built: two GitHub Actions workflows + a privacy page.

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
- **Privacy policy URL**: `https://<your-site>/triam-privacy` (page already built & served).
- **Data safety form**: declare you collect **Location, Photos, Personal info** → used for
  **App functionality** (field-sales/attendance), **not shared/sold**, encrypted in transit.
- **Background location**: declare it; justification — *"verifying field-rep dealer visits and
  recording work routes/travel for an internal sales workforce."* (Internal testing has lighter
  review, but still declare honestly.)
- Content rating questionnaire + target audience (adults / business).

## Notes
- For production, set `frontend/capacitor.config.json` → `server.url` to your prod URL before building.
- Same keystore must be reused for all updates — keep it safe.
