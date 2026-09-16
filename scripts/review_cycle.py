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
reviewer's comments attached. Applying the fix and resubmitting for
another look happens via resubmit_content_review()/resubmit_visual_review()
below (called directly, not part of the automated cron loop) — these
update the SAME row in the SAME tab the item was already being reviewed
in, per the 2026-09-17 "reiterate on one tab per batch, not a new tab
per revision round" redesign. A new tab only ever gets created for a
genuinely new batch (send_content_review, when items are still at
`drafted`).

Each item remembers which tab it's actively under review in via
`review_tab` — set whenever it enters content_review or visual_review —
so a check step several days into a multi-round revision still finds
the right tab regardless of what today's date happens to be by then.

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


def _notify(subject, body):
    """Best-effort notification — never let an email hiccup crash the
    script before stage transitions get saved. The sheet is always the
    source of truth; the email is just a convenience ping. A failure
    here means the user won't get pinged for this run, but nothing about
    the actual queue state is lost, and the next run's state is still
    correct (unlike a mid-function crash, which used to skip _save()
    entirely and cause the next run to redo work — see docs/build-plan.md
    2026-09-17)."""
    try:
        gmail_utils.send_notification_email(subject, body)
    except Exception as e:
        print(f"WARNING: notification email failed ({e!r}) — continuing anyway, "
              "state is already saved.")


def _group_by_tab(items):
    groups = {}
    for item in items:
        groups.setdefault(item["review_tab"], []).append(item)
    return groups


def check_content_review(queue, spreadsheet):
    outstanding = [i for i in queue if i["stage"] == "content_review"]
    if not outstanding:
        return False

    any_processed = False
    for tab_title, items in _group_by_tab(outstanding).items():
        try:
            ws = spreadsheet.worksheet(tab_title)
        except sheets_utils.gspread.WorksheetNotFound:
            continue  # tab not written yet this run (shouldn't normally happen)

        rows = sheets_utils.read_tab_rows(ws)
        if not sheets_utils.is_tab_fully_reviewed(rows):
            continue

        by_id = {i["id"]: i for i in items}
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
              f"{len(items) - len(dropped_ids)} item(s) updated, {len(dropped_ids)} dropped.")
        any_processed = True
    return any_processed


def send_visual_review(queue, spreadsheet, repo):
    """Only renders/sends items whose whole batch has FINISHED content
    review — per user request (2026-09-17): content gen -> content
    review (+ revision rounds) -> ALL content approved -> visual gen ->
    visual review (+ revision rounds) -> ALL visuals approved. An item
    stuck in content_needs_change blocks its batch-mates (same
    review_tab) from moving to rendering, even if they're individually
    already content_approved — don't spend render effort until the
    copy for the whole batch is locked."""
    approved = [i for i in queue if i["stage"] == "content_approved"]
    if not approved:
        return False

    still_reviewing_tabs = {
        i["review_tab"] for i in queue if i["stage"] in ("content_review", "content_needs_change")
    }
    ready = [i for i in approved if i["review_tab"] not in still_reviewing_tabs]
    held_back = len(approved) - len(ready)
    if held_back:
        print(f"{held_back} content_approved item(s) held back — their batch still has "
              f"content review in progress.")
    if not ready:
        return False
    approved = ready

    image_urls_by_id = {}
    for item in approved:
        rp.render_item(item)
        item["stage"] = "rendered"
        image_urls_by_id[item["id"]] = image_urls_for_item(item, repo)

    tab_title = f"visual-{_today()}"
    sheets_utils.write_visual_review_tab(spreadsheet, tab_title, approved, image_urls_by_id)
    for item in approved:
        item["stage"] = "visual_review"
        item["review_tab"] = tab_title
    print(f"Rendered and wrote visual review tab '{tab_title}' for {len(approved)} item(s).")
    _notify(
        subject=f"Ooops Visual Review — {_today()}",
        body=(
            f"{len(approved)} post(s) rendered and ready for visual review.\n\n"
            f"Open the sheet and go to the '{tab_title}' tab: {_sheet_url()}\n\n"
            "Fill in Status (Approved / Need Change / Rejected) and My Comments for each row."
        ),
    )
    return True


def check_visual_review(queue, spreadsheet):
    outstanding = [i for i in queue if i["stage"] == "visual_review"]
    if not outstanding:
        return False

    any_processed = False
    for tab_title, items in _group_by_tab(outstanding).items():
        try:
            ws = spreadsheet.worksheet(tab_title)
        except sheets_utils.gspread.WorksheetNotFound:
            continue

        rows = sheets_utils.read_tab_rows(ws)
        if not sheets_utils.is_tab_fully_reviewed(rows):
            continue

        by_id = {i["id"]: i for i in items}
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
              f"{len(items) - len(dropped_ids)} item(s) updated, {len(dropped_ids)} dropped.")
        any_processed = True
    return any_processed


def resubmit_content_review(queue, spreadsheet):
    """Items at content_needs_change that Claude has already revised —
    signaled by reviewer_comments having been cleared back to "" once
    the comment is addressed (still non-empty = still waiting on a fix,
    leave alone). Pushes the revised content into the SAME row of the
    SAME tab the item was already under review in, clears that row's
    Status/Comments, and puts the item back in the review queue."""
    ready = [i for i in queue if i["stage"] == "content_needs_change" and not i["reviewer_comments"]]
    if not ready:
        return False
    for item in ready:
        ws = spreadsheet.worksheet(item["review_tab"])
        sheets_utils.update_content_row(ws, item)
        item["stage"] = "content_review"
    print(f"Resubmitted {len(ready)} revised item(s) for content review.")
    return True


def resubmit_visual_review(queue, spreadsheet, repo):
    ready = [i for i in queue if i["stage"] == "visual_needs_change" and not i["reviewer_comments"]]
    if not ready:
        return False
    for item in ready:
        rp.render_item(item)  # re-render with whatever changed
        urls = image_urls_for_item(item, repo)
        ws = spreadsheet.worksheet(item["review_tab"])
        sheets_utils.update_visual_row(ws, item, urls)
        item["stage"] = "visual_review"
    print(f"Re-rendered and resubmitted {len(ready)} revised item(s) for visual review.")
    return True


def send_content_review(queue, spreadsheet):
    drafted = [i for i in queue if i["stage"] == "drafted"]
    if not drafted:
        return False
    tab_title = f"content-{_today()}"
    sheets_utils.write_content_review_tab(spreadsheet, tab_title, drafted)
    for item in drafted:
        item["stage"] = "content_review"
        item["review_tab"] = tab_title
    print(f"Wrote content review tab '{tab_title}' for {len(drafted)} item(s).")
    _notify(
        subject=f"Ooops Content Review — {_today()}",
        body=(
            f"{len(drafted)} post(s) ready for content review.\n\n"
            f"Open the sheet and go to the '{tab_title}' tab: {_sheet_url()}\n\n"
            "Fill in Status (Approved / Need Change / Rejected) and My Comments for each row."
        ),
    )
    return True


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    client = sheets_utils.get_client()
    spreadsheet = sheets_utils.open_spreadsheet(client)

    queue = _load()
    any_step_ran = False

    # Save after each step rather than once at the end — a crash partway
    # through (e.g. render_post failing on step 2) then never loses an
    # earlier step's already-completed work on the next run. This is the
    # fix for the 2026-09-17 incident where a step failure skipped the
    # single end-of-run save entirely and caused a later run to redo work.
    for step, args in [
        (resubmit_content_review, (queue, spreadsheet)),
        (check_content_review, (queue, spreadsheet)),
        (send_visual_review, (queue, spreadsheet, repo)),
        (resubmit_visual_review, (queue, spreadsheet, repo)),
        (check_visual_review, (queue, spreadsheet)),
        (send_content_review, (queue, spreadsheet)),
    ]:
        if step(*args):
            any_step_ran = True
            _save(queue)

    if not any_step_ran:
        print("Nothing to do this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
