"""
ONE-TIME migration (2026-09-17): the very first batch's items 3-9 got
their image links written to a separate "visual-2026-09-16" tab, from
before visual review moved onto the same tab as content review. This
copies those Image Link(s) values across into the corresponding rows
of "content-2026-09-16" (creating the visual columns there if needed,
via the same write_visual_columns() the regular pipeline uses) and then
deletes the now-redundant legacy tab.

Not part of the regular review cycle — run once via workflow_dispatch,
then this script (and the one-off workflow that runs it) can be deleted.
Safe to re-run: skips any post ID that already has an Image Link(s)
value on the content tab.

Usage:
  python migrate_legacy_visual_tab.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import sheets_utils

CONTENT_TAB = "content-2026-09-16"
LEGACY_VISUAL_TAB = "visual-2026-09-16"


def main():
    client = sheets_utils.get_client()
    spreadsheet = sheets_utils.open_spreadsheet(client)

    content_ws = spreadsheet.worksheet(CONTENT_TAB)
    try:
        legacy_ws = spreadsheet.worksheet(LEGACY_VISUAL_TAB)
    except sheets_utils.gspread.WorksheetNotFound:
        print(f"No '{LEGACY_VISUAL_TAB}' tab found — nothing to migrate.")
        return 0

    legacy_records = legacy_ws.get_all_records()
    content_headers = content_ws.row_values(1)
    image_col_already_present = "Image Link(s)" in content_headers
    existing_image_links = {}
    if image_col_already_present:
        col_idx = content_headers.index("Image Link(s)") + 1
        col_values = content_ws.col_values(col_idx)
        content_ids = content_ws.col_values(1)
        for pid, val in zip(content_ids[1:], col_values[1:]):
            existing_image_links[pid] = val

    migrated = 0
    for row in legacy_records:
        post_id = row.get("Post ID")
        image_link = row.get("Image link(s)", "")
        if not post_id or not image_link:
            continue
        if existing_image_links.get(str(post_id)):
            print(f"Post {post_id} already has an image link on '{CONTENT_TAB}' — skipping.")
            continue
        fake_item = {"id": int(post_id)}
        sheets_utils.write_visual_columns(spreadsheet, content_ws, fake_item, [image_link])
        print(f"Migrated post {post_id}'s image link onto '{CONTENT_TAB}'.")
        migrated += 1

    spreadsheet.del_worksheet(legacy_ws)
    print(f"Deleted legacy tab '{LEGACY_VISUAL_TAB}'. Migrated {migrated} post(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
