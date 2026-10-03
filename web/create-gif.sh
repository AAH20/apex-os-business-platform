#!/bin/bash
# Create comprehensive GIF from screenshots
SCREENSHOTS_DIR="/Users/ahmedhassan/apex-os-business-platform/web/screenshots"
GIF_OUTPUT="/Users/ahmedhassan/apex-os-business-platform/web/demo.gif"
FRAMERATE=1
DURATION=3  # seconds per frame

# Create a video from screenshots using ffmpeg
# First, create a file list for ffmpeg
LIST_FILE="/tmp/screenshot_list.txt"
> "$LIST_FILE"

for img in "$SCREENSHOTS_DIR"/*.png; do
  if [ -f "$img" ]; then
    echo "file '$img'" >> "$LIST_FILE"
    echo "duration $DURATION" >> "$LIST_FILE"
  fi
done

# Add the last image again for smooth loop
last_img=$(ls -1 "$SCREENSHOTS_DIR"/*.png | tail -1)
echo "file '$last_img'" >> "$LIST_FILE"

# Create GIF using ffmpeg
ffmpeg -y -f concat -safe 0 -i "$LIST_FILE" \
  -vf "fps=${FRAMERATE},scale=1280:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer" \
  -loop 0 \
  "$GIF_OUTPUT" 2>&1

echo "GIF created: $GIF_OUTPUT"
ls -la "$GIF_OUTPUT"
