# Native Android app (TRIAM A+) — always-on tracking

The PWA can't track location when closed. This native build (Capacitor) wraps the
**same app** in an Android shell that runs **background GPS** (with a foreground-service
notification) and reports **mock-location** attempts — solving the one PWA limit.

On first launch the app shows a **server-address screen** — the rep (or you) enters the
TRIAM A+ URL once and it's saved on the device; the app then loads your live site inside the
native shell with the `@capacitor-community/background-geolocation` plugin (wired in
`src/data/native.js`). **The same APK works for any server** (dev, production, etc.) — no
rebuild needed to change servers.

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

No rebuild needed. On first launch, just type the production URL (e.g.
`https://amitalliance.dexciss.tech`) on the server-address screen. To switch servers later,
clear the app's storage (Android Settings → Apps → TRIAM A+ → Storage → Clear) and it will
ask again. (The dev URL is only pre-filled as a convenience.)

## Notes / future
- This produces a **debug-signed** APK — perfect for internal sideloading. For Play Store
  or stable auto-updates, we'd add a release keystore (GitHub secret) — easy to add later.
- The CI adds the needed location permissions to the Android manifest automatically.
- Everything else (login, visits, attendance, offline, etc.) works exactly as the web app,
  since it's the same code loaded in the native shell.
