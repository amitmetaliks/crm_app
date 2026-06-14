# Native Android app (TRIAM A+) — always-on tracking

The PWA can't track location when closed. This native build (Capacitor) wraps the
**same app** in an Android shell that runs **background GPS** (with a foreground-service
notification) and reports **mock-location** attempts — solving the one PWA limit.

It loads the live web app (`server.url` in `frontend/capacitor.config.json`) and adds the
native `@capacitor-community/background-geolocation` plugin (wired in `src/data/native.js`).

## Build the APK (no Android Studio needed — built in the cloud)

1. Push the repo to GitHub (you already do this with `push-to-github.ps1`).
2. On GitHub → **Actions** tab → **"Build Android APK"** → **Run workflow**.
3. When it finishes (~10 min), open the run → **Artifacts** → download **`triam-aplus-apk`**
   (contains `app-debug.apk`).

## Install on reps' phones (sideload)

1. Send them the `app-debug.apk` (WhatsApp/email/USB).
2. On the phone: open it → allow **"Install unknown apps"** for that source → Install.
3. First launch: **allow Location → "Allow all the time"** (required for background tracking)
   and allow notifications.

## Point it at production

`frontend/capacitor.config.json` → `server.url` currently points at the dev URL. Before a
real rollout, change it to your production URL (e.g. `https://amitalliance.dexciss.tech/amit-crm`)
and rebuild.

## Notes / future
- This produces a **debug-signed** APK — perfect for internal sideloading. For Play Store
  or stable auto-updates, we'd add a release keystore (GitHub secret) — easy to add later.
- The CI adds the needed location permissions to the Android manifest automatically.
- Everything else (login, visits, attendance, offline, etc.) works exactly as the web app,
  since it's the same code loaded in the native shell.
