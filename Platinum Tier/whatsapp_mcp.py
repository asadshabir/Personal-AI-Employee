"""
WhatsApp Web MCP Handler — Platinum Tier
Playwright-based WhatsApp Web automation with:
  - QR scan login (one-time, session persisted)
  - Unread message monitoring
  - Keyword-based auto-reply
  - Human-approval workflow via Pending_Approval/
  - Full audit logging per Handbook §5.2
  - Tier 2 enforcement (all non-keyword replies require approval)
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("whatsapp_mcp")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PLATINUM_DIR = Path(__file__).resolve().parent
VAULT_ROOT   = PLATINUM_DIR.parent

SESSION_DIR     = PLATINUM_DIR / "whatsapp_session"
LOGS_DIR        = VAULT_ROOT / "Logs"
PENDING_DIR     = VAULT_ROOT / "Pending_Approval"
APPROVED_DIR    = VAULT_ROOT / "Approved"
DONE_DIR        = VAULT_ROOT / "Done"
RULES_FILE      = PLATINUM_DIR / "whatsapp_auto_reply_rules.json"
ACTION_LOG_FILE = LOGS_DIR / "whatsapp_actions.log"

for d in (SESSION_DIR, LOGS_DIR, PENDING_DIR, APPROVED_DIR, DONE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Selectors  (WhatsApp Web — fallback lists handle DOM changes across versions)
# ---------------------------------------------------------------------------
SEL_CHAT_LIST    = '[aria-label="Chat list"]'
SEL_QR_CANVAS    = 'canvas[aria-label="Scan me!"], div[data-ref] canvas, canvas'

SEL_UNREAD_BADGE = (
    'span[data-testid="icon-unread-count"], '
    'span[aria-label*="unread message"], '
    'span[aria-label*="unread"]'
)

# Ordered fallback lists — first match wins
# Confirmed live selectors (from debug_connected.txt 2026-02-27):
#   Search box  → INPUT data-tab='3' aria='Search or start a new chat'
#   data-testid → 0 found on this build (testid selectors kept as fallback)
SEARCH_SELECTORS = [
    '[aria-label="Search or start a new chat"]',   # confirmed live
    'input[data-tab="3"]',                          # confirmed live
    '[aria-label="Search input textbox"]',          # older WA builds
    'div[contenteditable="true"][data-tab="3"]',
    '[data-testid="chat-list-search"]',
    '[title="Search input textbox"]',
    'div[role="textbox"][data-tab="3"]',
    'div[contenteditable="true"][aria-label]',
]

# Message compose box — data-tab="10" appears only after a chat is opened.
# Keeping existing selectors; confirmed aria-label may vary by locale.
MSG_BOX_SELECTORS = [
    '[aria-label="Type a message"]',
    'div[contenteditable="true"][data-tab="10"]',
    'div[role="textbox"][data-tab="10"]',
    'footer div[contenteditable="true"]',
    '[data-testid="conversation-compose-box-input"]',
    '[title="Type a message"]',
    'div[contenteditable="true"][spellcheck="true"]',
]

INCOMING_MSG_SELECTORS = [
    'div.message-in span.selectable-text',
    'div[data-testid="msg-container"] span.selectable-text',
    'div[class*="message-in"] span[class*="selectable-text"]',
]

# Poll interval (seconds) for the message-monitor loop
MONITOR_INTERVAL_SECONDS = 10

# Poll interval (seconds) for the approval-watcher loop
APPROVAL_POLL_SECONDS = 5

# Max retries for send operations
MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# Helper: load auto-reply rules
# ---------------------------------------------------------------------------
def load_rules() -> dict:
    """
    Load keyword → reply mapping from whatsapp_auto_reply_rules.json.
    Falls back to built-in defaults if the file is missing.
    """
    if RULES_FILE.exists():
        try:
            with open(RULES_FILE, encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data)} auto-reply rules from {RULES_FILE.name}")
            return data
        except Exception as e:
            logger.warning(f"Could not load rules file: {e} — using defaults")

    # Built-in defaults (edit whatsapp_auto_reply_rules.json to customise)
    defaults = {
        "hello":     "Hi! I'm currently using an AI assistant. I'll get back to you shortly.",
        "hi":        "Hello! How can I help you today?",
        "available": "Yes, I'm available. Let me check and respond shortly.",
        "price":     "For pricing details please send an email. I'll reply as soon as possible.",
        "thanks":    "You're welcome! Let me know if there's anything else I can help with.",
    }
    logger.info("Using built-in default auto-reply rules")
    return defaults


# ---------------------------------------------------------------------------
# Main handler class
# ---------------------------------------------------------------------------
class WhatsAppMCPHandler:
    """Playwright-based WhatsApp Web automation (Platinum Tier)."""

    def __init__(self):
        self.playwright = None
        self.browser    = None
        self.context    = None
        self.page       = None
        self.rules       = load_rules()
        self._seen_msgs: set = set()   # dedup tracker for this session

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    async def setup_browser(self) -> bool:
        """Launch Chromium with a persistent context (reuses saved session)."""
        try:
            self.playwright = await async_playwright().start()
            self.browser    = await self.playwright.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            session_file = SESSION_DIR / "storage_state.json"
            self.context = await self.browser.new_context(
                storage_state=str(session_file) if session_file.exists() else None,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            self.page = await self.context.new_page()
            self.page.on("crash",     lambda:      logger.error("Page crashed"))
            self.page.on("pageerror", lambda err:  logger.error(f"Page error: {err}"))
            logger.info("Browser setup complete")
            return True
        except Exception as e:
            logger.error(f"Browser setup failed: {e}")
            return False

    async def save_session(self):
        """Persist cookies/localStorage so the next run skips QR scan."""
        try:
            await self.context.storage_state(
                path=str(SESSION_DIR / "storage_state.json")
            )
            logger.info("Session saved to whatsapp_session/storage_state.json")
        except Exception as e:
            logger.error(f"Could not save session: {e}")

    async def cleanup(self):
        """Save session and close browser gracefully."""
        try:
            if self.context:
                await self.save_session()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    # ------------------------------------------------------------------
    # Login / QR flow
    # ------------------------------------------------------------------

    async def wait_for_qr_scan(self) -> bool:
        """
        Navigate to WhatsApp Web and wait (up to 3 minutes) for the user to
        scan the QR code on their phone.
        """
        logger.info("Opening WhatsApp Web — QR code will appear in the browser.")
        logger.info("On your phone: WhatsApp → ⋮ → Linked Devices → Link a Device")
        logger.info("Scan the QR code shown in the browser window.")

        await self.page.goto("https://web.whatsapp.com", timeout=30_000)

        # Wait for QR canvas to appear (proves page loaded)
        try:
            await self.page.wait_for_selector(SEL_QR_CANVAS, timeout=20_000)
            logger.info("QR code is visible — scan it now.")
        except PWTimeoutError:
            logger.info("QR canvas not detected — may already be logged in.")

        # Wait until the chat list appears (confirms successful scan)
        try:
            await self.page.wait_for_selector(SEL_CHAT_LIST, timeout=180_000)
            logger.info("QR scanned successfully! WhatsApp Web is connected.")
            await self.save_session()
            await self._log_action("QR_SCAN_SUCCESS", "Session established via QR scan")
            return True
        except PWTimeoutError:
            logger.error("Timed out waiting for QR scan (3 min). Try again.")
            await self._log_action("QR_SCAN_TIMEOUT", "User did not scan within 3 minutes")
            return False

    async def ensure_connected(self) -> bool:
        """
        Check if the session is still active.  If not, trigger QR scan.
        Uses domcontentloaded (not networkidle) because WhatsApp Web keeps
        WebSocket connections open and never reaches a true networkidle state.
        Chat list timeout is 90 s to allow for the 'Loading your chats' splash.
        """
        logger.info("Checking WhatsApp Web connection status…")
        await self.page.goto("https://web.whatsapp.com", timeout=30_000)
        # domcontentloaded is safe; networkidle hangs on WA's persistent WebSocket
        await self.page.wait_for_load_state("domcontentloaded")

        logger.info("Waiting up to 90 s for chat list (may show 'Loading your chats')…")
        try:
            await self.page.wait_for_selector(SEL_CHAT_LIST, timeout=90_000)
            logger.info("Already connected to WhatsApp Web")
            return True
        except PWTimeoutError:
            logger.info("Chat list not found after 90 s — checking for QR screen…")
            return await self.wait_for_qr_scan()

    # ------------------------------------------------------------------
    # Message reading
    # ------------------------------------------------------------------

    async def _find_element(self, selectors: list, timeout_each: int = 4_000):
        """Try each selector in order; return the first ElementHandle found."""
        for sel in selectors:
            try:
                el = await self.page.wait_for_selector(sel, timeout=timeout_each)
                if el:
                    return el
            except PWTimeoutError:
                continue
        return None

    # ------------------------------------------------------------------
    # DOM debug — called once after connect to capture live selectors
    # ------------------------------------------------------------------

    async def debug_dom(self):
        """
        Capture screenshot + DOM snapshot while session is live.
        Saves debug_connected.png and debug_connected.txt.
        """
        shot   = PLATINUM_DIR / "debug_connected.png"
        report = PLATINUM_DIR / "debug_connected.txt"
        lines  = []

        def L(msg=""):
            logger.info(f"[DEBUG] {msg}")
            lines.append(str(msg))

        await self.page.wait_for_timeout(3_000)
        await self.page.screenshot(path=str(shot))
        L(f"Screenshot: {shot}")

        arialabels = await self.page.evaluate("""
            () => { const s = new Set();
                for (const el of document.querySelectorAll('[aria-label]'))
                    s.add(el.tagName + ' | ' + el.getAttribute('aria-label').slice(0,60));
                return [...s].slice(0,60); }
        """)
        L(f"aria-label ({len(arialabels)}):")
        for a in arialabels: L(f"  {a}")

        testids = await self.page.evaluate("""
            () => { const s = new Set();
                for (const el of document.querySelectorAll('[data-testid]'))
                    s.add(el.getAttribute('data-testid'));
                return [...s].slice(0,60); }
        """)
        L(f"data-testid ({len(testids)}):")
        for t in testids: L(f"  {t}")

        datatabs = await self.page.evaluate("""
            () => [...document.querySelectorAll('[data-tab]')].slice(0,20).map(el => ({
                tag: el.tagName, tab: el.getAttribute('data-tab'),
                role: el.getAttribute('role')||'',
                ce: el.getAttribute('contenteditable')||'',
                aria: (el.getAttribute('aria-label')||'').slice(0,40) }))
        """)
        L(f"data-tab ({len(datatabs)}):")
        for d in datatabs:
            L(f"  <{d['tag']} data-tab={d['tab']!r} ce={d['ce']!r} aria={d['aria']!r}>")

        chat_info = await self.page.evaluate("""
            () => {
                const cl = document.querySelector('[aria-label="Chat list"]');
                if (!cl) return {found:false, childCount:0, preview:'', children:[]};
                return { found:true, childCount: cl.children.length,
                    preview: cl.innerHTML.slice(0,800),
                    children: [...cl.children].slice(0,5).map(k=>({
                        tag:k.tagName, role:k.getAttribute('role')||'',
                        testid:k.getAttribute('data-testid')||'',
                        aria:(k.getAttribute('aria-label')||'').slice(0,40),
                        text:(k.textContent||'').slice(0,60).trim() })) };
            }
        """)
        L(f"Chat list found={chat_info.get('found')} children={chat_info.get('childCount')}")
        L(f"innerHTML preview: {chat_info.get('preview','')[:500]}")
        for c in chat_info.get("children", []):
            L(f"  <{c['tag']} role={c['role']!r} testid={c['testid']!r}> '{c['text'][:50]}'")

        unread_els = await self.page.evaluate("""
            () => { const hits = [];
                for (const el of document.querySelectorAll('*')) {
                    for (const a of el.getAttributeNames()) {
                        const v = (el.getAttribute(a)||'').toLowerCase();
                        if (v.includes('unread')) {
                            hits.push({tag:el.tagName, attr:a,
                                val:el.getAttribute(a).slice(0,60), id:el.id||''});
                            break; } }
                    if (hits.length>=15) break; }
                return hits; }
        """)
        L(f"Elements with 'unread' ({len(unread_els)}):")
        for u in unread_els: L(f"  <{u['tag']} {u['attr']}={u['val']!r} id={u['id']!r}>")

        report.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"[DEBUG] Report: {report}")

    # ------------------------------------------------------------------
    # Message reading
    # ------------------------------------------------------------------

    async def get_unread_chats(self) -> list[dict]:
        """
        Find unread chats and extract the message preview directly from the
        chat-list row — no need to click into the conversation.

        Row structure (confirmed live 2026-02-27):
          [aria-label="Chat list"] > div[role="row"]
            span[title]           → contact/group name
            span[aria-label*="unread"] → unread badge (primary detection)
            numeric badge span    → fallback detection
            span[dir="ltr/rtl"]  → message preview text (last one wins)
        """
        results = []
        try:
            unread_items = await self.page.evaluate("""
                () => {
                    const chatList =
                        document.querySelector('[aria-label="Chat list"]') ||
                        document.querySelector('[data-testid="chat-list"]');
                    if (!chatList) return [];

                    const found = [];
                    for (const row of chatList.children) {
                        // ── Unread detection ───────────────────────────────
                        let hasUnread = !!row.querySelector('[aria-label*="unread"]');
                        if (!hasUnread) {
                            for (const el of row.querySelectorAll('span, div, p')) {
                                if (/^[1-9][0-9]{0,2}$/.test((el.textContent||'').trim())) {
                                    hasUnread = true; break;
                                }
                            }
                        }
                        if (!hasUnread) continue;

                        // ── Contact name ───────────────────────────────────
                        const titleEl = row.querySelector('span[title]');
                        let name = titleEl ? titleEl.getAttribute('title') : '';
                        if (!name) {
                            const d = row.querySelector('[dir="auto"]');
                            name = d ? d.textContent.trim().split('\\n')[0] : 'Unknown';
                        }
                        name = (name || 'Unknown').trim();

                        // ── Message preview from the row itself ────────────
                        // Walk all span[dir] elements; skip the contact name,
                        // skip timestamps (HH:MM / "Yesterday" / weekday),
                        // take the last non-empty remainder as the preview.
                        let preview = '';
                        const TIME_RE = /^(\\d{1,2}:\\d{2}|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)$/i;
                        const SENDER_RE = /^(you|you:)$/i;
                        const TYPING_RE = /^(typing|recording|audio)[\\s.…\\d]*/i;
                        const spans = row.querySelectorAll('span[dir]');
                        for (const s of spans) {
                            const t = (s.textContent || '').trim();
                            if (!t || t === name) continue;
                            if (TIME_RE.test(t)) continue;
                            if (SENDER_RE.test(t)) continue;
                            if (TYPING_RE.test(t)) continue;  // skip typing/recording indicators
                            preview = t;   // keep updating — last wins
                        }

                        // Fallback: strip name + time from full row text
                        if (!preview) {
                            const raw = (row.textContent || '').replace(name, '')
                                .replace(/\\d{1,2}:\\d{2}(\\s*(am|pm))?/gi, '')
                                .replace(/yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday/gi, '')
                                .trim();
                            preview = raw.split('\\n')[0].trim();
                        }

                        if (name) found.push({ name, preview });
                    }
                    return found;
                }
            """)

            if not unread_items:
                return results

            logger.info(f"Unread chats: {[i['name'] for i in unread_items]}")

            for item in unread_items:
                contact = item["name"]
                last_text = (item.get("preview") or "").strip()

                if not last_text:
                    logger.warning(f"No preview text for {contact!r} — skipping")
                    continue

                # Skip WhatsApp typing/recording status indicators
                if re.match(r'^(typing|recording|audio)[\s.…\d]*$', last_text, re.IGNORECASE):
                    continue

                dedup_key = f"{contact}::{last_text[:80]}"
                if dedup_key in self._seen_msgs:
                    continue

                self._seen_msgs.add(dedup_key)
                results.append({"contact": contact, "message": last_text})
                logger.info(f"Message from {contact!r}: {last_text[:60]}")

        except Exception as e:
            logger.error(f"get_unread_chats error: {e}")

        return results

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_message(self, contact: str, text: str) -> bool:
        """
        Open a chat with `contact` and send `text`.
        Tries multiple selectors for search box and message box to handle
        WhatsApp Web DOM changes.  Returns True on success.
        """
        for attempt in range(MAX_RETRIES + 1):
            try:
                # ── Step 1: Find and activate the search box ──────────────
                search = await self._find_element(SEARCH_SELECTORS, timeout_each=5_000)
                if not search:
                    raise RuntimeError("Search box not found with any known selector")

                await search.click()
                # Triple-click to clear any previous text, then type contact name
                await search.click(click_count=3)
                await self.page.keyboard.press("Control+a")
                await self.page.keyboard.press("Delete")
                await self.page.wait_for_timeout(300)

                # .type() works on ElementHandle (press_sequentially is Locator-only)
                await search.type(contact, delay=60)
                await self.page.wait_for_timeout(2_000)   # wait for results to render

                # ── Step 2: Open the first matching result ─────────────────
                # When WhatsApp filters the chat list, results can appear in a
                # separate search-results panel (not always in [aria-label="Chat list"]).
                # Keyboard nav (ArrowDown → Enter) works universally regardless of
                # which DOM container holds the results.
                #
                # Primary:  span[title] exact/partial match via JS click
                # Fallback: ArrowDown + Enter (keyboard navigation)
                found = False

                # Try DOM click first (most precise)
                clicked = await self.page.evaluate(f"""
                    () => {{
                        const spans = document.querySelectorAll('span[title]');
                        for (const s of spans) {{
                            const t = (s.getAttribute('title') || '').toLowerCase();
                            if (t.includes({json.dumps(contact.lower())})) {{
                                s.closest('[role="row"], [role="listitem"], li') &&
                                    s.closest('[role="row"], [role="listitem"], li').click();
                                s.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                """)

                if clicked:
                    found = True
                    logger.info(f"Opened chat via span[title] click: {contact!r}")
                else:
                    # Keyboard fallback: navigate to first result and open it
                    logger.info(f"span[title] not found for {contact!r} — using ArrowDown+Enter")
                    await self.page.keyboard.press("ArrowDown")
                    await self.page.wait_for_timeout(400)
                    await self.page.keyboard.press("Enter")
                    found = True   # assume first result opened

                await self.page.wait_for_timeout(1_200)

                # ── Step 3: Find the message input box ────────────────────
                msg_box = await self._find_element(MSG_BOX_SELECTORS, timeout_each=5_000)
                if not msg_box:
                    raise RuntimeError("Message box not found with any known selector")

                await msg_box.click()
                # .type() works on ElementHandle for contenteditable divs
                await msg_box.type(text, delay=30)
                await self.page.wait_for_timeout(400)
                await self.page.keyboard.press("Enter")
                await self.page.wait_for_timeout(700)

                logger.info(f"Message sent to {contact!r}: {text[:60]}")
                await self._log_action("MSG_SENT", f"To: {contact} | {text[:60]}")
                return True

            except Exception as e:
                logger.warning(
                    f"send_message attempt {attempt + 1}/{MAX_RETRIES + 1} failed: {e}"
                )
                if attempt < MAX_RETRIES:
                    await self.page.wait_for_timeout(2_000)

        await self._log_action(
            "MSG_SEND_FAILED", f"To: {contact} after {MAX_RETRIES + 1} attempts"
        )
        return False

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------

    async def create_approval_request(
        self,
        contact: str,
        incoming_text: str,
        suggested_reply: str,
    ) -> str:
        """
        Write a Pending_Approval markdown file with the incoming message and
        a suggested reply for the human operator to review.
        Returns the created filename.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename  = f"WHATSAPP_REPLY_APPROVAL_REQUIRED_{timestamp}.md"
        filepath  = PENDING_DIR / filename

        content = f"""---
title: "WhatsApp Reply — Approval Required"
contact: "{contact}"
received: "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
priority: "P1"
status: "pending_approval"
assigned_to: "human_operator"
classification: "whatsapp_reply"
source: "playwright_whatsapp_mcp"
whatsapp_contact: "{contact}"
whatsapp_draft: true
---

# WhatsApp Reply Approval Required

## Incoming Message
**From:** {contact}

> {incoming_text}

## Suggested Reply
{suggested_reply}

## Approval Actions
- [ ] **Approve** — send the suggested reply as-is
- [ ] **Reject** — do not reply
- [ ] **Modify** — edit the reply above, then approve

## Instructions
To approve this reply:
1. Review the suggested reply above
2. Move this file to the `/Approved/` directory, **OR**
3. Update `status` to `approved` in the frontmatter and save

## Constitutional Requirement
⚠️ **TIER 2 ACTION**: All WhatsApp replies must be approved by the human
operator before sending.  This is enforced by Company_Handbook.md §3.3.
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        await self._log_action(
            "APPROVAL_CREATED",
            f"Contact: {contact} | File: {filename}",
        )
        logger.info(f"Approval request created: {filename}")
        return filename

    async def watch_approvals(self):
        """
        Background loop: poll Approved/ for WHATSAPP_* files and send them.
        Moves sent files to Done/ for audit.
        """
        logger.info("Approval watcher started — polling every %ds", APPROVAL_POLL_SECONDS)
        while True:
            try:
                for approved_file in sorted(APPROVED_DIR.glob("WHATSAPP_REPLY_APPROVAL_REQUIRED_*.md")):
                    await self._send_approved_file(approved_file)
            except Exception as e:
                logger.error(f"Approval watcher error: {e}")
            await asyncio.sleep(APPROVAL_POLL_SECONDS)

    async def _send_approved_file(self, filepath: Path):
        """Parse an approved file and send the reply."""
        try:
            raw = filepath.read_text(encoding="utf-8")

            # Extract frontmatter contact
            contact = "Unknown"
            for line in raw.splitlines():
                if line.startswith("whatsapp_contact:"):
                    contact = line.split(":", 1)[1].strip().strip('"')
                    break

            # Extract suggested reply (content between ## Suggested Reply and ## Approval)
            reply_text = ""
            capture = False
            for line in raw.splitlines():
                if line.strip() == "## Suggested Reply":
                    capture = True
                    continue
                if capture and line.startswith("## "):
                    break
                if capture:
                    reply_text += line + "\n"
            reply_text = reply_text.strip()

            if not reply_text or contact == "Unknown":
                logger.warning(f"Could not parse approved file: {filepath.name}")
                return

            success = await self.send_message(contact, reply_text)

            # Move to Done/
            done_path = DONE_DIR / filepath.name
            filepath.rename(done_path)

            status = "REPLY_SENT" if success else "REPLY_FAILED"
            await self._log_action(status, f"Contact: {contact} | File: {filepath.name}")
            logger.info(f"Approved file processed ({status}): {filepath.name}")

        except Exception as e:
            logger.error(f"Error processing approved file {filepath.name}: {e}")

    # ------------------------------------------------------------------
    # Monitor loop
    # ------------------------------------------------------------------

    async def monitor_and_reply(self):
        """
        Main loop: check for unread messages, apply auto-reply rules,
        create approval requests for everything else.
        """
        logger.info(
            "WhatsApp monitor started — polling every %ds. Ctrl+C to stop.",
            MONITOR_INTERVAL_SECONDS,
        )
        while True:
            try:
                chats = await self.get_unread_chats()
                for chat in chats:
                    contact = chat["contact"]
                    text    = chat["message"]

                    # Check auto-reply rules (case-insensitive keyword match)
                    matched_reply = None
                    for keyword, reply in self.rules.items():
                        if keyword.lower() in text.lower():
                            matched_reply = reply
                            break

                    if matched_reply:
                        await self.send_message(contact, matched_reply)
                    else:
                        # No keyword match — try Groq AI reply
                        from groq_ai import whatsapp_reply as groq_wa
                        ai_reply = groq_wa(contact, text)
                        if ai_reply:
                            logger.info(f"Groq reply for '{contact}': {ai_reply[:60]}")
                            await self.send_message(contact, ai_reply)
                        else:
                            # Groq unavailable — approval flow
                            suggested = (
                                f"Haan bhai! 😊 Abhi thoda busy hun — "
                                "thodi der mein baat karte hain!"
                            )
                            await self.create_approval_request(contact, text, suggested)

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            await asyncio.sleep(MONITOR_INTERVAL_SECONDS)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    async def _log_action(self, action_type: str, message: str):
        """Append a timestamped entry to Logs/whatsapp_actions.log."""
        try:
            entry = (
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                f"| {action_type:<25} | {message}\n"
            )
            with open(ACTION_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.error(f"Could not write action log: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    handler = WhatsAppMCPHandler()

    # ------------------------------------------------------------------
    # --debug-only : connect, dump DOM snapshot, then exit
    # ------------------------------------------------------------------
    if "--debug-only" in sys.argv:
        logger.info("=== Debug-Only Mode ===")
        if not await handler.setup_browser():
            return
        try:
            if not await handler.ensure_connected():
                logger.error("Could not connect.")
                return
            logger.info("Connected — running DOM debug snapshot...")
            await handler.debug_dom()
            logger.info("Debug complete. Check debug_connected.png and debug_connected.txt")
        finally:
            await handler.cleanup()
        return

    # ------------------------------------------------------------------
    # --setup : first-time QR login (saves session for future runs)
    # ------------------------------------------------------------------
    if "--setup" in sys.argv:
        logger.info("=== First-Time Setup Mode ===")
        logger.info("A browser will open.  Scan the QR code with your phone.")
        if not await handler.setup_browser():
            logger.error("Browser setup failed.  Is Playwright installed?")
            logger.error("Run: pip install playwright && playwright install chromium")
            return
        try:
            success = await handler.wait_for_qr_scan()
            if success:
                logger.info("Setup complete.  Run without --setup to start monitoring.")
            else:
                logger.error("Setup did not complete successfully.  Try again.")
        finally:
            await handler.cleanup()
        return

    # ------------------------------------------------------------------
    # --send : quick one-shot message send  (--send "Contact" "Message")
    # ------------------------------------------------------------------
    if "--send" in sys.argv:
        idx = sys.argv.index("--send")
        try:
            contact = sys.argv[idx + 1]
            message = sys.argv[idx + 2]
        except IndexError:
            logger.error('Usage: python whatsapp_mcp.py --send "Contact Name" "Message text"')
            return

        if not await handler.setup_browser():
            return
        try:
            if not await handler.ensure_connected():
                return
            result = await handler.send_message(contact, message)
            logger.info("Send result: %s", "SUCCESS" if result else "FAILED")
        finally:
            await handler.cleanup()
        return

    # ------------------------------------------------------------------
    # Normal operation: monitor + approval watcher running concurrently
    # ------------------------------------------------------------------
    logger.info("=== WhatsApp MCP Server Starting (Normal Mode) ===")

    if not await handler.setup_browser():
        logger.error("Browser setup failed.  Run --setup first.")
        return

    try:
        if not await handler.ensure_connected():
            logger.error("Could not connect to WhatsApp Web.")
            await handler.cleanup()
            return

        logger.info("Connected.  Running DOM debug snapshot...")
        await handler.debug_dom()   # writes debug_connected.png + debug_connected.txt
        logger.info("Connected.  Running monitor + approval watcher concurrently.")

        # Run monitor loop and approval watcher in parallel
        await asyncio.gather(
            handler.monitor_and_reply(),
            handler.watch_approvals(),
        )

    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await handler.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
