"""
Phase 3: pulls Instagram Insights for every posted queue item and stores
them in content_queue/performance.json, keyed by post ID.

Same host as post_to_instagram.py (graph.instagram.com, not
graph.facebook.com) — the IGAA-prefixed token only works against that
host. See docs/build-plan.md for why.

Uses v22.0+: Meta deprecated 'impressions'/'video_views' in v22.0
(replaced by 'views', which is video/Reels-only anyway). For static
IMAGE/CAROUSEL_ALBUM posts — everything this pipeline posted before
2026-09-22 — the valid metric set is reach/likes/comments/saved/shares.

REELS (posts 14-18 on, once post_to_instagram.py posts a rendered
content_queue/rendered/<id>.mp4 as a Reel instead of an image): not yet
verified whether this same METRICS list is fully valid against a real
posted Reel, or whether it needs 'views'/'ig_reels_avg_watch_time'
added. fetch_insights() already fails per-item (prints and skips,
doesn't crash the job) if a metric name is rejected, so this is safe
either way -- but if Reels start showing up with no performance.json
data, check this list first before assuming something else broke.

Run daily via .github/workflows/track-engagement.yml. Safe to run
before any posts exist yet (queue.json is empty until Phase 5) — it
just finds nothing to do and exits cleanly.

Usage:
  python track_engagement.py
"""

import json
import os

import requests

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
PERF_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "performance.json")
GRAPH_VERSION = "v22.0"
BASE_URL = f"https://graph.instagram.com/{GRAPH_VERSION}"
METRICS = ["reach", "likes", "comments", "saved", "shares"]


def load_queue():
    if not os.path.exists(QUEUE_PATH):
        return []
    with open(QUEUE_PATH) as f:
        return json.load(f)


def load_performance():
    if not os.path.exists(PERF_PATH):
        return {}
    with open(PERF_PATH) as f:
        return json.load(f)


def fetch_insights(media_id, token):
    resp = requests.get(
        f"{BASE_URL}/{media_id}/insights",
        params={"metric": ",".join(METRICS), "access_token": token},
    )
    if not resp.ok:
        print(f"Insights fetch failed for media {media_id}: {resp.text}")
        return None
    data = resp.json().get("data", [])
    return {entry["name"]: entry["values"][0]["value"] for entry in data if entry.get("values")}


def main():
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        print("Missing IG_ACCESS_TOKEN env var.")
        return 1

    queue = load_queue()
    posted = [item for item in queue if item.get("stage") == "posted" and item.get("ig_media_id")]
    if not posted:
        print("No posted items with an ig_media_id yet — nothing to track.")
        return 0

    performance = load_performance()
    for item in posted:
        post_id = str(item["id"])
        insights = fetch_insights(item["ig_media_id"], token)
        if insights is None:
            continue
        record = performance.get(post_id, {})
        record.update(insights)
        # Context fields Phase 3 asks for, so performance.json is useful for
        # Phase 5's "read performance.json" research step without a queue.json join.
        record["bg_variant"] = item.get("bg_variant")
        record["angle"] = item.get("angle")
        record["post_type"] = item.get("post_type")
        record["ig_media_id"] = item["ig_media_id"]
        performance[post_id] = record
        print(f"Post {post_id}: {insights}")

    with open(PERF_PATH, "w") as f:
        json.dump(performance, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
