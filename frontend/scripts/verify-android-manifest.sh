#!/usr/bin/env bash
# Fail the build if the FINAL MERGED manifest would ship background location, or if the
# location foreground service is missing.
#
# This checks the *merged* manifest (not our source one) because the permission we care
# about is contributed by a library and only appears after the manifest merger runs.
# Checking the source manifest alone would be meaningless.
#
# Run from the `frontend` directory, AFTER a gradle build.
set -euo pipefail

MERGED_FILES=$(find android/app/build/intermediates -name "AndroidManifest.xml" 2>/dev/null | grep -i "merge" || true)

if [ -z "$MERGED_FILES" ]; then
  echo "ERROR: no merged manifest found — cannot verify permissions. Failing closed."
  exit 1
fi

FAIL=0
for f in $MERGED_FILES; do
  echo "== checking $f"
  if grep -q 'android.permission.ACCESS_BACKGROUND_LOCATION' "$f"; then
    echo "   FAIL: ACCESS_BACKGROUND_LOCATION present — this triggers Google Play's"
    echo "         Permissions Declaration review. See PLAY-STORE-SETUP.md."
    FAIL=1
  else
    echo "   OK: no background location"
  fi
  if grep -q 'android.permission.ACCESS_FINE_LOCATION' "$f"; then
    echo "   OK: fine location present"
  else
    echo "   FAIL: ACCESS_FINE_LOCATION missing — tracking cannot work"
    FAIL=1
  fi
  if grep -qi 'foregroundServiceType="location"' "$f"; then
    echo "   OK: location foreground service declared"
  else
    echo "   FAIL: no foregroundServiceType=\"location\" — screen-off tracking will NOT work"
    FAIL=1
  fi
done

[ "$FAIL" = "0" ] || exit 1
echo "Manifest verified: foreground-service location only, no background location."
