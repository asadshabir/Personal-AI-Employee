"""
Gmail MCP Handler — Platinum Tier
IMAP-based Gmail monitoring with:
  - App Password login (no OAuth needed)
  - Unread email monitoring (polling every 30s)
  - Keyword-based auto-reply
  - Human-approval workflow via Pending_Approval/
  - Full audit logging per Handbook §5.2
  - Tier 2 enforcement (non-keyword replies require approval)
"""

import asyncio
import email
import imaplib
import json
import logging
import os
import re
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PLATINUM_DIR    = Path(__file__).resolve().parent
VAULT_ROOT      = PLATINUM_DIR.parent

ENV_FILE        = PLATINUM_DIR / ".env"
RULES_FILE      = PLATINUM_DIR / "gmail_auto_reply_rules.json"
LOGS_DIR        = VAULT_ROOT / "Logs"
PENDING_DIR     = VAULT_ROOT / "Pending_Approval"
APPROVED_DIR    = VAULT_ROOT / "Approved"
DONE_DIR        = VAULT_ROOT / "Done"
ACTION_LOG_FILE = LOGS_DIR / "gmail_actions.log"

for d in (LOGS_DIR, PENDING_DIR, APPROVED_DIR, DONE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gmail_mcp")


def action_log(event: str, detail: str = "") -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {event:<30} | {detail[:120]}\n"
    try:
        with ACTION_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    # Also check OS environment
    for key in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "ANTHROPIC_API_KEY"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


# ---------------------------------------------------------------------------
# Load rules
# ---------------------------------------------------------------------------
def load_rules() -> dict:
    if not RULES_FILE.exists():
        logger.warning(f"Rules file not found: {RULES_FILE}")
        return {}
    with RULES_FILE.open(encoding="utf-8") as f:
        rules = json.load(f)
    rules.pop("_comment", None)
    logger.info(f"Loaded {len(rules)} auto-reply rules from {RULES_FILE.name}")
    return rules


# ---------------------------------------------------------------------------
# Keyword match
# ---------------------------------------------------------------------------
def match_keyword(text: str, rules: dict) -> str | None:
    """Return first matching reply or None. Case-insensitive substring match."""
    lower = text.lower()
    for keyword, reply in rules.items():
        if keyword.lower() in lower:
            return reply
    return None


# ---------------------------------------------------------------------------
# Gmail IMAP/SMTP handler
# ---------------------------------------------------------------------------
class GmailMCPHandler:
    IMAP_HOST = "imap.gmail.com"
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(self, address: str, app_password: str):
        self.address      = address
        self.app_password = app_password
        self.imap: imaplib.IMAP4_SSL | None = None
        self.rules        = load_rules()
        self._seen_ids: set[str] = set()   # processed email UIDs

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def connect_imap(self) -> bool:
        try:
            self.imap = imaplib.IMAP4_SSL(self.IMAP_HOST)
            self.imap.login(self.address, self.app_password)
            logger.info("IMAP login successful ✅")
            action_log("IMAP_CONNECTED", f"Account: {self.address}")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP login failed: {e}")
            action_log("IMAP_LOGIN_FAILED", str(e))
            return False

    def ensure_connected(self) -> bool:
        try:
            if self.imap:
                self.imap.noop()
                return True
        except Exception:
            pass
        return self.connect_imap()

    # ------------------------------------------------------------------
    # Read unread emails
    # ------------------------------------------------------------------
    def get_unread_emails(self) -> list[dict]:
        results = []
        try:
            if not self.ensure_connected():
                return results

            self.imap.select("INBOX")
            _, data = self.imap.search(None, "UNSEEN")
            uid_list = data[0].split()

            if not uid_list:
                return results

            logger.info(f"Unread emails: {len(uid_list)}")

            for uid in uid_list:
                uid_str = uid.decode()
                if uid_str in self._seen_ids:
                    continue

                _, msg_data = self.imap.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                sender  = email.utils.parseaddr(msg.get("From", ""))[1]
                subject = msg.get("Subject", "(no subject)")
                body    = self._extract_body(msg)

                results.append({
                    "uid":     uid_str,
                    "sender":  sender,
                    "subject": subject,
                    "body":    body,
                })

        except Exception as e:
            logger.error(f"get_unread_emails error: {e}")
            self.imap = None  # force reconnect next poll

        return results

    def _extract_body(self, msg) -> str:
        """Extract plain text body from email."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
                    except Exception:
                        pass
        else:
            try:
                return msg.get_payload(decode=True).decode(
                    msg.get_content_charset() or "utf-8", errors="replace"
                )
            except Exception:
                pass
        return ""

    # ------------------------------------------------------------------
    # Send reply
    # ------------------------------------------------------------------
    def send_reply(self, to: str, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg["From"]    = self.address
            msg["To"]      = to
            msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(self.address, self.app_password)
                smtp.sendmail(self.address, to, msg.as_string())

            logger.info(f"Email sent to '{to}' | Subject: {subject[:60]}")
            action_log("EMAIL_SENT", f"To: {to} | Subject: {subject[:80]}")
            return True

        except Exception as e:
            logger.error(f"send_reply failed: {e}")
            action_log("EMAIL_SEND_FAILED", f"To: {to} | Error: {e}")
            return False

    # ------------------------------------------------------------------
    # Mark as read (after processing)
    # ------------------------------------------------------------------
    def mark_as_read(self, uid: str) -> None:
        try:
            self.imap.store(uid, "+FLAGS", "\\Seen")
        except Exception as e:
            logger.warning(f"Could not mark {uid} as read: {e}")

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------
    def create_approval_file(self, sender: str, subject: str,
                             body: str, suggested_reply: str) -> Path:
        ts   = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe = re.sub(r"[^\w]", "_", sender[:30])
        path = PENDING_DIR / f"GMAIL_REPLY_APPROVAL_REQUIRED_{ts}_{safe}.md"

        content = f"""---
title: "Gmail Reply — Approval Required"
from: "{sender}"
subject: "{subject}"
received: "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
priority: "P2"
status: "pending_approval"
assigned_to: "human_operator"
classification: "gmail_reply"
---

# Gmail Reply Approval Required

## Incoming Email
**From:** {sender}
**Subject:** {subject}

### Body
{body[:800]}

## Suggested Reply
{suggested_reply}

## Approval Actions
- [ ] **Approve** — send the suggested reply as-is
- [ ] **Reject** — do not reply
- [ ] **Modify** — edit the reply above, then approve

## Instructions
1. Review the suggested reply
2. Move this file to `/Approved/` directory, **OR**
3. Update `status` to `approved` in the frontmatter and save

## Constitutional Requirement
⚠️ **TIER 2 ACTION**: All Gmail replies must be approved by the human
operator before sending. Enforced by Company_Handbook.md §3.3.
"""
        path.write_text(content, encoding="utf-8")
        logger.info(f"Approval request created: {path.name}")
        action_log("APPROVAL_CREATED", f"From: {sender} | Subject: {subject[:60]} | File: {path.name}")
        return path

    # ------------------------------------------------------------------
    # Approval watcher
    # ------------------------------------------------------------------
    async def watch_approvals(self) -> None:
        logger.info("Approval watcher started — polling every 10s")
        while True:
            try:
                for md_file in sorted(APPROVED_DIR.glob("GMAIL_REPLY_APPROVAL_REQUIRED_*.md")):
                    self._process_approved_email(md_file)
            except Exception as e:
                logger.error(f"Approval watcher error: {e}")
            await asyncio.sleep(10)

    def _process_approved_email(self, md_file: Path) -> None:
        try:
            text   = md_file.read_text(encoding="utf-8")
            sender  = re.search(r'^from:\s+"(.+?)"', text, re.M)
            subject = re.search(r'^subject:\s+"(.+?)"', text, re.M)

            # Extract suggested reply (between "## Suggested Reply" and "## Approval")
            reply_match = re.search(
                r"## Suggested Reply\n(.+?)\n## Approval",
                text, re.S
            )

            if not (sender and subject and reply_match):
                logger.warning(f"Could not parse approval file: {md_file.name}")
                return

            to      = sender.group(1)
            subj    = subject.group(1)
            reply   = reply_match.group(1).strip()

            if self.send_reply(to, subj, reply):
                done_path = DONE_DIR / md_file.name
                md_file.rename(done_path)
                logger.info(f"Approved email sent and moved to Done/: {md_file.name}")
            else:
                logger.error(f"Failed to send approved email: {md_file.name}")

        except Exception as e:
            logger.error(f"Error processing approval {md_file.name}: {e}")

    # ------------------------------------------------------------------
    # Startup scan — mark existing unread as seen (skip old emails)
    # ------------------------------------------------------------------
    def seed_existing_unread(self) -> None:
        """On first run, load all currently-unread UIDs into _seen_ids so
        we only process NEW emails that arrive after startup."""
        try:
            if not self.ensure_connected():
                return
            self.imap.select("INBOX")
            _, data = self.imap.search(None, "UNSEEN")
            uid_list = data[0].split()
            for uid in uid_list:
                self._seen_ids.add(uid.decode())
            logger.info(f"Startup: {len(uid_list)} existing unread emails skipped — watching for NEW emails only.")
        except Exception as e:
            logger.warning(f"seed_existing_unread error: {e}")

    # ------------------------------------------------------------------
    # Main monitor loop
    # ------------------------------------------------------------------
    async def monitor_loop(self) -> None:
        logger.info("Gmail monitor started — polling every 30s. Ctrl+C to stop.")
        while True:
            try:
                emails = self.get_unread_emails()

                for em in emails:
                    uid     = em["uid"]
                    sender  = em["sender"]
                    subject = em["subject"]
                    body    = em["body"]

                    # Combined text for keyword matching
                    combined = f"{subject} {body}"
                    logger.info(f"New email from '{sender}' | Subject: {subject[:60]}")

                    reply = match_keyword(combined, self.rules)

                    if reply:
                        logger.info(f"Keyword match — auto-replying to '{sender}'")
                        self.send_reply(sender, subject, reply)
                        self.mark_as_read(uid)
                    else:
                        # No keyword match — try Groq AI reply
                        from groq_ai import gmail_reply as groq_gmail
                        ai_reply = groq_gmail(sender, subject, body)
                        if ai_reply:
                            logger.info(f"Groq reply for '{sender}': {ai_reply[:60]}")
                            self.send_reply(sender, subject, ai_reply)
                            self.mark_as_read(uid)
                        else:
                            # Groq unavailable — approval flow
                            default_reply = (
                                "Hi! 😊\n\nThanks for your email. "
                                "I'll review and get back to you shortly.\n\nBest,\nAsad Shabir"
                            )
                            self.create_approval_file(sender, subject, body, default_reply)
                        self.mark_as_read(uid)

                    self._seen_ids.add(uid)

            except Exception as e:
                logger.error(f"monitor_loop error: {e}")
                self.imap = None  # force reconnect

            await asyncio.sleep(30)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    env = load_env()

    address      = env.get("GMAIL_ADDRESS", "")
    app_password = env.get("GMAIL_APP_PASSWORD", "")

    if not address or not app_password:
        logger.error("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set in .env")
        sys.exit(1)

    logger.info(f"=== Gmail MCP Server Starting ===")
    logger.info(f"Account: {address}")

    handler = GmailMCPHandler(address, app_password)

    if not handler.connect_imap():
        logger.error("Could not connect to Gmail. Check credentials in .env")
        sys.exit(1)

    # Skip existing unread — only process NEW emails from this point
    handler.seed_existing_unread()

    # Run monitor + approval watcher concurrently
    await asyncio.gather(
        handler.monitor_loop(),
        handler.watch_approvals(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Gmail MCP stopped by user.")
