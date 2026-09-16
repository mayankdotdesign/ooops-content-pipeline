"""
Posts a rendered queue item to Instagram via the free Graph API,
building the caption from the queue item itself (hook image text
implied, caption + CTA + hashtags pulled from queue.json) instead
of a hardcoded placeholder.

Single-slide items post as a normal image. Multi-slide items
(content_queue/rendered/<id>/1.png, 2.png, ...) post as a carousel:
each image becomes a child media container (is_carousel_item=true),
then a parent container (media_type=CAROUSEL) references the children,
then that gets published — three API round-trips instead of one, this
is just how Instagram's carousel API works, not extra complexity added
here.

Usage:
  python post_to_instagram.py <queue_id>
"""

import glob
import os
import sys
import json
import time
import requests

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
RENDERED_DIR = os.path.join(os.path.dirname(__file__), "..", "content_queue", "rendered")
GRAPH_VERSION = "v21.0"
BASE_URL = f"https://graph.instagram.com/{GRAPH_VERSION}"

def build_caption(item):
    """Hook (image already shows it) -> caption -> CTA -> hashtags.
    Instagram caps hashtags at 5 per post (changed Dec 2025, down from 30) —
    exceeding this gets the request rejected, so we fail loudly here instead
    of finding out from a cryptic API error."""
    hashtags = item.get("hashtags", [])
    if len(hashtags) > 5:
        raise ValueError(
            f"Queue item {item['id']} has {len(hashtags)} hashtags — "
            f"Instagram's limit is 5. Trim before posting."
        )
    parts = [item["caption"]]
    if item.get("cta"):
        parts.append(item["cta"])
    caption = "\n\n".join(parts)
    if hashtags:
        caption += "\n\n" + " ".join(hashtags)
    return caption


def image_urls_for_item(item, repo, branch="main"):
    """Matches render_post.py's output convention: single-slide items at
    content_queue/rendered/<id>.png, carousels at .../<id>/1.png, 2.png, ..."""
    raw_base = f"https://raw.githubusercontent.com/{repo}/{branch}"
    item_dir = os.path.join(RENDERED_DIR, str(item["id"]))
    if os.path.isdir(item_dir):
        n = len(glob.glob(os.path.join(item_dir, "*.png")))
        return [f"{raw_base}/content_queue/rendered/{item['id']}/{i}.png" for i in range(1, n + 1)]
    return [f"{raw_base}/content_queue/rendered/{item['id']}.png"]


def _create_container(account_id, token, **fields):
    resp = requests.post(f"{BASE_URL}/{account_id}/media", data={**fields, "access_token": token})
    if not resp.ok:
        print("Container creation failed. Response body:")
        print(resp.text)
    resp.raise_for_status()
    return resp.json()["id"]


def post_image(image_url, caption, account_id, token):
    creation_id = _create_container(account_id, token, image_url=image_url, caption=caption)
    time.sleep(2)
    publish_resp = requests.post(
        f"{BASE_URL}/{account_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
    )
    if not publish_resp.ok:
        print("Publish failed. Response body:")
        print(publish_resp.text)
    publish_resp.raise_for_status()
    return publish_resp.json()


def post_carousel(image_urls, caption, account_id, token):
    child_ids = [
        _create_container(account_id, token, image_url=url, is_carousel_item="true")
        for url in image_urls
    ]
    time.sleep(2)
    parent_id = _create_container(
        account_id, token, media_type="CAROUSEL", children=",".join(child_ids), caption=caption
    )
    time.sleep(2)
    publish_resp = requests.post(
        f"{BASE_URL}/{account_id}/media_publish",
        data={"creation_id": parent_id, "access_token": token},
    )
    if not publish_resp.ok:
        print("Publish failed. Response body:")
        print(publish_resp.text)
    publish_resp.raise_for_status()
    return publish_resp.json()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python post_to_instagram.py <queue_id>")
        sys.exit(1)

    queue_id = sys.argv[1]
    token = os.environ.get("IG_ACCESS_TOKEN")
    account_id = os.environ.get("IG_ACCOUNT_ID")
    repo = os.environ.get("GITHUB_REPOSITORY")

    if not all([token, account_id, repo]):
        print("Missing IG_ACCESS_TOKEN, IG_ACCOUNT_ID, or GITHUB_REPOSITORY env vars.")
        sys.exit(1)

    with open(QUEUE_PATH) as f:
        queue = json.load(f)
    item = next((i for i in queue if i["id"] == int(queue_id)), None)
    if not item:
        print(f"Queue id {queue_id} not found.")
        sys.exit(1)

    caption = build_caption(item)
    image_urls = image_urls_for_item(item, repo)
    if len(image_urls) == 1:
        result = post_image(image_urls[0], caption, account_id, token)
    else:
        result = post_carousel(image_urls, caption, account_id, token)
    print("Posted:", result)

    item["stage"] = "posted"
    item["ig_media_id"] = result["id"]  # needed by scripts/track_engagement.py (Phase 3)
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)
