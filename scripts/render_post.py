"""
Renders a queued text idea into a 1080x1350 IG post image,
styled to match the Ooops visual system (coral-red / salmon-peach
gradient bg, dark maroon-brown text).

Free — uses Pillow only, no paid image generation API.

Usage:
  python render_post.py <queue_id>
Outputs to: content_queue/rendered/<queue_id>.png
"""

import json
import os
import sys
import textwrap
from PIL import Image, ImageDraw, ImageFont

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "content_queue", "rendered")
FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")

# Ooops palette (from project design system — update if brand shifts)
COLOR_BG_TOP = (255, 175, 145)      # salmon-peach
COLOR_BG_BOTTOM = (235, 110, 95)    # warm coral-red
COLOR_TEXT = (61, 26, 22)           # dark maroon-brown

W, H = 1080, 1350

def make_gradient_bg():
    base = Image.new("RGB", (W, H), COLOR_BG_TOP)
    top_r, top_g, top_b = COLOR_BG_TOP
    bot_r, bot_g, bot_b = COLOR_BG_BOTTOM
    for y in range(H):
        ratio = y / H
        r = int(top_r + (bot_r - top_r) * ratio)
        g = int(top_g + (bot_g - top_g) * ratio)
        b = int(top_b + (bot_b - top_b) * ratio)
        ImageDraw.Draw(base).line([(0, y), (W, y)], fill=(r, g, b))
    return base

def get_font(size):
    # Falls back to default if custom font isn't dropped into assets/fonts yet
    candidates = [f for f in os.listdir(FONT_PATH)] if os.path.exists(FONT_PATH) else []
    ttf = next((f for f in candidates if f.endswith(".ttf")), None)
    if ttf:
        return ImageFont.truetype(os.path.join(FONT_PATH, ttf), size)
    return ImageFont.load_default()

def render(text, out_path):
    img = make_gradient_bg()
    draw = ImageDraw.Draw(img)
    font = get_font(64)

    wrapped = textwrap.fill(text, width=22)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=16)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(
        ((W - tw) / 2, (H - th) / 2),
        wrapped, font=font, fill=COLOR_TEXT, spacing=16, align="center"
    )
    img.save(out_path)
    print(f"Rendered -> {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python render_post.py <queue_id>")
        sys.exit(1)

    with open(QUEUE_PATH) as f:
        queue = json.load(f)
    item = next((q for q in queue if q["id"] == int(sys.argv[1])), None)
    if not item:
        print("Queue id not found")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"{item['id']}.png")
    render(item["text"], out_path)

    item["status"] = "rendered"
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)
