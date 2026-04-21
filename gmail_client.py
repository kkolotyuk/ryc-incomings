import base64
import logging
import os
from dataclasses import dataclass
from email import message_from_bytes
from email.utils import parsedate_to_datetime

import html2text
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
]
PROCESSED_LABEL_SUFFIX = "/processed"


@dataclass
class EmailMessage:
    message_id: str
    subject: str
    sender: str
    date: str
    body: str


def get_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_or_create_label(service, name: str) -> str:
    existing = get_label_id(service, name)
    if existing:
        return existing
    try:
        created = service.users().labels().create(
            userId="me",
            body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
        ).execute()
        logger.info("Created Gmail label: %s", name)
        return created["id"]
    except Exception:
        # label was created between our check and create — fetch again
        return get_label_id(service, name)


def get_label_id(service, name: str) -> str | None:
    labels = service.users().labels().list(userId="me").execute()
    for label in labels.get("labels", []):
        if label["name"] == name:
            return label["id"]
    return None


def extract_body(raw_message: bytes) -> str:
    msg = message_from_bytes(raw_message)
    html_body = None
    text_body = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html" and html_body is None:
                html_body = part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", errors="replace"
                )
            elif content_type == "text/plain" and text_body is None:
                text_body = part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", errors="replace"
                )
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            if msg.get_content_type() == "text/html":
                html_body = payload.decode(charset, errors="replace")
            else:
                text_body = payload.decode(charset, errors="replace")

    if html_body:
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = True
        converter.body_width = 0  # no line wrapping so links stay intact
        return converter.handle(html_body).strip()
    return (text_body or "").strip()


def fetch_unprocessed_emails(
    service, source_label_id: str, processed_label_id: str, max_age_days: int = 30, limit: int | None = None,
) -> list[EmailMessage]:
    params = dict(
        userId="me",
        labelIds=[source_label_id],
        q=f"newer_than:{max_age_days}d",
    )
    if limit is not None:
        params["maxResults"] = limit
    results = service.users().messages().list(**params).execute()

    messages = results.get("messages", [])
    emails = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me",
            id=msg_ref["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()

        label_ids = msg.get("labelIds", [])
        if processed_label_id in label_ids:
            continue

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}

        raw = service.users().messages().get(
            userId="me",
            id=msg_ref["id"],
            format="raw",
        ).execute()

        raw_bytes = base64.urlsafe_b64decode(raw["raw"])
        body = extract_body(raw_bytes)

        date_str = headers.get("Date", "")
        try:
            dt = parsedate_to_datetime(date_str)
            date_formatted = dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            date_formatted = date_str

        emails.append(EmailMessage(
            message_id=msg_ref["id"],
            subject=headers.get("Subject", "(без темы)"),
            sender=headers.get("From", ""),
            date=date_formatted,
            body=body[:8000],  # cap at 8k chars to stay within token budget
        ))

    return emails


def mark_as_processed(service, message_id: str, processed_label_id: str) -> None:
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [processed_label_id]},
    ).execute()
