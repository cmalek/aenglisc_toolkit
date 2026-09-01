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

# 4. Deleted topic: must rebuild (exercises HELP_MARKER/HELP_TOPICS_HASH,
# not just ordinary mtime propagation). Restores the topic on any exit,
# including a failed assertion, so a broken run never leaves a real help
# topic deleted.
TOPIC_TO_DROP="$(ls oeapp/help/topics/*.md | head -1)"
TOPIC_BACKUP="$(mktemp)"
cleanup_topic() {
    if [ ! -f "$TOPIC_TO_DROP" ] && [ -s "$TOPIC_BACKUP" ]; then
        cp "$TOPIC_BACKUP" "$TOPIC_TO_DROP"
    fi
    rm -f "$TOPIC_BACKUP"
}
trap cleanup_topic EXIT

cp "$TOPIC_TO_DROP" "$TOPIC_BACKUP"
rm -f "$TOPIC_TO_DROP"
if make -q help-assets; then
    echo "FAIL: no rebuild triggered after deleting topic $TOPIC_TO_DROP"
    exit 1
fi

cp "$TOPIC_BACKUP" "$TOPIC_TO_DROP"
make help-assets >/dev/null

if ! git diff --quiet -- "$TOPIC_TO_DROP" 2>/dev/null; then
    echo "FAIL: $TOPIC_TO_DROP was not restored identically"
    exit 1
fi

if ! make -q help-assets; then
    echo "FAIL: rebuild triggered after restoring topic and rebuilding (skip state not restored)"
    exit 1
fi

echo "PASS: help rebuild rule behaves correctly"
