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

import datetime
import json
import os

import requests

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
PERF_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "performance.json")
GRAPH_VERSION = "v22.0"
BASE_URL = f"https://graph.instagram.com/{GRAPH_VERSION}"
METRICS = ["reach", "likes", "comments", "saved", "shares"]  # proven-valid base set, one call

# 2026-09-25 (per request: "fetch all data points the API allows"): extras
# are requested ONE AT A TIME so a metric Instagram rejects for a media
# type can't take the base set down with it. Which ones actually work is
# recorded in content_queue/tracking_meta.json on every run -- this list
# was written from Meta's docs and could not be tested locally (the token
# is a CI secret), so read that file after the first run before trusting
# any missing field to mean "no data" rather than "rejected".
# follows / profile_visits: rejected for REELS and FEED media by the Media
# Insights API (confirmed on the first live run, 2026-09-25) -- those
# numbers only exist at account level (profile_views, follows_and_unfollows).
EXTRA_METRICS_ALL = ["views", "total_interactions"]
EXTRA_METRICS_REEL = [
    "ig_reels_avg_watch_time",          # ms, average watch time -- the retention number
    "ig_reels_video_view_total_time",   # ms, total watch time across all plays
]  # ig_reels_aggregated_all_plays_count / clips_replays_count: rejected on the
   # first live run (not valid metric names on this API host), removed.
META_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "tracking_meta.json")
ACCOUNT_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "account_insights.json")
HISTORY_CAP = 60



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


def _values(resp_json):
    """Insights come back either as values[0].value (older shape) or
    total_value.value (metric_type=total_value shape)."""
    out = {}
    for entry in resp_json.get("data", []):
        if entry.get("values"):
            out[entry["name"]] = entry["values"][0].get("value")
        elif entry.get("total_value") is not None:
            out[entry["name"]] = entry["total_value"].get("value")
    return out


def fetch_insights(media_id, token):
    resp = requests.get(
        f"{BASE_URL}/{media_id}/insights",
        params={"metric": ",".join(METRICS), "access_token": token},
    )
    if not resp.ok:
        print(f"Insights fetch failed for media {media_id}: {resp.text}")
        return None
    return _values(resp.json())


def fetch_extra_metric(media_id, metric, token, unavailable):
    resp = requests.get(
        f"{BASE_URL}/{media_id}/insights",
        params={"metric": metric, "access_token": token},
    )
    if not resp.ok:
        unavailable.setdefault(metric, resp.text[:200])
        return {}
    return _values(resp.json())


def fetch_media_fields(media_id, token):
    resp = requests.get(
        f"{BASE_URL}/{media_id}",
        params={
            "fields": "media_type,media_product_type,timestamp,permalink,like_count,comments_count",
            "access_token": token,
        },
    )
    return resp.json() if resp.ok else {}


def fetch_account_snapshot(token, unavailable):
    """Account-level numbers (followers, reach, views, profile views,
    accounts engaged, follower/non-follower split, demographics). Each
    call is independent and failure-tolerant. Demographic breakdowns
    need roughly 100+ followers and are expected to be rejected until
    then -- that's recorded, not an error."""
    snap = {}
    me = requests.get(f"{BASE_URL}/me", params={
        "fields": "followers_count,follows_count,media_count", "access_token": token})
    if me.ok:
        snap.update(me.json())
    day = {"period": "day", "metric_type": "total_value", "access_token": token}
    for metric in ["reach", "views", "profile_views", "accounts_engaged", "total_interactions",
                   "likes", "comments", "shares", "saves", "follows_and_unfollows", "website_clicks"]:
        r = requests.get(f"{BASE_URL}/me/insights", params={**day, "metric": metric})
        if r.ok:
            snap.update(_values(r.json()))
        else:
            unavailable.setdefault(f"account:{metric}", r.text[:200])
    for breakdown_metric, breakdown in [("views", "follow_type"), ("views", "media_product_type"),
                                        ("reach", "follow_type")]:
        r = requests.get(f"{BASE_URL}/me/insights", params={**day, "metric": breakdown_metric, "breakdown": breakdown})
        key = f"{breakdown_metric}_by_{breakdown}"
        if r.ok:
            snap[key] = r.json().get("data", [])
        else:
            unavailable.setdefault(f"account:{key}", r.text[:200])
    for metric in ["follower_demographics", "reached_audience_demographics", "engaged_audience_demographics"]:
        for breakdown in ["country", "age", "gender"]:
            r = requests.get(f"{BASE_URL}/me/insights", params={
                "metric": metric, "period": "lifetime", "metric_type": "total_value",
                "breakdown": breakdown, "access_token": token})
            if r.ok:
                snap[f"{metric}_{breakdown}"] = r.json().get("data", [])
            else:
                unavailable.setdefault(f"account:{metric}_{breakdown}", r.text[:200])
    return snap


def _word_count(item):
    words = 0
    for slide in item.get("slides", []):
        text = slide.get("text") or "\n\n".join(slide.get("items", []))
        words += len(text.split())
    return words


def main():
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        print("Missing IG_ACCESS_TOKEN env var.")
        return 1

    queue = load_queue()
    posted = [item for item in queue if item.get("stage") == "posted" and item.get("ig_media_id")]
    performance = load_performance()
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    unavailable = {}

    # A post deleted on Instagram (e.g. id 19, 2026-09-25) has no live
    # media to fetch -- drop stale performance rows for anything no longer
    # marked posted so old numbers don't masquerade as current.
    posted_ids = {str(i["id"]) for i in posted}
    for stale in [k for k in performance if k not in posted_ids]:
        print(f"Dropping stale performance row for post {stale} (no longer posted).")
        del performance[stale]

    for item in posted:
        post_id = str(item["id"])
        media_id = item["ig_media_id"]
        insights = fetch_insights(media_id, token)
        if insights is None:
            continue
        fields = fetch_media_fields(media_id, token)
        is_reel = fields.get("media_product_type") == "REELS"
        for metric in EXTRA_METRICS_ALL + (EXTRA_METRICS_REEL if is_reel else []):
            insights.update(fetch_extra_metric(media_id, metric, token, unavailable))

        record = performance.get(post_id, {})
        record.update(insights)
        record["bg_variant"] = item.get("bg_variant")
        record["angle"] = item.get("angle")
        record["post_type"] = item.get("post_type")
        record["ig_media_id"] = media_id
        # Context so analysis never needs a queue.json join or a guess:
        record["format"] = fields.get("media_product_type")
        record["media_type"] = fields.get("media_type")
        record["posted_at"] = fields.get("timestamp")
        record["permalink"] = fields.get("permalink")
        record["like_count"] = fields.get("like_count")
        record["comments_count"] = fields.get("comments_count")
        record["words"] = _word_count(item)
        record["cta"] = item.get("cta")
        record["reel"] = item.get("reel")
        snapshot = {"date": today, **{k: v for k, v in insights.items()}}
        history = [h for h in record.get("history", []) if h.get("date") != today]
        record["history"] = (history + [snapshot])[-HISTORY_CAP:]
        performance[post_id] = record
        print(f"Post {post_id}: {insights}")

    with open(PERF_PATH, "w") as f:
        json.dump(performance, f, indent=2)

    account = {}
    if os.path.exists(ACCOUNT_PATH):
        with open(ACCOUNT_PATH) as f:
            account = json.load(f)
    account[today] = fetch_account_snapshot(token, unavailable)
    with open(ACCOUNT_PATH, "w") as f:
        json.dump(account, f, indent=2)

    with open(META_PATH, "w") as f:
        json.dump({"checked": today, "metrics_rejected_by_instagram": unavailable}, f, indent=2)
    if unavailable:
        print("Metrics Instagram rejected (see content_queue/tracking_meta.json):")
        for k, v in unavailable.items():
            print(f"  {k}: {v[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
