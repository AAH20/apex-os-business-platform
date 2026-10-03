#!/bin/bash
# Capture screenshots of all pages using Chrome headless with virtual time budget
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCREENSHOTS_DIR="/Users/ahmedhassan/apex-os-business-platform/web/screenshots"
mkdir -p "$SCREENSHOTS_DIR"

PAGES=(
  "dashboard|/"
  "accounting|/accounting"
  "crm|/crm"
  "analytics|/analytics"
  "agent-reach|/agent-reach"
  "bigdata|/bigdata"
  "datascience|/datascience"
  "continuous-bi|/continuous-bi"
)

for entry in "${PAGES[@]}"; do
  name="${entry%%|*}"
  path="${entry##*|}"
  echo "Capturing: $name ($path)"
  "$CHROME" \
    --headless \
    --disable-gpu \
    --no-sandbox \
    --screenshot="$SCREENSHOTS_DIR/${name}.png" \
    --window-size=1920,1080 \
    --hide-scrollbars \
    --virtual-time-budget=5000 \
    --run-all-compositor-stages-before-draw \
    "http://localhost:3000${path}" 2>/dev/null
  echo "  -> ${name}.png"
done

echo "All screenshots captured!"
ls -la "$SCREENSHOTS_DIR"/*.png
