"""
Posts a rendered image to Instagram via the free Graph API,
building the caption from the queue item itself (hook image text
implied, caption + CTA + hashtags pulled from queue.json) instead
of a hardcoded placeholder.

Usage:
  python post_to_instagram.py <queue_id>
"""

import os
import sys
import json
import time
import requests

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
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

def post_image(image_url, caption, account_id, token):
    container_resp = requests.post(
        f"{BASE_URL}/{account_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
    )
    if not container_resp.ok:
        print("Container creation failed. Response body:")
        print(container_resp.text)
    container_resp.raise_for_status()
    creation_id = container_resp.json()["id"]

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python post_to_instagram.py <queue_id>")
        sys.exit(1)

    queue_id = sys.argv[1]
    token = os.environ.get("IG_ACCESS_TOKEN")
    account_id = os.environ.get("IG_ACCOUNT_ID")
    image_url = os.environ.get("IMAGE_PUBLIC_URL")

    if not all([token, account_id, image_url]):
        print("Missing IG_ACCESS_TOKEN, IG_ACCOUNT_ID, or IMAGE_PUBLIC_URL env vars.")
        sys.exit(1)

    with open(QUEUE_PATH) as f:
        queue = json.load(f)
    item = next((i for i in queue if i["id"] == int(queue_id)), None)
    if not item:
        print(f"Queue id {queue_id} not found.")
        sys.exit(1)

    caption = build_caption(item)
    result = post_image(image_url, caption, account_id, token)
    print("Posted:", result)

    item["status"] = "posted"
    item["ig_media_id"] = result["id"]  # needed by scripts/track_engagement.py (Phase 3)
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)
