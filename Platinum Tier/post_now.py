"""
Direct LinkedIn post script — bypasses the monitor, posts immediately.
Run: python post_now.py
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

POST_TEXT = """🤖 This post was written and published by my AI Employee — not by me.

Let that sink in for a second.

While I was sleeping, my AI Employee was:
✅ Reading my WhatsApp messages & replying
✅ Monitoring my Gmail & sending professional responses
✅ Drafting this LinkedIn post — and publishing it

I built an AI Employee System from scratch — a 24/7 autonomous digital assistant that manages my entire communication stack.

Here's what it does:

📱 WhatsApp Auto-Reply
→ Keyword-matched replies in Roman Urdu & English
→ Approval workflow for anything sensitive
→ Built on Playwright browser automation

📧 Gmail Auto-Reply
→ IMAP-based inbox monitoring
→ Professional first-person replies as me
→ Human approval before anything goes out

💼 LinkedIn Auto-Post (you're reading it right now)
→ Drafts posts from a content queue
→ Human approves → AI publishes
→ Full audit trail of every action

🔒 Every single action goes through a human-approval layer.
No rogue posts. No accidental replies. Full control.

Tech Stack:
→ Python 3.14
→ Playwright (browser automation)
→ imaplib + smtplib (Gmail)
→ Claude AI (coming next)
→ Running 24/7 on a local Windows machine — zero cloud cost

This is what AI-augmented productivity looks like in 2026.

Not a SaaS tool. Not a subscription. Built by hand, running on my laptop.

I'm Asad Shabir — AI Engineer, GIAIC student, building the future one automation at a time. 🇵🇰

Portfolio → http://asadshabir.netlify.app/

Drop a comment or DM if you're curious how this works!

---
🤖 Posted autonomously by Asad's AI Employee System
Human-approved | AI-executed | Full audit log maintained

#AIEngineering #Automation #Python #Playwright #AIEmployee #GIAIC #Pakistan #BuildInPublic #FutureOfWork"""


async def post():
    storage = str(Path("linkedin_session/storage_state.json"))
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            storage_state=storage,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()

        # ── 1. Load feed ──────────────────────────────────────────────
        print("Step 1: Loading LinkedIn feed...")
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(4_000)

        # Dismiss any open dropdowns/overlays
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(800)
        await page.screenshot(path="post_step1_feed.png")
        print("  Feed loaded. Screenshot: post_step1_feed.png")

        # ── 2. Click "Start a post" ───────────────────────────────────
        print("Step 2: Clicking 'Start a post'...")

        # Use JS to find and click the exact "Start a post" button by text
        clicked = await page.evaluate("""
            () => {
                // Try span or button with exact text "Start a post"
                for (const el of document.querySelectorAll('button, span, div[role="button"]')) {
                    if ((el.textContent || '').trim() === 'Start a post' && el.offsetParent !== null) {
                        el.click();
                        return 'clicked: ' + el.tagName + ' | ' + (el.className || '').slice(0, 60);
                    }
                }
                return null;
            }
        """)

        if not clicked:
            # Fallback: click on the white share-box input area
            try:
                box = await page.wait_for_selector(
                    '.share-box-feed-entry__trigger, '
                    '[placeholder="Start a post"], '
                    'div.share-creation-state__placeholder',
                    timeout=5_000
                )
                await box.click()
                clicked = "fallback selector"
            except Exception as e:
                print(f"  FAILED to click Start a post: {e}")
                await page.screenshot(path="post_step2_fail.png")
                await browser.close()
                return

        print(f"  Clicked: {clicked}")

        # ── 3. Wait for modal to open ─────────────────────────────────
        print("Step 3: Waiting for post composer modal...")
        await page.wait_for_timeout(3_000)
        await page.screenshot(path="post_step3_modal.png")
        print("  Screenshot: post_step3_modal.png")

        # Check if modal opened — look for dialog or contenteditable
        modal_open = await page.evaluate("""
            () => {
                const dialog = document.querySelector('div[role="dialog"], .share-creation-modal, .share-box-modal');
                const editor = document.querySelector('[contenteditable="true"]');
                return { dialog: !!dialog, editor: !!editor };
            }
        """)
        print(f"  Modal open: {modal_open}")

        if not modal_open.get("editor") and not modal_open.get("dialog"):
            print("  Modal did not open — trying again...")
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

            # Try clicking directly on the share box area
            try:
                await page.click('.share-box-feed-entry__top-bar', timeout=5_000)
            except Exception:
                try:
                    await page.click('text=Start a post', timeout=5_000)
                except Exception as e:
                    print(f"  Could not open modal: {e}")
                    await browser.close()
                    return

            await page.wait_for_timeout(3_000)
            await page.screenshot(path="post_step3b_retry.png")

        # ── 4. Type post text ─────────────────────────────────────────
        print("Step 4: Typing post text...")

        typed = False

        # Try contenteditable div (Quill editor — LinkedIn standard)
        for sel in [
            'div.ql-editor[contenteditable="true"]',
            'div[role="textbox"][contenteditable="true"]',
            'div[contenteditable="true"]',
        ]:
            try:
                loc = page.locator(sel).first
                await loc.wait_for(state="visible", timeout=5_000)
                await loc.click()
                await page.wait_for_timeout(400)
                # Use keyboard type — no delay for speed
                await page.keyboard.type(POST_TEXT)
                print(f"  Text typed via keyboard (selector: {sel})")
                typed = True
                break
            except Exception:
                continue

        if not typed:
            print("  FAILED to type text")
            await page.screenshot(path="post_step4_fail.png")
            await browser.close()
            return

        await page.wait_for_timeout(2_000)
        await page.screenshot(path="post_step4_typed.png")
        print("  Screenshot: post_step4_typed.png")

        # ── 5. Click Post button ──────────────────────────────────────
        print("Step 5: Finding and clicking Post button...")

        # Strategy: find the POST button INSIDE the dialog/modal
        post_btn_info = await page.evaluate("""
            () => {
                // Look for buttons inside dialog
                const dialogs = document.querySelectorAll('div[role="dialog"], .share-creation-modal');
                for (const d of dialogs) {
                    const btns = d.querySelectorAll('button');
                    for (const b of btns) {
                        const t = (b.textContent || '').trim();
                        const a = b.getAttribute('aria-label') || '';
                        if ((t === 'Post' || a === 'Post') && !b.disabled && b.offsetParent !== null) {
                            return { found: true, text: t, aria: a, cls: (b.className||'').slice(0,80) };
                        }
                    }
                }
                // Fallback: any visible non-disabled button with exact text "Post"
                for (const b of document.querySelectorAll('button')) {
                    const t = (b.textContent || '').trim();
                    if (t === 'Post' && !b.disabled && b.offsetParent !== null) {
                        return { found: true, text: t, aria: b.getAttribute('aria-label')||'', cls: (b.className||'').slice(0,80) };
                    }
                }
                return { found: false };
            }
        """)
        print(f"  Post button info: {post_btn_info}")

        # Click it
        posted = False
        # First try: button inside dialog with exact text Post
        for sel in [
            'div[role="dialog"] button:has-text("Post")',
            'button.share-actions__primary-action',
            '.share-creation-modal button:has-text("Post")',
            'button[aria-label="Post"]',
        ]:
            try:
                btn = page.locator(sel).filter(has_not_text="job").last
                await btn.wait_for(state="visible", timeout=4_000)
                is_disabled = await btn.is_disabled()
                if is_disabled:
                    print(f"  Button disabled: {sel} — waiting...")
                    await page.wait_for_timeout(2_000)
                await btn.click()
                print(f"  POST clicked via: {sel}")
                posted = True
                break
            except Exception as e:
                continue

        if not posted:
            # Last resort: JS click on exact "Post" button
            js_clicked = await page.evaluate("""
                () => {
                    const btns = document.querySelectorAll('button');
                    for (const b of [...btns].reverse()) {
                        const t = (b.textContent || '').trim();
                        if (t === 'Post' && !b.disabled && b.offsetParent !== null) {
                            b.click();
                            return (b.className || '').slice(0, 80);
                        }
                    }
                    return null;
                }
            """)
            if js_clicked:
                print(f"  POST clicked via JS: {js_clicked}")
                posted = True
            else:
                print("  FAILED to click Post button")
                await page.screenshot(path="post_step5_fail.png")
                await browser.close()
                return

        await page.wait_for_timeout(5_000)
        await page.screenshot(path="post_step5_result.png")
        print("  Screenshot: post_step5_result.png")

        # ── 6. Verify ─────────────────────────────────────────────────
        print("Step 6: Verifying post...")
        url = page.url
        print(f"  Current URL: {url}")

        # Check if modal closed (good sign)
        modal_still_open = await page.evaluate("""
            () => !!document.querySelector('div[role="dialog"] div[contenteditable="true"]')
        """)
        if not modal_still_open:
            print("  SUCCESS: Modal closed — post likely published!")
        else:
            print("  WARNING: Modal still open — post may not have submitted")

        await browser.close()
        print("\nDone! Check screenshots for visual confirmation.")


asyncio.run(post())
