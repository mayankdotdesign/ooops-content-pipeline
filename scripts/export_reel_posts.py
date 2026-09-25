"""
Writes reel-studio/src/reelPosts.json from content_queue/queue.json -- the
reel renderer's only source of post text and reel settings, so copy is
never retyped by hand. Includes every item from id 14 on that has a
`reel` block. An item whose reel.experiment is "send_cta_9-10s" also gets
its caption CTA shown on screen (ctaLine) during the hold.

Usage:
  python scripts/export_reel_posts.py
"""

import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
QUEUE_PATH = os.path.join(ROOT, "content_queue", "queue.json")
OUT_PATH = os.path.join(ROOT, "reel-studio", "src", "reelPosts.json")


def main():
    with open(QUEUE_PATH) as f:
        queue = json.load(f)
    out = []
    for item in queue:
        reel = item.get("reel")
        if not reel or item["id"] < 14:
            continue
        slides = [s.get("text") or "\n\n".join(s.get("items", [])) for s in item["slides"]]
        post = {
            "id": item["id"],
            "template": reel["template"],
            "music": f"audio/{reel['music']}.mp3",
            "stagger": reel.get("stagger", 6),
            "slides": slides,
        }
        if reel.get("experiment") == "send_cta_9-10s":
            post["ctaLine"] = item["cta"]
        out.append(post)
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(out)} reel posts to {OUT_PATH}")


if __name__ == "__main__":
    main()
