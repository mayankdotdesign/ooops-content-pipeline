"""
Posts a rendered image to Instagram via the free Graph API
(Content Publishing endpoint). No paid tool involved.
"""

import os
import sys
import json
import time
import requests

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
GRAPH_VERSION = "v21.0"
BASE_URL = f"https://graph.instagram.com/{GRAPH_VERSION}"

def post_image(image_url, caption, account_id, token):
    container_resp = requests.post(
        f"{BASE_URL}/{account_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        },
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
