"""
SMTP send + IMAP reply-polling for Phase 6's email-driven approval
cycles. Uses GMAIL_ADDRESS/GMAIL_APP_PASSWORD (already-configured GitHub
repo secrets, per docs/build-plan.md's Email Setup section) — never
raw Gmail login passwords, an App Password specifically.

Usage: imported by scripts/review_cycle.py, not run directly.
"""

import email
import imaplib
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_notification_email(subject, body):
    """Link-only notification (2026-09-17 Sheets redesign) — no
    attachment, just tells the user a new tab is ready to review."""
    address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart()
    msg["From"] = address
    msg["To"] = address
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, app_password)
        server.sendmail(address, [address], msg.as_string())


def send_review_email(subject, body, attachment_path):
    address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart()
    msg["From"] = address
    msg["To"] = address  # reviewer replies to themselves/their own thread
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with open(attachment_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, app_password)
        server.sendmail(address, [address], msg.as_string())


def find_reply_with_attachment(subject_contains, save_dir):
    """Searches the inbox for an unread reply whose subject contains
    `subject_contains` and that has an attachment. If found, saves the
    first attachment into save_dir, marks the message as read (so it
    isn't reprocessed next run), and returns the saved path. Returns
    None if no matching unread reply exists yet — this is the normal
    case on most polling runs, not an error."""
    address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]

    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(address, app_password)
        imap.select("INBOX")

        status, data = imap.search(None, "UNSEEN", "SUBJECT", f'"{subject_contains}"')
        if status != "OK" or not data[0]:
            return None

        for msg_id in data[0].split():
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])

            for part in msg.walk():
                filename = part.get_filename()
                if not filename or not filename.lower().endswith((".xlsx", ".xls")):
                    continue
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename)
                with open(save_path, "wb") as f:
                    f.write(part.get_payload(decode=True))
                imap.store(msg_id, "+FLAGS", "\\Seen")
                return save_path

    return None
