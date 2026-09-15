"""
Posts a rendered image to Instagram via the free Graph API
(Content Publishing endpoint). No paid tool involved.

Requires env vars (set as GitHub Actions secrets — see README):
  IG_ACCESS_TOKEN   - long-lived token for your Business/Creator account
  IG_ACCOUNT_ID     - your Instagram Business Account ID (not username)
  IMAGE_PUBLIC_URL  - Graph API requires a publicly reachable image URL,
                       not a local file. See README for the two ways
                       to satisfy this for free (GitHub raw URL, or
                       a free static host).

Usage:
  python post_to_instagram.py <queue_id> <caption>
"""

import os
import sys
import json
import time
import requests

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
GRAPH_VERSION = "v21.0"
# IMPORTANT: tokens starting with "IGAA" (Instagram API with Instagram Login)
# only work against graph.instagram.com — NOT graph.facebook.com.
# If you ever switch to a Facebook-Login-based token (starts differently),
# change this back to https://graph.facebook.com/{GRAPH_VERSION}
BASE_URL = f"https://graph.instagram.com/{GRAPH_VERSION}"

def post_image(image_url, caption, account_id, token):
    # Step 1: create a media container
    container_resp = requests.post(
        f"{BASE_URL}/{account_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        },
    )
    container_resp.raise_for_status()
    creation_id = container_resp.json()["id"]

    # Step 2: publish the container
    time.sleep(2)  # brief buffer while Meta processes the container
    publish_resp = requests.post(
        f"{BASE_URL}/{account_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
    )
    publish_resp.raise_for_status()
    return publish_resp.json()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python post_to_instagram.py <queue_id> <caption>")
        sys.exit(1)

    queue_id, caption = sys.argv[1], sys.argv[2]

    token = os.environ.get("IG_ACCESS_TOKEN")
    account_id = os.environ.get("IG_ACCOUNT_ID")
    image_url = os.environ.get("IMAGE_PUBLIC_URL")

    if not all([token, account_id, image_url]):
        print("Missing IG_ACCESS_TOKEN, IG_ACCOUNT_ID, or IMAGE_PUBLIC_URL env vars.")
        sys.exit(1)

    result = post_image(image_url, caption, account_id, token)
    print("Posted:", result)

    with open(QUEUE_PATH) as f:
        queue = json.load(f)
    for item in queue:
        if item["id"] == int(queue_id):
            item["status"] = "posted"
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)
