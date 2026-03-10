"""
WhatsApp MCP — Test Suite
Runs 4 tests and reports pass/fail for each.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

PLATINUM_DIR = Path(__file__).resolve().parent
VAULT_ROOT   = PLATINUM_DIR.parent
SESSION_FILE = PLATINUM_DIR / "whatsapp_session" / "storage_state.json"
RULES_FILE   = PLATINUM_DIR / "whatsapp_auto_reply_rules.json"
PENDING_DIR  = VAULT_ROOT / "Pending_Approval"
APPROVED_DIR = VAULT_ROOT / "Approved"
DONE_DIR     = VAULT_ROOT / "Done"

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def section(title):
    print(f"\n{'-'*55}")
    print(f"  {title}")
    print(f"{'-'*55}")

def report(name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append((name, passed))
    print(f"  {status}  {name}")
    if detail:
        print(f"         {detail}")

# ──────────────────────────────────────────────────────────
# TEST 1 — Session file
# ──────────────────────────────────────────────────────────
section("TEST 1 — Session File Validity")
try:
    with open(SESSION_FILE, encoding="utf-8") as f:
        data = json.load(f)
    cookies = data.get("cookies", [])
    origins = data.get("origins", [])
    has_wa   = any("whatsapp" in c.get("domain","") for c in cookies)
    report("Session file exists",    SESSION_FILE.exists(),
           f"Path: {SESSION_FILE}")
    report("Session file is valid JSON", True,
           f"Cookies: {len(cookies)}, Origins: {len(origins)}")
    report("WhatsApp cookies present", has_wa,
           "domain=.whatsapp.com found" if has_wa else "WARNING: No WhatsApp cookies -- may need re-login")
    size_kb = SESSION_FILE.stat().st_size // 1024
    report("Session file size > 1 KB", size_kb >= 1,
           f"Size: {size_kb} KB")
except Exception as e:
    report("Session file check", False, str(e))

# ──────────────────────────────────────────────────────────
# TEST 2 — Auto-reply rules
# ──────────────────────────────────────────────────────────
section("TEST 2 — Auto-Reply Rules")
try:
    sys.path.insert(0, str(PLATINUM_DIR))
    from whatsapp_mcp import load_rules, WhatsAppMCPHandler

    rules = load_rules()
    report("Rules file loads without error", True,
           f"File: {RULES_FILE.name}")
    report("Rules contain entries", len(rules) > 0,
           f"{len(rules)} keywords loaded")

    # Check keyword matching logic
    test_cases = [
        ("hello world",       "hello",    True),
        ("Hi there!",         "hi",       True),
        ("What is the PRICE?","price",     True),
        ("random question",   "NOMATCH",  False),
    ]
    all_match = True
    for msg, keyword, should_match in test_cases:
        matched = any(k.lower() in msg.lower() for k in rules)
        ok = matched == should_match
        if not ok:
            all_match = False
        lbl = "match" if should_match else "no-match"
        report(f'Keyword rule: "{msg[:25]}" → {lbl}', ok)

except Exception as e:
    report("Rules / import check", False, str(e))

# ──────────────────────────────────────────────────────────
# TEST 3 — Approval workflow (file-system only, no browser)
# ──────────────────────────────────────────────────────────
section("TEST 3 — Approval Workflow (file-system)")
try:
    async def test_approval_workflow():
        handler = WhatsAppMCPHandler()

        # Manually create an approval request
        fname = await handler.create_approval_request(
            contact        = "Test Contact",
            incoming_text  = "What are your services?",
            suggested_reply= "Thank you for asking! I'll get back to you with full details shortly.",
        )

        pending_path = PENDING_DIR / fname
        report("Approval file created in Pending_Approval/", pending_path.exists(),
               str(pending_path))

        # Verify file content
        content = pending_path.read_text(encoding="utf-8")
        has_contact = "Test Contact" in content
        has_reply   = "Thank you for asking" in content
        has_tier    = "TIER 2" in content
        report("File contains contact name",   has_contact)
        report("File contains suggested reply", has_reply)
        report("File contains Tier 2 warning", has_tier)

        # Simulate human approval: move to Approved/
        APPROVED_DIR.mkdir(exist_ok=True)
        approved_path = APPROVED_DIR / fname
        pending_path.rename(approved_path)
        report("File moved to Approved/ (simulated human approval)",
               approved_path.exists() and not pending_path.exists())

        return fname

    fname = asyncio.run(test_approval_workflow())

except Exception as e:
    report("Approval workflow", False, str(e))

# ──────────────────────────────────────────────────────────
# TEST 4 — Browser connection check (headless, session reuse)
# ──────────────────────────────────────────────────────────
section("TEST 4 — Browser Connection (session reuse)")
try:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    async def test_browser_connection():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx     = await browser.new_context(
                storage_state=str(SESSION_FILE),
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await ctx.new_page()

            report("Browser launched (headless)", True)
            report("Session loaded into context", True,
                   f"From: {SESSION_FILE.name}")

            # Navigate to WhatsApp Web
            await page.goto("https://web.whatsapp.com", timeout=30_000)
            await page.wait_for_load_state("domcontentloaded")
            current_url = page.url
            report("WhatsApp Web page loaded", "whatsapp.com" in current_url,
                   f"URL: {current_url}")

            # Check title
            title = await page.title()
            report("Page has WhatsApp title", "WhatsApp" in title,
                   f"Title: {title!r}")

            # Check for chat list OR QR code (tells us if session is active)
            try:
                await page.wait_for_selector(
                    '[aria-label="Chat list"]', timeout=12_000
                )
                report("Session active -- Chat list visible", True,
                       "WhatsApp Web is fully connected using saved session")
                connected = True
            except PWTimeout:
                # Check if QR code appeared (session expired)
                try:
                    await page.wait_for_selector("canvas", timeout=5_000)
                    report("Session active -- Chat list visible", False,
                           "WARNING: QR code appeared -- session expired, run --setup again")
                except PWTimeout:
                    report("Session active -- Chat list visible", False,
                           "WARNING: Neither chat list nor QR found -- check network")
                connected = False

            await browser.close()
            return connected

    connected = asyncio.run(test_browser_connection())

except Exception as e:
    report("Browser connection check", False, str(e))

# ──────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────
section("SUMMARY")
passed = sum(1 for _, ok in results if ok)
total  = len(results)
pct    = int(passed / total * 100) if total else 0
print(f"\n  Results: {passed}/{total} passed ({pct}%)")
print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

for name, ok in results:
    icon = "[PASS]" if ok else "[FAIL]"
    print(f"  {icon}  {name}")

print()
if passed == total:
    print("  [OK] ALL TESTS PASSED -- ready to run: python whatsapp_mcp.py")
elif any(n == "Session active -- Chat list visible" and ok for n, ok in results):
    print("  [OK] MOSTLY PASSING -- WhatsApp connected, minor issues above")
else:
    print("  [!!] ISSUES FOUND -- review failures above before running monitor")
print()
