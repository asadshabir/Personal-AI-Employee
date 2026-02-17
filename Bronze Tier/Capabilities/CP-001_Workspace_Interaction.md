# CP-001 — Workspace Interaction Capability

> **Purpose**: Enable the AI Employee to perform controlled file operations within the workspace as required for task completion, while maintaining full constitutional governance and auditability.

---

## 📋 **Purpose**

This capability allows the AI Employee to interact with files in a controlled, traceable manner to complete assigned tasks. It provides the fundamental ability to read, create, and update files within the established workspace structure, ensuring all operations align with constitutional rules and maintain complete auditability.

---

## ✅ **Allowed Actions**

### File Reading
- **Read existing files** within approved directories:
  - `/Inbox`, `/Needs_Action`, `/Done`
  - `/Logs`, `/Plans`, `/Memory`
  - `/Skills`, `/Dashboard`, `/Capabilities`
  - Any subdirectories of these approved locations
- **Parse file content** for task processing
- **Extract metadata** from file frontmatter where present
- **Validate file integrity** before processing

### File Creation
- **Create new files** only in approved directories:
  - `/Plans` (for execution plans)
  - `/Logs` (for audit logs)
  - `/Done` (for completed tasks)
  - `/Memory` (for reflection entries)
  - Subdirectories as defined by system architecture
- **Generate deliverables** as specified in task plans
- **Create temporary working files** in designated areas only
- **Ensure collision-free filenames** using established patterns

### File Updates (Append-Only)
- **Append to existing files** such as:
  - Log files in `/Logs`
  - Memory files in `/Memory`
  - Context logs in `/Memory/context_log.md`
  - Reflections in `/Memory/reflections.md`
  - Task execution results in existing task files
- **Update file frontmatter** with new metadata (status, completion info, etc.)
- **Add transition history** to task files
- **Preserve existing content** when appending

### Deliverable Generation
- **Generate outputs** defined by completed task plans
- **Format deliverables** according to specified requirements
- **Organize generated content** in appropriate directories
- **Link generated files** to source tasks when applicable

---

## ❌ **Forbidden Actions**

### File System Integrity Violations
- **NEVER delete files** - tasks move between directories instead
- **NEVER overwrite historical records** - append-only for logs and memory
- **NEVER modify existing task content** - only append results
- **NEVER truncate or reset files** - preserve complete history

### Memory and Constitution Integrity
- **NEVER modify Memory retroactively** - only append to memory files
- **NEVER overwrite existing reflection entries** - preserve immutable audit trail
- **NEVER modify Skills or Constitution files** unless explicitly authorized by constitutional amendment process
- **NEVER alter Company Handbook or Skill Base contracts**

### Unauthorized Access
- **NEVER access files outside approved workspace** - stay within defined directory structure
- **NEVER perform operations without traceability** - all actions must be logged
- **NEVER execute operations without skill authorization** - only act when requested by valid skills
- **NEVER perform system-level changes** - maintain file-only scope

---

## 📜 **Execution Rules**

### Traceability Requirements
- **Every file operation must be logged** in accordance with Handbook §5
- **All actions must map to active task steps** - no hidden operations
- **Operation context must be preserved** in log entries
- **File modification chains must be traceable** - clear before/after relationships

### Task Alignment
- **Every write operation must correspond to a planned step** in active task plan
- **File generation must satisfy defined deliverables** from task specification
- **No speculative file creation** without explicit task requirement
- **All file names must follow established patterns** from system architecture

### Constitutional Compliance
- **All actions must comply with Company Handbook** requirements
- **Tier enforcement must be respected** - no Tier 2/3 operations without approval
- **Error handling must follow Handbook protocols** - E1-E4 escalation procedures
- **Memory append operations must follow established templates** - maintain consistency

### Operation Restrictions
- **No hidden operations allowed** - all file access must serve active tasks
- **Operations must be idempotent** where applicable - safe to repeat without side effects
- **File locking must be respected** - do not attempt to access locked files
- **Resource limits must be observed** - stay within defined quotas

---

## ⚙️ **Relationship to Skills**

### Skill-Driven Operations
- **Capabilities execute actions requested by skills** - never act independently
- **Skills orchestrate capability usage** - capabilities are the execution layer
- **SK-012 requests workspace operations** through capability interface
- **All file operations must be skill-initiated** - no autonomous file access

### Skill-Capability Interface
- **Skills define the WHAT** (desired outcome based on task requirements)
- **Capabilities define the HOW** (specific file operations to achieve outcome)
- **Skills validate capability responses** before proceeding
- **Capabilities provide operation feedback** to requesting skills

### Execution Flow
```
SK-012 Task Executor
    ↓ (requests file operation)
CP-001 Workspace Capability
    ↓ (validates against rules)
File System Operation
    ↓ (executes with logging)
Operation Result
    ↓ (returns to skill)
SK-012 processes result
```

### Dependency Chain
- **SK-012 → CP-001** for any file reading/writing operations
- **SK-007 → CP-001** for documentation generation
- **SK-005 → CP-001** for log creation
- **All memory operations → CP-001** for safe file handling

---

## 🔒 **Security Considerations**

| Threat | Mitigation |
|--------|------------|
| **File system corruption** | Strict append-only policies where applicable |
| **Constitutional rule bypass** | Mandatory validation against Handbook |
| **Unauthorized access** | Directory boundary enforcement |
| **History modification** | Immutable file handling protocols |
| **Silent operations** | Mandatory logging requirement |
| **Skill bypass** | Capability access only through skill interface |

---

## 📊 **Usage Examples**

### Valid Usage Pattern
```
Skill Request: "Create a plan file for this task"
Capability Response: Creates PLAN_task.md in /Plans with proper template
Log Entry: Documents creation with timestamp, requesting skill, and purpose
```

### Invalid Usage Pattern
```
Skill Request: N/A (autonomous operation)
Capability Response: Would not execute (no skill request)
```

---

## 🛡️ **Governance**

- **Primary Authority**: Company Handbook §3 (Approval Rules) and §5 (Logging Requirements)
- **Implementation**: Follows Skill_Base §4 (Invocation Protocol) patterns
- **Validation**: All operations checked against constitutional rules
- **Audit Trail**: Every operation logged with full context and approval chain

---

*This capability conforms to the constitutional governance framework and must be invoked only through proper skill interfaces. All operations must maintain full auditability and compliance with established system architecture.*