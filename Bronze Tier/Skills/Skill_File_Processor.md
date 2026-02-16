---
skill_id: SK-010
name: File Processor
status: active
tier: 0
trigger: New or unrecognized file detected in /Inbox or workspace root
version: "1.0"
depends_on: [SK-BASE]
created: 2026-02-13
updated: 2026-02-13
tags: [skill, file-processing, intake, routing]
---

# Skill: File Processor

> Inherits all rules from [Skill_Base.md](./Skill_Base.md) — Tier enforcement, logging, error handling, and halt conditions apply.

---

## Purpose

The File Processor skill **detects, validates, classifies, and routes new files** that enter the workspace. It acts as the intake gate — ensuring every file is identified, tagged with proper frontmatter, and moved to its correct location before any other skill processes it.

This skill prevents unstructured or misplaced files from polluting the workspace.

---

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `file_path` | string | Yes | Absolute or workspace-relative path to the new file |
| `file_content` | string | Yes | Raw content of the file (read by Claude) |
| `source` | string | No | Origin of the file: `manual`, `automated`, `unknown`. Defaults to `unknown` |

---

## Outputs

| Output | Type | Location | Description |
|--------|------|----------|-------------|
| Classified file | `.md` file | Target folder (`/Inbox`, `/Plans`, `/Skills`, etc.) | File with validated frontmatter, moved to correct location |
| Processing log | `.md` file | `/Logs/LOG_YYYY-MM-DD_HHmm.md` | Execution log of what was done |
| Rejection note | `.md` file | `/Needs_Action/` (if file is invalid) | Escalation note explaining why a file was rejected |

---

## Execution Steps

### Step 1: Detect File

- Scan for new or unrecognized files in `/Inbox` and workspace root.
- Identify file extension and type (`.md`, `.txt`, `.json`, `.csv`, other).
- If file is not a recognized text format → skip to Step 6 (Reject).

### Step 2: Read and Parse Content

- Read the full file content.
- Check for existing YAML frontmatter (`---` delimiters at top of file).
- Extract any metadata if frontmatter exists.

### Step 3: Validate Structure

Run validation checks:

| Check | Pass Condition | Fail Action |
|-------|---------------|-------------|
| File is not empty | Content length > 0 | Reject → Step 6 |
| File is text-based | Extension in `.md`, `.txt`, `.json`, `.csv`, `.yaml` | Reject → Step 6 |
| File size is reasonable | < 1 MB | Reject → Step 6 |
| No secrets detected | No patterns matching API keys, tokens, passwords | Reject → Step 6 with E3 flag |

### Step 4: Classify File Type

Determine destination based on content analysis:

| Classification | Detection Signal | Target Folder |
|---------------|-----------------|---------------|
| Task | Contains `title`, `requester`, `priority` or task-like language | `/Inbox` (if not already there) |
| Plan | Contains `## Steps`, `## Goals`, `## Milestones` or plan structure | `/Plans` |
| Skill Definition | Contains `skill_id`, `## Execution Steps`, `## Inputs` | `/Skills` |
| Log | Contains `log_id`, `## Action Taken`, timestamp patterns | `/Logs` |
| General Document | Does not match above patterns | `/Inbox` (default, for triage) |

### Step 5: Enrich and Route

- **If frontmatter is missing:** Generate frontmatter based on classification:

```yaml
---
title: <inferred from filename or first heading>
type: <task | plan | skill | log | document>
source: <manual | automated | unknown>
received: <YYYY-MM-DD HH:mm>
status: new
processed_by: SK-010
---
```

- **If frontmatter exists but is incomplete:** Add missing required fields, preserve existing values.
- **Move file** to the classified target folder.
- **Rename file** to match naming conventions from Company Handbook §9 if needed.

### Step 6: Handle Rejection

If the file fails validation:

1. Do NOT delete the file.
2. Move it to `/Needs_Action` with a rejection wrapper:

```yaml
---
title: "FILE REJECTED — <original filename>"
type: escalation
severity: E2
source_file: <original path>
reason: <why it was rejected>
created: <YYYY-MM-DD HH:mm>
status: awaiting_human
processed_by: SK-010
---
```

3. Log the rejection in `/Logs`.

### Step 7: Log Execution

Write a structured execution log to `/Logs` per Skill_Base §6.

---

## Safety Constraints

| Constraint | Rule |
|-----------|------|
| **Tier** | 0 — Fully autonomous for read, classify, route operations |
| **Never delete files** | Files are moved or flagged, never destroyed |
| **Never overwrite** | If target path already has a file with same name, append `_N` suffix |
| **Secret detection** | If a file contains patterns matching secrets (API keys, tokens), reject immediately and flag as E3 |
| **Size limit** | Refuse to process files > 1 MB — log and escalate |
| **No external calls** | This skill operates entirely within the local workspace |
| **Preserve original** | Always keep original content intact — only add/modify frontmatter |

---

## Error Handling

| Scenario | Error Code | Response |
|----------|-----------|----------|
| File is empty | E1 | Log warning, move to `/Needs_Action` with note |
| File is binary/unreadable | E2 | Log, reject, create escalation note |
| Secret pattern detected in file | E3 | Halt immediately, do NOT move file, create E3 escalation |
| File path is inaccessible | E2 | Log, retry once, then escalate |
| Target folder missing | E4 | Halt, log as workspace corruption, trigger self-check |
| Filename collision at target | E1 | Append `_2`, `_3`, etc. to filename, log the rename |

---

## Success Criteria

- [ ] File has valid frontmatter after processing
- [ ] File is in the correct target folder
- [ ] No original content was lost or altered
- [ ] Execution log exists in `/Logs` for this invocation
- [ ] No secrets remain in any processed file
- [ ] Rejected files have corresponding escalation notes

---

*This skill conforms to [Skill_Base.md](./Skill_Base.md) v1.0*
