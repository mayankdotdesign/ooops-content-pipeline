"""
Phase 6: two-cycle approval, Google Sheets-backed. One persistent
spreadsheet (GOOGLE_SHEET_ID), one tab per weekly batch (named
`content-{date}` — the name stuck from before visual review moved onto
the same tab, kept for continuity with tabs already in flight) that
carries the batch through its ENTIRE lifecycle: content columns and
visual columns live side by side on the same rows
(scripts/sheets_utils.py's HEADERS). No downloading/re-uploading a
file, no email attachments — reviewed directly in Sheets.

Advances whatever's ready each time it's run — safe to call repeatedly
(e.g. on a recurring GitHub Actions cron). Steps run in this order so a
same-run approval flows straight into the next step:

  1. content_review   -> Content Status filled in for the whole batch?
                          -> content_approved | content_needs_change
                          | (dropped if Rejected)
  2. content_approved -> ALL of this batch's content approved?
                          -> render, fill in Image Link(s) -> visual_review
     (catches items approved in step 1 during THIS SAME run; per user
     request, 2026-09-17, visual work only starts once the WHOLE batch's
     copy is locked, not item-by-item)
  3. visual_review    -> Visual Status filled in for the whole batch?
                          -> queued | visual_needs_change
                          | (dropped if Rejected)
  4. drafted          -> write a new batch's content rows -> content_review
     (starts the cycle for a fresh Phase 5 batch; ordered last since it
     doesn't interact with the same-run approval chain above)

"Need Change" does NOT auto-regenerate content or images — that needs
actual judgment (rewriting a caption, fixing a slide), which is a
Claude Code job, not a deterministic script's. This script only sets
stage to content_needs_change/visual_needs_change with the reviewer's
comments attached. Applying the fix and resubmitting happens via
resubmit_content_review()/resubmit_visual_review() below — these update
the SAME row of the SAME tab the item was already under review in
(never a new tab for a revision round — only a genuinely new weekly
batch gets a new tab).

Each item remembers its tab via `review_tab`, set once when it first
enters content_review and never reassigned (content and visual both
live there now) — so a check step, days into a multi-round revision,
still finds the right tab regardless of what today's date is by then.

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
    source of truth; the email is just a convenience ping."""
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
    """Processes each outstanding item independently, based on whatever
    its OWN row currently says — NOT gated on every row in the tab
    being filled in. That all-or-nothing gate used to deadlock: e.g.
    post 2 already marked Approved would sit blocked forever just
    because post 1's row was blank pending a revision. Items resolve
    at their own pace; send_visual_review is what waits for a whole
    batch to finish before rendering (see its docstring)."""
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
        by_id = {i["id"]: i for i in items}
        dropped_ids = set()
        processed_count = 0
        for row in rows:
            item = by_id.get(row["post_id"])
            if item is None or row["content_status"] not in sheets_utils.STATUS_OPTIONS:
                continue
            processed_count += 1
            if row["content_status"] == "Approved":
                item["stage"] = "content_approved"
            elif row["content_status"] == "Need Change":
                item["stage"] = "content_needs_change"
                item["reviewer_comments"] = row["content_comments"]
            elif row["content_status"] == "Rejected":
                dropped_ids.add(item["id"])

        if dropped_ids:
            queue[:] = [i for i in queue if i["id"] not in dropped_ids]
        if processed_count:
            print(f"Processed content review in tab '{tab_title}': "
                  f"{processed_count - len(dropped_ids)} item(s) updated, {len(dropped_ids)} dropped.")
            any_processed = True
    return any_processed


def send_visual_review(queue, spreadsheet, repo):
    """Only renders/sends items whose whole batch has FINISHED content
    review — an item stuck in content_needs_change blocks its
    batch-mates (same review_tab) from moving to rendering, even if
    they're individually already content_approved."""
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

    by_tab = _group_by_tab(ready)
    for tab_title, items in by_tab.items():
        ws = spreadsheet.worksheet(tab_title)
        for item in items:
            rp.render_item(item)
            item["stage"] = "rendered"
            urls = image_urls_for_item(item, repo)
            sheets_utils.write_visual_columns(spreadsheet, ws, item, urls)
            item["stage"] = "visual_review"
        print(f"Rendered and filled in Image Link(s) for {len(items)} item(s) in tab '{tab_title}'.")
        _notify(
            subject=f"Ooops Visual Review — {_today()}",
            body=(
                f"{len(items)} post(s) rendered and ready for visual review.\n\n"
                f"Open the sheet, tab '{tab_title}': {_sheet_url()}\n\n"
                "Fill in Visual Status (Approved / Need Change / Rejected) and "
                "Visual Comments for each row."
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
        by_id = {i["id"]: i for i in items}
        dropped_ids = set()
        processed_count = 0
        for row in rows:
            item = by_id.get(row["post_id"])
            if item is None or row["visual_status"] not in sheets_utils.STATUS_OPTIONS:
                continue
            processed_count += 1
            if row["visual_status"] == "Approved":
                item["stage"] = "queued"
            elif row["visual_status"] == "Need Change":
                item["stage"] = "visual_needs_change"
                item["reviewer_comments"] = row["visual_comments"]
            elif row["visual_status"] == "Rejected":
                dropped_ids.add(item["id"])

        if dropped_ids:
            queue[:] = [i for i in queue if i["id"] not in dropped_ids]
        if processed_count:
            print(f"Processed visual review in tab '{tab_title}': "
                  f"{processed_count - len(dropped_ids)} item(s) updated, {len(dropped_ids)} dropped.")
            any_processed = True
    return any_processed


def resubmit_content_review(queue, spreadsheet):
    """Items at content_needs_change that Claude has already revised —
    signaled by reviewer_comments having been cleared back to "" once
    the comment is addressed (still non-empty = still waiting on a fix,
    leave alone). Pushes the revision into the SAME row of the SAME
    tab and clears that row's Content Status/Comments for re-review."""
    ready = [i for i in queue if i["stage"] == "content_needs_change" and not i["reviewer_comments"]]
    if not ready:
        return False
    tabs = set()
    for item in ready:
        ws = spreadsheet.worksheet(item["review_tab"])
        sheets_utils.update_content_row(ws, item)
        item["stage"] = "content_review"
        tabs.add(item["review_tab"])
    print(f"Resubmitted {len(ready)} revised item(s) for content review.")
    _notify(
        subject=f"Ooops Content Revision Resubmitted — {_today()}",
        body=(
            f"{len(ready)} revised post(s) pushed back into content review.\n\n"
            f"Tab(s): {', '.join(sorted(tabs))}\n"
            f"Open the sheet: {_sheet_url()}\n\n"
            "Fill in Content Status (Approved / Need Change / Rejected) again for each revised row."
        ),
    )
    return True


def resubmit_visual_review(queue, spreadsheet, repo):
    ready = [i for i in queue if i["stage"] == "visual_needs_change" and not i["reviewer_comments"]]
    if not ready:
        return False
    tabs = set()
    for item in ready:
        rp.render_item(item)  # re-render with whatever changed
        urls = image_urls_for_item(item, repo)
        ws = spreadsheet.worksheet(item["review_tab"])
        sheets_utils.write_visual_columns(spreadsheet, ws, item, urls)
        item["stage"] = "visual_review"
        tabs.add(item["review_tab"])
    print(f"Re-rendered and resubmitted {len(ready)} revised item(s) for visual review.")
    _notify(
        subject=f"Ooops Visual Revision Resubmitted — {_today()}",
        body=(
            f"{len(ready)} revised post(s) re-rendered with updated Image Link(s).\n\n"
            f"Tab(s): {', '.join(sorted(tabs))}\n"
            f"Open the sheet: {_sheet_url()}\n\n"
            "Fill in Visual Status (Approved / Need Change / Rejected) again for each revised row."
        ),
    )
    return True


def send_content_review(queue, spreadsheet):
    drafted = [i for i in queue if i["stage"] == "drafted"]
    if not drafted:
        return False
    tab_title = f"content-{_today()}"
    sheets_utils.write_content_rows(spreadsheet, tab_title, drafted)
    for item in drafted:
        item["stage"] = "content_review"
        item["review_tab"] = tab_title
    print(f"Wrote content review rows in tab '{tab_title}' for {len(drafted)} item(s).")
    _notify(
        subject=f"Ooops Content Review — {_today()}",
        body=(
            f"{len(drafted)} post(s) ready for content review.\n\n"
            f"Open the sheet and go to the '{tab_title}' tab: {_sheet_url()}\n\n"
            "Fill in Content Status (Approved / Need Change / Rejected) and "
            "Content Comments for each row."
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
    # through then never loses an earlier step's already-completed work
    # on the next run.
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
