# How to get the APK — start to finish

Everything technical is built and committed (40 commits). The build has simply never had
anywhere to run: the repo has never been pushed, so GitHub Actions has never seen it.
These are the only steps left, and the first one is the only real blocker.

---

## Step 1 — Push the repo (only you can do this)

Claude is hard-blocked from pushing to GitHub (data-exfiltration guard), so this one is
yours. In a **normal PowerShell window** (not inside Claude):

```powershell
powershell -ExecutionPolicy Bypass -File "D:\Claude Cowork\Frappe App\deploy\push-to-github.ps1" -Token ghp_YOUR_FRESH_TOKEN
```

**Get a fresh token:** https://github.com/settings/tokens → *Generate new token (classic)*
→ tick scope **`repo`** → copy it.

> ⚠️ **Revoke the old token first.** One was pasted into a chat earlier and must be
> treated as compromised: https://github.com/settings/tokens → Delete.

The script creates the private repo `amitmetaliks/crm_app` and pushes `main`.

---

> ### Shortcut: just want an APK on a phone today?
>
> Skip steps 2–3. Go straight to GitHub → **Actions** → **"Build Android APK"** →
> **Run workflow**. It needs **no keystore and no secrets**, and produces
> `app-debug.apk` under **Artifacts → `triam-aplus-apk`**. Installs on any phone; not
> accepted by Play Store. That is the fastest path from here to an app in your hand.

---

## Step 2 — Create the signing key (once, ~2 minutes) — *only needed for Play Store*

GitHub → **Actions** → **"Create Android Keystore (run once)"** → **Run workflow**.
Enter a keystore password and a key password. **Write both down.**

Then open the finished run → **Artifacts** → download **`triam-upload-keystore`**.

> **Back up `triam-upload.jks` somewhere safe.** Lose it and you can never *update* the
> app on Play Store — only publish it fresh under a new listing. This matters even if
> Play Store is months away.

Now add four repo secrets — GitHub → **Settings → Secrets and variables → Actions →
New repository secret**:

| Secret | Value |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | contents of `triam-upload.jks.b64` |
| `ANDROID_STORE_PASSWORD` | your keystore password |
| `ANDROID_KEY_ALIAS` | `triam-upload` |
| `ANDROID_KEY_PASSWORD` | your key password |

---

## Step 3 — Build it

GitHub → **Actions** → **"Build Android Release (AAB for Play Store)"** → **Run workflow**.

Takes ~10 minutes. When it finishes, open the run → **Artifacts** →
**`triam-aplus-release`**, which contains:

* **`app-release.apk`** — install this on a phone directly
* **`app-release.aab`** — upload this to Play Store (Play will not accept an APK for a
  new app)

> The four workflows you will see in the Actions tab:
>
> | Workflow | Needs secrets? | Gives you |
> |---|---|---|
> | **Build Android APK** | no | `app-debug.apk` — install today |
> | **Create Android Keystore (run once)** | no | the signing key + its base64 |
> | **Build Android Release (AAB for Play Store)** | yes (the 4 above) | `app-release.aab` + `app-release.apk` |
> | **CI** | no | runs the test suite on every push |

---

## Step 4 — Install on a phone

1. Copy `app-release.apk` to the phone (WhatsApp/Drive/USB).
2. Tap it. Android will warn about "unknown sources" — allow it for your file manager.
3. Open **TRIAM A+**. It asks for a **server URL**, pre-filled with
   `https://amitalliance.dexciss.tech`.

**For testing today, change that to:** `https://hrdev.34-93-148-147.sslip.io`
— production does not have `crm_app` installed yet, so the default URL will not work
until Dexciss installs it.

4. Log in with normal company credentials. Allow **Location** and **Camera**.

---

## What you get vs the phone web app

The PWA at `https://hrdev.34-93-148-147.sslip.io/amit-crm` already works today and is
the *same app*. The APK adds:

* Route recording **with the screen off** (a location foreground service — the PWA
  cannot do this at all)
* A Play Store listing and auto-updates
* A real app icon and no browser chrome

**The pilot does not need to wait for the APK.** Reps can start on the PWA now
(see `PILOT-CHECKLIST.md`); the APK is a better wrapper around the same thing.

---

## Play Store (optional, later)

One-time **$25** developer fee. `PLAY-STORE-SETUP.md` has the exact Data-safety answers
and explains why the app deliberately avoids background-location permission (it uses a
foreground service instead, which keeps review routine).

Claude cannot create the account, pay the fee, or upload the app — those three are
yours. Everything feeding into them is prepared.
