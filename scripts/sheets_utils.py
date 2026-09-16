"""
Google Sheets integration for Phase 6. One persistent spreadsheet, one
tab per weekly batch (named by date) that carries a batch through its
ENTIRE review lifecycle — content columns AND visual columns live side
by side on the same rows (2026-09-17 redesign: originally visual review
got its own separate tab, changed after the user asked for everything
on one sheet). A tab is created once, when its batch starts content
review, with all 11 columns from the start; the visual columns just sit
blank until that batch's content is fully approved and rendering fills
them in.

Auth: a Google Cloud service account, JSON key pasted into the
GOOGLE_SERVICE_ACCOUNT_JSON secret (the whole file content, not a
path). The spreadsheet itself is identified by GOOGLE_SHEET_ID (a repo
variable, not a secret — it's just the ID from the sheet's URL, not
sensitive) and must already be shared with the service account's
`client_email` as Editor — the service account can't see a sheet that
hasn't been explicitly shared with it, no matter what permissions it
has elsewhere.

Usage: imported by scripts/review_cycle.py, not run directly.
"""

import json
import os
import time

import gspread
from google.oauth2.service_account import Credentials

STATUS_OPTIONS = ["Approved", "Need Change", "Rejected"]

_RETRYABLE_STATUSES = {429, 500, 502, 503}


def _with_retry(fn, *args, retries=5, base_delay=2, **kwargs):
    """Google Sheets enforces a per-minute-per-user API quota. A single
    item touches the sheet 3-5 times (find its row, read headers, write
    values, plus the hyperlink formatting call); a run resubmitting a
    whole batch at once (2026-09-17: 13 items in one run) can burn
    through that quota in a few seconds and get a 429 partway through,
    crashing the run and losing every item still queued behind the one
    that failed. Retries with exponential backoff on quota/5xx errors
    instead of letting one hiccup take down the whole batch."""
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            status = e.response.status_code if e.response is not None else None
            if status not in _RETRYABLE_STATUSES or attempt == retries - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "Post ID", "Content/slide text", "Caption", "Hashtags", "CTA", "Post type",  # A-F
    "Content Status", "Content Comments",                                        # G-H
    "Image Link(s)", "Visual Status", "Visual Comments",                         # I-K
]
CONTENT_STATUS_COL = 7   # 1-based, "Content Status"
VISUAL_STATUS_COL = 10   # 1-based, "Visual Status"


def get_client():
    creds_dict = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def open_spreadsheet(client):
    return client.open_by_key(os.environ["GOOGLE_SHEET_ID"])


def get_or_create_worksheet(spreadsheet, title):
    try:
        return spreadsheet.worksheet(title), False
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=100, cols=len(HEADERS) + 2)
        ws.append_row(HEADERS)
        return ws, True


def _dropdown_request(worksheet, col_index_1based, n_rows):
    return {
        "setDataValidation": {
            "range": {
                "sheetId": worksheet.id,
                "startRowIndex": 1,
                "endRowIndex": n_rows + 1,
                "startColumnIndex": col_index_1based - 1,
                "endColumnIndex": col_index_1based,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": v} for v in STATUS_OPTIONS],
                },
                "showCustomUi": True,
                "strict": True,
            },
        }
    }


def _apply_dropdowns(spreadsheet, worksheet, n_rows):
    requests = [_dropdown_request(worksheet, col, n_rows) for col in (CONTENT_STATUS_COL, VISUAL_STATUS_COL)]
    spreadsheet.batch_update({"requests": requests})


def _write_hyperlinked_urls(spreadsheet, worksheet, row_idx, col_idx, urls):
    """Writes urls joined by "\n" into one cell, each one an actual
    clickable hyperlink — not relying on Sheets' own auto-linking, which
    only kicks in when a cell's ENTIRE content is a single URL. A
    carousel's Image Link(s) cell holds 2+ URLs on separate lines, so
    none of them got auto-linked and showed up as plain text (caught
    2026-09-17 testing post 14, the first carousel through the sheet).
    A plain gspread `update()` can only set cell text, not per-substring
    link metadata, so this goes through the same raw batch_update()
    escape hatch _dropdown_request already uses."""
    joined = "\n".join(urls)
    runs = []
    offset = 0
    for i, url in enumerate(urls):
        runs.append({"startIndex": offset, "format": {"link": {"uri": url}}})
        offset += len(url)
        if i < len(urls) - 1:
            # More urls follow (separated by "\n") — reset formatting for
            # the separator. Skipped after the LAST url: the Sheets API
            # rejects a run whose startIndex == len(string) ("must be less
            # than the length of the string being formatted"), which a
            # trailing reset run always would be, single-url case included
            # (real bug, caught 2026-09-17 — crashed every resubmit).
            runs.append({"startIndex": offset, "format": {}})
            offset += 1  # the "\n" separator
    _with_retry(spreadsheet.batch_update, {
        "requests": [{
            "updateCells": {
                "rows": [{"values": [{
                    "userEnteredValue": {"stringValue": joined},
                    "textFormatRuns": runs,
                }]}],
                "fields": "userEnteredValue,textFormatRuns",
                "start": {
                    "sheetId": worksheet.id,
                    "rowIndex": row_idx - 1,
                    "columnIndex": col_idx - 1,
                },
            }
        }]
    })


def _slide_summary(item):
    parts = []
    for i, slide in enumerate(item["slides"], start=1):
        layout = slide["layout"]
        if layout == "hook":
            parts.append(f"[{i}:hook] {slide['text']}")
        elif layout == "bullet_list":
            parts.append(f"[{i}:bullet_list] " + " / ".join(slide["items"]))
        elif layout == "stat_card":
            parts.append(f"[{i}:stat_card] {slide['stat']} — {slide['caption']}")
        elif layout == "photo":
            parts.append(f"[{i}:photo] {slide['caption']}")
        elif layout == "logo_endcard":
            parts.append(f"[{i}:logo_endcard]")
    return "\n".join(parts)


def _existing_post_ids(worksheet):
    """Post IDs (column A) already present, skipping the header row."""
    return {v for v in worksheet.col_values(1)[1:] if v}


def _find_row_index(worksheet, post_id):
    """1-based row index (including the header row) of the row whose
    Post ID matches, or None. Post ID is always column A."""
    col_values = _with_retry(worksheet.col_values, 1)
    for i, val in enumerate(col_values, start=1):
        if val == str(post_id):
            return i
    return None


def write_content_rows(spreadsheet, tab_title, items):
    """Appends any of `items` not already present in the tab (by Post
    ID), with the visual columns left blank. Safe to call again for a
    tab that already has some rows — never touches rows already there,
    so an in-progress review of other rows in the same tab is left
    alone."""
    ws, _ = get_or_create_worksheet(spreadsheet, tab_title)
    existing_ids = _existing_post_ids(ws)

    new_items = [item for item in items if str(item["id"]) not in existing_ids]
    rows = [[
        item["id"], _slide_summary(item), item["caption"], " ".join(item["hashtags"]),
        item["cta"], item["post_type"], "", "", "", "", "",
    ] for item in new_items]
    if rows:
        ws.append_rows(rows)
    total_rows = len(existing_ids) + len(rows)
    if total_rows:
        _apply_dropdowns(spreadsheet, ws, n_rows=total_rows)
    return ws


def update_content_row(worksheet, item):
    """Overwrites one row's content columns (A-F) in place and clears
    Content Status/Comments (G-H) — used when resubmitting a 'Need
    Change' content revision. Leaves the visual columns (I-K) alone."""
    row_idx = _find_row_index(worksheet, item["id"])
    if row_idx is None:
        raise ValueError(f"Post ID {item['id']} not found in tab '{worksheet.title}'")
    row = [
        item["id"], _slide_summary(item), item["caption"], " ".join(item["hashtags"]),
        item["cta"], item["post_type"], "", "",
    ]
    _with_retry(worksheet.update, f"A{row_idx}:H{row_idx}", [row])


def _is_legacy_visual_only_tab(headers):
    """The very first batch's items (3-9) got their own separate tab
    before visual review moved onto the content tab — 5 columns, Post
    ID / Image link(s) / Caption (context) / Status / My Comments."""
    return len(headers) >= 2 and headers[1] == "Image link(s)"


def write_visual_columns(spreadsheet, worksheet, item, image_urls):
    """Fills in the Image Link(s) column for a row that's already there
    from content review, leaving Visual Status/Comments blank for the
    reviewer. Does not touch the content columns.

    Handles three tab shapes (2026-09-17):
    1. New unified 11-column tab (created after this design existed) —
       Image Link(s)/Visual Status/Visual Comments are already columns
       I-K, just write to them.
    2. The legacy 5-column visual-only tab from the very first batch
       (see _is_legacy_visual_only_tab) — Image Link(s) is at B,
       Status/My Comments at D-E.
    3. A content-only tab that predates the unified schema and has
       NEVER had visual columns (the live content-2026-09-16 tab, items
       1-2's batch) — append the 3 visual headers once, with their own
       dropdown, then write to them. Without this, writing blindly to
       I-K would either land on the wrong existing columns (corrupting
       content data) or create headerless columns get_all_records()
       can't see — both real bugs caught by testing before this fix."""
    row_idx = _find_row_index(worksheet, item["id"])
    if row_idx is None:
        raise ValueError(f"Post ID {item['id']} not found in tab '{worksheet.title}'")
    headers = _with_retry(worksheet.row_values, 1)

    if _is_legacy_visual_only_tab(headers):
        _with_retry(worksheet.update, f"B{row_idx}", [["\n".join(image_urls)]])
        _with_retry(worksheet.update, f"D{row_idx}:E{row_idx}", [["", ""]])
        return

    if "Image Link(s)" not in headers:
        image_col = len(headers) + 1
        start = gspread.utils.rowcol_to_a1(1, image_col)
        end = gspread.utils.rowcol_to_a1(1, image_col + 2)
        _with_retry(worksheet.update, f"{start}:{end}", [["Image Link(s)", "Visual Status", "Visual Comments"]])
        n_rows = len(_with_retry(worksheet.col_values, 1)) - 1
        _with_retry(spreadsheet.batch_update, {"requests": [_dropdown_request(worksheet, image_col + 1, n_rows)]})
    else:
        image_col = headers.index("Image Link(s)") + 1

    start = gspread.utils.rowcol_to_a1(row_idx, image_col)
    end = gspread.utils.rowcol_to_a1(row_idx, image_col + 2)
    _with_retry(worksheet.update, f"{start}:{end}", [["\n".join(image_urls), "", ""]])
    _write_hyperlinked_urls(spreadsheet, worksheet, row_idx, image_col, image_urls)


def read_tab_rows(worksheet):
    """Returns [{post_id, content_status, content_comments, visual_status,
    visual_comments}, ...] for every row with a Post ID, by header name
    so column order doesn't matter.

    Back-compat shim (2026-09-17): the very first batch's visual review
    happened on a separate tab with the old 5-column layout (Post ID,
    Image link(s), Caption (context), Status, My Comments) before this
    got merged onto one tab. Falls back to "Status"/"My Comments" for
    "Visual Status"/"Visual Comments" only when the new headers aren't
    present, so that one legacy tab keeps working for Approved/Rejected
    outcomes. Not exercised by any tab created after this change."""
    records = worksheet.get_all_records()
    headers = worksheet.row_values(1)
    # The live content-2026-09-16 tab predates the "Content Status"/
    # "Content Comments" rename (it was created when those columns were
    # just called "Status"/"My Comments") -- fall back to the old names
    # so that tab keeps working. Explicitly excludes the legacy
    # visual-only tab (its "Status" means something else entirely) --
    # conflating the two was a real bug caught by testing: it made a
    # freshly-content-approved item read as already visually approved
    # too, before visual review had even started. Not exercised by any
    # tab created after this fix.
    legacy_visual_tab = _is_legacy_visual_only_tab(headers)
    legacy_content_tab = (not legacy_visual_tab) and "Content Status" not in headers and "Status" in headers

    results = []
    for row in records:
        if not row.get("Post ID"):
            continue
        if legacy_content_tab:
            content_status = str(row.get("Status", "")).strip()
            content_comments = str(row.get("My Comments", "")).strip()
        else:
            content_status = str(row.get("Content Status", "")).strip()
            content_comments = str(row.get("Content Comments", "")).strip()
        if legacy_visual_tab:
            visual_status = str(row.get("Status", "")).strip()
            visual_comments = str(row.get("My Comments", "")).strip()
        else:
            visual_status = str(row.get("Visual Status", "")).strip()
            visual_comments = str(row.get("Visual Comments", "")).strip()
        results.append({
            "post_id": int(row["Post ID"]),
            "content_status": content_status,
            "content_comments": content_comments,
            "visual_status": visual_status,
            "visual_comments": visual_comments,
        })
    return results
