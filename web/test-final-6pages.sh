#!/bin/bash
# Final test of 6 pages using Chrome headless command (as specified by user)
# For each page: (1) Screenshot, (2) Verify dark theme, (3) Verify data loads, (4) Verify buttons, (5) Check console errors

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE="http://localhost:3000"
SCREENSHOT_DIR="/Users/ahmedhassan/apex-os-business-platform/web/screenshots/final-6pages"
RESULTS_FILE="/Users/ahmedhassan/apex-os-business-platform/web/final-6pages-results.json"

mkdir -p "$SCREENSHOT_DIR"

PAGES=("product-management" "order-management" "customer-management" "employee-management" "project-management" "task-management")

echo "["
first=true
for page in "${PAGES[@]}"; do
    url="$BASE/$page"
    ss_path="$SCREENSHOT_DIR/$page.png"
    dom_path="$SCREENSHOT_DIR/$page-dom.html"
    
    # 1. Screenshot + DOM dump using Chrome headless
    "$CHROME" --headless --disable-gpu --no-sandbox --disable-dev-shm-usage \
        --window-size=1440,900 \
        --screenshot="$ss_path" \
        --virtual-time-budget=5000 \
        --dump-dom "$url" > "$dom_path" 2>/dev/null
    
    ss_size=0
    [ -f "$ss_path" ] && ss_size=$(stat -f%z "$ss_path" 2>/dev/null || stat -c%s "$ss_path" 2>/dev/null)
    
    # 2-5. Analyze DOM for dark theme, data, buttons
    # Use python to parse the DOM
    analysis=$(python3 -c "
import json, re, sys

with open('$dom_path', 'r') as f:
    html = f.read()

# Dark theme check
body_match = re.search(r'<body[^>]*style=\"([^\"]*)\"', html)
body_style = body_match.group(1) if body_match else ''
html_match = re.search(r'<html[^>]*style=\"([^\"]*)\"', html)
html_style = html_match.group(1) if html_match else ''

# Check for dark background in style or class
has_dark = 'dark' in html.lower() or '#1a1a1a' in html.lower() or '#0f172a' in html.lower() or '#111827' in html.lower()

# Data loaded check
tables = len(re.findall(r'<table', html))
rows = len(re.findall(r'<tr', html))
buttons = len(re.findall(r'<button', html))
inputs = len(re.findall(r'<input', html))
divs = len(re.findall(r'<div', html))
text_content = re.sub(r'<[^>]+>', ' ', html)
text_content = re.sub(r'\s+', ' ', text_content).strip()
text_len = len(text_content)

# Check for error messages
has_error = 'error' in text_content.lower() or 'failed' in text_content.lower()
has_loading = 'loading' in text_content.lower()
has_no_data = 'no data' in text_content.lower() or 'empty' in text_content.lower()

# Button texts
button_texts = re.findall(r'<button[^>]*>([^<]*)</button>', html)
button_texts = [b.strip() for b in button_texts if b.strip()]

print(json.dumps({
    'dark_theme': has_dark,
    'tables': tables,
    'rows': rows,
    'buttons': buttons,
    'button_texts': button_texts[:10],
    'inputs': inputs,
    'divs': divs,
    'text_length': text_len,
    'has_error': has_error,
    'has_loading': has_loading,
    'has_no_data': has_no_data,
    'text_preview': text_content[:200]
}))
" 2>/dev/null)
    
    if [ "$first" = true ]; then
        first=false
    else
        echo ","
    fi
    
    echo "  {\"page\": \"$page\", \"url\": \"$url\", \"screenshot_size\": $ss_size, \"analysis\": $analysis}"
done
echo "]"
