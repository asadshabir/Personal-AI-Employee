---
skill_id: SK-012
name: Task Executor
status: active
tier: 0
trigger: Task with status ready or in_progress in /Needs_Action is picked up by orchestrator
version: "1.0"
depends_on: [SK-BASE, SK-011, SK-004, SK-005]
created: 2026-02-13
updated: 2026-02-13
tags: [skill, executor, reasoning-loop, primary]
---

# Skill: Task Executor — Primary Reasoning Loop

> Inherits all rules from [Skill_Base.md](./Skill_Base.md) — Tier enforcement, logging, error handling, and halt conditions apply.

---

## Purpose

The Task Executor is the **primary reasoning loop** of the AI Employee. While other skills handle routing (SK-010), transitions (SK-011), and decomposition (SK-004), this skill owns the **actual thinking and execution** of work.

It reads a task, understands what is being asked, formulates a plan, executes that plan step by step, writes results back into the task file, and marks `status: done` only when all work is verifiably complete.

**The orchestrator's completion loop will keep re-invoking this skill until `status: done` is confirmed in the task file's frontmatter.** This means:
- If the work is incomplete, this skill must return `in_progress` with a clear description of remaining work.
- If the work is done, this skill must write `status: done` into the frontmatter.
- There is no shortcut. The file is the source of truth.

### Relationship to Orchestrator

```
orchestrator.py                          SK-012 (This Skill)
┌──────────────────┐                     ┌──────────────────────────┐
│  Completion Loop  │ ──── invokes ────▶ │  1. Read task            │
│                   │                     │  2. Analyze request      │
│  Checks file for  │                     │  3. Generate Plan.md     │
│  status: done     │ ◀── writes back ── │  4. Execute plan         │
│  after each cycle │                     │  5. Update task results  │
│                   │                     │  6. Mark status: done    │
│  If not done:     │                     │  7. Signal orchestrator  │
│  re-invoke SK-012 │                     └──────────────────────────┘
└──────────────────┘
```

---

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `task_file` | string | Yes | Path to the task `.md` file in `/Needs_Action` |
| `task_content` | string | Yes | Full markdown content of the task file |
| `task_metadata` | dict | Yes | Parsed frontmatter: title, priority, classification, status, etc. |
| `cycle_number` | int | Yes | Current completion loop cycle (1-based). Provided by orchestrator. |
| `previous_result` | string | No | Output from previous cycle if this is a reprocessing (cycle > 1). Extracted from `remaining_work` in frontmatter. |
| `skill_context` | string | No | Additional skill definition loaded by orchestrator if task has a domain tag (#code, #review, etc.) |

---

## Outputs

| Output | Type | Location | Description |
|--------|------|----------|-------------|
| Execution plan | `.md` file | `/Plans/PLAN_<task-stem>.md` | Structured plan with numbered steps and success criteria |
| Updated task | `.md` file | `/Needs_Action/<task-file>` | Task file with results appended and frontmatter updated |
| Execution log | `.md` file | `/Logs/LOG_YYYY-MM-DD_HHmm_*.md` | Audit log per Handbook §5.2 |
| Status signal | frontmatter | In task file | `status: done` when complete, `status: in_progress` when not |

---

## Execution Steps

### Step 1: Read and Parse Task

**Action:** Load the task file and extract all structured information.

- Read `task_content` and `task_metadata` provided by orchestrator.
- Extract these fields from frontmatter:
  - `title` — what the task is called
  - `priority` — P0-P3
  - `classification` — task type (task, code, review, docs, etc.)
  - `status` — current state
  - `remaining_work` — if this is a reprocessing cycle, what was left
- Extract the task body (everything after frontmatter) as the **request**.
- If `cycle_number > 1`: read `remaining_work` to understand what still needs to be done.

**Validation:**
- If `title` is missing → infer from first heading or filename.
- If `task_content` is empty → E2 error, halt.
- If task body contains no actionable request → E1 warning, attempt to infer intent.

---

### Step 2: Analyze Request

**Action:** Decompose the request into a structured understanding.

Produce an internal analysis (not written to file) covering:

| Analysis Field | Description |
|---------------|-------------|
| **Intent** | What is the human asking for? (1 sentence) |
| **Deliverables** | Concrete outputs expected (numbered list) |
| **Complexity** | Simple (1-3 steps) / Medium (4-7 steps) / Complex (8+ steps) |
| **Domain** | Code, documentation, research, review, planning, general |
| **Dependencies** | Does this task depend on other tasks or external resources? |
| **Tier Assessment** | What approval tier does the execution require? (0-3) |
| **Risks** | What could go wrong during execution? |

**Tier Gate:**
- If Tier Assessment >= 2 → HALT. Do not proceed. Return `status: halted` with approval request per Handbook §3.3.
- If Tier Assessment <= 1 → proceed to Step 3.

**Reprocessing Logic (cycle > 1):**
- Read `remaining_work` from the previous cycle.
- Re-analyze only the unfinished items — do NOT redo completed work.
- Carry forward all previous outputs.

---

### Step 3: Generate Plan

**Action:** Create a structured execution plan in `/Plans`.

Plan file: `/Plans/PLAN_<task-stem>.md`

```yaml
---
plan_for: <task filename>
skill_id: SK-012
created: <YYYY-MM-DD HH:mm>
status: active
complexity: <simple | medium | complex>
steps_total: <N>
steps_completed: 0
cycle: <current cycle number>
tags: [plan, execution]
---

# PLAN — <task title>

## Objective
<1-2 sentence goal extracted from task analysis>

## Deliverables
1. <deliverable 1>
2. <deliverable 2>
3. <deliverable N>

## Execution Steps
1. [ ] <Step 1 — description> | Expected output: <what this step produces>
2. [ ] <Step 2 — description> | Expected output: <what this step produces>
3. [ ] <Step N — description> | Expected output: <what this step produces>

## Success Criteria
- [ ] <Criterion 1 — how to verify the task is truly done>
- [ ] <Criterion 2>
- [ ] <Criterion N>

## Dependencies
- <dependency or "None">

## Risks & Mitigations
| Risk | Mitigation |
|------|-----------|
| <risk 1> | <mitigation 1> |

## Rollback
<What to undo if the plan fails midway>
```

**Rules:**
- If a plan already exists for this task (from a previous cycle) → update it, don't create a new one.
- Mark completed steps with `[x]` and update `steps_completed` count.
- If complexity is `simple` (1-3 steps), the plan can be minimal — no need for risks/rollback sections.
- Never overwrite an existing plan file — use the existing one if `PLAN_<task-stem>.md` exists.

---

### Step 4: Execute Plan

**Action:** Work through each plan step in order.

For each step in the plan:

```
4.1  Read the step description and expected output
4.2  Determine if this step requires domain skill chaining:
       - Code generation → chain to SK-002
       - Code review     → chain to SK-003
       - Research        → chain to SK-006
       - Documentation   → chain to SK-007
       - Testing         → chain to SK-008
       - General work    → execute directly (no chaining)
4.3  Execute the step
4.4  Validate the output against expected output
4.5  Mark step as [x] in the plan file
4.6  Update plan frontmatter: steps_completed += 1
4.7  Log the step execution
```

**Skill Chaining Rules (per Skill_Base §4.3):**
- Maximum chain depth: 3 (SK-012 → Domain Skill → Sub-skill → STOP)
- Each chained invocation is independently logged
- If any chained skill fails, halt the entire plan at that step
- SK-012 is responsible for rollback of its own outputs

**Per-Step Error Handling:**

| Scenario | Response |
|----------|----------|
| Step produces no output | E1 — log warning, attempt step once more, then skip with note |
| Step produces wrong output type | E2 — log, retry step once, escalate if still wrong |
| Step requires Tier 2/3 action | HALT entire plan — return `in_progress` with remaining steps |
| Step depends on unresolved external resource | HALT step — mark as blocked, continue with independent steps |
| Chained skill fails | E3 — halt plan execution, log, report remaining steps |

**Partial Completion:**
- If the plan cannot be fully completed in one cycle (e.g., blocked step, tier gate), the executor must:
  1. Mark all completed steps as `[x]`
  2. Record which steps remain
  3. Return `status: in_progress` with `remaining_work` describing unfinished steps
  4. The orchestrator will re-invoke this skill for the next cycle

---

### Step 5: Update Task File with Results

**Action:** Write execution results back into the task `.md` file.

Append the following section to the task body (do not modify existing content):

```markdown
## Execution Result — Cycle <N>

- **Skill:** SK-012 (Task Executor)
- **Plan:** [PLAN_<task-stem>.md](../Plans/PLAN_<task-stem>.md)
- **Steps Completed:** <X> / <Total>
- **Status:** <done | in_progress>
- **Processed:** <YYYY-MM-DD HH:mm>

### Deliverables Produced
1. <deliverable 1 — description and location>
2. <deliverable 2 — description and location>

### Output
<The actual work product, inline or linked>

### Decisions Made
<Key choices during execution>

### Remaining Work
<None if done, or specific list of unfinished items>
```

**Frontmatter Updates:**

If all steps completed and success criteria met:
```yaml
status: done
completed: <YYYY-MM-DD HH:mm>
plan: PLAN_<task-stem>.md
executed_by: SK-012
completion_cycle: <N>
```

If work remains:
```yaml
status: in_progress
remaining_work: <concise description of what's left>
last_cycle: <N>
plan: PLAN_<task-stem>.md
executed_by: SK-012
```

---

### Step 6: Verify Completion — Mark `status: done`

**Action:** Final verification before signaling completion.

This is the **critical gate**. The orchestrator's `is_task_done()` function checks the file for `status: done`. This step determines whether to write it.

**Completion Checklist:**

```
6.1  All plan steps marked [x]?                    → Yes / No
6.2  All deliverables produced?                     → Yes / No
6.3  All success criteria met?                      → Yes / No
6.4  No unresolved errors (E2+) in execution?       → Yes / No
6.5  No pending Tier 2/3 approvals?                 → Yes / No
6.6  Task body updated with results?                → Yes / No
6.7  Plan file updated with final state?            → Yes / No
```

**Decision:**
- If ALL checks pass → write `status: done` in frontmatter. Task is complete.
- If ANY check fails → write `status: in_progress` with `remaining_work` listing the failed checks.
- **Never write `status: done` unless ALL checks pass.** This is a hard rule.

**The `status: done` contract:**
```
Writing `status: done` is a PROMISE that:
  - All requested work has been performed
  - All outputs exist and are valid
  - No work was skipped or deferred
  - The task can be safely moved to /Done without loss
```

---

### Step 7: Signal Orchestrator

**Action:** Return structured result to the orchestrator's completion loop.

The orchestrator reads the result via the Claude response format:

If done:
```
RESULT_STATUS: done
RESULT_SUMMARY: <what was accomplished>
RESULT_OUTPUT: <deliverables produced>
RESULT_DECISIONS: <key choices made>
RESULT_ERRORS: None
RESULT_REMAINING: None
```

If not done:
```
RESULT_STATUS: in_progress
RESULT_SUMMARY: <what was accomplished so far>
RESULT_OUTPUT: <partial deliverables>
RESULT_DECISIONS: <key choices made>
RESULT_ERRORS: <any errors encountered, or None>
RESULT_REMAINING: <specific description of what's left>
```

The orchestrator will:
- Read the task file and call `is_task_done()`
- If `status: done` → move to `/Done`
- If not → re-invoke SK-012 for the next cycle (up to MAX_COMPLETION_CYCLES)

---

## Safety Constraints

| Constraint | Rule |
|-----------|------|
| **Tier** | 0 for internal reasoning and planning. Escalates to Tier 1-3 based on task content analysis in Step 2. |
| **Never fake completion** | `status: done` may ONLY be written when ALL success criteria are verified. Premature completion is an E3 violation. |
| **Never delete task content** | Results are appended, never overwritten. Previous cycle outputs are preserved. |
| **Never overwrite plans** | Existing plan files are updated in-place, not replaced. |
| **Respect chain depth** | Maximum 3 levels of skill chaining. Exceeding this is an E3. |
| **Respect cycle cap** | If the orchestrator's MAX_COMPLETION_CYCLES is reached, accept the E3 escalation gracefully. |
| **No external calls** | All execution is local unless the task explicitly requires it AND Tier 3 approval is granted. |
| **Idempotent re-entry** | If re-invoked on a partially complete task, resume from where it left off. Never redo completed steps. |
| **Plan linkage** | Every executed task must have a corresponding plan in `/Plans`, linked in frontmatter. |
| **Log everything** | Every step execution, every decision, every error — all logged per Handbook §5. |

---

## Error Handling

| Scenario | Error Code | Response |
|----------|-----------|----------|
| Task file is empty or unreadable | E2 | Log, return `failed`, orchestrator will retry |
| No actionable request found in task | E1 | Log warning, attempt to infer intent, proceed if possible |
| Plan generation fails | E2 | Retry once, then return `failed` with details |
| Step execution produces no output | E1 | Log, retry step once, skip with note if still empty |
| Step execution produces wrong output | E2 | Log, retry step once, escalate if still wrong |
| Chained skill fails | E3 | Halt plan, log full chain state, return `in_progress` with remaining |
| Tier 2/3 action detected mid-execution | E2 | Halt at that step, return `in_progress`, orchestrator will escalate |
| Plan file missing on reprocessing | E2 | Regenerate plan from task content, log the regeneration |
| Success criteria cannot be verified | E2 | Do NOT write `status: done`, return `in_progress`, escalate |
| Cycle cap approaching (cycle >= 8) | E1 | Log warning, attempt aggressive completion of remaining items |
| Infinite reasoning loop detected | E3 | If same `remaining_work` appears 3 cycles in a row, halt and escalate |

### Stale Loop Detection

To prevent infinite reprocessing:
- Track `remaining_work` across cycles via frontmatter.
- If the exact same `remaining_work` string appears for 3 consecutive cycles, this indicates a stuck loop.
- On detection: halt, mark as `E3`, create escalation note, do NOT continue.

---

## Success Criteria

- [ ] Task file has `status: done` in frontmatter (the ultimate gate)
- [ ] Plan file exists in `/Plans` and all steps are marked `[x]`
- [ ] All deliverables listed in the plan are produced and referenced in the task
- [ ] Execution result section appended to task body with all required fields
- [ ] Execution log exists in `/Logs` for this invocation
- [ ] No unresolved E2+ errors remain
- [ ] No skipped steps without documented justification
- [ ] If reprocessed: previous cycle outputs are preserved (not overwritten)
- [ ] Frontmatter contains `plan`, `executed_by`, `completion_cycle` fields

---

## Interaction with Other Skills

| Skill | Relationship |
|-------|-------------|
| **SK-BASE** | Inherits contract — all rules apply |
| **SK-010 (File Processor)** | Upstream — processes raw files into tasks before SK-012 sees them |
| **SK-011 (Task Manager)** | Parallel — manages folder transitions; SK-012 manages the actual work |
| **SK-004 (Plan Decomposition)** | Can be chained — SK-012 may invoke SK-004 for complex sub-task breakdown |
| **SK-002 (Code Generation)** | Can be chained — invoked when a plan step requires code output |
| **SK-003 (Code Review)** | Can be chained — invoked when a plan step requires code analysis |
| **SK-005 (Log Generation)** | Invoked implicitly — every step produces a log entry |
| **SK-006 (Research)** | Can be chained — invoked when a plan step requires information gathering |
| **SK-007 (Documentation)** | Can be chained — invoked when a plan step requires doc generation |
| **SK-008 (Testing)** | Can be chained — invoked when a plan step requires test creation |

---

*This skill conforms to [Skill_Base.md](./Skill_Base.md) v1.0 — Primary reasoning loop of the AI Employee system.*
