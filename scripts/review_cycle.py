"""
Phase 6: two-cycle approval, Google Sheets-backed (2026-09-17 redesign
— originally email/xlsx-attachment round-trip, replaced before the
first real send per user request: one persistent spreadsheet
(GOOGLE_SHEET_ID), a new tab per cycle named by date, edited directly
in Sheets — no downloading/re-uploading a file each time).

Advances whatever's ready each time it's run — safe to call repeatedly
(e.g. on a recurring GitHub Actions cron). Four steps, each a no-op if
there's nothing to do, run in this order so a same-run approval flows
straight into the next step (matching "same day, cycle 2 right after
cycle 1"):

  1. content_review   -> tab fully filled in?         -> content_approved
                                                        | content_needs_change
                                                        | (dropped if Rejected)
  2. content_approved -> render + write visual tab      -> visual_review
     (catches items approved in step 1 during THIS SAME run)
  3. visual_review    -> tab fully filled in?           -> queued
                                                        | visual_needs_change
                                                        | (dropped if Rejected)
  4. drafted          -> write content-review tab       -> content_review
     (starts the cycle for a fresh Phase 5 batch; ordered last since it
     doesn't interact with the same-run approval chain above)

A tab counts as "fully filled in" once every row has a non-blank
Status — checked by re-reading the live sheet, not by polling email.

"Need Change" does NOT auto-regenerate content or images — that needs
actual judgment (rewriting a caption, fixing a slide), which is a
Claude Code job, not a deterministic script's. This script only sets
stage back to content_needs_change/visual_needs_change with the
reviewer's comments attached; a human (via Claude Code) applies them
and manually advances the stage back to content_review/rendered to
re-enter the cycle (which writes a NEW tab, since get_or_create_worksheet
won't overwrite an existing one — the old tab stays as a record).

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
import sheets_utils
from post_to_instagram import image_urls_for_item

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "content_queue", "queue.json")


def _today():
    return datetime.date.today().isoformat()


def _load():
    with open(QUEUE_PATH) as f:
        return json.load(f)


def _save(queue):
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)


def _sheet_url():
    return f"https://docs.google.com/spreadsheets/d/{os.environ['GOOGLE_SHEET_ID']}/edit"


def check_content_review(queue, spreadsheet):
    outstanding = [i for i in queue if i["stage"] == "content_review"]
    if not outstanding:
        return False
    tab_title = f"content-{_today()}"
    try:
        ws = spreadsheet.worksheet(tab_title)
    except sheets_utils.gspread.WorksheetNotFound:
        return False  # tab not written yet this run (shouldn't normally happen)

    rows = sheets_utils.read_tab_rows(ws)
    if not sheets_utils.is_tab_fully_reviewed(rows):
        return False

    by_id = {i["id"]: i for i in outstanding}
    dropped_ids = set()
    for row in rows:
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
    print(f"Processed content-review tab '{tab_title}': "
          f"{len(outstanding) - len(dropped_ids)} item(s) updated, {len(dropped_ids)} dropped.")
    return True


def send_visual_review(queue, spreadsheet, repo):
    approved = [i for i in queue if i["stage"] == "content_approved"]
    if not approved:
        return False

    image_urls_by_id = {}
    for item in approved:
        rp.render_item(item)
        item["stage"] = "rendered"
        image_urls_by_id[item["id"]] = image_urls_for_item(item, repo)

    tab_title = f"visual-{_today()}"
    sheets_utils.write_visual_review_tab(spreadsheet, tab_title, approved, image_urls_by_id)
    gmail_utils.send_notification_email(
        subject=f"Ooops Visual Review — {_today()}",
        body=(
            f"{len(approved)} post(s) rendered and ready for visual review.\n\n"
            f"Open the sheet and go to the '{tab_title}' tab: {_sheet_url()}\n\n"
            "Fill in Status (Approved / Need Change / Rejected) and My Comments for each row."
        ),
    )
    for item in approved:
        item["stage"] = "visual_review"
    print(f"Rendered and wrote visual review tab '{tab_title}' for {len(approved)} item(s).")
    return True


def check_visual_review(queue, spreadsheet):
    outstanding = [i for i in queue if i["stage"] == "visual_review"]
    if not outstanding:
        return False
    tab_title = f"visual-{_today()}"
    try:
        ws = spreadsheet.worksheet(tab_title)
    except sheets_utils.gspread.WorksheetNotFound:
        return False

    rows = sheets_utils.read_tab_rows(ws)
    if not sheets_utils.is_tab_fully_reviewed(rows):
        return False

    by_id = {i["id"]: i for i in outstanding}
    dropped_ids = set()
    for row in rows:
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
    print(f"Processed visual-review tab '{tab_title}': "
          f"{len(outstanding) - len(dropped_ids)} item(s) updated, {len(dropped_ids)} dropped.")
    return True


def send_content_review(queue, spreadsheet):
    drafted = [i for i in queue if i["stage"] == "drafted"]
    if not drafted:
        return False
    tab_title = f"content-{_today()}"
    sheets_utils.write_content_review_tab(spreadsheet, tab_title, drafted)
    gmail_utils.send_notification_email(
        subject=f"Ooops Content Review — {_today()}",
        body=(
            f"{len(drafted)} post(s) ready for content review.\n\n"
            f"Open the sheet and go to the '{tab_title}' tab: {_sheet_url()}\n\n"
            "Fill in Status (Approved / Need Change / Rejected) and My Comments for each row."
        ),
    )
    for item in drafted:
        item["stage"] = "content_review"
    print(f"Wrote content review tab '{tab_title}' for {len(drafted)} item(s).")
    return True


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    client = sheets_utils.get_client()
    spreadsheet = sheets_utils.open_spreadsheet(client)

    queue = _load()
    changed = False

    changed |= check_content_review(queue, spreadsheet)
    changed |= send_visual_review(queue, spreadsheet, repo)
    changed |= check_visual_review(queue, spreadsheet)
    changed |= send_content_review(queue, spreadsheet)

    if changed:
        _save(queue)
    else:
        print("Nothing to do this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
