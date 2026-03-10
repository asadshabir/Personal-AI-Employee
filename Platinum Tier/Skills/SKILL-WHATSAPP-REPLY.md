---
skill_id: SK-WHATSAPP-001
name: WhatsApp Auto-Reply
status: active
tier: 2
trigger: Task tagged #whatsapp or classification == whatsapp_reply or incoming WhatsApp message detected
version: "1.0"
depends_on: [SK-BASE, SK-012]
created: 2026-02-27
updated: 2026-02-27
tags: [skill, social_media, whatsapp, messaging, automation, browser, platinum-tier]
---

# Skill: WhatsApp Auto-Reply

> Inherits all rules from [Skill_Base.md](../../Skills/Skill_Base.md) — Tier enforcement, logging,
> error handling, and halt conditions apply.

---

## Purpose

The WhatsApp Auto-Reply skill enables the AI Employee to monitor WhatsApp Web for incoming messages
and respond automatically using Playwright browser automation.  It uses a keyword-based rules engine
for instant replies, and routes all other messages through the constitutional approval workflow
(Pending_Approval → Approved → send) before any message is dispatched.

This skill is part of the Platinum tier and requires a one-time QR code scan to link the browser
session to the user's WhatsApp account.

### Architecture

```
Phone receives WhatsApp message
        ↓
  WhatsApp Web (browser, kept alive by Playwright)
        ↓
  whatsapp_mcp.py monitor loop (polls every 10s)
        ↓
  ┌─────────────────────┬──────────────────────────────┐
  │ Keyword match?      │ No keyword match              │
  │ ↓                   │ ↓                             │
  │ auto-reply sent     │ Pending_Approval/ draft       │
  │                     │ ↓ Human reviews               │
  │                     │ Move to Approved/             │
  │                     │ ↓ Approval watcher detects    │
  │                     │ Reply sent → Done/            │
  └─────────────────────┴──────────────────────────────┘
```

---

## Inputs

| Input          | Type   | Required | Description |
|----------------|--------|----------|-------------|
| `contact`      | string | Yes      | WhatsApp contact name as it appears in the chat list |
| `message`      | string | Yes      | Incoming message text to respond to |
| `auto_rules`   | dict   | No       | Override keyword→reply map (defaults to whatsapp_auto_reply_rules.json) |
| `suggested_reply` | string | No    | Pre-composed reply to stage in the approval file |

---

## Outputs

| Output             | Type      | Location                                          | Description |
|--------------------|-----------|---------------------------------------------------|-------------|
| Approval Request   | `.md`     | `Pending_Approval/WHATSAPP_REPLY_APPROVAL_REQUIRED_*.md` | Draft awaiting human review |
| Sent Confirmation  | `.md`     | `Done/WHATSAPP_REPLY_APPROVAL_REQUIRED_*.md`      | Moved here after successful send |
| Action Log         | `.log`    | `Logs/whatsapp_actions.log`                       | Full timestamped audit trail |
| Error Screenshot   | `.png`    | `Logs/whatsapp_error_*.png`                       | Captured on failure (if applicable) |

---

## Execution Steps

### Step 1: Ensure WhatsApp Web Connection
- Check `whatsapp_session/storage_state.json` exists
- Load session; verify chat list is accessible
- If not connected, trigger QR scan flow (user must scan phone)

### Step 2: Monitor for Unread Messages
- Poll WhatsApp Web every 10 seconds for unread badges
- Extract contact name and last message text
- Dedup against already-processed messages this session

### Step 3: Apply Auto-Reply Rules
- Load `whatsapp_auto_reply_rules.json`
- Case-insensitive keyword substring match against message text
- If match found → send reply directly (Tier 2 exception for keyword rules)
- Log action to `Logs/whatsapp_actions.log`

### Step 4: Create Approval Request (no keyword match)
- Generate `Pending_Approval/WHATSAPP_REPLY_APPROVAL_REQUIRED_<timestamp>.md`
- Include: contact name, original message, suggested reply, approval instructions
- Log draft creation to action log

### Step 5: Watch for Approvals
- Poll `Approved/` every 5 seconds for `WHATSAPP_REPLY_APPROVAL_REQUIRED_*.md` files
- Parse contact name and reply text from approved file
- Send the reply via WhatsApp Web
- Move file to `Done/`
- Log outcome

---

## Safety Constraints

| Constraint                | Rule |
|---------------------------|------|
| **Tier Enforcement**      | Tier 2 — all non-keyword replies require human approval before sending |
| **Session File Security** | `whatsapp_session/` must be in `.gitignore`; never committed |
| **Rate Limiting**         | Max ~50 messages/hour to avoid WhatsApp account flags |
| **No Bulk Messaging**     | Only reply to messages already received; no unsolicited outreach |
| **Audit Trail**           | Every send, draft, and approval logged to `Logs/whatsapp_actions.log` |
| **Constitutional Compliance** | All messages must comply with Company_Handbook.md governance rules |

---

## Error Handling

| Scenario                    | Code | Response |
|-----------------------------|------|----------|
| Session expired / QR needed | E2   | Trigger QR scan flow; log event |
| Contact not found in search | E2   | Log warning; create escalation note |
| Message send fails (retries exhausted) | E3 | Log REPLY_FAILED; keep file in Approved/ for manual action |
| WhatsApp Web DOM changed    | E3   | Log selector failure; screenshot; escalate |
| Browser crash               | E4   | Restart browser; re-establish session |
| Rules file parse error      | E1   | Fall back to built-in defaults; log warning |

---

## First-Time Setup

### Prerequisites
```bash
pip install playwright>=1.40.0
playwright install chromium
```

### Setup (one-time QR scan)
```bash
cd "AI_Employee_Vault/Platinum Tier"
python whatsapp_mcp.py --setup
```
1. Chrome opens → `web.whatsapp.com` loads
2. QR code appears in the browser window
3. On your phone: WhatsApp → ⋮ → **Linked Devices** → **Link a Device**
4. Scan the QR code
5. Terminal prints `QR scanned successfully!`
6. Session saved to `whatsapp_session/storage_state.json`

### Normal Operation
```bash
python whatsapp_mcp.py
```

### One-Shot Send
```bash
python whatsapp_mcp.py --send "Contact Name" "Message text"
```

---

## Success Criteria

- [ ] Session established without QR scan (session file reused)
- [ ] Unread messages detected and processed within one poll cycle
- [ ] Keyword messages receive instant auto-reply
- [ ] Non-keyword messages create file in `Pending_Approval/`
- [ ] Approved files trigger message send and move to `Done/`
- [ ] All actions logged to `Logs/whatsapp_actions.log`
- [ ] No messages sent without either keyword match or human approval

---

## Integration Points

| Component                     | Role |
|-------------------------------|------|
| `whatsapp_mcp.py`             | Browser automation engine |
| `whatsapp_auto_reply_rules.json` | Editable keyword→reply configuration |
| `whatsapp_session/`           | Persistent browser session (gitignored) |
| `Pending_Approval/`           | Approval queue for non-keyword replies |
| `Approved/`                   | Human-approved replies ready to send |
| `Done/`                       | Archive of sent replies |
| `Logs/whatsapp_actions.log`   | Full audit trail |
| `Company_Handbook.md`         | Constitutional authority |
| `SK-BASE`                     | Inherited skill contract |
| `SK-012 (Task Executor)`      | Called by primary reasoning loop |
