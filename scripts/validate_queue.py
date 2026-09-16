"""
Validates content_queue/queue.json against the Phase 4 schema
(docs/queue-schema.md). Run before committing any change to queue.json —
Phase 5/6 will write to this file a lot, and a malformed entry (6
hashtags, a stray post_type typo, a misplaced logo_endcard) should fail
loud here, not surface as a confusing render/post error later.

Usage:
  python validate_queue.py [path/to/queue.json]
Exit code 0 = valid, 1 = errors found (printed to stdout).
"""

import json
import sys
import os

VALID_POST_TYPES = {"relatable", "app_promo"}
VALID_LAYOUTS = {"hook", "bullet_list", "stat_card", "photo", "logo_endcard"}
VALID_STAGES = {
    "drafted", "content_review", "content_approved", "content_needs_change",
    "rendered", "visual_review", "visual_needs_change", "queued", "posted",
}
REQUIRED_FIELDS = ["id", "post_type", "slides", "bg_variant", "caption", "hashtags", "cta", "angle", "stage"]


def validate_item(item, errors):
    prefix = f"id={item.get('id', '?')}"

    for field in REQUIRED_FIELDS:
        if field not in item:
            errors.append(f"{prefix}: missing required field '{field}'")
    if any(field not in item for field in REQUIRED_FIELDS):
        return  # further checks assume the fields exist

    if item["post_type"] not in VALID_POST_TYPES:
        errors.append(f"{prefix}: invalid post_type '{item['post_type']}' (expected {VALID_POST_TYPES})")

    slides = item["slides"]
    if not isinstance(slides, list) or not (1 <= len(slides) <= 10):
        errors.append(f"{prefix}: slides must be a list of length 1-10, got {slides!r}")
        slides = []

    for i, slide in enumerate(slides):
        layout = slide.get("layout")
        if layout not in VALID_LAYOUTS:
            errors.append(f"{prefix} slide[{i}]: invalid layout '{layout}' (expected {VALID_LAYOUTS})")
        if layout == "logo_endcard":
            is_last = i == len(slides) - 1
            if not is_last or item["post_type"] != "app_promo" or len(slides) == 1:
                errors.append(
                    f"{prefix} slide[{i}]: logo_endcard is only valid as the last slide of an "
                    f"app_promo carousel (post_type={item['post_type']!r}, {len(slides)} slides, "
                    f"is_last={is_last})"
                )
        if layout == "hook" and "text" not in slide:
            errors.append(f"{prefix} slide[{i}]: hook layout requires 'text'")
        if layout == "bullet_list" and "items" not in slide:
            errors.append(f"{prefix} slide[{i}]: bullet_list layout requires 'items'")
        if layout == "stat_card" and ("stat" not in slide or "caption" not in slide):
            errors.append(f"{prefix} slide[{i}]: stat_card layout requires 'stat' and 'caption'")
        if layout == "photo" and ("photo_path" not in slide or "caption" not in slide):
            errors.append(f"{prefix} slide[{i}]: photo layout requires 'photo_path' and 'caption'")

    if item["bg_variant"] not in (1, 2):
        errors.append(f"{prefix}: bg_variant must be 1 or 2, got {item['bg_variant']!r}")

    hashtags = item["hashtags"]
    if not isinstance(hashtags, list) or len(hashtags) > 5:
        errors.append(f"{prefix}: hashtags must be a list of at most 5, got {len(hashtags) if isinstance(hashtags, list) else hashtags!r}")

    if item["stage"] not in VALID_STAGES:
        errors.append(f"{prefix}: invalid stage '{item['stage']}' (expected one of {VALID_STAGES})")


def validate_queue(queue):
    errors = []
    seen_ids = set()
    for item in queue:
        if not isinstance(item, dict):
            errors.append(f"queue entry is not an object: {item!r}")
            continue
        item_id = item.get("id")
        if item_id in seen_ids:
            errors.append(f"duplicate id: {item_id}")
        seen_ids.add(item_id)
        validate_item(item, errors)
    return errors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "content_queue", "queue.json"
    )
    with open(path) as f:
        queue = json.load(f)

    errors = validate_queue(queue)
    if errors:
        print(f"{len(errors)} error(s) in {path}:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"{path}: {len(queue)} item(s), all valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
