#!/usr/bin/env python3
"""Build the platform demo GIF from the final2 screenshot set.

Run: python3 make_gif.py
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# This script lives at web/screenshots/make_gif.py, so the repo root is two
# levels up (screenshots -> web -> repo).
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "web" / "screenshots" / "final2"
GIF = REPO / "web" / "screenshots" / "platform-demo.gif"
FFMPEG = "/opt/homebrew/bin/ffmpeg"

# Logical walkthrough order: overview -> core business -> intelligence -> CRUD -> setup
HERO = [
    "dashboard", "analytics", "continuous-bi", "accounting", "budgeting", "crm",
    "agent-reach", "bigdata", "datascience", "hr-management", "onboarding", "sizing",
]

FRAME_SECONDS = 0.45   # dwell per page
LOOP_TAIL = 1.2        # hold last frame so the loop is seamless


def build_route_list() -> list[str]:
    """Every route in App.tsx, hero pages first."""
    app = REPO / "web" / "frontend" / "src" / "App.tsx"
    routes = sorted(
        {
            m.replace('path="', "").replace('"', "")
            for m in subprocess.run(
                ["grep", "-oE", r'path="[a-z0-9-]+"', str(app)],
                capture_output=True, text=True, check=False,
            ).stdout.split()
            if m
        }
    )
    rest = [r for r in routes if r not in HERO]
    return [r for r in HERO if r in routes] + rest


def main() -> None:
    routes = build_route_list()
    missing = [r for r in routes if not (OUT / f"{r}.png").exists()]
    if missing:
        raise SystemExit(f"missing screenshots: {missing}")

    frames = [OUT / f"{r}.png" for r in routes]
    sizes = {r: (OUT / f"{r}.png").stat().st_size for r in routes}
    thin = {r: s for r, s in sizes.items() if s <= 100_000}
    if thin:
        raise SystemExit(f"refusing to build GIF from thin/error frames: {thin}")

    lst = REPO / "web" / "screenshots" / "frames.txt"
    with lst.open("w") as fh:
        for path in frames:
            fh.write(f"file '{path}'\nduration {FRAME_SECONDS}\n")
        fh.write(f"file '{frames[-1]}'\nduration {LOOP_TAIL}\n")

    vf = (
        "scale=1280:-1:flags=lanczos,fps=2,split[s0][s1];"
        "[s0]palettegen=max_colors=192[p];[s1][p]paletteuse=dither=bayer"
    )
    subprocess.run(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-vf", vf, "-loop", "0", str(GIF)],
        check=True, capture_output=True, text=True, timeout=600,
    )

    size = GIF.stat().st_size
    print(f"GIF: {GIF}")
    print(f"     {size:,} bytes ({size / 1024 / 1024:.1f} MB)")
    print(f"     {len(frames)} frames @ {FRAME_SECONDS}s -> "
          f"{len(frames) * FRAME_SECONDS:.1f}s loop")


if __name__ == "__main__":
    main()
