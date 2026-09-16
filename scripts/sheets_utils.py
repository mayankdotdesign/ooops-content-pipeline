"""
Google Sheets integration for Phase 6 (2026-09-17 redesign: one
persistent spreadsheet, a new tab per review cycle named by date,
instead of emailing xlsx attachments back and forth).

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

import gspread
from google.oauth2.service_account import Credentials

STATUS_OPTIONS = ["Approved", "Need Change", "Rejected"]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_client():
    creds_dict = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def open_spreadsheet(client):
    return client.open_by_key(os.environ["GOOGLE_SHEET_ID"])


def get_or_create_worksheet(spreadsheet, title, headers):
    try:
        return spreadsheet.worksheet(title), False
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=100, cols=len(headers) + 2)
        ws.append_row(headers)
        return ws, True


def _apply_status_dropdown(spreadsheet, worksheet, status_col_index, n_rows):
    """status_col_index is 0-based."""
    request = {
        "requests": [{
            "setDataValidation": {
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": 1,
                    "endRowIndex": n_rows + 1,
                    "startColumnIndex": status_col_index,
                    "endColumnIndex": status_col_index + 1,
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
        }]
    }
    spreadsheet.batch_update(request)


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


def write_content_review_tab(spreadsheet, tab_title, items):
    headers = ["Post ID", "Content/slide text", "Caption", "Hashtags", "CTA", "Post type", "Status", "My Comments"]
    ws, created = get_or_create_worksheet(spreadsheet, tab_title, headers)
    if not created:
        return ws  # already exists — don't overwrite an in-progress review

    rows = [[
        item["id"], _slide_summary(item), item["caption"], " ".join(item["hashtags"]),
        item["cta"], item["post_type"], "", "",
    ] for item in items]
    if rows:
        ws.append_rows(rows)
    _apply_status_dropdown(spreadsheet, ws, status_col_index=6, n_rows=len(rows))
    return ws


def write_visual_review_tab(spreadsheet, tab_title, items, image_urls_by_id):
    headers = ["Post ID", "Image link(s)", "Caption (context)", "Status", "My Comments"]
    ws, created = get_or_create_worksheet(spreadsheet, tab_title, headers)
    if not created:
        return ws

    rows = [[
        item["id"], "\n".join(image_urls_by_id[item["id"]]), item["caption"], "", "",
    ] for item in items]
    if rows:
        ws.append_rows(rows)
    _apply_status_dropdown(spreadsheet, ws, status_col_index=3, n_rows=len(rows))
    return ws


def read_tab_rows(worksheet):
    """Returns [{post_id, status, comments}, ...] for every row with a
    Post ID, by header name so column order doesn't matter."""
    records = worksheet.get_all_records()
    results = []
    for row in records:
        if not row.get("Post ID"):
            continue
        results.append({
            "post_id": int(row["Post ID"]),
            "status": str(row.get("Status", "")).strip(),
            "comments": str(row.get("My Comments", "")).strip(),
        })
    return results


def is_tab_fully_reviewed(rows):
    """True once every row has a non-blank Status — the signal that the
    user is done with that tab, checked by re-reading the live sheet
    rather than polling for an emailed reply."""
    return bool(rows) and all(r["status"] in STATUS_OPTIONS for r in rows)
