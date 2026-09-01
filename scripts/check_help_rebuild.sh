#!/usr/bin/env bash
# Verify the help-asset Make rule rebuilds when it should and skips when it shouldn't.
set -euo pipefail

QCH="oeapp/help/assets/aenglisc_toolkit_help.qch"
QHC="oeapp/help/assets/aenglisc_toolkit_help.qhc"

make help-assets >/dev/null

# 1. Unchanged sources: must not rebuild.
if ! make -q help-assets; then
    echo "FAIL: rebuild triggered with unchanged sources"
    exit 1
fi

# 2. Missing .qhc: must rebuild.
rm -f "$QHC"
if make -q help-assets; then
    echo "FAIL: no rebuild triggered when $QHC was missing"
    exit 1
fi

make help-assets >/dev/null
test -f "$QHC" || { echo "FAIL: $QHC not regenerated"; exit 1; }
test -f "$QCH" || { echo "FAIL: $QCH not regenerated"; exit 1; }

# 3. Changed topic: must rebuild.
# GNU Make 3.81 compares mtimes at whole-second resolution, and the rebuild
# above can finish within the same second as this touch on fast hardware.
# Sleep past the second boundary so the touch is unambiguously newer.
sleep 1
touch oeapp/help/topics/*.md
if make -q help-assets; then
    echo "FAIL: no rebuild triggered after touching a topic"
    exit 1
fi

make help-assets >/dev/null
echo "PASS: help rebuild rule behaves correctly"
