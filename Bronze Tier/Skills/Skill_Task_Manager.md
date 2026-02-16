---
skill_id: SK-011
name: Task Manager
status: active
tier: 0
trigger: Task ready for transition between lifecycle stages (Inbox → Needs_Action → Done)
version: "1.0"
depends_on: [SK-BASE, SK-010]
created: 2026-02-13
updated: 2026-02-13
tags: [skill, task-management, lifecycle, routing]
---

# Skill: Task Manager

> Inherits all rules from [Skill_Base.md](./Skill_Base.md) — Tier enforcement, logging, error handling, and halt conditions apply.

---

## Purpose

The Task Manager skill is the **execution engine for the task lifecycle pipeline** defined in Company Handbook §4. It owns the movement of tasks across folders (`/Inbox` → `/Needs_Action` → `/Done`), enforces priority assignments, validates transitions, and ensures every state change is logged.

This is the central orchestration skill. Other skills produce work — this skill manages where that work lives and what state it is in.

---

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `task_file` | string | Yes | Filename of the task to act on |
| `current_folder` | string | Yes | Current location: `Inbox`, `Needs_Action`, or `Done` |
| `action` | string | Yes | One of: `triage`, `start`, `complete`, `block`, `reject`, `return` |
| `priority` | string | No | Priority override: `P0`, `P1`, `P2`, `P3`. If omitted, auto-assigned during triage |
| `reason` | string | No | Context for the transition (required for `block`, `reject`, `return`) |

---

## Outputs

| Output | Type | Location | Description |
|--------|------|----------|-------------|
| Transitioned task | `.md` file | Target folder | Task file moved with updated frontmatter |
| Transition log | `.md` file | `/Logs/LOG_YYYY-MM-DD_HHmm.md` | Record of what moved and why |
| Plan (if complex) | `.md` file | `/Plans/PLAN_<task-name>.md` | Decomposition plan for complex tasks |
| Escalation (if blocked) | `.md` file | `/Needs_Action/` | Escalation note when task cannot proceed |

---

## Execution Steps

### Step 1: Locate and Read Task

- Resolve `task_file` within `current_folder`.
- Read the full file content and parse frontmatter.
- If file not found → E2 error, abort.

### Step 2: Validate Transition

Check the requested `action` against the allowed transition matrix:

| Action | Valid From | Moves To | Frontmatter Update |
|--------|-----------|----------|---------------------|
| `triage` | `/Inbox` | `/Needs_Action` | Add `triaged`, `priority`, `status: ready`, `assigned_to: ai-employee` |
| `start` | `/Needs_Action` | (stays, status changes) | Set `status: in_progress`, add `started: <timestamp>` |
| `complete` | `/Needs_Action` | `/Done` | Set `status: completed`, add `completed: <timestamp>` |
| `block` | `/Needs_Action` | (stays, status changes) | Set `status: blocked`, add `blocked_reason: <reason>` |
| `reject` | `/Inbox` | `/Done` | Set `status: rejected`, add `rejected_reason: <reason>` |
| `return` | `/Needs_Action` | `/Inbox` | Set `status: returned`, add `returned_reason: <reason>` |

- If the transition is **not valid** (e.g., `complete` from `/Inbox`) → E2 error, abort.

### Step 3: Auto-Assign Priority (Triage Only)

When `action == triage` and no `priority` is provided, classify using these signals:

| Signal | Assigned Priority |
|--------|-------------------|
| Contains "urgent", "critical", "down", "broken" | P0 |
| Contains "important", "deadline", "asap", "blocker" | P1 |
| Contains "update", "add", "create", "implement" | P2 |
| Contains "nice to have", "backlog", "low", "someday" | P3 |
| No clear signal | P2 (default) |

### Step 4: Assess Complexity (Triage Only)

During triage, determine if the task needs decomposition:

| Indicator | Classification | Action |
|-----------|---------------|--------|
| Task description > 500 words | Complex | Generate plan in `/Plans` |
| Task mentions 3+ distinct deliverables | Complex | Generate plan in `/Plans` |
| Task contains "multi-step", "phase", "stages" | Complex | Generate plan in `/Plans` |
| None of the above | Simple | Proceed directly to `/Needs_Action` |

If complex, create a plan file:

```yaml
---
plan_for: <task filename>
created: <YYYY-MM-DD HH:mm>
status: active
steps_total: <N>
steps_completed: 0
tags: [plan, decomposition]
---

# PLAN — <task title>

## Objective
<extracted from task description>

## Steps
1. [ ] Step 1 — <description>
2. [ ] Step 2 — <description>
3. [ ] Step N — <description>

## Success Criteria
<extracted or inferred from task>

## Dependencies
<any prerequisites identified>
```

### Step 5: Execute Transition

1. **Update frontmatter** with the fields specified in Step 2's table.
2. **Add transition record** to the task body:

```markdown
## Transition History
| Timestamp | From | To | Action | By |
|-----------|------|----|--------|-----|
| <YYYY-MM-DD HH:mm> | <source folder> | <target folder> | <action> | SK-011 |
```

3. **Move the file** to the target folder (if folder changes).
4. **Rename file** if needed to match naming conventions (Handbook §9).

### Step 6: Handle Special Cases

| Case | Behavior |
|------|----------|
| Task already in target state | Skip — log "no-op: task already in <status>" |
| Task has `status: blocked` and action is `start` | Reject — log "cannot start blocked task" |
| Task in `/Done` with action other than `reject` | Reject — completed tasks are immutable |
| Filename collision in target folder | Append timestamp suffix `_HHmm` to filename |

### Step 7: Log Transition

Write execution log to `/Logs` including:

- Task filename (before and after, if renamed)
- Source and target folders
- Frontmatter diff (what changed)
- Priority assigned (if triage)
- Plan created (if complex task)

---

## Safety Constraints

| Constraint | Rule |
|-----------|------|
| **Tier** | 0 — Autonomous for all internal task movements |
| **Never delete tasks** | Tasks are moved, never destroyed. Even rejected tasks go to `/Done` |
| **Never skip logging** | Every transition generates a log entry, no exceptions |
| **Respect immutability** | Tasks in `/Done` with `status: completed` cannot be modified |
| **No content alteration** | Only frontmatter and transition history are modified — task body is never changed |
| **Approval escalation** | If a task's content requests a Tier 2/3 action, flag it and halt — do not auto-execute |
| **Preserve history** | Transition history table is append-only — never remove previous entries |
| **Plan linkage** | If a plan is created, it must be linked in the task's frontmatter as `plan: <plan filename>` |

---

## Error Handling

| Scenario | Error Code | Response |
|----------|-----------|----------|
| Task file not found | E2 | Log, retry once with alternate paths, then escalate |
| Invalid transition requested | E2 | Log "invalid transition: <from> → <to>", abort, notify |
| Frontmatter is malformed/unparseable | E2 | Log, attempt to reconstruct from content, escalate if unable |
| Target folder missing | E4 | Halt all operations, log workspace corruption, trigger self-check |
| Filename collision after 5 suffix attempts | E3 | Halt, log, escalate — possible folder corruption |
| Task contains Tier 2/3 action request | E2 | Do NOT execute task content, flag for human approval |
| Circular return loop detected (Inbox → Needs_Action → Inbox > 2 times) | E3 | Halt task, log full history, escalate with recommendation |

---

## Success Criteria

- [ ] Task file exists in the correct folder after transition
- [ ] Frontmatter reflects the new status, timestamps, and priority
- [ ] Transition history table is appended (not overwritten)
- [ ] Execution log exists in `/Logs` for this transition
- [ ] Complex tasks have a linked plan in `/Plans`
- [ ] No task content was altered — only metadata changed
- [ ] No completed tasks were modified

---

*This skill conforms to [Skill_Base.md](./Skill_Base.md) v1.0*
