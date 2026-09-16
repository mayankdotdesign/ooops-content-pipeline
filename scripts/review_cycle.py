"""
Phase 6: two-cycle email-driven approval. Advances whatever's ready
each time it's run — safe to call repeatedly (e.g. on a recurring
GitHub Actions cron). Four steps, each a no-op if there's nothing in
the relevant stage, run in this order so a same-run approval flows
straight into the next step (matching the plan's "same day, cycle 2
right after cycle 1"):

  1. content_review   -> check for reply             -> content_approved
                                                       | content_needs_change
                                                       | (dropped if Rejected)
  2. content_approved -> render + send visual-review  -> visual_review
     (catches items approved in step 1 during THIS SAME run)
  3. visual_review    -> check for reply              -> queued
                                                       | visual_needs_change
                                                       | (dropped if Rejected)
  4. drafted          -> send content-review email    -> content_review
     (starts the cycle for a fresh Phase 5 batch; ordered last since it
     doesn't interact with the same-run approval chain above)

"Need Change" does NOT auto-regenerate content or images here — that
needs actual judgment (rewriting a caption, fixing a slide), which is
a Claude Code job, not a deterministic script's. This script only sets
stage back to content_needs_change/visual_needs_change with the
reviewer's comments attached; a human (via Claude Code) applies them
and manually advances the stage back to content_review/rendered to
re-trigger the email cycle.

Usage:
  python review_cycle.py
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import gmail_utils
import render_post as rp
import review_xlsx
from post_to_instagram import image_urls_for_item

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")
REVIEW_DIR = os.path.join(os.path.dirname(__file__), "..", "content_queue", "review")

CONTENT_SUBJECT = "Ooops Content Review"
VISUAL_SUBJECT = "Ooops Visual Review"


def _today():
    return datetime.date.today().isoformat()


def _load():
    with open(QUEUE_PATH) as f:
        return json.load(f)


def _save(queue):
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)


def send_content_review(queue):
    drafted = [i for i in queue if i["stage"] == "drafted"]
    if not drafted:
        return False
    path = review_xlsx.build_content_review_sheet(
        drafted, os.path.join(REVIEW_DIR, f"content-review-{_today()}.xlsx")
    )
    gmail_utils.send_review_email(
        subject=f"{CONTENT_SUBJECT} — {_today()}",
        body=(
            f"{len(drafted)} post(s) ready for content review. Fill in Status "
            "(Approved / Need Change / Rejected) and My Comments, then reply "
            "to this email with the edited file attached."
        ),
        attachment_path=path,
    )
    for item in drafted:
        item["stage"] = "content_review"
    print(f"Sent content review for {len(drafted)} item(s) -> {path}")
    return True


def check_content_review_reply(queue):
    outstanding = [i for i in queue if i["stage"] == "content_review"]
    if not outstanding:
        return False
    attachment = gmail_utils.find_reply_with_attachment(CONTENT_SUBJECT, REVIEW_DIR)
    if not attachment:
        return False

    by_id = {i["id"]: i for i in outstanding}
    dropped_ids = set()
    for row in review_xlsx.read_review_sheet(attachment):
        item = by_id.get(row["post_id"])
        if item is None:
            continue
        if row["status"] == "Approved":
            item["stage"] = "content_approved"
        elif row["status"] == "Need Change":
            item["stage"] = "content_needs_change"
            item["reviewer_comments"] = row["comments"]
        elif row["status"] == "Rejected":
            dropped_ids.add(item["id"])

    if dropped_ids:
        queue[:] = [i for i in queue if i["id"] not in dropped_ids]
    print(f"Processed content-review reply: {len(outstanding) - len(dropped_ids)} item(s) updated, "
          f"{len(dropped_ids)} dropped.")
    return True


def send_visual_review(queue, repo):
    approved = [i for i in queue if i["stage"] == "content_approved"]
    if not approved:
        return False

    image_urls_by_id = {}
    for item in approved:
        rp.render_item(item)
        item["stage"] = "rendered"
        image_urls_by_id[item["id"]] = image_urls_for_item(item, repo)

    path = review_xlsx.build_visual_review_sheet(
        approved, image_urls_by_id, os.path.join(REVIEW_DIR, f"visual-review-{_today()}.xlsx")
    )
    gmail_utils.send_review_email(
        subject=f"{VISUAL_SUBJECT} — {_today()}",
        body=(
            f"{len(approved)} post(s) rendered and ready for visual review. Fill in Status "
            "(Approved / Need Change / Rejected) and My Comments, then reply "
            "to this email with the edited file attached."
        ),
        attachment_path=path,
    )
    for item in approved:
        item["stage"] = "visual_review"
    print(f"Rendered and sent visual review for {len(approved)} item(s) -> {path}")
    return True


def check_visual_review_reply(queue):
    outstanding = [i for i in queue if i["stage"] == "visual_review"]
    if not outstanding:
        return False
    attachment = gmail_utils.find_reply_with_attachment(VISUAL_SUBJECT, REVIEW_DIR)
    if not attachment:
        return False

    by_id = {i["id"]: i for i in outstanding}
    dropped_ids = set()
    for row in review_xlsx.read_review_sheet(attachment):
        item = by_id.get(row["post_id"])
        if item is None:
            continue
        if row["status"] == "Approved":
            item["stage"] = "queued"
        elif row["status"] == "Need Change":
            item["stage"] = "visual_needs_change"
            item["reviewer_comments"] = row["comments"]
        elif row["status"] == "Rejected":
            dropped_ids.add(item["id"])

    if dropped_ids:
        queue[:] = [i for i in queue if i["id"] not in dropped_ids]
    print(f"Processed visual-review reply: {len(outstanding) - len(dropped_ids)} item(s) updated, "
          f"{len(dropped_ids)} dropped.")
    return True


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    queue = _load()
    changed = False

    changed |= check_content_review_reply(queue)
    changed |= send_visual_review(queue, repo)
    changed |= check_visual_review_reply(queue)
    changed |= send_content_review(queue)

    if changed:
        _save(queue)
    else:
        print("Nothing to do this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
