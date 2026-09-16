"""
Renders a queued item (Phase 4 schema, see docs/queue-schema.md) into
its slide image(s) via scripts/design_system.py.

Single-slide item -> content_queue/rendered/<id>.png
Carousel item      -> content_queue/rendered/<id>/1.png, .../2.png, ...

Called by the (future) Phase 6 visual-approval step when an item
reaches stage "content_approved" — NOT by the daily posting cron.
Rendering happens during review, well before publish day; see
docs/queue-schema.md's "Where rendering actually happens". Still usable
standalone for ad-hoc testing:

Usage:
  python render_post.py <queue_id>
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import design_system as ds

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "content_queue", "rendered")


def render_slide(slide, bg_variant, branded):
    layout = slide["layout"]
    if layout == "hook":
        return ds.render_hook(slide["text"], bg_variant=bg_variant, branded=branded)
    if layout == "bullet_list":
        return ds.render_bullet_list(slide["items"], bg_variant=bg_variant, branded=branded)
    if layout == "stat_card":
        return ds.render_stat_card(slide["stat"], slide["caption"], bg_variant=bg_variant, branded=branded)
    if layout == "photo":
        return ds.render_photo(slide["photo_path"], slide["caption"], bg_variant=bg_variant, branded=branded)
    if layout == "logo_endcard":
        return ds.render_logo_endcard()
    raise ValueError(f"Unknown layout '{layout}'")


def render_item(item):
    """Returns a list of output paths (length 1 for a single post, N for
    a carousel). Applies the logo-placement rule (docs/queue-schema.md
    'Logo placement') — this is derived from post_type + slide count/
    position, never a per-slide flag a caller sets directly."""
    slides = item["slides"]
    post_type = item["post_type"]
    bg_variant = item["bg_variant"]
    is_carousel = len(slides) > 1

    paths = []
    if not is_carousel:
        branded = post_type == "app_promo"
        img = render_slide(slides[0], bg_variant, branded)
        out_path = os.path.join(OUT_DIR, f"{item['id']}.png")
        os.makedirs(OUT_DIR, exist_ok=True)
        img.convert("RGB").save(out_path)
        paths.append(out_path)
    else:
        item_dir = os.path.join(OUT_DIR, str(item["id"]))
        os.makedirs(item_dir, exist_ok=True)
        for i, slide in enumerate(slides):
            # app_promo carousels are unbranded except the fixed last
            # logo_endcard slide; relatable carousels are never branded.
            img = render_slide(slide, bg_variant, branded=False)
            out_path = os.path.join(item_dir, f"{i + 1}.png")
            img.convert("RGB").save(out_path)
            paths.append(out_path)
    return paths


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

    paths = render_item(item)
    for p in paths:
        print(f"Rendered -> {p}")

    item["stage"] = "rendered"
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)
