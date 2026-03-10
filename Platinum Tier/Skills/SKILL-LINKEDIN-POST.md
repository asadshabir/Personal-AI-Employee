---
skill_id: SK-LINKEDIN-POST-001
name: LinkedIn Browser Post Creator
status: active
tier: 2
trigger: Task requires creating a LinkedIn post using browser automation
version: "1.0"
depends_on: [SK-BASE, SK-012]
created: 2026-02-22
updated: 2026-02-22
tags: [skill, social_media, linkedin, posting, automation, browser]
---

# Skill: LinkedIn Browser Post Creator

> Inherits all rules from [Skill_Base.md](../../Skills/Skill_Base.md) — Tier enforcement, logging, error handling, and halt conditions apply.

---

## Purpose

The LinkedIn Browser Post Creator skill enables the AI Employee to create professional LinkedIn posts using Playwright browser automation. This skill follows constitutional safety protocols by creating draft posts in the Pending_Approval directory that require human approval before publication.

This skill is part of the Platinum tier LinkedIn integration requirements and enables professional social media automation while maintaining governance and approval processes.

### Relationship to Platinum Tier Requirements

```
AI Employee → [SK-LINKEDIN-POST-001] → Playwright MCP Server → LinkedIn Browser → Professional Post
     │                                    │
     │                                    └── Drafts to Pending_Approval/
     │
     └── MCP Server (linkedin_mcp.py) handles browser automation
```

---

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | The content of the LinkedIn post |
| `image_path` | string | No | Path to image file to include in the post |
| `title` | string | No | Title for the draft file (defaults to "LinkedIn Post Draft") |
| `task_context` | string | No | Context from the original task requesting the LinkedIn post |

---

## Outputs

| Output | Type | Location | Description |
|--------|------|----------|-------------|
| Success Response | dict | JSON | Confirmation of draft creation |
| Draft File | `.md` file | `/Pending_Approval/LINKEDIN_POST_APPROVAL_REQUIRED_*.md` | Draft post awaiting approval |
| Success Log | `.md` file | `/Done/LINKEDIN_POST_LOG_*.md` | Log file when post is successfully published |
| Action Log | `.log` file | `/Logs/linkedin_actions.log` | Timestamped action log |
| Error Screenshot | `.png` file | `/Logs/linkedin_error_*.png` | Screenshot on failure |

---

## Execution Steps

### Step 1: Validate Request

**Action:** Check if the request is valid and properly formatted.

- Verify `text` parameter is provided and not empty
- Validate `image_path` exists if provided
- Check if user has permissions for LinkedIn operations (Tier 2 approval required for posting)

**Validation Checklist:**

```
1.1 Post text content provided?              → Yes / No
1.2 Text content not empty?                 → Yes / No
1.3 Image path valid if provided?           → Yes / No
1.4 Constitutional boundaries respected?    → Yes / No
1.5 Human approval pathway defined?         → Yes / No
```

**If validation fails:** Return error with specific details about what's missing or invalid.

---

### Step 2: Create Draft Content for Approval

**Action:** Create a draft LinkedIn post in the Pending_Approval directory.

The skill creates a markdown file with the following structure:

- Contains the proposed post content
- Includes all necessary metadata for approval
- Follows the constitutional requirement for human oversight
- Provides clear approval/rejection instructions

**Draft File Structure:**
```markdown
---
title: "LinkedIn Post Draft"
requester: "system"
received: "YYYY-MM-DD HH:MM:SS"
priority: "P2"
status: "pending_approval"
assigned_to: "human_operator"
classification: "linkedin_post"
linkedin_draft: true
---

# LinkedIn Post Approval Required

## Post Content
[Original post content]

## Additional Information
- **Image Path**: [if provided]
- **Created**: YYYY-MM-DD HH:MM:SS
- **Status**: Awaiting human approval for LinkedIn posting

## Approval Actions
- [ ] Approve and post to LinkedIn
- [ ] Reject and cancel
- [ ] Modify content before posting

## Instructions
To approve this post, move this file to the `/Approved` directory or update the status to 'approved'.
```

---

### Step 3: Execute Browser Automation

**Action:** Communicate with the Playwright-based linkedin_mcp_server.py.

- Format the request in MCP-compliant format
- Send draft request to the MCP server endpoint
- Wait for and validate the response
- Handle browser automation errors gracefully

**MCP Protocol:**
```
Request: { "action": "draft_post", "params": { "text": "...", "image_path": "...", "title": "..." } }
Response: { "success": true, "data": { "draft_file": "filename" }, "message": "..." }
```

---

### Step 4: Process Browser Response

**Action:** Handle the response from the LinkedIn MCP server.

Process based on response type:

| Response Type | Action |
|---------------|--------|
| **Success** | Log success, create draft file in Pending_Approval |
| **Browser Error** | Log error, retry if appropriate, escalate if persistent |
| **Connection Error** | Check browser, notify user, escalate if needed |
| **Authentication Error** | Check session, refresh if needed, escalate |
| **Content Violation** | Check for policy violations, suggest alternatives |

**Response Validation:**
- Verify that the response format is correct
- Check for LinkedIn-specific error messages
- Validate that the draft file was created successfully

---

### Step 5: Update Task File with Results

**Action:** Write the results back to the task file.

Append to the task body:

```markdown
## LinkedIn Integration Result

- **Action:** LinkedIn post draft created
- **Status:** Draft awaiting approval
- **Draft File:** <filename in Pending_Approval>
- **Processed:** <YYYY-MM-DD HH:mm>

### Draft Details
<Summary of draft created>

### Next Steps
- Manual: Review and approve the post in Pending_Approval directory
- Or: Task complete - awaiting human approval
```

**Frontmatter Updates:**
```yaml
linkedin_result: draft_created
linkedin_draft_file: <filename>
last_linkedin_action: draft
```

---

### Step 6: Monitor for Approval (Optional)

**Action:** If the system is configured to monitor for approval, check for status changes.

- Monitor Pending_Approval directory for file status changes
- When a file is moved to Approved directory, trigger posting
- Update task status accordingly

**Monitoring Checklist:**
```
6.1 MCP server responded?                    → Yes / No
6.2 Draft file created in Pending_Approval? → Yes / No
6.3 Response written to task file?          → Yes / No
6.4 No browser errors?                      → Yes / No
6.5 All required data captured?             → Yes / No
```

**Decision:**
- If ALL checks pass → return success status
- If ANY check fails → return appropriate error status

---

## Safety Constraints

| Constraint | Rule |
|-----------|------|
| **Tier Enforcement** | 2 for any social media posting. Drafts always require human approval before posting. |
| **Never bypass MCP** | All LinkedIn communication must go through the MCP server (linkedin_mcp.py). No direct browser automation. |
| **Constitutional Compliance** | All posts must comply with Company Handbook rules and constitutional principles. |
| **Audit Trail** | Every LinkedIn action must be logged per Handbook §5.2. |
| **Content Safety** | Validate content for constitutional compliance before draft creation. |
| **Browser Automation Safety** | Ensure proper error handling and session management. |
| **Privacy Protection** | Ensure no sensitive personal or company data is included without authorization. |

---

## Error Handling

| Scenario | Error Code | Response |
|----------|-----------|----------|
| No text content provided | E2 | Return error, request proper content |
| Invalid image path | E2 | Validate path, return file not found error |
| Browser automation failure | E3 | Check browser status, retry (max 2x), escalate |
| Authentication failure | E3 | Check session, trigger re-login process |
| Content violates policies | E2 | Identify policy violation, suggest alternatives |
| Draft creation failed | E2 | Analyze error, validate input data |
| Network timeout | E2 | Retry with exponential backoff, then escalate |
| Screenshot on failure | E2/E3 | Capture browser state for debugging |

---

## Success Criteria

- [ ] Request successfully sent to MCP server
- [ ] MCP server successfully processes draft request
- [ ] Draft file created in Pending_Approval directory
- [ ] Human approval workflow initiated
- [ ] Execution log exists in `/Logs/linkedin_actions.log`
- [ ] All content validated for constitutional compliance
- [ ] Task file updated with draft details

---

## Integration Points

| Component | Integration |
|-----------|-------------|
| **linkedin_mcp_server.py** | Primary communication channel with LinkedIn via Playwright |
| **linkedin_session/** | Persistent browser session storage |
| **[Skill_Base.md](../../Skills/Skill_Base.md)** | Inherits standard skill contract |
| **[SK-012 (Task Executor)](../../Skills/Skill_Task_Executor.md)** | Called by primary reasoning loop |
| **Company_Handbook.md** | Follows constitutional authority and Tier rules |
| **Pending_Approval/** | Directory for awaiting human approval |
| **Logs/linkedin_actions.log** | Action logging for audit trail |
| **`/Done`** | Directory for completed post logs |

---

## First-Time Setup Instructions

### Prerequisites
- Install Playwright: `pip install playwright`
- Install required browsers: `playwright install chromium`

### Setup Process
1. Run the LinkedIn MCP server in setup mode:
   ```
   python "Platinum Tier/linkedin_mcp.py" --setup
   ```
2. A browser will open automatically
3. Log in to LinkedIn using your email and password
4. After successful login, close the browser window
5. The session will be saved automatically
6. The skill will be ready to use for creating draft posts

---

*This skill enables Platinum tier LinkedIn integration using Playwright browser automation with constitutional governance requiring human approval before posting, as required by the enterprise AI employee specifications.*