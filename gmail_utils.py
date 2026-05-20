import base64
import json
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from cryptography.fernet import Fernet
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")


def credentials_file_exists():
    return os.path.exists(CREDENTIALS_PATH)


def load_client_config():
    with open(CREDENTIALS_PATH) as f:
        data = json.load(f)
    return data.get("web") or data.get("installed")


def get_fernet():
    key = os.environ.get("GMAIL_TOKEN_KEY", "").strip()
    if not key:
        raise RuntimeError("GMAIL_TOKEN_KEY environment variable is not set.")
    raw = key.encode() if isinstance(key, str) else key
    return Fernet(raw)


def encrypt_token(token):
    return get_fernet().encrypt(token.encode()).decode()


def decrypt_token(token_enc):
    return get_fernet().decrypt(token_enc.encode()).decode()


def build_gmail_service(account_row):
    """Build authenticated Gmail API service, refreshing tokens as needed."""
    if not GMAIL_AVAILABLE:
        raise RuntimeError("Google API packages are not installed.")

    access_token = decrypt_token(account_row["access_token"])
    refresh_token = decrypt_token(account_row["refresh_token"])
    config = load_client_config()

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        scopes=SCOPES,
    )

    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        from database.db import upsert_gmail_account
        expiry = creds.expiry.isoformat() if creds.expiry else None
        upsert_gmail_account(
            user_id=account_row["user_id"],
            gmail_email=account_row["gmail_email"],
            google_account_id=account_row["google_account_id"],
            access_token_enc=encrypt_token(creds.token),
            refresh_token_enc=encrypt_token(creds.refresh_token or refresh_token),
            token_expiry=expiry,
            scope=account_row["scope"],
        )

    return build("gmail", "v1", credentials=creds)


def sync_inbox(user_id, account_row, max_results=50):
    """Fetch latest inbox emails and persist new ones. Returns count of newly saved emails."""
    from database.db import get_email_by_gmail_id, save_email, save_email_attachment

    service = build_gmail_service(account_row)
    result = service.users().messages().list(
        userId="me", maxResults=max_results, labelIds=["INBOX"]
    ).execute()

    synced = 0
    for ref in result.get("messages", []):
        gmail_id = ref["id"]
        if get_email_by_gmail_id(gmail_id):
            continue
        raw = service.users().messages().get(
            userId="me", id=gmail_id, format="full"
        ).execute()
        parsed = parse_message(raw)
        email_id = save_email(
            user_id=user_id,
            gmail_message_id=parsed["gmail_message_id"],
            gmail_thread_id=parsed["gmail_thread_id"],
            direction="INBOUND",
            from_email=parsed["from_email"],
            from_name=parsed["from_name"],
            to_email=parsed["to_email"],
            to_name=parsed["to_name"],
            cc=parsed["cc"],
            subject=parsed["subject"],
            body_plain=parsed["body_plain"],
            body_html=parsed["body_html"],
            snippet=parsed["snippet"],
            label_names=parsed["label_names"],
            has_attachments=parsed["has_attachments"],
            received_at=parsed["received_at"],
        )
        if email_id:
            for att in parsed.get("attachment_meta", []):
                save_email_attachment(
                    email_id=email_id,
                    filename=att["filename"],
                    mime_type=att["mime_type"],
                    gmail_attachment_id=att["gmail_attachment_id"],
                )
            synced += 1

    return synced


def send_gmail(account_row, to, subject, body, reply_to_thread_id=None, cc=None, bcc=None):
    """Send an email via Gmail API. Returns sent message data from the API."""
    service = build_gmail_service(account_row)

    msg = MIMEMultipart()
    msg["to"] = to
    msg["from"] = account_row["gmail_email"]
    msg["subject"] = subject
    if cc:
        msg["cc"] = cc
    if bcc:
        msg["bcc"] = bcc
    msg.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if reply_to_thread_id:
        payload["threadId"] = reply_to_thread_id

    return service.users().messages().send(userId="me", body=payload).execute()


def parse_message(raw_msg):
    """Extract structured data from a raw Gmail API message object."""
    payload = raw_msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

    from_name, from_email = _parse_addr(headers.get("from", ""))
    to_name, to_email = _parse_addr(headers.get("to", ""))

    body_plain, body_html = _extract_body(payload)
    attachments = []
    _collect_attachments(payload, attachments)

    received_at = None
    ts = raw_msg.get("internalDate")
    if ts:
        try:
            received_at = datetime.utcfromtimestamp(int(ts) / 1000).isoformat()
        except Exception:
            pass

    return {
        "gmail_message_id": raw_msg["id"],
        "gmail_thread_id": raw_msg.get("threadId"),
        "from_email": from_email,
        "from_name": from_name,
        "to_email": to_email,
        "to_name": to_name,
        "cc": headers.get("cc") or None,
        "subject": headers.get("subject", "(no subject)"),
        "body_plain": body_plain,
        "body_html": body_html,
        "snippet": raw_msg.get("snippet", ""),
        "label_names": ",".join(raw_msg.get("labelIds", [])),
        "has_attachments": 1 if attachments else 0,
        "received_at": received_at,
        "attachment_meta": attachments,
    }


def _parse_addr(header):
    if not header:
        return None, None
    if "<" in header:
        parts = header.split("<", 1)
        name = parts[0].strip().strip('"') or None
        email = parts[1].rstrip(">").strip() or None
    else:
        name = None
        email = header.strip() or None
    return name, email


def _extract_body(payload):
    mime = payload.get("mimeType", "")
    plain = html = None

    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            plain = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    elif mime == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    elif "multipart" in mime:
        for part in payload.get("parts", []):
            p, h = _extract_body(part)
            if p and not plain:
                plain = p
            if h and not html:
                html = h

    return plain, html


def _collect_attachments(payload, result):
    if payload.get("filename"):
        body = payload.get("body", {})
        result.append({
            "filename": payload["filename"],
            "mime_type": payload.get("mimeType"),
            "gmail_attachment_id": body.get("attachmentId"),
        })
    for part in payload.get("parts", []):
        _collect_attachments(part, result)
