#!/usr/bin/env bash
# Patch the Capacitor-generated Android manifest for FOREGROUND-SERVICE location tracking.
#
# Why: the app records a rep's route while the screen is off. Android allows this with
# only FINE/COARSE location as long as a location-type FOREGROUND SERVICE is running
# ("Your app retains access when it's placed in the background, such as when the user
# ... turns their device's display off" — Android docs). We therefore must NOT ship
# ACCESS_BACKGROUND_LOCATION, which triggers Google Play's Permissions Declaration
# review (form + video demo) and is a common rejection cause.
#
# The @capacitor-community/background-geolocation library declares
# ACCESS_BACKGROUND_LOCATION in its own manifest, and the manifest merger would pull it
# into our APK/AAB. `tools:node="remove"` strips it during the merge.
#
# Run from the `frontend` directory, after `npx cap add android`.
set -euo pipefail

MAN=android/app/src/main/AndroidManifest.xml
[ -f "$MAN" ] || { echo "ERROR: $MAN not found (run npx cap add android first)"; exit 1; }

# The tools: namespace is required for tools:node="remove".
grep -q 'xmlns:tools' "$MAN" || \
  perl -0pi -e 's#(<manifest\s)#${1}xmlns:tools="http://schemas.android.com/tools" #' "$MAN"

# Idempotent: only inject if we have not already patched this manifest.
if ! grep -q 'ACCESS_FINE_LOCATION' "$MAN"; then
  perl -0pi -e 's#(<application)#<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>\n    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>\n    <uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>\n    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION"/>\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>\n    <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" tools:node="remove"/>\n    ${1}#' "$MAN"
fi

echo "--- source manifest permissions ---"
grep 'uses-permission' "$MAN" || true
