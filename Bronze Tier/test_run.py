from pathlib import Path
import yaml
from orchestrator import process_task

# Step 1 — Load task file
task_file = Path("Tasks/TASK-001.md")

raw_text = task_file.read_text(encoding="utf-8")

# Step 2 — Split frontmatter + body
parts = raw_text.split('---')

if len(parts) < 3:
    raise ValueError("Invalid task format")

metadata_block = parts[1]
content_block = parts[2]

# Step 3 — Parse YAML metadata
metadata = yaml.safe_load(metadata_block)

# Step 4 — Clean content
content = content_block.strip()

# Step 5 — Send structured data to AI Employee
result = process_task(task_file, metadata, content)

print(result)
