#!/usr/bin/env python3
"""Create comprehensive GIF from page screenshots."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sys

SCREENSHOTS_DIR = Path("/Users/ahmedhassan/apex-os-business-platform/web/screenshots")
OUTPUT_GIF = Path("/Users/ahmedhassan/apex-os-business-platform/web/demo.gif")

PAGES = [
    ("dashboard", "Executive Dashboard"),
    ("accounting", "Accounting Module"),
    ("crm", "CRM & Sales Pipeline"),
    ("analytics", "Analytics & Forecasting"),
    ("agent-reach", "Agent-Reach Platform"),
    ("bigdata", "Big Data Platform"),
    ("datascience", "Data Science & ML"),
    ("continuous-bi", "Continuous BI"),
]

def create_gif():
    frames = []
    
    for name, title in PAGES:
        filepath = SCREENSHOTS_DIR / f"{name}.png"
        if not filepath.exists():
            print(f"⚠️ Missing: {filepath}")
            continue
        
        img = Image.open(filepath)
        
        # Resize to consistent width
        target_width = 1280
        ratio = target_width / img.width
        target_height = int(img.height * ratio)
        img = img.resize((target_width, target_height), Image.LANCZOS)
        
        # Add title bar
        title_height = 60
        titled_img = Image.new("RGB", (target_width, target_height + title_height), (7, 9, 14))
        titled_img.paste(img, (0, title_height))
        
        # Draw title
        draw = ImageDraw.Draw(titled_img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Inter.ttc", 28)
        except:
            font = ImageFont.load_default()
        
        draw.text((20, 15), title, fill=(6, 182, 212), font=font)
        draw.text((target_width - 200, 20), "APEX-OS", fill=(168, 85, 247), font=font)
        
        frames.append(titled_img)
        print(f"✅ Added frame: {title}")
    
    if not frames:
        print("❌ No frames to create GIF")
        return
    
    # Save as GIF with 3 seconds per frame
    frames[0].save(
        OUTPUT_GIF,
        save_all=True,
        append_images=frames[1:],
        duration=3000,
        loop=0,
        optimize=True
    )
    
    print(f"\n✅ GIF created: {OUTPUT_GIF}")
    print(f"   Frames: {len(frames)}")
    print(f"   Size: {OUTPUT_GIF.stat().st_size // 1024}KB")

if __name__ == "__main__":
    create_gif()
