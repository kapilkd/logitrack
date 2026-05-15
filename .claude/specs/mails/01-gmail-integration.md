# Spec: Gmail Integration

## Overview

This feature replaces the /emails placeholder with a production-ready Gmail integration module powered by the Gmail API and OAuth 2.0 authentication.

Users can securely connect their Gmail account using Google OAuth consent flow without storing Gmail passwords or app passwords in the database.

## The system supports:

Sending emails from the application
Reading incoming Gmail inbox messages
Syncing shipment/vendor communication
AI-ready email processing workflows
Email logging and conversation tracking
Attachment handling foundation
Future automation support (AI summarization, shipment extraction, auto-reply workflows)

This becomes the foundation for all future email-driven workflows:

vendor communication
shipment updates
invoice dispatch
automated follow-ups
AI-powered shipment tracking
document extraction

The implementation uses Google's official Gmail API instead of SMTP-only architecture.

## Depends on

All base features must be complete:

auth
profile
shipments
vendors
billing
company settings

The company-profile settings page (which demonstrates the settings pattern) should be complete — this feature follows the same settings approach.

## Routes

Gmail Authentication
GET /settings/gmail
Gmail integration settings page — logged-in
GET /auth/gmail/connect
Start Google OAuth flow — logged-in
GET /auth/gmail/callback
OAuth callback handler from Google
POST /auth/gmail/disconnect
Disconnect Gmail account and revoke tokens
Email UI
GET /emails
Unified inbox + compose page — logged-in
GET /emails/sync
Fetch latest Gmail emails and store locally
POST /emails/send
Send email via Gmail API
GET /emails/:id
View email details and conversation thread
Future AI Routes (Foundation Only)
POST /emails/process
AI process incoming emails
POST /emails/auto-reply
Generate AI-assisted replies

## Database changes

New table: gmail_accounts
gmail_accounts (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
gmail_email TEXT NOT NULL,
google_account_id TEXT,
access_token TEXT NOT NULL,
refresh_token TEXT NOT NULL,
token_expiry TEXT,
scope TEXT,
is_connected INTEGER DEFAULT 1,
created_at TEXT DEFAULT (datetime('now')),
updated_at TEXT
)
New table: emails
emails (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER NOT NULL REFERENCES users(id),
gmail_message_id TEXT NOT NULL UNIQUE,
gmail_thread_id TEXT,
direction TEXT NOT NULL, -- INBOUND | OUTBOUND
from_email TEXT,
from_name TEXT,
to_email TEXT,
to_name TEXT,
cc TEXT,
bcc TEXT,
subject TEXT,
body_plain TEXT,
body_html TEXT,
snippet TEXT,
status TEXT DEFAULT 'RECEIVED',
label_names TEXT,
has_attachments INTEGER DEFAULT 0,
received_at TEXT,
sent_at TEXT,
synced_at TEXT DEFAULT (datetime('now'))
)
New table: email_attachments
email_attachments (
id INTEGER PRIMARY KEY AUTOINCREMENT,
email_id INTEGER NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
filename TEXT,
mime_type TEXT,
gmail_attachment_id TEXT,
file_path TEXT,
created_at TEXT DEFAULT (datetime('now'))
)
New table: email_ai_processing
email_ai_processing (
id INTEGER PRIMARY KEY AUTOINCREMENT,
email_id INTEGER NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
ai_summary TEXT,
detected_category TEXT,
extracted_entities TEXT,
shipment_reference TEXT,
invoice_reference TEXT,
processing_status TEXT DEFAULT 'PENDING',
created_at TEXT DEFAULT (datetime('now'))
)

## Templates

Create
templates/emails.html
inbox + compose layout
conversation thread view
email details modal
AI summary section placeholder
templates/settings_gmail.html
Gmail connect/disconnect page
templates/email_details.html
complete thread/conversation view

## Modify

templates/\_sidebar.html
add "Emails" section
add "Gmail Integration" sub-link under Settings accordion

## Files to change

app.py
add OAuth routes
add email sync routes
add Gmail send/read logic
add inbox rendering
add token refresh logic
database/db.py
add all Gmail/email table DDL
add CRUD helpers
add sync/update helpers
templates/\_sidebar.html
static/css/emails.css
Files to create
templates/emails.html
templates/settings_gmail.html
templates/email_details.html
static/css/emails.css

## New dependencies

google-api-python-client
google-auth
google-auth-oauthlib
google-auth-httplib2
Google Cloud requirements
Create Google Cloud project
Enable Gmail API
Configure OAuth consent screen
Create OAuth Client Credentials
Download credentials.json
Store securely outside public directory

## Gmail API scopes

SCOPES = [
'https://www.googleapis.com/auth/gmail.readonly',
'https://www.googleapis.com/auth/gmail.send',
'https://www.googleapis.com/auth/gmail.modify'
]

## Rules for implementation

No SQLAlchemy or ORMs
Parameterised queries only (? placeholders)
Never store Gmail passwords or app passwords
OAuth 2.0 only
Never expose tokens in templates/logs
Refresh expired access tokens automatically
All templates extend base.html
Login required on all routes
Redirect unauthenticated users to /login
Gracefully handle revoked Google access
Use CSS variables — never hardcode hex values
Store Gmail message/thread IDs for conversation tracking
Preserve email threading and reply chain support
Wrap Gmail API calls in try/except
Log API failures cleanly
Sync inbox incrementally
Support vendor email auto-suggestions via <datalist>
Handle empty inbox state gracefully
Do not block UI during sync operations
Future-ready architecture for AI processing pipeline
Email synchronization behaviour
/emails/sync fetches latest Gmail emails
Prevent duplicate inserts using gmail_message_id

## Store:

sender
recipients
subject
snippet
body
labels
timestamps
Download attachment metadata
Maintain thread relationships
AI processing foundation

## Incoming emails should later support:

shipment status extraction
invoice detection
ETA extraction
container number detection
vendor classification
auto-summary generation
AI-generated replies

This spec only creates the foundation schema and routing structure.

## Security rules

OAuth credentials stored securely
Use HTTPS in production
Encrypt refresh tokens at rest
Never log token values
Validate OAuth state parameter
Revoke tokens on disconnect
Use least-privilege Gmail scopes
Definition of done
Visiting /settings/gmail shows Gmail integration status
Clicking "Connect Gmail" opens Google OAuth consent flow
Successful OAuth stores Gmail account connection
Gmail account can be disconnected cleanly
/emails shows inbox + compose interface
/emails/sync imports latest Gmail messages
Duplicate emails are prevented
Sending email works through Gmail API
Sent emails appear in inbox history
Conversation threading works
Vendor emails populate compose <datalist>
Email details page renders correctly
Access token refresh works automatically
Revoked tokens handled gracefully
Attachments metadata stored successfully
AI processing table structure created
Sidebar contains Gmail Integration and Emails sections
All POST routes return redirects (302)
Visiting routes while logged out redirects to /login
No Gmail passwords or app passwords stored anywhere
Application ready for future AI shipment automation workflows
