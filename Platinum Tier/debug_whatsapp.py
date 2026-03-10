"""
WhatsApp Web — Deep DOM Diagnostic v2
Waits longer, checks iframes, dumps actual chat list innerHTML.
Run: python debug_whatsapp.py
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

PLATINUM_DIR = Path(__file__).resolve().parent
SESSION_FILE = PLATINUM_DIR / "whatsapp_session" / "storage_state.json"
REPORT_FILE  = PLATINUM_DIR / "debug_report.txt"
SHOT_FILE    = PLATINUM_DIR / "debug_screenshot.png"

lines = []

def log(msg=""):
    print(msg)
    lines.append(str(msg))

async def probe_frame(frame, label="main"):
    """Run all selector probes inside a given frame."""
    log(f"\n{'='*60}")
    log(f"FRAME: {label}")
    log(f"{'='*60}")

    # Check chat list
    chat_list = await frame.query_selector('[aria-label="Chat list"]')
    if chat_list:
        log(f"  [FOUND] Chat list container")
        html = await chat_list.inner_html()
        log(f"  innerHTML length: {len(html)} chars")
        log(f"  innerHTML preview (first 800 chars):")
        log(f"  {html[:800]}")

        # Count direct children
        child_count = await frame.evaluate(
            "el => el ? el.children.length : 0",
            await frame.query_selector('[aria-label="Chat list"]')
        )
        log(f"  Direct children: {child_count}")
    else:
        log(f"  [MISS] Chat list NOT found in this frame")

    # All data-testid values
    testids = await frame.evaluate("""
        () => {
            const els = document.querySelectorAll('[data-testid]');
            const seen = new Set();
            for (const el of els) { seen.add(el.getAttribute('data-testid')); }
            return [...seen].slice(0, 60);
        }
    """)
    log(f"\n  data-testid values ({len(testids)} unique):")
    for t in testids:
        log(f"    {t}")

    # All aria-label values
    arialabels = await frame.evaluate("""
        () => {
            const els = document.querySelectorAll('[aria-label]');
            const seen = new Set();
            for (const el of els) {
                const v = el.getAttribute('aria-label');
                if (v) seen.add(v.slice(0, 60));
            }
            return [...seen].slice(0, 40);
        }
    """)
    log(f"\n  aria-label values ({len(arialabels)} unique):")
    for a in arialabels:
        log(f"    {a}")

    # All data-tab values (WhatsApp uses this for input panels)
    datatabs = await frame.evaluate("""
        () => {
            const els = document.querySelectorAll('[data-tab]');
            const hits = [];
            for (const el of els) {
                hits.push({
                    tag: el.tagName,
                    tab: el.getAttribute('data-tab'),
                    role: el.getAttribute('role') || '',
                    ce: el.getAttribute('contenteditable') || ''
                });
            }
            return hits.slice(0, 20);
        }
    """)
    log(f"\n  data-tab elements ({len(datatabs)}):")
    for d in datatabs:
        log(f"    <{d['tag']} data-tab={d['tab']!r} role={d['role']!r} contenteditable={d['ce']!r}>")

    # Any element with 'unread' anywhere
    unread_els = await frame.evaluate("""
        () => {
            const hits = [];
            for (const el of document.querySelectorAll('*')) {
                for (const a of el.getAttributeNames()) {
                    const v = (el.getAttribute(a) || '').toLowerCase();
                    if (v.includes('unread')) {
                        hits.push({
                            tag: el.tagName,
                            attr: a,
                            val: el.getAttribute(a).slice(0, 80),
                            id: el.id || '',
                            cls: el.className.toString().slice(0, 60)
                        });
                        break;
                    }
                }
                if (hits.length >= 20) break;
            }
            return hits;
        }
    """)
    log(f"\n  Elements with 'unread' in attributes ({len(unread_els)}):")
    for u in unread_els:
        log(f"    <{u['tag']} {u['attr']}={u['val']!r} id={u['id']!r}>")

    # Chat-specific: look for any div/li/span that could be a chat row
    chat_rows = await frame.evaluate("""
        () => {
            const candidates = document.querySelectorAll(
                '[aria-label="Chat list"] > *, [aria-label="Chat list"] > * > *'
            );
            const hits = [];
            for (const el of candidates) {
                hits.push({
                    tag: el.tagName,
                    role: el.getAttribute('role') || '',
                    testid: el.getAttribute('data-testid') || '',
                    arialabel: (el.getAttribute('aria-label') || '').slice(0, 40),
                    cls: el.className.toString().slice(0, 60),
                    text: (el.textContent || '').slice(0, 50).trim()
                });
            }
            return hits.slice(0, 10);
        }
    """)
    log(f"\n  Children inside [aria-label='Chat list'] ({len(chat_rows)}):")
    for r in chat_rows:
        log(f"    <{r['tag']} role={r['role']!r} testid={r['testid']!r} aria={r['arialabel']!r} text={r['text']!r}>")

    return bool(chat_list)


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        ctx = await browser.new_context(
            storage_state=str(SESSION_FILE) if SESSION_FILE.exists() else None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await ctx.new_page()

        log("Navigating to WhatsApp Web...")
        await page.goto("https://web.whatsapp.com", timeout=30_000)

        # Wait for any sign of the page
        log("Waiting up to 40s for WhatsApp to load...")
        try:
            await page.wait_for_selector('[aria-label="Chat list"]', timeout=40_000)
            log("Chat list appeared!")
        except PWTimeout:
            log("Chat list not found in 40s")

        # Extra wait for lazy-loaded chats to render
        log("Waiting 8s more for chats to lazy-load...")
        await page.wait_for_timeout(8_000)

        await page.screenshot(path=str(SHOT_FILE))
        log(f"Screenshot: {SHOT_FILE}")

        # ── Check for iframes ───────────────────────────────────────────
        log(f"\n{'='*60}")
        log("IFRAMES ON THE PAGE")
        log(f"{'='*60}")
        frames = page.frames
        log(f"Total frames (including main): {len(frames)}")
        for i, frame in enumerate(frames):
            log(f"  frame[{i}] url={frame.url[:80]!r}")

        # ── Probe main frame ────────────────────────────────────────────
        found_in_main = await probe_frame(page.main_frame, "main frame")

        # ── Probe child iframes if main failed ──────────────────────────
        if not found_in_main:
            for i, frame in enumerate(page.frames[1:], 1):
                found = await probe_frame(frame, f"iframe[{i}] {frame.url[:40]}")
                if found:
                    break

        # ── Page title + URL ────────────────────────────────────────────
        log(f"\n{'='*60}")
        log("PAGE INFO")
        log(f"{'='*60}")
        log(f"  Title : {await page.title()}")
        log(f"  URL   : {page.url}")

        await browser.close()

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nReport saved: {REPORT_FILE}")

asyncio.run(main())
