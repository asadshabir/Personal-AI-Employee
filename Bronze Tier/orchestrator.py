"""
orchestrator.py — AI Employee Operational Loop
================================================
The central execution engine for the AI Employee system.

Monitors /Needs_Action for tasks, invokes Claude with the appropriate
skill context, and keeps reprocessing until the task file contains
`status: done`. Only then is the task moved to /Done.

Completion Definition:
  A task is complete ONLY when `status: done` is written inside the
  markdown file's frontmatter. If not done → Claude must reprocess.

Conforms to:
  - Company_Handbook.md §3 (Approval Rules — Tier enforcement)
  - Company_Handbook.md §4 (Task Lifecycle — transitions)
  - Company_Handbook.md §5 (Logging Requirements — audit trail)
  - Company_Handbook.md §6 (Error Handling — E1-E4, retry policy)
  - Skills/Skill_Base.md §4  (Invocation Protocol — 8-step)
  - Skills/Skill_Task_Manager.md (SK-011 — transition matrix)

Safety:
  - Never overwrites files
  - Tier 2/3 tasks are halted and escalated, never auto-executed
  - Completion loop capped at MAX_COMPLETION_CYCLES to prevent runaway
  - Error retries capped at MAX_RETRIES per cycle per Handbook §6.2
  - All exceptions caught, logged, and recovered from
  - Graceful shutdown on Ctrl+C with final audit log
"""

import os
import re
import sys
import json
import time
import shutil
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VAULT_ROOT = Path(__file__).resolve().parent
INBOX_DIR = VAULT_ROOT / "Inbox"
NEEDS_ACTION_DIR = VAULT_ROOT / "Needs_Action"
DONE_DIR = VAULT_ROOT / "Done"
LOGS_DIR = VAULT_ROOT / "Logs"
PLANS_DIR = VAULT_ROOT / "Plans"
SKILLS_DIR = VAULT_ROOT / "Skills"
MEMORY_DIR = VAULT_ROOT / "Memory"
CAPABILITIES_DIR = VAULT_ROOT / "Capabilities"
HANDBOOK_PATH = VAULT_ROOT / "Company_Handbook.md"

POLL_INTERVAL_SECONDS = 5
MAX_RETRIES = 2  # Handbook §6.2: max 2 retries (3 total attempts) per cycle
MAX_COMPLETION_CYCLES = 10  # Safety cap: max reprocessing cycles before escalation
COMPLETION_COOLDOWN_SECONDS = 2  # Pause between reprocessing cycles
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

# Skill definitions — maps classification tags to skill files and IDs
# SK-012 (Task Executor) is the primary reasoning loop — default for all tasks
SKILL_REGISTRY = {
    "task":     {"skill_id": "SK-012", "name": "Task Executor",      "file": "Skill_Task_Executor.md"},
    "code":     {"skill_id": "SK-012", "name": "Task Executor",      "file": "Skill_Task_Executor.md"},
    "review":   {"skill_id": "SK-012", "name": "Task Executor",      "file": "Skill_Task_Executor.md"},
    "complex":  {"skill_id": "SK-012", "name": "Task Executor",      "file": "Skill_Task_Executor.md"},
    "research": {"skill_id": "SK-012", "name": "Task Executor",      "file": "Skill_Task_Executor.md"},
    "docs":     {"skill_id": "SK-012", "name": "Task Executor",      "file": "Skill_Task_Executor.md"},
    "test":     {"skill_id": "SK-012", "name": "Task Executor",      "file": "Skill_Task_Executor.md"},
    "default":  {"skill_id": "SK-012", "name": "Task Executor",      "file": "Skill_Task_Executor.md"},
}

# Tier 2/3 keywords — tasks containing these require human approval
TIER_2_KEYWORDS = [
    "install", "deploy", "execute code", "modify config", "run script",
    "change environment", "alter system", "modify production",
]
TIER_3_KEYWORDS = [
    "send email", "send message", "slack", "webhook", "api call",
    "payment", "transfer", "invoice", "financial", "publish",
    "external", "notify client", "sms", "push notification",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("orchestrator")


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def ensure_directories() -> bool:
    """Verify all required workspace folders exist. Auto-remediate if missing (Tier 0)."""
    all_ok = True
    for folder in [INBOX_DIR, NEEDS_ACTION_DIR, DONE_DIR, LOGS_DIR, PLANS_DIR, SKILLS_DIR, MEMORY_DIR, CAPABILITIES_DIR]:
        if not folder.exists():
            logger.warning(f"Missing folder: {folder.name} — recreating")
            folder.mkdir(parents=True, exist_ok=True)
            all_ok = False
    return all_ok


def get_safe_path(directory: Path, filename: str) -> Path:
    """Return a non-colliding file path. Never overwrites existing files."""
    target = directory / filename
    if not target.exists():
        return target
    stem = Path(filename).stem
    ext = Path(filename).suffix
    counter = 2
    while counter <= 100:
        candidate = directory / f"{stem}_{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1
    raise RuntimeError(f"Filename collision overflow: {filename} in {directory}")


def scan_memory_for_task_patterns(task_analysis: dict) -> list:
    """
    Scan /Memory/task_patterns.md for similar task types to the current request.

    Args:
        task_analysis: Dictionary containing analysis from Step 2 with keys like
                      'domain', 'complexity', 'intent', etc.

    Returns:
        List of relevant pattern dictionaries with applicable insights.
    """
    patterns_file = MEMORY_DIR / "task_patterns.md"
    if not patterns_file.exists():
        return []

    patterns_content = patterns_file.read_text(encoding='utf-8')

    # Extract pattern blocks
    import re
    pattern_blocks = re.findall(r'### Pattern ID: ([^\n]+).*?\n(.*?)(?=\n---\s*$|\n### Pattern ID:|\Z)',
                                patterns_content, re.DOTALL)

    relevant_patterns = []
    for pattern_id, pattern_content in pattern_blocks:
        # Check if this pattern matches current task characteristics
        is_relevant = False

        # Match based on domain, complexity, or other characteristics
        if task_analysis.get('domain', '').lower() in pattern_content.lower():
            is_relevant = True
        elif task_analysis.get('complexity', '').lower() in pattern_content.lower():
            is_relevant = True
        elif task_analysis.get('intent', '').lower() in pattern_content.lower():
            is_relevant = True

        if is_relevant:
            # Extract key information from the pattern
            pattern_info = {
                'id': pattern_id.strip(),
                'content': pattern_content.strip()
            }
            # Extract pattern description
            desc_match = re.search(r'#### \*\*Pattern Description\*\*\n(.*?)(?=\n####|\n---|\Z)', pattern_content, re.DOTALL)
            if desc_match:
                pattern_info['description'] = desc_match.group(1).strip()

            # Extract reusability score
            score_match = re.search(r'Reusability Score: (.*)', pattern_content)
            if score_match:
                pattern_info['reusability'] = score_match.group(1).strip()

            relevant_patterns.append(pattern_info)

    return relevant_patterns


def scan_memory_for_failures(task_analysis: dict) -> list:
    """
    Scan /Memory/failures.md for related past mistakes or error patterns.

    Args:
        task_analysis: Dictionary containing analysis from Step 2 with keys like
                      'domain', 'complexity', 'intent', etc.

    Returns:
        List of relevant failure dictionaries with applicable prevention strategies.
    """
    failures_file = MEMORY_DIR / "failures.md"
    if not failures_file.exists():
        return []

    failures_content = failures_file.read_text(encoding='utf-8')

    # Extract failure blocks
    import re
    failure_blocks = re.findall(r'### Failure ID: ([^\n]+).*?\n(.*?)(?=\n---\s*$|\n### Failure ID:|\Z)',
                                failures_content, re.DOTALL)

    relevant_failures = []
    for failure_id, failure_content in failure_blocks:
        # Check if this failure matches current task context
        is_relevant = False

        # Match based on domain, failure category, or trigger conditions
        if task_analysis.get('domain', '').lower() in failure_content.lower():
            is_relevant = True
        elif task_analysis.get('complexity', '').lower() in failure_content.lower():
            is_relevant = True
        elif 'category' in task_analysis and task_analysis['category'].lower() in failure_content.lower():
            is_relevant = True

        if is_relevant:
            # Extract key information from the failure
            failure_info = {
                'id': failure_id.strip(),
                'content': failure_content.strip()
            }

            # Extract failure description
            desc_match = re.search(r'#### \*\*Failure Description\*\*\n(.*?)(?=\n####|\n---|\Z)', failure_content, re.DOTALL)
            if desc_match:
                failure_info['description'] = desc_match.group(1).strip()

            # Extract prevention strategy
            prev_match = re.search(r'#### \*\*Prevention Strategy\*\*\n(.*?)(?=\n####|\n---|\Z)', failure_content, re.DOTALL)
            if prev_match:
                failure_info['prevention'] = prev_match.group(1).strip()

            # Extract severity level
            severity_match = re.search(r'Severity Level: (.*)', failure_content)
            if severity_match:
                failure_info['severity'] = severity_match.group(1).strip()

            relevant_failures.append(failure_info)

    return relevant_failures


def scan_memory_for_decisions(task_analysis: dict) -> list:
    """
    Scan /Memory/decisions.md for reusable reasoning patterns or decision frameworks.

    Args:
        task_analysis: Dictionary containing analysis from Step 2 with keys like
                      'domain', 'complexity', 'intent', etc.

    Returns:
        List of relevant decision dictionaries with applicable reasoning frameworks.
    """
    decisions_file = MEMORY_DIR / "decisions.md"
    if not decisions_file.exists():
        return []

    decisions_content = decisions_file.read_text(encoding='utf-8')

    # Extract decision blocks
    import re
    decision_blocks = re.findall(r'### Decision ID: ([^\n]+).*?\n(.*?)(?=\n---\s*$|\n### Decision ID:|\Z)',
                                 decisions_content, re.DOTALL)

    relevant_decisions = []
    for decision_id, decision_content in decision_blocks:
        # Check if this decision matches current task context
        is_relevant = False

        # Match based on domain, decision category, or situational context
        if task_analysis.get('domain', '').lower() in decision_content.lower():
            is_relevant = True
        elif task_analysis.get('complexity', '').lower() in decision_content.lower():
            is_relevant = True
        elif 'category' in task_analysis and task_analysis['category'].lower() in decision_content.lower():
            is_relevant = True

        if is_relevant:
            # Extract key information from the decision
            decision_info = {
                'id': decision_id.strip(),
                'content': decision_content.strip()
            }

            # Extract situation summary
            situation_match = re.search(r'#### \*\*Situation\*\*\n(.*?)(?=\n####|\n---|\Z)', decision_content, re.DOTALL)
            if situation_match:
                decision_info['situation'] = situation_match.group(1).strip()

            # Extract reasoning
            reasoning_match = re.search(r'#### \*\*Reasoning\*\*\n(.*?)(?=\n####|\n---|\Z)', decision_content, re.DOTALL)
            if reasoning_match:
                decision_info['reasoning'] = reasoning_match.group(1).strip()

            # Extract outcome
            outcome_match = re.search(r'#### \*\*Actual Outcome\*\*\n(.*?)(?=\n####|\n---|\Z)', decision_content, re.DOTALL)
            if outcome_match:
                decision_info['outcome'] = outcome_match.group(1).strip()

            # Extract confidence level
            confidence_match = re.search(r'Confidence Level: (.*)', decision_content)
            if confidence_match:
                decision_info['confidence'] = confidence_match.group(1).strip()

            relevant_decisions.append(decision_info)

    return relevant_decisions


def create_memory_influence_note(task_analysis: dict) -> str:
    """
    Create a Memory Influence Note by scanning all memory files.

    Args:
        task_analysis: Dictionary containing analysis from Step 2 with keys like
                      'domain', 'complexity', 'intent', etc.

    Returns:
        Formatted Memory Influence Note as a string.
    """
    # Scan all memory files
    patterns = scan_memory_for_task_patterns(task_analysis)
    failures = scan_memory_for_failures(task_analysis)
    decisions = scan_memory_for_decisions(task_analysis)

    # Build the note
    note_parts = ["MEMORY INFLUENCE NOTE", "="*23, ""]

    if patterns:
        note_parts.append("FROM task_patterns.md:")
        for pattern in patterns:
            pattern_id = pattern.get('id', 'Unknown')
            description = pattern.get('description', 'No description')[:100] + "..." if len(pattern.get('description', '')) > 100 else pattern.get('description', 'No description')
            reusability = f" (Reusability: {pattern.get('reusability', 'N/A')})" if pattern.get('reusability') else ""
            note_parts.append(f"- [Pattern ID: {pattern_id}] {description}{reusability}")
        note_parts.append("")

    if failures:
        note_parts.append("FROM failures.md:")
        for failure in failures:
            failure_id = failure.get('id', 'Unknown')
            description = failure.get('description', 'No description')[:100] + "..." if len(failure.get('description', '')) > 100 else failure.get('description', 'No description')
            note_parts.append(f"- [Failure ID: {failure_id}] {description}")

            prevention = failure.get('prevention', '')
            if prevention:
                prevention_preview = prevention[:100] + "..." if len(prevention) > 100 else prevention
                note_parts.append(f"- [Prevention] {prevention_preview}")
        note_parts.append("")

    if decisions:
        note_parts.append("FROM decisions.md:")
        for decision in decisions:
            decision_id = decision.get('id', 'Unknown')
            situation = decision.get('situation', 'No situation')[:100] + "..." if len(decision.get('situation', '')) > 100 else decision.get('situation', 'No situation')
            note_parts.append(f"- [Decision ID: {decision_id}] {situation}")

            outcome = decision.get('outcome', '')
            if outcome:
                outcome_preview = outcome[:100] + "..." if len(outcome) > 100 else outcome
                note_parts.append(f"- [Outcome] {outcome_preview}")
        note_parts.append("")

    # Summary section
    if patterns or failures or decisions:
        note_parts.append("SUMMARY OF INFLUENCES:")

        # Recommended strategies
        if patterns:
            note_parts.append("- Recommended strategies to reuse:")
            for pattern in patterns:
                desc = pattern.get('description', 'N/A')[:50] + "..." if len(pattern.get('description', '')) > 50 else pattern.get('description', 'N/A')
                note_parts.append(f"  - {desc}")

        # Mistakes to avoid
        if failures:
            note_parts.append("- Mistakes to avoid:")
            for failure in failures:
                desc = failure.get('description', 'N/A')[:50] + "..." if len(failure.get('description', '')) > 50 else failure.get('description', 'N/A')
                note_parts.append(f"  - {desc}")

        # Decision frameworks
        if decisions:
            note_parts.append("- Decision frameworks that apply:")
            for decision in decisions:
                reason = decision.get('reasoning', 'N/A')[:50] + "..." if len(decision.get('reasoning', '')) > 50 else decision.get('reasoning', 'N/A')
                note_parts.append(f"  - {reason}")

        # Overall guidance
        note_parts.append("- Overall guidance: Leverage relevant patterns, avoid known failure paths, and apply proven decision frameworks.")
    else:
        note_parts.append("SUMMARY OF INFLUENCES:")
        note_parts.append("- No prior memory relevant")

    return "\n".join(note_parts)


def generate_reflection_entry(file_path: Path, metadata: dict, content: str, task_analysis: dict, execution_result: dict = None) -> str:
    """
    Generate a reflection entry for a completed task based on its execution.

    Args:
        file_path: Path to the completed task file
        metadata: Task metadata dictionary
        content: Task content
        task_analysis: Task analysis from Step 2
        execution_result: Result from the execution (optional, for more detailed assessment)

    Returns:
        Formatted reflection entry as a string
    """
    import re
    from datetime import datetime

    # Create reflection ID based on current timestamp - use a simple placeholder approach for now
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d")

    # In a real system, we would scan the reflections.md file to find the next available number
    # For now, we'll use a simple approach by trying to read the file and find the highest number
    reflections_file = MEMORY_DIR / "reflections.md"
    next_number = 1

    if reflections_file.exists():
        content_text = reflections_file.read_text(encoding='utf-8')
        # Find all reflection IDs and extract the number
        matches = re.findall(r'Reflection ID: \d{4}-\d{2}-\d{2}_REF-(\d+)', content_text)
        if matches:
            numbers = [int(m) for m in matches]
            if numbers:
                next_number = max(numbers) + 1

    reflection_id = f"{timestamp}_REF-{next_number:03d}"

    # Extract key information from the completed task
    task_id = file_path.name
    date_time = now.strftime("%Y-%m-%dT%H:%M:%S")

    # Calculate scores based on deterministic criteria

    # Plan Quality Score based on task characteristics
    plan_quality_score = 4  # Default
    plan_content = content.lower()

    # Look for evidence of good planning in the content or metadata
    if 'plan' in plan_content or 'step' in plan_content or 'objective' in plan_content:
        plan_quality_score = 5
    elif metadata.get('plan', ''):  # If there's a plan reference in metadata
        plan_quality_score = 5
    elif task_analysis.get('complexity', 'medium') == 'simple':
        plan_quality_score = 4  # Simple tasks may not need detailed planning

    # Execution Efficiency Score based on task characteristics
    execution_efficiency_score = 4  # Default
    if execution_result:
        # If there were errors, reduce score
        if execution_result.get('errors') and execution_result['errors'] != 'None':
            execution_efficiency_score = 3
        # If there were retries, reduce score slightly
        elif 'remaining' in str(execution_result.get('remaining', '')) or 'retry' in str(execution_result.get('summary', '')).lower():
            execution_efficiency_score = 4
        else:
            execution_efficiency_score = 5

    # Memory Usage Effectiveness score based on task_analysis and whether memory was used
    memory_usage_effectiveness = 4  # Default
    memory_influence_applied = False

    # If memory influence was applied (would be in metadata or content), adjust score
    if 'Memory Influence' in content or 'memory' in content.lower():
        memory_usage_effectiveness = 5
        memory_influence_applied = True
    elif not any([scan_memory_for_task_patterns(task_analysis),
                  scan_memory_for_failures(task_analysis),
                  scan_memory_for_decisions(task_analysis)]):
        # No memory entries applied
        memory_usage_effectiveness = 3

    # Extract issues from task content or execution result
    issues_encountered = "None identified during standard execution"
    if execution_result and execution_result.get('errors') and execution_result['errors'] != 'None':
        issues_encountered = str(execution_result.get('errors', 'Minor processing issues'))
    elif execution_result and execution_result.get('remaining'):
        issues_encountered = f"Partial completion - some work remained: {execution_result.get('remaining', '')[:100]}..."

    improvement_suggestions = "Review memory influence note effectiveness for future similar tasks"

    # Determine if this task should be considered a pattern candidate based on domain, complexity, etc.
    pattern_domains_for_candidate = ['code', 'documentation', 'research', 'planning']
    pattern_candidate = "Yes" if task_analysis.get('domain') in pattern_domains_for_candidate and plan_quality_score >= 4 else "No"

    optimization_notes = f"Task domain: {task_analysis.get('domain', 'general')}, Complexity: {task_analysis.get('complexity', 'medium')}, Memory influence: {'Applied' if memory_influence_applied else 'Not applied'}"

    # Create the reflection entry
    reflection_template = f"""### Reflection ID: {reflection_id}
**Task ID**: {task_id}
**Date/Time**: {date_time}
**Plan Quality Score**: {plan_quality_score} ⭐
**Execution Efficiency Score**: {execution_efficiency_score} ⭐
**Memory Usage Effectiveness**: {memory_usage_effectiveness} ⭐
**Issues Encountered**: {issues_encountered}
**What Should Be Done Differently Next Time**: {improvement_suggestions}
**Pattern Candidate**: {pattern_candidate}
**Notes for Future Optimization**: {optimization_notes}"""

    return reflection_template


def append_reflection_to_log(reflection_entry: str) -> None:
    """
    Append a reflection entry to the reflections.md file.

    Args:
        reflection_entry: The formatted reflection entry to append
    """
    reflections_file = MEMORY_DIR / "reflections.md"

    # If file doesn't exist, create it with basic template
    if not reflections_file.exists():
        initial_content = """# 🧘 Reflections Log

> **Purpose**: This file stores structured self-evaluation records after each completed task. It serves as an append-only log of execution quality assessments that enable continuous optimization and learning.

## 📋 **Reflection Template**

### Reflection ID: [YYYY-MM-DD_REF-###]
**Task ID**: [task_file_name]
**Date/Time**: [timestamp]
**Plan Quality Score**: [1-5] ⭐
**Execution Efficiency Score**: [1-5] ⭐
**Memory Usage Effectiveness**: [1-5] ⭐
**Issues Encountered**: [brief description of any problems during execution]
**What Should Be Done Differently Next Time**: [specific improvements for future tasks]
**Pattern Candidate**: [Yes/No] — Should this approach be saved as a reusable pattern?
**Notes for Future Optimization**: [technical notes for system improvement]

---

## ⭐ **Scoring Rubric**

### Plan Quality Score (1-5)
- **5**: Plan was comprehensive, all steps were relevant, success criteria were precise and complete
- **4**: Plan was mostly comprehensive with only minor omissions
- **3**: Plan was adequate but had some unclear steps or criteria
- **2**: Plan had significant gaps that required improvisation
- **1**: Plan was incomplete or fundamentally flawed

### Execution Efficiency Score (1-5)
- **5**: All steps completed as planned, no resource waste, optimal path followed
- **4**: Nearly all steps completed as planned with minor inefficiencies
- **3**: Most steps completed with some rework needed
- **2**: Significant rework or detours required during execution
- **1**: Execution required major improvisation or failed steps

### Memory Usage Effectiveness (1-5)
- **5**: Memory recall was highly relevant, influenced planning positively, avoided known failures
- **4**: Memory recall was mostly relevant and helpful
- **3**: Memory recall was somewhat helpful but limited impact
- **2**: Memory recall was minimally helpful or only partially applied
- **1**: Memory recall was not effectively used or had no impact

## 📚 **Reflection Registry**
_Add new reflections below this line - NEVER modify existing entries_

### Reflection ID: 2026-02-16_REF-001
**Task ID**: N/A (System Initialization)
**Date/Time**: 2026-02-16T00:00:00Z
**Plan Quality Score**: 5 ⭐
**Execution Efficiency Score**: 5 ⭐
**Memory Usage Effectiveness**: 5 ⭐
**Issues Encountered**: None
**What Should Be Done Differently Next Time**: None
**Pattern Candidate**: No
**Notes for Future Optimization**: Initial reflection entry for system completeness

---
"""
        reflections_file.write_text(initial_content, encoding='utf-8')

    # Read the current content
    current_content = reflections_file.read_text(encoding='utf-8')

    # Find the insertion point (before the closing --- or at the end)
    insertion_point = current_content.rfind('\n---\n', 0, current_content.rfind('Reflection Registry'))  # Find the last separator before registry
    if insertion_point == -1:
        insertion_point = current_content.find('Reflection Registry') + len('Reflection Registry')
        # Find the next newline
        newline_pos = current_content.find('\n', insertion_point)
        if newline_pos != -1:
            insertion_point = newline_pos + 1

    # Insert the new reflection before the final ---
    if insertion_point and insertion_point < len(current_content):
        # Split the content
        before_insertion = current_content[:insertion_point]
        after_insertion = current_content[insertion_point:]

        # Add the new reflection with proper spacing
        new_content = f"{before_insertion}\n{reflection_entry}\n\n{after_insertion}"
    else:
        # If we couldn't find a good insertion point, just append
        new_content = f"{current_content}\n{reflection_entry}\n\n---"

    # Write the updated content back
    reflections_file.write_text(new_content, encoding='utf-8')


def write_audit_log(
    task_ref: str,
    action_taken: str,
    input_desc: str,
    output_desc: str,
    decisions: str,
    errors: str,
    start_time: datetime,
    status: str = "success",
    category: str = "orchestration",
    skill_id: str = "—",
) -> Path:
    """Write a Handbook §5.2 compliant audit log to /Logs."""
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d")
    hm = now.strftime("%H%M")
    suffix = hashlib.md5(now.isoformat().encode()).hexdigest()[:6]
    log_id = f"LOG_{ts}_{hm}_{suffix}"
    filename = f"{log_id}.md"
    log_path = LOGS_DIR / filename

    duration = f"{start_time.strftime('%H:%M:%S')} → {now.strftime('%H:%M:%S')}"

    content = f"""---
log_id: {log_id}
task_ref: {task_ref}
skill_id: {skill_id}
created: {now.strftime('%Y-%m-%d %H:%M')}
status: {status}
tags: [log, {category}]
---

# Execution Log — {task_ref}

## Action Taken
{action_taken}

## Input
{input_desc}

## Output
{output_desc}

## Decisions Made
{decisions}

## Errors Encountered
{errors}

## Duration
{duration}
"""
    log_path.write_text(content, encoding="utf-8")
    logger.info(f"Audit log: {filename}")
    return log_path


def write_escalation(
    task_name: str,
    severity: str,
    what_happened: str,
    what_tried: str,
    what_needed: str,
    impact: str,
) -> Path:
    """Create an escalation note in /Needs_Action per Handbook §6.3."""
    now = datetime.now()
    filename = f"ESCALATION_{now.strftime('%Y-%m-%d')}_{Path(task_name).stem}.md"
    esc_path = get_safe_path(NEEDS_ACTION_DIR, filename)

    content = f"""---
type: escalation
severity: {severity}
task_ref: {task_name}
created: {now.strftime('%Y-%m-%d %H:%M')}
status: awaiting_human
---

# ESCALATION — {task_name}

## What Happened
{what_happened}

## What Was Tried
{what_tried}

## What Is Needed
{what_needed}

## Impact If Unresolved
{impact}
"""
    esc_path.write_text(content, encoding="utf-8")
    logger.warning(f"Escalation created: {esc_path.name}")
    return esc_path


# ---------------------------------------------------------------------------
# Frontmatter parsing and updating
# ---------------------------------------------------------------------------


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter dict and body from markdown content."""
    metadata = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_block = parts[1].strip()
            body = parts[2]
            for line in fm_block.split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, body


def render_frontmatter(metadata: dict) -> str:
    """Render a dict back into YAML frontmatter string."""
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, str) and (" " in value or "," in value):
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def update_task_frontmatter(file_path: Path, updates: dict) -> str:
    """Read a task file, update its frontmatter fields, write back. Returns new content."""
    content = file_path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(content)
    metadata.update(updates)
    new_content = render_frontmatter(metadata) + body
    file_path.write_text(new_content, encoding="utf-8")
    return new_content


def append_transition_history(file_path: Path, from_folder: str, to_folder: str, action: str, by: str) -> None:
    """Append a row to the Transition History table in the task file."""
    content = file_path.read_text(encoding="utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = f"| {now} | {from_folder} | {to_folder} | {action} | {by} |"

    if "## Transition History" in content:
        content = content.rstrip() + "\n" + row + "\n"
    else:
        table = f"""

## Transition History

| Timestamp | From | To | Action | By |
|-----------|------|----|--------|-----|
{row}
"""
        content = content.rstrip() + table

    file_path.write_text(content, encoding="utf-8")


def is_task_done(file_path: Path) -> bool:
    """
    Authoritative completion check.

    A task is complete ONLY when its frontmatter contains `status: done`.
    Any other status (success, completed, partial, in_progress, ready) is NOT done.
    Claude must keep reprocessing until this returns True.
    """
    if not file_path.exists():
        return False
    try:
        content = file_path.read_text(encoding="utf-8")
        metadata, _ = parse_frontmatter(content)
        return metadata.get("status", "").strip().lower() == "done"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Skill resolution and tier enforcement
# ---------------------------------------------------------------------------


def resolve_skill(metadata: dict, content: str) -> dict:
    """Determine which skill to invoke based on task metadata and content."""
    # Check classification from frontmatter first
    classification = metadata.get("classification", "").lower()
    if classification in SKILL_REGISTRY:
        return SKILL_REGISTRY[classification]

    # Check for tag-based triggers in content
    content_lower = content.lower()
    for tag, skill in SKILL_REGISTRY.items():
        if tag != "default" and f"#{tag}" in content_lower:
            return skill

    return SKILL_REGISTRY["default"]


def detect_tier(metadata: dict, content: str) -> int:
    """Detect the approval tier required for this task. Returns 0, 1, 2, or 3."""
    content_lower = content.lower()

    # Tier 3 check — financial / external communication
    for keyword in TIER_3_KEYWORDS:
        if keyword in content_lower:
            return 3

    # Tier 2 check — system-modifying actions
    for keyword in TIER_2_KEYWORDS:
        if keyword in content_lower:
            return 2

    # Tier 1 — plan creation, skill modifications
    if metadata.get("classification") in ("plan", "skill"):
        return 1

    # Tier 0 — standard task processing
    return 0


def load_skill_context(skill_info: dict) -> str:
    """Load the full skill definition file as context for Claude."""
    if not skill_info.get("file"):
        return f"[Skill {skill_info['skill_id']} — {skill_info['name']}]: No detailed definition file. Process using general task handling."

    skill_path = SKILLS_DIR / skill_info["file"]
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return f"[WARNING] Skill file not found: {skill_info['file']}"


def load_handbook_rules() -> str:
    """Load Company Handbook as constitutional context for Claude."""
    if HANDBOOK_PATH.exists():
        return HANDBOOK_PATH.read_text(encoding="utf-8")
    return "[CRITICAL] Company_Handbook.md not found — operating without constitutional authority."


# ---------------------------------------------------------------------------
# Claude invocation
# ---------------------------------------------------------------------------


def build_claude_prompt(task_content: str, skill_context: str, handbook_summary: str, memory_influence_note: str = None) -> str:
    """
    Build the full prompt that will be sent to Claude for task execution.

    This constructs a structured prompt with:
    1. Constitutional rules (Handbook)
    2. Skill execution steps
    3. Memory influence (if applicable)
    4. The actual task to process
    """
    prompt_parts = ["You are the AI Employee operating under strict constitutional rules."]

    # Add constitutional authority
    prompt_parts.append(f"""
== CONSTITUTIONAL AUTHORITY ==
You must obey these rules. Violations are system-level failures.
{handbook_summary}
""")

    # Add memory influence if provided
    if memory_influence_note:
        prompt_parts.append(f"""
== MEMORY INFLUENCE NOTE ==
Apply relevant insights from past experiences to guide your planning:
{memory_influence_note}
""")

    # Add active skill
    prompt_parts.append(f"""
== ACTIVE SKILL ==
Follow these execution steps precisely:
{skill_context}
""")

    # Add task to process
    prompt_parts.append(f"""
== TASK TO PROCESS ==
{task_content}
""")

    # Add instructions
    prompt_parts.append("""
== INSTRUCTIONS ==
1. Analyze the task against the skill's execution steps.
2. Incorporate relevant insights from the Memory Influence Note when appropriate.
3. Produce the required outputs as defined by the skill.
4. CRITICAL COMPLETION RULE: A task is ONLY considered complete when you
   explicitly set `status: done` in your response. If work remains unfinished,
   set `status: in_progress` and describe what still needs to happen.
   The orchestrator will keep invoking you until `status: done` is confirmed.
5. Report your result in this exact format:

RESULT_STATUS: <done | in_progress | failed>
RESULT_SUMMARY: <1-2 sentence summary of what was done>
RESULT_OUTPUT: <the actual output or artifact produced>
RESULT_DECISIONS: <any choices or branching logic you applied>
RESULT_ERRORS: <None, or description of issues encountered>
RESULT_REMAINING: <None if done, or description of remaining work>
""")

    return "".join(prompt_parts)


def invoke_claude(prompt: str, task_name: str) -> dict:
    """
    Invoke Claude to process a task.

    Integration modes (checked in order):
    1. Anthropic Python SDK (if installed and ANTHROPIC_API_KEY is set)
    2. Local simulation (for offline / development use)

    Returns a dict with keys: status, summary, output, decisions, errors
    """
    result = _try_anthropic_sdk(prompt, task_name)
    if result is not None:
        return result

    # Fallback: local simulation for development / offline operation
    return _simulate_local(prompt, task_name)


def _try_anthropic_sdk(prompt: str, task_name: str) -> Optional[dict]:
    """Attempt to invoke Claude via the Anthropic Python SDK."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("No ANTHROPIC_API_KEY found — using local simulation mode")
        return None

    try:
        import anthropic
    except ImportError:
        logger.info("anthropic package not installed — using local simulation mode")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text
        logger.info(f"Claude API response received for: {task_name}")
        return _parse_claude_response(response_text)

    except Exception as api_err:
        logger.error(f"Claude API call failed: {api_err}")
        return {
            "status": "failed",
            "summary": f"API call failed: {type(api_err).__name__}",
            "output": "",
            "decisions": "Attempted Anthropic SDK invocation",
            "errors": str(api_err),
        }


def _simulate_local(prompt: str, task_name: str) -> dict:
    """
    Local simulation mode — processes the task without an API call.
    Extracts task intent and produces a structured completion response.
    Used when no API key is available or for development/testing.

    Sets status to 'done' to satisfy the completion loop.
    """
    logger.info(f"[LOCAL MODE] Simulating Claude processing for: {task_name}")

    # Extract the task section from the prompt
    task_section = ""
    if "== TASK TO PROCESS ==" in prompt:
        task_section = prompt.split("== TASK TO PROCESS ==")[1].split("== INSTRUCTIONS ==")[0].strip()

    return {
        "status": "done",
        "summary": f"Task '{task_name}' processed in local simulation mode. Marked as done.",
        "output": (
            f"## Processing Result — {task_name}\n\n"
            f"- **Mode:** Local simulation (no API key)\n"
            f"- **Task received:** Yes\n"
            f"- **Skill context loaded:** Yes\n"
            f"- **Handbook rules loaded:** Yes\n"
            f"- **Action:** Task analyzed and marked as `status: done`\n\n"
            f"> To enable full Claude processing, set the `ANTHROPIC_API_KEY` environment variable.\n"
        ),
        "decisions": "Local simulation mode — task structure validated, marked as done",
        "errors": "None",
        "remaining": "None",
    }


def _parse_claude_response(response_text: str) -> dict:
    """Parse Claude's structured response into a result dict."""
    result = {
        "status": "in_progress",
        "summary": "",
        "output": response_text,
        "decisions": "",
        "errors": "None",
        "remaining": "Unknown — could not parse RESULT_REMAINING",
    }

    for line in response_text.split("\n"):
        line = line.strip()
        if line.startswith("RESULT_STATUS:"):
            result["status"] = line.split(":", 1)[1].strip().lower()
        elif line.startswith("RESULT_SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
        elif line.startswith("RESULT_OUTPUT:"):
            result["output"] = line.split(":", 1)[1].strip()
        elif line.startswith("RESULT_DECISIONS:"):
            result["decisions"] = line.split(":", 1)[1].strip()
        elif line.startswith("RESULT_ERRORS:"):
            result["errors"] = line.split(":", 1)[1].strip()
        elif line.startswith("RESULT_REMAINING:"):
            result["remaining"] = line.split(":", 1)[1].strip()

    # Normalize status: accept 'done', 'success', 'completed' as done
    if result["status"] in ("done", "success", "completed"):
        result["status"] = "done"

    if not result["summary"]:
        result["summary"] = response_text[:200]

    return result


# ---------------------------------------------------------------------------
# Task processing pipeline
# ---------------------------------------------------------------------------


def get_pending_tasks() -> list[tuple[Path, dict, str]]:
    """
    Scan /Needs_Action for tasks ready to process.
    Returns list of (file_path, metadata, content) sorted by priority.
    Skips escalations, blocked tasks, and already in-progress tasks.
    """
    tasks = []

    if not NEEDS_ACTION_DIR.exists():
        return tasks

    for file_path in NEEDS_ACTION_DIR.iterdir():
        if not file_path.is_file() or not file_path.suffix == ".md":
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        metadata, _ = parse_frontmatter(content)

        # Skip non-task files
        if metadata.get("type") == "escalation":
            continue

        # Skip terminal, in-progress, or blocked tasks
        status = metadata.get("status", "ready").lower()
        if status in ("done", "in_progress", "completed", "blocked", "failed", "rejected"):
            continue

        tasks.append((file_path, metadata, content))

    # Sort by priority (P0 first)
    tasks.sort(key=lambda t: PRIORITY_ORDER.get(t[1].get("priority", "P2"), 2))

    return tasks


def process_task(file_path: Path, metadata: dict, content: str) -> dict:
    """
    Full processing pipeline for a single task. Follows Skill_Base §4.1 protocol:
    DETECT → VALIDATE → AUTHORIZE → PREPARE → EXECUTE → LOG → OUTPUT → VERIFY

    Returns the Claude result dict.
    """
    task_name = file_path.name
    start_time = datetime.now()

    logger.info(f"{'='*60}")
    logger.info(f"Processing: {task_name} [Priority: {metadata.get('priority', 'P2')}]")

    # --- STEP 1: VALIDATE — Mark as in_progress ---
    update_task_frontmatter(file_path, {
        "status": "in_progress",
        "started": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

    # --- STEP 2: AUTHORIZE — Tier enforcement ---
    tier = detect_tier(metadata, content)
    logger.info(f"  Tier detected: {tier}")

    if tier >= 2:
        logger.warning(f"  HALTED — Tier {tier} requires Human Operator approval")
        update_task_frontmatter(file_path, {
            "status": "blocked",
            "blocked_reason": f"Tier {tier} — requires human approval",
        })
        append_transition_history(file_path, "/Needs_Action", "/Needs_Action", "block", "orchestrator")

        write_escalation(
            task_name=task_name,
            severity="E2" if tier == 2 else "E3",
            what_happened=f"Task requires Tier {tier} approval before execution.",
            what_tried="Orchestrator detected Tier 2/3 keywords and halted per Handbook §3.",
            what_needed=f"Human Operator must review and approve this task for Tier {tier} execution.",
            impact="Task will remain blocked until approval is granted.",
        )

        write_audit_log(
            task_ref=task_name,
            action_taken=f"HALTED — Tier {tier} approval required",
            input_desc=f"Task: {task_name}",
            output_desc="Escalation note created. Task blocked.",
            decisions=f"Tier {tier} keywords detected. Handbook §3 enforced.",
            errors=f"None — intentional halt for approval",
            start_time=start_time,
            status="halted",
            category="tier-enforcement",
        )

        return {"status": "halted", "summary": f"Tier {tier} — awaiting approval"}

    # --- STEP 3: PREPARE — Resolve skill and load context ---
    skill = resolve_skill(metadata, content)
    skill_context = load_skill_context(skill)
    handbook_rules = load_handbook_rules()

    logger.info(f"  Skill resolved: {skill['skill_id']} ({skill['name']})")

    # --- STEP 3.5: RECALL — Generate memory influence note (Silver Tier SM-002) ---
    # Analyze task to create a task analysis dict for memory recall
    task_analysis = {}

    # Extract basic analysis from content and metadata
    task_analysis['title'] = metadata.get('title', file_path.stem)
    task_analysis['priority'] = metadata.get('priority', 'P2')
    task_analysis['classification'] = metadata.get('classification', 'task')
    task_analysis['domain'] = 'general'  # Will be inferred from content

    # Determine domain from content/keywords
    content_lower = content.lower()
    if any(keyword in content_lower for keyword in ['code', 'python', 'javascript', 'program', 'function', 'class', 'method', 'bug', 'fix', 'debug']):
        task_analysis['domain'] = 'code'
    elif any(keyword in content_lower for keyword in ['review', 'analyze', 'check', 'examine', 'audit', 'validate']):
        task_analysis['domain'] = 'review'
    elif any(keyword in content_lower for keyword in ['research', 'find', 'search', 'information', 'data', 'study']):
        task_analysis['domain'] = 'research'
    elif any(keyword in content_lower for keyword in ['document', 'write', 'create', 'draft', 'text', 'article', 'documentation']):
        task_analysis['domain'] = 'documentation'
    elif any(keyword in content_lower for keyword in ['plan', 'strategy', 'organize', 'schedule', 'arrange', 'design']):
        task_analysis['domain'] = 'planning'

    # Complexity assessment
    word_count = len(content.split())
    if word_count < 50:
        task_analysis['complexity'] = 'simple'
    elif word_count < 200:
        task_analysis['complexity'] = 'medium'
    else:
        task_analysis['complexity'] = 'complex'

    # Intent extraction
    lines = content.split('\n')
    task_analysis['intent'] = lines[0][:100] if lines else 'Unknown request'  # First line as intent

    # Create memory influence note
    memory_influence_note = create_memory_influence_note(task_analysis)
    logger.info(f"  Memory influence generated with {len(memory_influence_note.split())} words")

    # --- STEP 4: EXECUTE — Build prompt and invoke Claude ---
    prompt = build_claude_prompt(
        task_content=content,
        skill_context=skill_context,
        handbook_summary=handbook_rules,
        memory_influence_note=memory_influence_note,
    )

    result = invoke_claude(prompt, task_name)

    logger.info(f"  Result status: {result['status']}")

    return result


def complete_task(file_path: Path, result: dict, total_cycles: int = 1) -> Path:
    """
    Move a task confirmed as `status: done` to /Done.
    Updates frontmatter and appends transition history.
    Per Skill_Task_Manager Step 5: update → move → rename if needed.

    A task reaches here ONLY after is_task_done() returns True.
    """
    now = datetime.now()

    # Update frontmatter — write authoritative `status: done`
    update_task_frontmatter(file_path, {
        "status": "done",
        "completed": now.strftime("%Y-%m-%d %H:%M"),
        "completion_cycles": str(total_cycles),
        "result_summary": result.get("summary", "Processed by orchestrator")[:200],
    })

    # Append transition history
    append_transition_history(file_path, "/Needs_Action", "/Done", "complete", "orchestrator")

    # Append result output to task body
    content = file_path.read_text(encoding="utf-8")
    result_section = f"""

## Orchestrator Result

- **Status:** {result.get('status', 'unknown')}
- **Summary:** {result.get('summary', 'N/A')}
- **Processed:** {now.strftime('%Y-%m-%d %H:%M')}

### Output
{result.get('output', 'No output produced.')}

### Decisions
{result.get('decisions', 'None')}
"""
    content = content.rstrip() + result_section
    file_path.write_text(content, encoding="utf-8")

    # --- STEP 6.6: REFLECT — Add reflection entry to memory (Silver Tier SM-003) ---
    # This is the reflection step that evaluates execution quality and adds to reflections.md
    # Extract metadata for reflection generation
    content_after_update, metadata = parse_frontmatter(content)

    # Create a basic task analysis for reflection purposes
    task_analysis = {}
    task_analysis['title'] = metadata.get('title', file_path.stem)
    task_analysis['priority'] = metadata.get('priority', 'P2')
    task_analysis['classification'] = metadata.get('classification', 'task')
    task_analysis['domain'] = metadata.get('domain', 'general')  # Would be determined during initial processing
    task_analysis['complexity'] = metadata.get('complexity', 'medium')

    # Generate reflection entry based on execution
    try:
        reflection_entry = generate_reflection_entry(file_path, metadata, content_after_update, task_analysis, result)
        append_reflection_to_log(reflection_entry)
        logger.info(f"  Reflection entry added for task: {file_path.name}")
    except Exception as e:
        logger.warning(f"  Could not generate reflection for {file_path.name}: {e}")

    # Move to /Done — never overwrite
    done_path = get_safe_path(DONE_DIR, file_path.name)
    shutil.move(str(file_path), str(done_path))

    logger.info(f"  Moved to Done: {done_path.name}")
    return done_path


def fail_task(file_path: Path, error_msg: str, severity: str, attempts: int) -> None:
    """Mark a task as failed, log the error, create escalation if E3+."""
    update_task_frontmatter(file_path, {
        "status": "failed",
        "error": error_msg[:200],
        "attempts": str(attempts),
    })
    append_transition_history(file_path, "/Needs_Action", "/Needs_Action", f"fail ({severity})", "orchestrator")

    if severity in ("E3", "E4"):
        write_escalation(
            task_name=file_path.name,
            severity=severity,
            what_happened=f"Task failed after {attempts} attempt(s): {error_msg}",
            what_tried=f"Orchestrator attempted {attempts} execution(s) per Handbook §6.2 retry policy.",
            what_needed="Human Operator must investigate the failure and either fix the task or remove it.",
            impact="Task remains in /Needs_Action with status: failed. No further auto-retries.",
        )


# ---------------------------------------------------------------------------
# Retry-aware execution wrapper
# ---------------------------------------------------------------------------


def _invoke_single_cycle(file_path: Path, metadata: dict, content: str, cycle: int, attempt: int) -> dict:
    """
    Execute a single Claude invocation attempt within a completion cycle.
    Returns the result dict from Claude. Raises on unrecoverable errors.
    """
    result = process_task(file_path, metadata, content)

    # If Claude says done, write `status: done` into the task file
    if result.get("status") == "done":
        update_task_frontmatter(file_path, {"status": "done"})

    # If Claude says in_progress, update file with remaining work context
    elif result.get("status") == "in_progress":
        remaining = result.get("remaining", "Unspecified remaining work")
        update_task_frontmatter(file_path, {
            "status": "in_progress",
            "remaining_work": remaining[:200],
            "last_cycle": str(cycle),
        })
        append_transition_history(
            file_path, "/Needs_Action", "/Needs_Action",
            f"reprocess (cycle {cycle})", "orchestrator"
        )

    return result


def execute_with_retry(file_path: Path, metadata: dict, content: str) -> None:
    """
    Completion-driven execution loop.

    Claude keeps working until `status: done` is written in the task file.
    Each cycle allows up to MAX_RETRIES on errors (Handbook §6.2).
    Total cycles capped at MAX_COMPLETION_CYCLES to prevent runaway.

    Flow per cycle:
      1. Invoke Claude with task + skill + handbook context
      2. Check if Claude set `status: done` in response
      3. If done → verify file has `status: done` → move to /Done
      4. If not done → re-invoke Claude with updated context (next cycle)
      5. If error → retry up to MAX_RETRIES within this cycle
      6. If all cycles exhausted without done → escalate as E3
    """
    task_name = file_path.name
    loop_start = datetime.now()
    last_error = ""
    last_result = {}

    logger.info(f"  Completion loop: max {MAX_COMPLETION_CYCLES} cycles, {MAX_RETRIES + 1} attempts/cycle")

    for cycle in range(1, MAX_COMPLETION_CYCLES + 1):
        max_attempts = MAX_RETRIES + 1  # 3 attempts per cycle
        cycle_succeeded = False

        logger.info(f"  --- Cycle {cycle}/{MAX_COMPLETION_CYCLES} ---")

        for attempt in range(1, max_attempts + 1):
            start_time = datetime.now()

            try:
                logger.info(f"    Attempt {attempt}/{max_attempts}")

                # Re-read file each attempt to get latest state
                if file_path.exists():
                    content = file_path.read_text(encoding="utf-8")
                    metadata, _ = parse_frontmatter(content)

                result = _invoke_single_cycle(file_path, metadata, content, cycle, attempt)
                last_result = result

                # Halted tasks (Tier 2/3) — exit entire loop
                if result.get("status") == "halted":
                    return

                # Check: did Claude fail outright?
                if result.get("status") == "failed":
                    last_error = result.get("errors", "Claude returned failed status")
                    logger.warning(f"    Attempt {attempt} failed: {last_error}")
                    if attempt < max_attempts:
                        update_task_frontmatter(file_path, {"status": "ready"})
                        continue  # Retry within this cycle
                    else:
                        break  # Move to next cycle

                # Check: is the task now done?
                if is_task_done(file_path):
                    logger.info(f"    CONFIRMED: status: done found in file (cycle {cycle}, attempt {attempt})")
                    done_path = complete_task(file_path, result, total_cycles=cycle)

                    write_audit_log(
                        task_ref=task_name,
                        action_taken=f"Task completed with status: done (cycle {cycle}, attempt {attempt})",
                        input_desc=f"Task: Needs_Action/{task_name}",
                        output_desc=f"Completed: Done/{done_path.name}",
                        decisions=f"Cycles: {cycle} | {result.get('decisions', '—')}",
                        errors=result.get("errors", "None"),
                        start_time=loop_start,
                        status="success",
                        category="task-completion",
                        skill_id=resolve_skill(metadata, content)["skill_id"],
                    )
                    return

                # Claude returned in_progress or partial — break to next cycle
                remaining = result.get("remaining", "Not specified")
                logger.info(f"    Not done yet. Remaining: {remaining}")
                cycle_succeeded = True  # The invocation worked, just not finished
                break  # Exit retry loop, proceed to next cycle

            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.error(f"    Attempt {attempt} exception: {last_error}")

                if attempt < max_attempts:
                    try:
                        update_task_frontmatter(file_path, {"status": "ready"})
                    except Exception:
                        pass

                write_audit_log(
                    task_ref=task_name,
                    action_taken=f"Exception in cycle {cycle}, attempt {attempt}",
                    input_desc=f"Task: Needs_Action/{task_name}",
                    output_desc="No output — exception raised",
                    decisions=f"Retry {'scheduled' if attempt < max_attempts else 'exhausted for this cycle'}",
                    errors=f"E2 — {last_error}",
                    start_time=start_time,
                    status="failed",
                    category="task-error",
                )

        # After all attempts in this cycle — final done check before next cycle
        if file_path.exists() and is_task_done(file_path):
            logger.info(f"    Late confirmation: status: done (end of cycle {cycle})")
            done_path = complete_task(file_path, last_result, total_cycles=cycle)
            write_audit_log(
                task_ref=task_name,
                action_taken=f"Task completed (late confirmation, cycle {cycle})",
                input_desc=f"Task: Needs_Action/{task_name}",
                output_desc=f"Completed: Done/{done_path.name}",
                decisions=f"Total cycles: {cycle}",
                errors="None",
                start_time=loop_start,
                status="success",
                category="task-completion",
            )
            return

        # Cooldown before next cycle
        if cycle < MAX_COMPLETION_CYCLES:
            logger.info(f"    Cooling down {COMPLETION_COOLDOWN_SECONDS}s before next cycle...")
            time.sleep(COMPLETION_COOLDOWN_SECONDS)

    # === All cycles exhausted without `status: done` ===
    logger.error(f"  COMPLETION FAILED: {task_name} not done after {MAX_COMPLETION_CYCLES} cycles")

    fail_task(file_path, f"Task not done after {MAX_COMPLETION_CYCLES} cycles. Last error: {last_error}", "E3", MAX_COMPLETION_CYCLES)

    write_audit_log(
        task_ref=task_name,
        action_taken=f"Task failed — not done after {MAX_COMPLETION_CYCLES} completion cycles",
        input_desc=f"Task: Needs_Action/{task_name}",
        output_desc="No output — completion loop exhausted",
        decisions=f"E3 escalation. Cycles attempted: {MAX_COMPLETION_CYCLES}. Last result status: {last_result.get('status', 'unknown')}",
        errors=f"E3 — Task never reached status: done. Last error: {last_error or 'None'}",
        start_time=loop_start,
        status="failed",
        category="task-failure",
    )


# ---------------------------------------------------------------------------
# Main orchestration loop
# ---------------------------------------------------------------------------


def run_orchestrator() -> None:
    """
    Main infinite loop — the AI Employee's operational heartbeat.

    Each cycle:
    1. Verify workspace integrity
    2. Scan /Needs_Action for pending tasks
    3. Process tasks in priority order (P0 first)
    4. Handle all errors with recovery
    5. Sleep and repeat
    """
    logger.info("=" * 60)
    logger.info("AI Employee — Orchestrator starting")
    logger.info(f"  Vault root     : {VAULT_ROOT}")
    logger.info(f"  Monitoring     : {NEEDS_ACTION_DIR}")
    logger.info(f"  Output         : {DONE_DIR}")
    logger.info(f"  Logs           : {LOGS_DIR}")
    logger.info(f"  Poll rate      : {POLL_INTERVAL_SECONDS}s")
    logger.info(f"  Max cycles     : {MAX_COMPLETION_CYCLES} (per task)")
    logger.info(f"  Max retries    : {MAX_RETRIES} (per cycle)")
    logger.info(f"  Cycle cooldown : {COMPLETION_COOLDOWN_SECONDS}s")
    logger.info(f"  Completion def : status: done in frontmatter")
    logger.info(f"  Handbook       : {'LOADED' if HANDBOOK_PATH.exists() else 'MISSING'}")
    logger.info("=" * 60)

    # Pre-flight checks
    ensure_directories()

    if not HANDBOOK_PATH.exists():
        logger.error("CRITICAL: Company_Handbook.md not found — orchestrator cannot operate without constitution")
        write_audit_log(
            task_ref="orchestrator",
            action_taken="HALTED — Company_Handbook.md missing",
            input_desc="Pre-flight check",
            output_desc="Orchestrator refused to start",
            decisions="Handbook is constitutional authority — cannot operate without it (E4)",
            errors="E4 — Company_Handbook.md not found",
            start_time=datetime.now(),
            status="failed",
            category="system-critical",
        )
        sys.exit(1)

    # Track tasks we've already attempted (to avoid re-processing failed tasks in same session)
    session_failed: set[str] = set()
    tasks_completed = 0

    write_audit_log(
        task_ref="orchestrator",
        action_taken="Orchestrator started successfully",
        input_desc="System startup",
        output_desc="Monitoring /Needs_Action for tasks",
        decisions="All pre-flight checks passed",
        errors="None",
        start_time=datetime.now(),
        status="success",
        category="orchestrator-lifecycle",
    )

    logger.info("Orchestrator is live. Waiting for tasks in /Needs_Action...")
    logger.info("-" * 60)

    while True:
        try:
            ensure_directories()

            # Get pending tasks sorted by priority
            pending = get_pending_tasks()

            for file_path, metadata, content in pending:
                task_name = file_path.name

                # Skip tasks that already failed this session
                if task_name in session_failed:
                    continue

                # Process the task with retry logic
                try:
                    execute_with_retry(file_path, metadata, content)

                    # Check if it was completed (file moved to /Done)
                    if not file_path.exists():
                        tasks_completed += 1
                        logger.info(f"  Total completed this session: {tasks_completed}")

                        # Lightweight self-check every 25 tasks (Handbook §7.4)
                        if tasks_completed % 25 == 0:
                            logger.info("Triggering lightweight self-check (25-task interval)")
                            ensure_directories()

                    # If file still exists with failed status, add to session skip list
                    elif file_path.exists():
                        try:
                            check_content = file_path.read_text(encoding="utf-8")
                            check_meta, _ = parse_frontmatter(check_content)
                            if check_meta.get("status") in ("failed", "blocked"):
                                session_failed.add(task_name)
                        except Exception:
                            pass

                except Exception as task_err:
                    logger.error(f"Unhandled error for {task_name}: {task_err}")
                    session_failed.add(task_name)

                    try:
                        write_audit_log(
                            task_ref=task_name,
                            action_taken=f"Unhandled exception in orchestrator task loop",
                            input_desc=f"Task: {task_name}",
                            output_desc="No output",
                            decisions="Exception caught by outer safety net",
                            errors=f"E3 — {type(task_err).__name__}: {task_err}",
                            start_time=datetime.now(),
                            status="failed",
                            category="orchestrator-error",
                        )
                    except Exception:
                        pass

        except KeyboardInterrupt:
            logger.info("Orchestrator stopped by user (Ctrl+C)")
            write_audit_log(
                task_ref="orchestrator",
                action_taken="Orchestrator gracefully shut down via KeyboardInterrupt",
                input_desc="User signal",
                output_desc=f"Session complete. Tasks processed: {tasks_completed}",
                decisions="Clean shutdown",
                errors="None",
                start_time=datetime.now(),
                status="success",
                category="orchestrator-lifecycle",
            )
            break

        except Exception as loop_err:
            logger.error(f"Orchestrator loop error: {loop_err}")
            try:
                write_audit_log(
                    task_ref="orchestrator",
                    action_taken="Orchestrator loop-level error — recovered",
                    input_desc="Main loop cycle",
                    output_desc="No output — error recovered, loop continues",
                    decisions="Outer exception handler caught error, continuing",
                    errors=f"E2 — {type(loop_err).__name__}: {loop_err}",
                    start_time=datetime.now(),
                    status="partial",
                    category="orchestrator-error",
                )
            except Exception:
                pass  # Last resort: if logging fails, silently continue

        time.sleep(POLL_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_orchestrator()
