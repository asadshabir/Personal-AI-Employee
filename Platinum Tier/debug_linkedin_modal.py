"""Debug script — find exact LinkedIn modal selectors"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def debug_post():
    storage = str(Path("linkedin_session/storage_state.json"))
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(
            storage_state=storage,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()

        # Step 1
        print("Step 1: Loading feed...")
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

        # Step 2: open composer
        print("Step 2: Opening post composer...")
        opened = False
        for sel in [
            'button[aria-label*="post"]',
            'div[role="button"]:has-text("Start a post")',
            'span:has-text("Start a post")',
            '.share-box-feed-entry__trigger',
        ]:
            try:
                btn = await page.wait_for_selector(sel, timeout=4000)
                await btn.click()
                print(f"  Opened via: {sel}")
                opened = True
                break
            except Exception:
                continue

        if not opened:
            print("  FAILED to open composer")
            await page.screenshot(path="debug_fail.png")
            await browser.close()
            return

        await page.wait_for_timeout(4000)
        await page.screenshot(path="debug_modal_open.png")
        print("  Screenshot saved: debug_modal_open.png")

        # Step 3: dump all buttons
        print("\nStep 3: All buttons in DOM:")
        btns = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll("button").forEach(b => {
                    const t = (b.textContent || "").trim().slice(0, 40);
                    const a = b.getAttribute("aria-label") || "";
                    const c = (b.className || "").slice(0, 60);
                    const vis = b.offsetParent !== null;
                    results.push({t, a, c, vis});
                });
                return results;
            }
        """)
        for b in btns:
            if b["vis"]:
                print(f"  VISIBLE | text={repr(b['t']):<30} aria={repr(b['a']):<35} cls={repr(b['c'])[:50]}")

        # Step 4: all contenteditable
        print("\nStep 4: Contenteditable elements:")
        editors = await page.evaluate("""
            () => {
                const els = document.querySelectorAll("[contenteditable='true']");
                return [...els].map(e => ({
                    tag: e.tagName,
                    role: e.getAttribute("role") || "",
                    cls: (e.className || "").slice(0, 80),
                    visible: e.offsetParent !== null,
                    placeholder: e.getAttribute("data-placeholder") || e.getAttribute("aria-placeholder") || ""
                }));
            }
        """)
        for e in editors:
            print(f"  {e['tag']} role={repr(e['role'])} visible={e['visible']} placeholder={repr(e['placeholder'])} cls={repr(e['cls'][:60])}")

        # Step 5: look specifically for share/post modal elements
        print("\nStep 5: Share modal specific elements:")
        modal_info = await page.evaluate("""
            () => {
                const info = {};
                // Modal container
                const modal = document.querySelector('.share-creation-modal, [data-view-name*="share"], .share-box-modal, div[role="dialog"]');
                info.modal = modal ? modal.tagName + ' class=' + (modal.className||"").slice(0,60) : "NOT FOUND";

                // Post button specifically
                const postBtns = [...document.querySelectorAll("button")].filter(b =>
                    (b.textContent||"").trim() === "Post" && b.offsetParent !== null
                );
                info.exactPostBtns = postBtns.map(b => ({
                    text: (b.textContent||"").trim(),
                    aria: b.getAttribute("aria-label") || "",
                    cls: (b.className||"").slice(0,80),
                    disabled: b.disabled
                }));
                return info;
            }
        """)
        print(f"  Modal: {modal_info['modal']}")
        print(f"  Exact 'Post' buttons ({len(modal_info['exactPostBtns'])}):")
        for b in modal_info["exactPostBtns"]:
            print(f"    text={repr(b['text'])} aria={repr(b['aria'])} disabled={b['disabled']} cls={repr(b['cls'])[:60]}")

        print("\nDone. Check debug_modal_open.png for visual confirmation.")
        await page.wait_for_timeout(3000)
        await browser.close()

asyncio.run(debug_post())
