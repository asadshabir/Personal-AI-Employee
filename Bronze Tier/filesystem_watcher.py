"""
filesystem_watcher.py — AI Employee Inbox Monitor
===================================================
Continuously watches /Inbox for new files.
On detection: extracts metadata, creates a task in /Needs_Action,
references SK-010 (Skill_File_Processor), and logs all activity to /Logs.

Conforms to:
  - Company_Handbook.md §4 (Task Lifecycle)
  - Company_Handbook.md §5 (Logging Requirements)
  - Company_Handbook.md §6 (Error Handling)
  - Skills/Skill_File_Processor.md (SK-010)

Safety:
  - Never overwrites existing files
  - Runs in an infinite loop with full error recovery
  - Secret detection halts processing for that file (E3)
  - All exceptions are caught, logged, and recovered from
"""

import os
import re
import sys
import time
import hashlib
import logging
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VAULT_ROOT = Path(__file__).resolve().parent
INBOX_DIR = VAULT_ROOT / "Inbox"
NEEDS_ACTION_DIR = VAULT_ROOT / "Needs_Action"
LOGS_DIR = VAULT_ROOT / "Logs"
DONE_DIR = VAULT_ROOT / "Done"
PLANS_DIR = VAULT_ROOT / "Plans"
SKILLS_DIR = VAULT_ROOT / "Skills"

POLL_INTERVAL_SECONDS = 3
MAX_FILE_SIZE_BYTES = 1_048_576  # 1 MB
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".yaml", ".yml"}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(secret|token|password|passwd|pwd)\s*[:=]\s*\S+"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"(?i)bearer\s+[a-zA-Z0-9\-._~+/]+=*"),
]

PRIORITY_KEYWORDS = {
    "P0": ["urgent", "critical", "down", "broken", "outage", "emergency"],
    "P1": ["important", "deadline", "asap", "blocker", "high priority"],
    "P2": ["update", "add", "create", "implement", "build", "feature"],
    "P3": ["nice to have", "backlog", "low", "someday", "optional"],
}

# ---------------------------------------------------------------------------
# Logging — Python logger for console + Handbook-compliant markdown logs
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("filesystem_watcher")


def write_markdown_log(
    task_ref: str,
    action_taken: str,
    input_desc: str,
    output_desc: str,
    decisions: str,
    errors: str,
    start_time: datetime,
    status: str = "success",
    category: str = "file-processing",
) -> Path:
    """Write a Handbook §5.2 compliant log file to /Logs."""
    now = datetime.now()
    log_id = f"LOG_{now.strftime('%Y-%m-%d')}_{now.strftime('%H%M')}"
    # Avoid collision by appending seconds + microseconds hash
    suffix = hashlib.md5(now.isoformat().encode()).hexdigest()[:6]
    filename = f"{log_id}_{suffix}.md"
    log_path = LOGS_DIR / filename

    duration = f"{start_time.strftime('%H:%M:%S')} → {now.strftime('%H:%M:%S')}"

    content = f"""---
log_id: {log_id}_{suffix}
task_ref: {task_ref}
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
    logger.info(f"Log written: {filename}")
    return log_path


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def ensure_directories() -> bool:
    """Verify all required folders exist. Create if missing (Tier 0 auto-remediation)."""
    all_ok = True
    for folder in [INBOX_DIR, NEEDS_ACTION_DIR, DONE_DIR, LOGS_DIR, PLANS_DIR, SKILLS_DIR]:
        if not folder.exists():
            logger.warning(f"Missing folder detected: {folder.name} — recreating")
            folder.mkdir(parents=True, exist_ok=True)
            all_ok = False
    return all_ok


def get_safe_filename(directory: Path, base_name: str) -> Path:
    """Generate a non-colliding filename. Never overwrites."""
    target = directory / base_name
    if not target.exists():
        return target

    stem = Path(base_name).stem
    ext = Path(base_name).suffix
    counter = 2
    while True:
        candidate = directory / f"{stem}_{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1
        if counter > 100:
            raise RuntimeError(f"Filename collision overflow for {base_name} in {directory}")


def detect_secrets(content: str) -> list[str]:
    """Scan content for secret patterns. Returns list of matched pattern names."""
    matches = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            matches.append(pattern.pattern[:40] + "...")
    return matches


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    metadata = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_block = parts[1].strip()
            for line in fm_block.split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def auto_assign_priority(content: str) -> str:
    """Assign priority based on content keywords per Skill_Task_Manager rules."""
    content_lower = content.lower()
    for priority, keywords in PRIORITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in content_lower:
                return priority
    return "P2"  # Default


def extract_title(file_path: Path, content: str, metadata: dict) -> str:
    """Extract title from frontmatter, first heading, or filename."""
    if metadata.get("title"):
        return metadata["title"]

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# ") and not line.startswith("##"):
            return line.lstrip("# ").strip()

    return file_path.stem.replace("_", " ").replace("-", " ").title()


def classify_file(content: str, metadata: dict) -> str:
    """Classify file type per Skill_File_Processor Step 4."""
    content_lower = content.lower()

    if any(k in metadata for k in ("skill_id", "trigger")) or "## execution steps" in content_lower:
        return "skill"
    if any(s in content_lower for s in ("## steps", "## goals", "## milestones", "## phases")):
        return "plan"
    if any(k in metadata for k in ("log_id",)) or "## action taken" in content_lower:
        return "log"
    return "task"


def create_needs_action_task(
    source_file: Path,
    title: str,
    priority: str,
    classification: str,
    metadata: dict,
    original_content: str,
) -> Path:
    """Create a structured task file in /Needs_Action per Handbook §4.2."""
    now = datetime.now()
    task_filename = f"{now.strftime('%Y-%m-%d')}_{source_file.stem}.md"
    task_path = get_safe_filename(NEEDS_ACTION_DIR, task_filename)

    requester = metadata.get("requester", metadata.get("author", "filesystem_watcher"))
    source_label = metadata.get("source", "automated")

    task_content = f"""---
title: "{title}"
requester: {requester}
received: {now.strftime('%Y-%m-%d %H:%M')}
triaged: {now.strftime('%Y-%m-%d %H:%M')}
priority: {priority}
status: ready
assigned_to: ai-employee
classification: {classification}
source: {source_label}
source_file: {source_file.name}
processed_by: SK-010
---

# {title}

## Source
- **Original file:** `Inbox/{source_file.name}`
- **Detected type:** {classification}
- **Auto-priority:** {priority}
- **Processed by:** [Skill_File_Processor](../Skills/Skill_File_Processor.md) (SK-010)

## Original Content

{original_content.strip()}

## Transition History

| Timestamp | From | To | Action | By |
|-----------|------|----|--------|-----|
| {now.strftime('%Y-%m-%d %H:%M')} | /Inbox | /Needs_Action | triage | SK-010 via filesystem_watcher |
"""

    task_path.write_text(task_content, encoding="utf-8")
    logger.info(f"Task created: {task_path.name} [Priority: {priority}]")
    return task_path


def process_file(file_path: Path) -> None:
    """Full processing pipeline for a single inbox file. References SK-010."""
    start_time = datetime.now()
    logger.info(f"Processing: {file_path.name}")

    # --- Step 1: Validate extension ---
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        logger.warning(f"Rejected (unsupported extension): {file_path.name}")
        write_markdown_log(
            task_ref=file_path.name,
            action_taken=f"Rejected file with unsupported extension: {file_path.suffix}",
            input_desc=f"New file detected: {file_path.name}",
            output_desc="Rejection note created in /Needs_Action",
            decisions=f"Extension {file_path.suffix} not in allowed set {ALLOWED_EXTENSIONS}",
            errors="E2 — Unsupported file type",
            start_time=start_time,
            status="failed",
            category="file-rejection",
        )
        _create_rejection_note(file_path, f"Unsupported extension: {file_path.suffix}", "E2")
        return

    # --- Step 2: Validate size ---
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        logger.warning(f"Rejected (too large): {file_path.name} ({file_size} bytes)")
        write_markdown_log(
            task_ref=file_path.name,
            action_taken=f"Rejected oversized file: {file_size} bytes",
            input_desc=f"New file detected: {file_path.name}",
            output_desc="Rejection note created in /Needs_Action",
            decisions=f"File size {file_size} exceeds limit {MAX_FILE_SIZE_BYTES}",
            errors="E2 — File too large",
            start_time=start_time,
            status="failed",
            category="file-rejection",
        )
        _create_rejection_note(file_path, f"File too large: {file_size} bytes (limit: 1 MB)", "E2")
        return

    # --- Step 3: Read content ---
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning(f"Rejected (unreadable): {file_path.name}")
        write_markdown_log(
            task_ref=file_path.name,
            action_taken="Rejected unreadable file (binary or encoding error)",
            input_desc=f"New file detected: {file_path.name}",
            output_desc="Rejection note created in /Needs_Action",
            decisions="File could not be decoded as UTF-8",
            errors="E2 — Encoding error",
            start_time=start_time,
            status="failed",
            category="file-rejection",
        )
        _create_rejection_note(file_path, "File is not valid UTF-8 text", "E2")
        return

    # --- Step 4: Check for empty ---
    if not content.strip():
        logger.warning(f"Rejected (empty): {file_path.name}")
        write_markdown_log(
            task_ref=file_path.name,
            action_taken="Rejected empty file",
            input_desc=f"New file detected: {file_path.name}",
            output_desc="Rejection note created in /Needs_Action",
            decisions="File content is empty after stripping whitespace",
            errors="E1 — Empty file",
            start_time=start_time,
            status="failed",
            category="file-rejection",
        )
        _create_rejection_note(file_path, "File is empty", "E1")
        return

    # --- Step 5: Secret detection (E3 — halt immediately) ---
    secret_matches = detect_secrets(content)
    if secret_matches:
        logger.error(f"SECRETS DETECTED in {file_path.name} — halting processing (E3)")
        write_markdown_log(
            task_ref=file_path.name,
            action_taken="HALTED — Secrets detected in file content",
            input_desc=f"New file detected: {file_path.name}",
            output_desc="E3 escalation note created in /Needs_Action",
            decisions="Secret patterns matched — file must NOT be moved or processed further",
            errors=f"E3 — Secret patterns detected: {'; '.join(secret_matches)}",
            start_time=start_time,
            status="failed",
            category="security-escalation",
        )
        _create_rejection_note(
            file_path,
            f"SECRETS DETECTED — {len(secret_matches)} pattern(s) matched. File left in /Inbox untouched.",
            "E3",
        )
        return

    # --- Step 6: Extract metadata and classify ---
    metadata = extract_frontmatter(content)
    title = extract_title(file_path, content, metadata)
    classification = classify_file(content, metadata)
    priority = metadata.get("priority", auto_assign_priority(content))

    # --- Step 7: Create task in /Needs_Action ---
    task_path = create_needs_action_task(
        source_file=file_path,
        title=title,
        priority=priority,
        classification=classification,
        metadata=metadata,
        original_content=content,
    )

    # --- Step 8: Log success ---
    write_markdown_log(
        task_ref=task_path.name,
        action_taken=f"Processed inbox file and created task in /Needs_Action",
        input_desc=f"New file detected: Inbox/{file_path.name} ({file_size} bytes)",
        output_desc=f"Task created: Needs_Action/{task_path.name} [Priority: {priority}, Type: {classification}]",
        decisions=(
            f"Classification: {classification} | "
            f"Priority: {priority} | "
            f"Title: {title} | "
            f"Skill ref: SK-010"
        ),
        errors="None",
        start_time=start_time,
        status="success",
        category="file-processing",
    )


def _create_rejection_note(file_path: Path, reason: str, severity: str) -> None:
    """Create a rejection/escalation note in /Needs_Action per Skill_File_Processor Step 6."""
    now = datetime.now()
    note_filename = f"ESCALATION_{now.strftime('%Y-%m-%d')}_{file_path.stem}.md"
    note_path = get_safe_filename(NEEDS_ACTION_DIR, note_filename)

    content = f"""---
title: "FILE REJECTED — {file_path.name}"
type: escalation
severity: {severity}
source_file: Inbox/{file_path.name}
reason: "{reason}"
created: {now.strftime('%Y-%m-%d %H:%M')}
status: awaiting_human
processed_by: SK-010
---

# ESCALATION — {file_path.name}

## What Happened
File `Inbox/{file_path.name}` was detected by the filesystem watcher but failed validation.

## Reason for Rejection
{reason}

## What Was Tried
- File was scanned per [Skill_File_Processor](../Skills/Skill_File_Processor.md) (SK-010) validation rules
- Validation failed at the check described above

## What Is Needed
Human Operator must review the original file in `/Inbox` and decide:
1. Fix the file and re-save it to `/Inbox` for reprocessing
2. Manually move it to the appropriate folder
3. Delete it if it is not needed

## Impact If Unresolved
File remains unprocessed in `/Inbox`. No task will be created for it.
"""
    note_path.write_text(content, encoding="utf-8")
    logger.info(f"Escalation note created: {note_path.name}")


# ---------------------------------------------------------------------------
# Watcher loop
# ---------------------------------------------------------------------------


def run_watcher() -> None:
    """
    Main infinite loop. Polls /Inbox every POLL_INTERVAL_SECONDS.
    Tracks processed files by maintaining a set of (filename, mtime) tuples.
    Full error recovery — no single failure kills the watcher.
    """
    logger.info("=" * 60)
    logger.info("AI Employee — Filesystem Watcher starting")
    logger.info(f"  Vault root : {VAULT_ROOT}")
    logger.info(f"  Watching   : {INBOX_DIR}")
    logger.info(f"  Output     : {NEEDS_ACTION_DIR}")
    logger.info(f"  Logs       : {LOGS_DIR}")
    logger.info(f"  Poll rate  : {POLL_INTERVAL_SECONDS}s")
    logger.info(f"  Skill ref  : SK-010 (File Processor)")
    logger.info("=" * 60)

    # Pre-flight: ensure all directories exist
    ensure_directories()

    # Track processed files: set of (filename, modification_time) tuples
    processed: set[tuple[str, float]] = set()

    # Snapshot existing files on startup so we don't re-process them
    if INBOX_DIR.exists():
        for existing in INBOX_DIR.iterdir():
            if existing.is_file():
                processed.add((existing.name, existing.stat().st_mtime))
                logger.info(f"  Existing (skipped): {existing.name}")

    logger.info("Watcher is live. Waiting for new files in /Inbox...")
    logger.info("-" * 60)

    while True:
        try:
            # Verify directories still exist each cycle
            ensure_directories()

            # Scan /Inbox for new files
            if INBOX_DIR.exists():
                for file_path in sorted(INBOX_DIR.iterdir()):
                    if not file_path.is_file():
                        continue

                    file_key = (file_path.name, file_path.stat().st_mtime)

                    if file_key in processed:
                        continue

                    # New file detected — process it
                    try:
                        process_file(file_path)
                    except Exception as proc_err:
                        # Per Handbook §6: catch, log, recover — never crash the loop
                        logger.error(f"Error processing {file_path.name}: {proc_err}")
                        try:
                            write_markdown_log(
                                task_ref=file_path.name,
                                action_taken=f"FAILED to process file: {file_path.name}",
                                input_desc=f"File detected in /Inbox: {file_path.name}",
                                output_desc="No output — processing failed",
                                decisions="Error caught by watcher recovery loop",
                                errors=f"E3 — {type(proc_err).__name__}: {proc_err}",
                                start_time=datetime.now(),
                                status="failed",
                                category="watcher-error",
                            )
                        except Exception as log_err:
                            logger.error(f"Failed to write error log: {log_err}")

                    # Mark as processed regardless of success/failure
                    # (prevents infinite retry loops — failed files get escalation notes)
                    processed.add(file_key)

        except KeyboardInterrupt:
            logger.info("Watcher stopped by user (KeyboardInterrupt)")
            write_markdown_log(
                task_ref="filesystem_watcher",
                action_taken="Watcher stopped by user via KeyboardInterrupt",
                input_desc="User signal",
                output_desc="Watcher process terminated gracefully",
                decisions="Clean shutdown initiated",
                errors="None",
                start_time=datetime.now(),
                status="success",
                category="watcher-lifecycle",
            )
            break

        except Exception as loop_err:
            # Outer recovery: log and continue — the watcher must not die
            logger.error(f"Watcher loop error: {loop_err}")
            try:
                write_markdown_log(
                    task_ref="filesystem_watcher",
                    action_taken="Watcher encountered a loop-level error and recovered",
                    input_desc="Watcher poll cycle",
                    output_desc="No output — error recovered",
                    decisions="Outer exception handler caught error, continuing loop",
                    errors=f"E2 — {type(loop_err).__name__}: {loop_err}",
                    start_time=datetime.now(),
                    status="partial",
                    category="watcher-error",
                )
            except Exception:
                pass  # Last resort: if even logging fails, silently continue

        time.sleep(POLL_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_watcher()
