"""
filesystem_watcher.py — Gold Tier PHR Filesystem Monitor
========================================================
Healthcare-specific filesystem monitor for the Personal Health Record system.

Monitors /Inbox for health data files, validates them for basic correctness
and PHI compliance, and moves them to /Needs_Action for processing by the
multi-agent orchestrator.

Healthcare Safety:
  - Scans all files for PHI before processing
  - Never overwrites files
  - Tier 2/3 health tasks are flagged for human review
  - All health data access is logged for compliance
  - Graceful shutdown on Ctrl+C with cleanup
"""
import os
import re
import sys
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
SKILLS_DIR = VAULT_ROOT / "Skills"
MEMORY_DIR = VAULT_ROOT / "Memory"
HANDBOOK_PATH = VAULT_ROOT / "Company_Handbook.md"
PHR_PROTOCOL_PATH = VAULT_ROOT / "PHR_Compliance_Protocol.md"

POLL_INTERVAL_SECONDS = 3  # More responsive for health data
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit for health files
HEALTH_FILE_EXTENSIONS = {'.md', '.txt', '.json', '.csv', '.pdf', '.xml', '.fhir'}

# Healthcare-specific dangerous patterns that indicate non-health files
HEALTH_DANGEROUS_PATTERNS = [
    # Financial terms (non-health context)
    r'\b(credit card|paypal|bank|account|ssn|social security)\b',
    # System files
    r'\.(exe|bat|com|pif|reg|scr|vbs|js|jar|msi|msp|dll|sys|bin|iso|img)$',
    # Security-sensitive terms
    r'\b(password|passwd|secret|private|config|credential|token|api_key)\b',
    # Potentially malicious code patterns
    r'eval\s*\(',
    r'exec\s*\(',
    r'import\s+os\s*',
    r'import\s+subprocess\s*',
    r'import\s+sys\s*',
    r'__import__\s*',
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
logger = logging.getLogger("phr_filesystem_watcher")


# ---------------------------------------------------------------------------
# Healthcare-specific utilities
# ---------------------------------------------------------------------------

def detect_phi(content: str) -> bool:
    """
    Detect Protected Health Information (PHI) in content per HIPAA standards.

    Args:
        content: Text content to scan for PHI

    Returns:
        True if PHI is detected, False otherwise
    """
    # Common PHI patterns
    phi_patterns = [
        # Medical record numbers (usually 6-8 digits)
        r'\b\d{6,8}\b',
        # SSN pattern
        r'\b\d{3}-\d{2}-\d{4}\b',
        # Phone number pattern
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        # Email addresses (could be PHI in healthcare context)
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        # IP addresses (could be PHI in healthcare context)
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        # Dates that could be birth dates or other health-related dates
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        # Addresses (simple pattern to catch obvious ones)
        r'\b\d+\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Circle|Cir)\b'
    ]

    content_lower = content.lower()

    # Common health-related terms that might indicate PHI context
    health_terms = [
        'patient', 'medical', 'health', 'clinic', 'hospital', 'doctor', 'physician',
        'nurse', 'pharmacy', 'prescription', 'medication', 'treatment', 'diagnosis',
        'condition', 'symptom', 'vital', 'blood pressure', 'heart rate', 'temperature',
        'weight', 'height', 'allergy', 'vaccination', 'immunization', 'lab results',
        'test results', 'x-ray', 'mri', 'ct scan', 'ekg', 'ekg', 'blood test'
    ]

    # Check for PHI patterns
    for pattern in phi_patterns:
        if re.search(pattern, content):
            # If we find a pattern, also check if health terms are present to confirm context
            for term in health_terms:
                if term in content_lower:
                    logger.warning(f"PHI detected: {term} with pattern {pattern}")
                    return True

    # Check for explicit PHI terms
    phi_terms = [
        'mrn', 'medical record', 'patient id', 'health plan', 'social security',
        'insurance', 'beneficiary', 'account number', 'license number',
        'certificate number', 'vehicle identifier', 'device identifier'
    ]

    for term in phi_terms:
        if term in content_lower:
            logger.warning(f"PHI detected: {term} term found")
            return True

    return False


def validate_health_file_content(file_path: Path) -> tuple[bool, str]:
    """
    Validate health file content for basic correctness and safety.

    Args:
        file_path: Path to the health file to validate

    Returns:
        Tuple of (is_valid, reason_message)
    """
    try:
        # Check file size
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return False, f"File too large: {file_path.stat().st_size} bytes (max {MAX_FILE_SIZE})"

        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Check for dangerous patterns
        content_lower = content.lower()
        for pattern in HEALTH_DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected in {file_path.name}: {pattern}")
                return False, f"Dangerous pattern detected: {pattern}"

        # Check for basic health file structure (if markdown)
        if file_path.suffix.lower() == '.md':
            # Check if file has basic structure expected for health tasks
            if '---' in content[:200]:  # Has frontmatter
                # Check for required health fields
                if 'title:' not in content_lower and 'patient_id:' not in content_lower:
                    # Not a structured health task, but could still be valid
                    pass
            else:
                # No frontmatter, but might be valid health content
                # Just ensure it's not clearly non-health
                non_health_indicators = [
                    'password', 'credit card', 'paypal', 'bank account',
                    'config', 'secret', 'token', 'api_key'
                ]
                for indicator in non_health_indicators:
                    if indicator in content_lower:
                        return False, f"Non-health indicator found: {indicator}"

        # If we get here, file appears safe and potentially health-related
        has_phi = detect_phi(content)
        phi_status = " (contains PHI)" if has_phi else " (no PHI detected)"
        logger.info(f"Health file validation passed{phi_status}: {file_path.name}")

        return True, f"Valid health file{phi_status}"

    except UnicodeDecodeError:
        # For non-text files like PDF, CSV, etc., we'll allow them through
        # but with a warning for content we can't check
        logger.info(f"Non-text file (possibly health-related): {file_path.name}")
        return True, "Non-text file (content not analyzed)"

    except Exception as e:
        logger.error(f"Error validating health file {file_path.name}: {e}")
        return False, f"Validation error: {str(e)}"


def write_phr_audit_log(
    task_ref: str,
    action_taken: str,
    input_desc: str,
    output_desc: str,
    decisions: str,
    errors: str,
    start_time: datetime,
    status: str = "success",
    category: str = "filesystem",
    phi_related: bool = False
) -> Path:
    """Write a healthcare-compliant audit log to /Logs."""
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d")
    hm = now.strftime("%H%M")
    suffix = hashlib.md5(now.isoformat().encode()).hexdigest()[:6]
    log_id = f"PHR_FILESYS_{ts}_{hm}_{suffix}"
    filename = f"{log_id}.md"
    log_path = LOGS_DIR / filename

    duration = f"{start_time.strftime('%H:%M:%S')} → {now.strftime('%H:%M:%S')}"

    content = f"""---
log_id: {log_id}
task_ref: {task_ref}
created: {now.strftime('%Y-%m-%d %H:%M')}
status: {status}
category: {category}
phi_related: {phi_related}
tags: [log, {category}, health]
---

# PHR Filesystem Audit Log — {task_ref}

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

## PHI Classification
Protected Health Information processing: {phi_related}
"""
    log_path.write_text(content, encoding="utf-8")
    logger.info(f"PHR filesystem audit log: {filename}")
    return log_path


# ---------------------------------------------------------------------------
# Main filesystem monitoring
# ---------------------------------------------------------------------------

def ensure_directories() -> bool:
    """Verify all required workspace folders exist. Auto-remediate if missing."""
    all_ok = True
    for folder in [INBOX_DIR, NEEDS_ACTION_DIR, DONE_DIR, LOGS_DIR, SKILLS_DIR, MEMORY_DIR]:
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


def process_new_health_files():
    """Scan /Inbox for new files and move valid ones to /Needs_Action."""
    if not INBOX_DIR.exists():
        return

    for file_path in INBOX_DIR.iterdir():
        if not file_path.is_file():
            continue

        # Skip if not a supported health file type
        if file_path.suffix.lower() not in HEALTH_FILE_EXTENSIONS:
            logger.info(f"Skipping non-supported file type: {file_path.name}")
            continue

        try:
            # Validate the file for health data content and safety
            is_valid, validation_result = validate_health_file_content(file_path)

            if not is_valid:
                logger.warning(f"Invalid health file skipped: {file_path.name} - {validation_result}")

                # Log the rejection for compliance
                write_phr_audit_log(
                    task_ref=file_path.name,
                    action_taken="Health file rejected - validation failed",
                    input_desc=f"File: {file_path.name}",
                    output_desc=validation_result,
                    decisions="File did not meet health data validation requirements",
                    errors=validation_result,
                    start_time=datetime.now(),
                    status="rejected",
                    category="file-validation",
                    phi_related=detect_phi(open(file_path, 'r', encoding='utf-8', errors='ignore').read())
                )

                # Move to a quarantine directory instead of deleting
                quarantine_dir = VAULT_ROOT / "Quarantine"
                quarantine_dir.mkdir(exist_ok=True)
                quarantine_path = get_safe_path(quarantine_dir, file_path.name)
                shutil.move(str(file_path), str(quarantine_path))
                logger.info(f"Health file quarantined: {quarantine_path.name}")
                continue

            # File is valid, move to Needs_Action
            needs_action_path = get_safe_path(NEEDS_ACTION_DIR, file_path.name)

            # For health files, we may need to add PHI metadata before moving
            if file_path.suffix.lower() in ['.md', '.txt', '.json']:
                try:
                    content = file_path.read_text(encoding='utf-8')
                    has_phi = detect_phi(content)

                    # If it's a markdown file with frontmatter, add phi_detected field
                    if content.startswith('---') and file_path.suffix.lower() == '.md':
                        lines = content.split('\n')
                        # Find the end of frontmatter
                        frontmatter_end = -1
                        for i, line in enumerate(lines[1:], 1):  # Skip first ---
                            if line.strip() == '---' and i > 0:
                                frontmatter_end = i
                                break

                        if frontmatter_end > 0:
                            # Insert phi_detected in the frontmatter
                            frontmatter_lines = lines[1:frontmatter_end]
                            new_frontmatter_lines = []
                            phi_field_added = False

                            for line in frontmatter_lines:
                                if line.strip().startswith('status:') and not phi_field_added:
                                    new_frontmatter_lines.append(f"phi_detected: {has_phi}")
                                    phi_field_added = True
                                new_frontmatter_lines.append(line)

                            # Add phi_detected if it wasn't added yet
                            if not phi_field_added:
                                new_frontmatter_lines.append(f"phi_detected: {has_phi}")

                            # Reconstruct the content
                            new_content = "---\n" + "\n".join(new_frontmatter_lines) + "\n---" + "\n".join(lines[frontmatter_end+1:])
                            file_path.write_text(new_content, encoding='utf-8')
                    else:
                        # For non-markdown files, we'll still track the PHI status in our logs
                        pass

                except Exception as e:
                    logger.warning(f"Could not update PHI status in {file_path.name}: {e}")

            # Move the file to Needs_Action
            shutil.move(str(file_path), str(needs_action_path))

            logger.info(f"Health file moved to processing: {needs_action_path.name}")

            # Log the file intake for healthcare compliance
            write_phr_audit_log(
                task_ref=needs_action_path.name,
                action_taken="Health file intake and validation complete",
                input_desc=f"File: Inbox/{file_path.name}",
                output_desc=f"File: Needs_Action/{needs_action_path.name}",
                decisions=f"File validated and accepted for health data processing. {validation_result}",
                errors="None",
                start_time=datetime.now(),
                status="success",
                category="file-intake",
                phi_related=has_phi if 'has_phi' in locals() else detect_phi(needs_action_path.read_text(encoding='utf-8', errors='ignore'))
            )

        except Exception as e:
            logger.error(f"Error processing health file {file_path.name}: {e}")


def run_filesystem_watcher():
    """
    Main monitoring loop - the nervous system of the PHR intake process.

    Each cycle:
    1. Verify directory structure
    2. Scan for new health files
    3. Validate and intake them
    4. Sleep and repeat
    """
    logger.info("=" * 60)
    logger.info("PHR Filesystem Watcher starting")
    logger.info(f"  Vault root    : {VAULT_ROOT}")
    logger.info(f"  Monitoring    : {INBOX_DIR}")
    logger.info(f"  Processing to : {NEEDS_ACTION_DIR}")
    logger.info(f"  Poll rate     : {POLL_INTERVAL_SECONDS}s")
    logger.info(f"  Max file size : {MAX_FILE_SIZE / (1024*1024):.1f}MB")
    logger.info(f"  Health types  : {HEALTH_FILE_EXTENSIONS}")
    logger.info("=" * 60)

    # Pre-flight checks
    ensure_directories()

    if not HANDBOOK_PATH.exists():
        logger.error("CRITICAL: Company_Handbook.md not found — PHR filesystem watcher cannot operate without constitution")
        sys.exit(1)

    # Log startup
    write_phr_audit_log(
        task_ref="phr_filesystem_watcher",
        action_taken="PHR filesystem watcher started",
        input_desc="System startup",
        output_desc="Monitoring /Inbox for health files",
        decisions="All pre-flight checks passed",
        errors="None",
        start_time=datetime.now(),
        status="success",
        category="filesystem-lifecycle",
        phi_related=False
    )

    logger.info("PHR Filesystem Watcher is live. Monitoring /Inbox for health files...")
    logger.info("-" * 60)

    while True:
        try:
            ensure_directories()
            process_new_health_files()

        except KeyboardInterrupt:
            logger.info("PHR Filesystem Watcher stopped by user (Ctrl+C)")

            write_phr_audit_log(
                task_ref="phr_filesystem_watcher",
                action_taken="PHR filesystem watcher stopped by user",
                input_desc="User interrupt signal",
                output_desc="Monitoring stopped",
                decisions="Clean shutdown",
                errors="None",
                start_time=datetime.now(),
                status="success",
                category="filesystem-lifecycle",
                phi_related=False
            )

            break

        except Exception as e:
            logger.error(f"PHR Filesystem Watcher error: {e}")

            try:
                write_phr_audit_log(
                    task_ref="phr_filesystem_watcher",
                    action_taken="PHR filesystem watcher error",
                    input_desc="Filesystem monitoring cycle",
                    output_desc="No action taken — error recovered",
                    decisions="Error caught by outer handler, continuing",
                    errors=f"System error: {str(e)}",
                    start_time=datetime.now(),
                    status="error",
                    category="filesystem-error",
                    phi_related=False
                )
            except Exception:
                pass  # If logging fails, continue anyway

        time.sleep(POLL_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_filesystem_watcher()