---
skill_id: SK-BASE
name: Skill Base Contract
status: active
type: meta-skill
authority: Constitutional — all skills must conform to this specification
version: "1.0"
created: 2026-02-13
updated: 2026-02-13
tags: [skill, base, contract, architecture]
---

# Skill Base Contract — Master Specification

> This document defines the **behavioral contract** that every AI Employee skill must implement.
> No skill may operate outside the boundaries defined here.
> All skills inherit these rules implicitly — violations are treated as E3 errors.

---

## 1. Purpose

The Skill Base Contract establishes a **uniform interface** for all AI Employee capabilities. It ensures every skill is:

- **Predictable:** Same inputs produce same outputs.
- **Auditable:** Every invocation is logged.
- **Safe:** Bounded by approval tiers and the Company Handbook.
- **Composable:** Skills can invoke other skills through a defined protocol.

---

## 2. Required Skill Structure

Every skill file in `/Skills` must implement the following sections. Missing sections render the skill invalid.

```
┌──────────────────────────────────────────────┐
│              SKILL DEFINITION                │
├──────────────────────────────────────────────┤
│  Frontmatter    → ID, name, status, tier     │
│  Purpose        → What and why               │
│  Inputs         → Required + optional params  │
│  Outputs        → Artifacts produced          │
│  Execution Steps→ Ordered, deterministic      │
│  Safety         → Tier, constraints, halts    │
│  Error Handling → Classification + fallback   │
│  Logging        → What gets recorded          │
└──────────────────────────────────────────────┘
```

### 2.1 Required Frontmatter Schema

```yaml
---
skill_id: SK-XXX                          # Unique identifier (SK-001 through SK-999)
name: Human-readable Skill Name           # Descriptive name
status: draft | active | deprecated       # Lifecycle state
tier: 0 | 1 | 2 | 3                      # Approval tier from Company Handbook §3.2
trigger: Description of activation event  # When Claude should invoke this skill
version: "1.0"                            # Semantic version
depends_on: [SK-XXX, SK-YYY]             # Skills this skill may call (empty if none)
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [skill, category]
---
```

---

## 3. Skill Lifecycle

```
┌─────────┐     ┌──────────┐     ┌──────────────┐
│  DRAFT   │────▶│  ACTIVE  │────▶│  DEPRECATED  │
└─────────┘     └──────────┘     └──────────────┘
     │                │                   │
     │  Validation    │  Retirement       │  Reference only
     │  required      │  logged           │  never invoked
     └────────────────┴───────────────────┘
```

| State | Can Be Invoked? | Requirements |
|-------|----------------|--------------|
| `draft` | No | Must pass validation before activation |
| `active` | Yes | All required sections present, tested on sample input |
| `deprecated` | No | Kept for audit trail, never executed |

### 3.1 Activation Checklist

Before a skill transitions from `draft` → `active`:

- [ ] All 8 required sections are present and complete
- [ ] Tier assignment matches Company Handbook §3.2
- [ ] At least one successful dry-run on sample input
- [ ] Entry added to [SKILL_INDEX.md](./SKILL_INDEX.md)
- [ ] No conflicts with existing active skills

---

## 4. Invocation Protocol

### 4.1 How Claude Invokes a Skill

```
1. DETECT   → Trigger condition is met (new file, task tag, schedule, etc.)
2. VALIDATE → Check skill status == "active"
3. AUTHORIZE→ Verify tier allows autonomous execution, or request approval
4. PREPARE  → Gather all required inputs
5. EXECUTE  → Run execution steps in order
6. LOG      → Write execution log to /Logs
7. OUTPUT   → Deliver outputs to specified location
8. VERIFY   → Confirm outputs match success criteria
```

### 4.2 Pre-Execution Checks (Mandatory)

Before executing ANY skill, Claude must verify:

| Check | Fail Action |
|-------|-------------|
| Skill status is `active` | Abort — log "skill not active" |
| All required inputs are present | Abort — log "missing inputs: [list]" |
| Tier allows autonomous execution | If Tier 2/3 → halt and request approval |
| No circular dependency with currently running skills | Abort — log as E3 |
| Company Handbook is accessible | Abort — log as E4, run self-check |

### 4.3 Skill Chaining

Skills may invoke other skills under these constraints:

- Maximum chain depth: **3** (Skill A → Skill B → Skill C → STOP)
- Each link in the chain must be independently logged
- If any skill in the chain fails, the entire chain halts
- The originating skill is responsible for rollback of its own outputs
- Circular chains are forbidden — detected chains trigger E3

---

## 5. Safety Constraints (Universal)

These constraints apply to **every skill**, no exceptions:

### 5.1 Tier Enforcement

| Tier | Skill Behavior |
|------|---------------|
| **Tier 0** | Execute autonomously. Log action. |
| **Tier 1** | Execute autonomously. Log action with notification flag. |
| **Tier 2** | HALT. Generate approval request per Handbook §3.3. Wait. |
| **Tier 3** | HALT. Generate approval request. Do NOT proceed under any circumstance. |

### 5.2 Hard Boundaries

Every skill must enforce these regardless of its own logic:

1. **No external network calls** without Tier 3 approval.
2. **No secret storage** — never write API keys, tokens, or passwords to any `.md` file.
3. **No destructive file operations** (delete, overwrite production data) without Tier 2+ approval.
4. **No modification of Company_Handbook.md** — ever.
5. **No modification of Skill_Base.md** — only Human Operator may change this contract.
6. **No bypassing the logging mandate** — every execution produces a log entry.
7. **No silent failures** — if something fails, it must be logged and surfaced.

### 5.3 Halt Conditions

A skill must **immediately stop execution** if:

- Required input is malformed or missing
- An output would overwrite an existing file without explicit instruction
- The action would escalate beyond the skill's assigned tier
- An E3 or E4 error is encountered
- The Company Handbook is inaccessible or appears modified unexpectedly

---

## 6. Logging Contract

Every skill invocation must produce a log entry in `/Logs` following this structure:

```markdown
---
log_id: LOG_<YYYY-MM-DD>_<HHmm>
skill_id: <SK-XXX>
task_ref: <linked task filename or "none">
created: <YYYY-MM-DD HH:mm>
status: <success | partial | failed | halted>
tier: <0-3>
tags: [log, skill-execution]
---

# Skill Execution Log — <Skill Name>

## Trigger
<What activated this skill>

## Inputs Received
<List of inputs with values>

## Steps Executed
<Numbered list of steps completed>

## Output Produced
<What was created/modified and where>

## Decisions Made
<Any branching logic or choices applied>

## Errors
<None, or error code + description>

## Duration
<Start → End>
```

---

## 7. Error Handling Contract

Skills must classify errors using Company Handbook §6.1:

| Error Code | Skill Response |
|-----------|---------------|
| E1 (Low) | Log warning, continue execution |
| E2 (Medium) | Retry once with same inputs, then halt + log if still failing |
| E3 (High) | Halt immediately, log, create escalation note in `/Needs_Action` |
| E4 (Critical) | Halt ALL skill execution, log, escalate, trigger full self-check |

### 7.1 Retry Rules (Per Skill Invocation)

- Max retries: **1** (2 total attempts)
- Retry only for E1 and E2
- E3 and E4: never retry, always halt

### 7.2 Escalation Output

On halt, the skill must produce:

```markdown
---
type: skill-escalation
skill_id: <SK-XXX>
severity: <E1-E4>
task_ref: <original task>
created: <YYYY-MM-DD HH:mm>
status: awaiting_human
---

# SKILL ESCALATION — <Skill Name>

## Failed At Step
<Step number and description>

## Error Details
<What went wrong>

## Inputs That Caused Failure
<Exact inputs received>

## Recommended Action
<What the Human Operator should do>
```

---

## 8. Skill Template (Copy-Paste Starter)

```markdown
---
skill_id: SK-XXX
name: New Skill Name
status: draft
tier: 0
trigger: <when this skill activates>
version: "1.0"
depends_on: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [skill]
---

# New Skill Name

## Purpose
<What this skill does and why it exists>

## Inputs
| Input | Type | Required | Description |
|-------|------|----------|-------------|
| input_1 | string | Yes | Description |
| input_2 | string | No | Description |

## Outputs
| Output | Type | Location | Description |
|--------|------|----------|-------------|
| output_1 | file | /path | Description |

## Execution Steps
1. Step one
2. Step two
3. Step three

## Safety Constraints
- Tier: <0-3>
- Halt conditions: <list>
- Forbidden actions: <list>

## Error Handling
| Scenario | Error Code | Response |
|----------|-----------|----------|
| Scenario 1 | E1 | Action |
| Scenario 2 | E3 | Action |

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

---

*This contract is immutable by the AI Employee. Only the Human Operator may amend it.*
