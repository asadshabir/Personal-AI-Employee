"""
LinkedIn MCP Handler — Platinum Tier
Playwright-based LinkedIn automation with:
  - Session-persisted login (one-time manual login, then auto)
  - Human-approval workflow (Pending_Approval → Approved → Post)
  - Approval watcher loop (auto-posts when you move file to Approved/)
  - Post scheduler (linkedin_post_queue.json)
  - Full audit logging
  - Tier 2 enforcement (all posts require human approval)
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
# Paths
# ---------------------------------------------------------------------------
PLATINUM_DIR = Path(__file__).resolve().parent
VAULT_ROOT   = PLATINUM_DIR.parent

SESSION_DIR     = PLATINUM_DIR / "linkedin_session"
LOGS_DIR        = VAULT_ROOT / "Logs"
PENDING_DIR     = VAULT_ROOT / "Pending_Approval"
APPROVED_DIR    = VAULT_ROOT / "Approved"
DONE_DIR        = VAULT_ROOT / "Done"
QUEUE_FILE      = PLATINUM_DIR / "linkedin_post_queue.json"
ACTION_LOG_FILE = LOGS_DIR / "linkedin_actions.log"

for d in (SESSION_DIR, LOGS_DIR, PENDING_DIR, APPROVED_DIR, DONE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("linkedin_mcp")


def action_log(event: str, detail: str = "") -> None:
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {event:<30} | {detail[:120]}\n"
    try:
        ACTION_LOG_FILE.open("a", encoding="utf-8").write(line)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Selectors — fallback lists, first match wins
# ---------------------------------------------------------------------------
# LinkedIn post composer — confirmed live selector (debug 2026-03-03)
POST_BOX_SELECTORS = [
    'div.ql-editor[contenteditable="true"]',           # confirmed live
    'div[role="textbox"][contenteditable="true"]',
    'div[contenteditable="true"][data-placeholder]',
    'div[contenteditable="true"]',
]

# "Start a post" trigger — use JS text match (avoids wrong button)
# Confirmed: button text = "Start a post", aria = "", cls = artdeco-button--muted
START_POST_SELECTORS = [
    '__JS_TEXT_CLICK__',                               # handled specially in post_to_linkedin
    'button.share-box-feed-entry__trigger',
    '.share-box-feed-entry__top-bar',
    'button:has-text("Start a post")',
]

# Final "Post" submit — confirmed live: share-actions__primary-action (2026-03-03)
SUBMIT_POST_SELECTORS = [
    'div[role="dialog"] button:has-text("Post")',      # confirmed live — inside dialog only
    'button.share-actions__primary-action',            # confirmed live class
    'button[aria-label="Post"]',
]

# Image upload button
IMAGE_UPLOAD_SELECTORS = [
    'button[aria-label="Add a photo"]',
    'button[aria-label="Add photos/videos"]',
    'button[aria-label="Add visual media"]',
    'button[aria-label*="photo"]',
    'button[aria-label*="image"]',
    'button[aria-label*="media"]',
]


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------
class LinkedInMCPHandler:

    def __init__(self):
        self.playwright = None
        self.browser    = None
        self.context    = None
        self.page       = None
        self.max_retries = 2

    # ------------------------------------------------------------------
    # Browser setup
    # ------------------------------------------------------------------
    async def setup_browser(self, headless: bool = False) -> bool:
        try:
            self.playwright = await async_playwright().start()
            storage = str(SESSION_DIR / "storage_state.json")

            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-blink-features=AutomationControlled"],
            )
            self.context = await self.browser.new_context(
                storage_state=storage if Path(storage).exists() else None,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            self.page = await self.context.new_page()
            self.page.on("crash", lambda: logger.error("Page crashed"))
            logger.info("Browser setup complete")
            return True
        except Exception as e:
            logger.error(f"Browser setup error: {e}")
            return False

    async def save_session(self) -> None:
        try:
            await self.context.storage_state(
                path=str(SESSION_DIR / "storage_state.json")
            )
            logger.info("Session saved to linkedin_session/storage_state.json")
        except Exception as e:
            logger.error(f"Could not save session: {e}")

    async def cleanup(self) -> None:
        try:
            if self.context:
                await self.save_session()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Login / connection check
    # ------------------------------------------------------------------
    async def ensure_connected(self) -> bool:
        """Return True if already logged in, else open login page and wait."""
        try:
            await self.page.goto(
                "https://www.linkedin.com/feed/",
                timeout=30_000,
                wait_until="domcontentloaded",
            )
            await self.page.wait_for_timeout(3_000)

            url = self.page.url
            if "feed" in url or "mynetwork" in url:
                logger.info("Already logged in to LinkedIn")
                action_log("LI_CONNECTED", "Session valid")
                return True

            # Not logged in — open login page
            logger.info("Session expired or not logged in — opening login page")
            await self.page.goto(
                "https://www.linkedin.com/login",
                timeout=30_000,
                wait_until="domcontentloaded",
            )
            logger.info("Please log in to LinkedIn in the browser window (up to 120s)...")

            # Wait for redirect to feed after successful login
            await self.page.wait_for_url(
                re.compile(r"linkedin\.com/(feed|mynetwork|in/)"),
                timeout=120_000,
            )
            await self.save_session()
            action_log("LI_LOGIN_SUCCESS", "Manual login completed, session saved")
            logger.info("Login successful! Session saved.")
            return True

        except PWTimeoutError:
            logger.error("Login timeout — please run --setup again")
            return False
        except Exception as e:
            logger.error(f"ensure_connected error: {e}")
            return False

    # ------------------------------------------------------------------
    # First-time setup
    # ------------------------------------------------------------------
    async def run_setup(self) -> bool:
        logger.info("=== LinkedIn First-Time Setup ===")
        logger.info("A browser will open. Log in to LinkedIn manually.")
        logger.info("Once you see your LinkedIn feed, the session will save automatically.")

        if not await self.setup_browser(headless=False):
            return False

        result = await self.ensure_connected()
        await self.cleanup()
        return result

    # ------------------------------------------------------------------
    # Create draft post (Pending_Approval)
    # ------------------------------------------------------------------
    async def create_draft_post(self, text: str, title: str = "",
                                 image_path: str = "") -> Path:
        ts       = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        slug     = re.sub(r"\W+", "_", (title or text[:30]).strip())[:40]
        filename = f"LINKEDIN_POST_APPROVAL_REQUIRED_{ts}_{slug}.md"
        path     = PENDING_DIR / filename

        content = f"""---
title: "{title or text[:60]}"
created: "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
priority: "P2"
status: "pending_approval"
assigned_to: "human_operator"
classification: "linkedin_post"
image_path: "{image_path}"
---

# LinkedIn Post — Approval Required

## Post Content

{text}

## Meta
- **Image:** {image_path if image_path else 'None'}
- **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Approval Actions
- [ ] **Approve** — move this file to `/Approved/` directory
- [ ] **Reject** — delete this file
- [ ] **Modify** — edit the Post Content above, then move to `/Approved/`

## Constitutional Requirement
All LinkedIn posts require human approval before publication. (Company_Handbook §3.3)
"""
        path.write_text(content, encoding="utf-8")
        logger.info(f"Draft created: {filename}")
        action_log("LI_DRAFT_CREATED", f"File: {filename} | Text: {text[:60]}")
        return path

    # ------------------------------------------------------------------
    # Post to LinkedIn (Playwright)
    # ------------------------------------------------------------------
    async def post_to_linkedin(self, text: str, image_path: str = "") -> bool:
        for attempt in range(self.max_retries + 1):
            try:
                # Fresh navigation to feed
                await self.page.goto(
                    "https://www.linkedin.com/feed/",
                    timeout=30_000,
                    wait_until="domcontentloaded",
                )
                await self.page.wait_for_timeout(3_000)

                # Dismiss any open dropdowns/overlays
                await self.page.keyboard.press("Escape")
                await self.page.wait_for_timeout(800)

                # Click "Start a post" — use JS text match (most reliable)
                triggered = False
                clicked = await self.page.evaluate("""
                    () => {
                        for (const el of document.querySelectorAll('button, span, div[role="button"]')) {
                            if ((el.textContent || '').trim() === 'Start a post' && el.offsetParent !== null) {
                                el.click();
                                return el.tagName + ':' + (el.className||'').slice(0,40);
                            }
                        }
                        return null;
                    }
                """)
                if clicked:
                    triggered = True
                    logger.info(f"Post composer opened via JS text click: {clicked}")
                else:
                    for sel in [s for s in START_POST_SELECTORS if s != '__JS_TEXT_CLICK__']:
                        try:
                            btn = await self.page.wait_for_selector(sel, timeout=4_000)
                            await btn.click()
                            triggered = True
                            logger.info(f"Post composer opened via: {sel}")
                            break
                        except Exception:
                            continue

                if not triggered:
                    logger.error("Could not open post composer")
                    await self._screenshot(f"composer_fail_attempt{attempt}")
                    if attempt < self.max_retries:
                        await self.page.wait_for_timeout(3_000)
                        continue
                    return False

                # Wait for modal to fully render
                await self.page.wait_for_timeout(3_000)

                # Find textbox — try multiple strategies
                box_found = False

                # Strategy 1: locator-based (more reliable than wait_for_selector)
                MODAL_BOX_SELS = [
                    'div.ql-editor[contenteditable="true"]',
                    'div[role="textbox"][contenteditable="true"]',
                    'div[role="textbox"]',
                    'div[contenteditable="true"][data-placeholder]',
                    'div[contenteditable="true"]',
                ]
                for sel in MODAL_BOX_SELS:
                    try:
                        loc = self.page.locator(sel).first
                        await loc.wait_for(state="visible", timeout=6_000)
                        await loc.click()
                        await self.page.wait_for_timeout(500)
                        # Use JS execCommand to insert text instantly (no timeout risk)
                        await self.page.evaluate(
                            "(text) => document.execCommand('insertText', false, text)",
                            text
                        )
                        logger.info(f"Text inserted via execCommand (selector: {sel})")
                        box_found = True
                        break
                    except Exception:
                        continue

                # Strategy 2: JS direct focus + type via keyboard
                if not box_found:
                    logger.warning("execCommand strategy failed — trying keyboard type")
                    try:
                        await self.page.evaluate("""
                            () => {
                                const boxes = document.querySelectorAll('[contenteditable="true"]');
                                for (const b of boxes) {
                                    const r = b.getBoundingClientRect();
                                    if (r.width > 200 && r.height > 50) { b.focus(); return true; }
                                }
                                return false;
                            }
                        """)
                        await self.page.wait_for_timeout(300)
                        await self.page.keyboard.type(text)  # no delay = fast
                        box_found = True
                        logger.info("Text typed via keyboard fallback")
                    except Exception as e:
                        logger.error(f"Keyboard fallback failed: {e}")

                if not box_found:
                    logger.error("Could not input post text")
                    await self._screenshot(f"textbox_fail_attempt{attempt}")
                    if attempt < self.max_retries:
                        await self.page.wait_for_timeout(3_000)
                        continue
                    return False

                # Upload image if provided
                if image_path and Path(image_path).exists():
                    await self._upload_image(image_path)

                await self.page.wait_for_timeout(2_000)

                # Click Post submit — confirmed: share-actions__primary-action inside dialog
                posted = False
                for sel in SUBMIT_POST_SELECTORS:
                    try:
                        loc = self.page.locator(sel).last
                        await loc.wait_for(state="visible", timeout=5_000)
                        if not await loc.is_disabled():
                            await loc.click()
                            posted = True
                            logger.info(f"Post submitted via: {sel}")
                            break
                    except Exception:
                        continue

                if not posted:
                    # JS fallback: click exact "Post" button (last visible, not disabled)
                    js_cls = await self.page.evaluate("""
                        () => {
                            const btns = [...document.querySelectorAll('button')].reverse();
                            for (const b of btns) {
                                if ((b.textContent||'').trim() === 'Post' && !b.disabled && b.offsetParent) {
                                    b.click(); return (b.className||'').slice(0,60);
                                }
                            }
                            return null;
                        }
                    """)
                    if js_cls:
                        posted = True
                        logger.info(f"Post submitted via JS fallback: {js_cls}")

                if not posted:
                    logger.error("Post submit button not found")
                    await self._screenshot(f"submit_fail_attempt{attempt}")
                    if attempt < self.max_retries:
                        await self.page.wait_for_timeout(3_000)
                        continue
                    return False

                await self.page.wait_for_timeout(4_000)
                action_log("LI_POST_SUCCESS", f"Text: {text[:80]}")
                return True

            except Exception as e:
                logger.error(f"post_to_linkedin error (attempt {attempt+1}): {e}")
                if attempt < self.max_retries:
                    await self.page.wait_for_timeout(3_000)
                else:
                    action_log("LI_POST_FAILED", str(e)[:120])
                    return False

        return False

    async def _upload_image(self, image_path: str) -> None:
        for sel in IMAGE_UPLOAD_SELECTORS:
            try:
                btn = await self.page.wait_for_selector(sel, timeout=5_000)
                await btn.click()
                fi  = await self.page.wait_for_selector('input[type="file"]', timeout=5_000)
                await fi.set_input_files(image_path)
                await self.page.wait_for_timeout(2_000)
                logger.info(f"Image uploaded: {image_path}")
                return
            except Exception:
                continue
        logger.warning(f"Could not upload image: {image_path}")

    async def _screenshot(self, name: str) -> None:
        try:
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = LOGS_DIR / f"linkedin_error_{name}_{ts}.png"
            await self.page.screenshot(path=str(path))
            logger.info(f"Screenshot: {path}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Approval watcher — watches Approved/ for LINKEDIN_POST_*.md
    # ------------------------------------------------------------------
    async def watch_approvals(self) -> None:
        logger.info("Approval watcher started — polling every 15s")
        while True:
            try:
                for md_file in sorted(
                    APPROVED_DIR.glob("LINKEDIN_POST_APPROVAL_REQUIRED_*.md")
                ):
                    await self._process_approved_post(md_file)
            except Exception as e:
                logger.error(f"Approval watcher error: {e}")
            await asyncio.sleep(15)

    async def _process_approved_post(self, md_file: Path) -> None:
        try:
            raw  = md_file.read_text(encoding="utf-8")

            # Extract post content between "## Post Content" and "## Meta"
            text_match = re.search(
                r"## Post Content\s*\n(.+?)\n## Meta",
                raw, re.S
            )
            img_match = re.search(r'^image_path:\s*"(.+?)"', raw, re.M)

            if not text_match:
                logger.warning(f"Cannot parse post content from: {md_file.name}")
                return

            text       = text_match.group(1).strip()
            image_path = (img_match.group(1) if img_match else "").strip()
            image_path = "" if image_path in ("None", "") else image_path

            logger.info(f"Processing approved post: {md_file.name}")

            if not await self.ensure_connected():
                logger.error("Not connected to LinkedIn — skipping post")
                return

            success = await self.post_to_linkedin(text, image_path)

            if success:
                done_path = DONE_DIR / md_file.name
                md_file.rename(done_path)
                logger.info(f"Post published! Moved to Done/: {md_file.name}")
                action_log("LI_APPROVED_POSTED", f"File: {md_file.name}")
            else:
                logger.error(f"Post failed for: {md_file.name}")

        except Exception as e:
            logger.error(f"_process_approved_post error ({md_file.name}): {e}")

    # ------------------------------------------------------------------
    # Post queue scheduler
    # ------------------------------------------------------------------
    async def run_queue(self) -> None:
        """
        Reads linkedin_post_queue.json and creates draft approval files
        for any posts whose scheduled time has passed.

        Queue format:
        [
          {
            "title": "My post title",
            "text": "Post content here...",
            "image_path": "",
            "scheduled_for": "2026-03-03 09:00",
            "status": "pending"
          }
        ]
        """
        logger.info("Post queue scheduler started — checking every 60s")
        while True:
            try:
                if QUEUE_FILE.exists():
                    with QUEUE_FILE.open(encoding="utf-8") as f:
                        queue = json.load(f)

                    changed = False
                    now     = datetime.now()

                    for item in queue:
                        if item.get("status") != "pending":
                            continue
                        scheduled = item.get("scheduled_for", "")
                        if not scheduled:
                            # No schedule — create draft immediately
                            pass
                        else:
                            try:
                                sched_dt = datetime.strptime(scheduled, "%Y-%m-%d %H:%M")
                                if sched_dt > now:
                                    continue  # Not yet
                            except ValueError:
                                pass

                        # Time to draft this post
                        await self.create_draft_post(
                            text=item.get("text", ""),
                            title=item.get("title", ""),
                            image_path=item.get("image_path", ""),
                        )
                        item["status"] = "drafted"
                        changed = True

                    if changed:
                        with QUEUE_FILE.open("w", encoding="utf-8") as f:
                            json.dump(queue, f, indent=2, ensure_ascii=False)

            except Exception as e:
                logger.error(f"Queue scheduler error: {e}")

            await asyncio.sleep(60)

    # ------------------------------------------------------------------
    # Main monitor (approval watcher + queue)
    # ------------------------------------------------------------------
    async def run_monitor(self) -> None:
        if not await self.setup_browser(headless=False):
            logger.error("Browser setup failed")
            return

        if not await self.ensure_connected():
            logger.error("LinkedIn login failed")
            await self.cleanup()
            return

        logger.info("LinkedIn MCP running — watching Approved/ + queue. Ctrl+C to stop.")

        try:
            await asyncio.gather(
                self.watch_approvals(),
                self.run_queue(),
            )
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        finally:
            await self.cleanup()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
async def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--monitor"

    if mode == "--setup":
        # First-time login
        handler = LinkedInMCPHandler()
        ok = await handler.run_setup()
        if ok:
            logger.info("Setup complete! Run without --setup to start monitoring.")
        else:
            logger.error("Setup failed. Try again.")

    elif mode == "--post":
        # Quick post: python linkedin_mcp.py --post "Your post text here"
        if len(sys.argv) < 3:
            print("Usage: python linkedin_mcp.py --post \"Post text here\"")
            return
        text = sys.argv[2]
        handler = LinkedInMCPHandler()
        path = await handler.create_draft_post(text=text)
        print(f"Draft created: {path}")
        print(f"Move to Approved/ folder to publish.")

    elif mode == "--monitor":
        # Normal operation — watch approvals + queue
        handler = LinkedInMCPHandler()
        await handler.run_monitor()

    else:
        print("Usage:")
        print("  python linkedin_mcp.py --setup      # First-time login")
        print("  python linkedin_mcp.py --post \"text\" # Create draft post")
        print("  python linkedin_mcp.py --monitor    # Start monitor (default)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("LinkedIn MCP stopped.")
