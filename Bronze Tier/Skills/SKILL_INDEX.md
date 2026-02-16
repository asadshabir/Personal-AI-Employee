---
tags: [skills, index, capabilities]
created: 2026-02-13
updated: 2026-02-13
---

# Skill Index — AI Employee Capabilities

> Registry of all skills available to the AI Employee. Each skill is a defined, repeatable capability with clear inputs, outputs, and trigger conditions.
> All skills must conform to the [Skill Base Contract](./Skill_Base.md).

---

## Architecture Skills (Core)

These skills define the system's operational backbone. They are invoked autonomously by Claude.

| ID | Skill Name | Status | Tier | Trigger | File | Description |
|----|-----------|--------|------|---------|------|-------------|
| SK-BASE | Skill Base Contract | `active` | — | — | [Skill_Base.md](./Skill_Base.md) | Master specification all skills inherit from |
| SK-010 | File Processor | `active` | 0 | New/unrecognized file in `/Inbox` or root | [Skill_File_Processor.md](./Skill_File_Processor.md) | Detect, validate, classify, and route new files |
| SK-011 | Task Manager | `active` | 0 | Task ready for lifecycle transition | [Skill_Task_Manager.md](./Skill_Task_Manager.md) | Move tasks across Inbox → Needs_Action → Done |
| **SK-012** | **Task Executor** | `active` | **0** | **Task with status ready/in_progress picked by orchestrator** | [Skill_Task_Executor.md](./Skill_Task_Executor.md) | **Primary reasoning loop — analyze, plan, execute, complete** |

## Domain Skills (Capabilities)

These skills handle specific work types. They are invoked when tasks match their trigger tags or chained by SK-012.

| ID | Skill Name | Status | Tier | Trigger | Description |
|----|-----------|--------|------|---------|-------------|
| SK-001 | Task Triage | `active` | 0 | New note in `/Inbox` | Classify, prioritize, and route incoming tasks |
| SK-002 | Code Generation | `active` | 1 | Task tagged `#code` or chained by SK-012 | Generate code artifacts from specifications |
| SK-003 | Code Review | `active` | 1 | Task tagged `#review` or chained by SK-012 | Analyze code for bugs, style, and security issues |
| SK-004 | Plan Decomposition | `active` | 0 | Task tagged `#complex` or chained by SK-012 | Break large tasks into actionable sub-tasks in `/Plans` |
| SK-005 | Log Generation | `active` | 0 | Every execution cycle | Write structured execution logs to `/Logs` |
| SK-006 | Research & Summarize | `active` | 1 | Task tagged `#research` or chained by SK-012 | Gather information and produce concise summaries |
| SK-007 | Documentation | `active` | 1 | Task tagged `#docs` or chained by SK-012 | Generate or update project documentation |
| SK-008 | Testing | `active` | 1 | Task tagged `#test` or chained by SK-012 | Write and execute test cases for code artifacts |

---

## Dependency Graph

```
SK-BASE (Skill Base Contract)
 │
 ├── SK-010 (File Processor)       ← depends on SK-BASE
 │
 ├── SK-011 (Task Manager)         ← depends on SK-BASE, SK-010
 │
 ├── SK-012 (Task Executor)        ← depends on SK-BASE, SK-011, SK-004, SK-005
 │    │                               PRIMARY REASONING LOOP
 │    ├── chains → SK-002 (Code Generation)
 │    ├── chains → SK-003 (Code Review)
 │    ├── chains → SK-004 (Plan Decomposition)
 │    ├── chains → SK-006 (Research & Summarize)
 │    ├── chains → SK-007 (Documentation)
 │    └── chains → SK-008 (Testing)
 │
 ├── SK-001 (Task Triage)          ← uses SK-011 for transitions
 │
 └── SK-005 (Log Generation)       ← invoked by all skills
```

### Execution Flow

```
File arrives → SK-010 (classify) → SK-011 (triage) → SK-012 (execute) → SK-011 (complete)
                                                          │
                                                          ├── chains domain skills as needed
                                                          ├── generates plan in /Plans
                                                          ├── writes results to task file
                                                          └── marks status: done when verified
```

---

## Skill Lifecycle

```
[draft] → [active] → [deprecated]
```

| State | Invocable? | Requirements |
|-------|-----------|--------------|
| `draft` | No | Must pass Skill_Base §3.1 activation checklist |
| `active` | Yes | All required sections present, tested, registered here |
| `deprecated` | No | Kept for audit trail, never executed |

---

## Adding a New Skill

1. Copy the template from [Skill_Base.md §8](./Skill_Base.md)
2. Create file: `/Skills/Skill_<Name>.md`
3. Set `status: draft` and assign a unique `skill_id` (next available SK-XXX)
4. Implement all 8 required sections per Skill_Base contract
5. Dry-run on sample input
6. Set `status: active` and add entry to this index
7. Log the registration in `/Logs`

---

## Skill Count Summary

| Status | Count |
|--------|-------|
| Active (Architecture) | 4 |
| Active (Domain) | 8 |
| Draft | 0 |
| Deprecated | 0 |
| **Total** | **12** |

---

*This index must stay synchronized with all skill files in `/Skills`. Last verified: 2026-02-13.*
