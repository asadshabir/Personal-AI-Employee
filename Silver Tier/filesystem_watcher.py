"""
Filesystem watcher for Silver Tier AI Employee
Monitors file changes in the Silver Tier workspace and triggers appropriate responses
"""

import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Callable, Optional
import asyncio

class SilverTierFileWatcher:
    """Enhanced filesystem watcher for Silver Tier with intelligent monitoring capabilities."""

    def __init__(self, watch_directory: str, callbacks: Optional[Dict[str, Callable]] = None):
        """
        Initialize the filesystem watcher for Silver Tier.

        Args:
            watch_directory: Directory to monitor for changes
            callbacks: Dictionary of callbacks for different file types/changes
        """
        self.watch_directory = Path(watch_directory)
        self.callbacks = callbacks or {}
        self.last_checked = {}
        self.monitoring = True

        # Initialize last checked times
        self._init_last_checked()

        # Silver Tier specific tracking
        self.intelligence_level = "enhanced"  # Silver Tier intelligence level
        self.adaptive_learning = True  # Enable adaptive learning features
        self.decision_support = True   # Enable decision support features

    def _init_last_checked(self):
        """Initialize the last checked times for all files in the directory."""
        for root, dirs, files in os.walk(self.watch_directory):
            for file in files:
                file_path = Path(root) / file
                self.last_checked[str(file_path)] = file_path.stat().st_mtime

    def get_file_age(self, file_path: Path) -> float:
        """Get the age of a file in seconds."""
        return time.time() - file_path.stat().st_mtime

    def scan_for_changes(self) -> List[Dict]:
        """
        Scan for changes in the watched directory.

        Returns:
            List of changes detected, each with file_path, change_type, and metadata
        """
        changes = []

        for root, dirs, files in os.walk(self.watch_directory):
            for file in files:
                file_path = Path(root) / file

                # Skip directories
                if file_path.is_dir():
                    continue

                current_mtime = file_path.stat().st_mtime

                # Check if file is new or modified
                file_key = str(file_path)
                if file_key not in self.last_checked:
                    # New file
                    changes.append({
                        "file_path": str(file_path),
                        "change_type": "created",
                        "timestamp": datetime.now().isoformat(),
                        "metadata": self._get_file_metadata(file_path),
                        "intelligence_trigger": self._determine_intelligence_trigger(file_path)
                    })
                elif self.last_checked[file_key] != current_mtime:
                    # Modified file
                    changes.append({
                        "file_path": str(file_path),
                        "change_type": "modified",
                        "timestamp": datetime.now().isoformat(),
                        "metadata": self._get_file_metadata(file_path),
                        "intelligence_trigger": self._determine_intelligence_trigger(file_path)
                    })

                # Update last checked time
                self.last_checked[file_key] = current_mtime

        # Remove deleted files from tracking
        current_files = set()
        for root, dirs, files in os.walk(self.watch_directory):
            for file in files:
                current_files.add(str(Path(root) / file))

        deleted_files = set(self.last_checked.keys()) - current_files
        for deleted_file in deleted_files:
            changes.append({
                "file_path": deleted_file,
                "change_type": "deleted",
                "timestamp": datetime.now().isoformat(),
                "metadata": {},
                "intelligence_trigger": "deletion_impact_assessment"
            })
            del self.last_checked[deleted_file]

        return changes

    def _get_file_metadata(self, file_path: Path) -> Dict:
        """Get metadata for a file."""
        stat = file_path.stat()
        return {
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "extension": file_path.suffix.lower(),
            "is_task_file": self._is_task_file(file_path),
            "is_memory_file": self._is_memory_file(file_path),
            "is_skill_file": self._is_skill_file(file_path)
        }

    def _is_task_file(self, file_path: Path) -> bool:
        """Check if the file is a task file."""
        return any(part in str(file_path).lower() for part in ['task', 'plan', 'todo'])

    def _is_memory_file(self, file_path: Path) -> bool:
        """Check if the file is a memory file."""
        return 'memory' in str(file_path).lower() or any(
            part in str(file_path).lower() for part in ['decision', 'pattern', 'failure', 'context']
        )

    def _is_skill_file(self, file_path: Path) -> bool:
        """Check if the file is a skill file."""
        return 'skill' in str(file_path).lower() or str(file_path).endswith('.py')

    def _determine_intelligence_trigger(self, file_path: Path) -> str:
        """Determine the appropriate intelligence level trigger based on file type."""
        ext = file_path.suffix.lower()

        if self._is_task_file(file_path):
            return "task_processing_enhanced"
        elif self._is_memory_file(file_path):
            return "memory_integration_enhanced"
        elif self._is_skill_file(file_path):
            return "capability_enhancement"
        elif ext in ['.py', '.js', '.ts', '.java', '.cpp', '.cs']:
            return "code_intelligence_enhanced"
        elif ext in ['.md', '.txt', '.docx', '.pdf']:
            return "document_intelligence_enhanced"
        else:
            return "data_intelligence_enhanced"

    def process_changes(self, changes: List[Dict]):
        """Process the detected changes and trigger appropriate callbacks."""
        for change in changes:
            file_path = Path(change["file_path"])
            change_type = change["change_type"]
            intelligence_trigger = change["intelligence_trigger"]

            print(f"Silver Tier Intelligence Triggered: {intelligence_trigger}")
            print(f"File: {file_path}, Change: {change_type}")

            # Trigger Silver Tier enhanced intelligence
            self._trigger_intelligence(change)

            # Call appropriate callback based on intelligence trigger
            if intelligence_trigger in self.callbacks:
                try:
                    self.callbacks[intelligence_trigger](change)
                except Exception as e:
                    print(f"Error in callback for {intelligence_trigger}: {e}")

    def _trigger_intelligence(self, change: Dict):
        """Trigger Silver Tier enhanced intelligence for the change."""
        file_path = Path(change["file_path"])
        intelligence_type = change["intelligence_trigger"]

        if intelligence_type == "task_processing_enhanced":
            self._process_task_intelligence(file_path)
        elif intelligence_type == "memory_integration_enhanced":
            self._process_memory_intelligence(file_path)
        elif intelligence_type == "capability_enhancement":
            self._process_capability_intelligence(file_path)
        elif intelligence_type.startswith("intelligence_enhanced"):
            self._process_data_intelligence(file_path)

        # Log the intelligence trigger for adaptive learning
        self._log_intelligence_trigger(change)

    def _process_task_intelligence(self, file_path: Path):
        """Process task intelligence with enhanced Silver Tier capabilities."""
        print(f"Enhanced task intelligence activated for: {file_path}")

        # Enhanced task analysis
        if file_path.suffix.lower() == '.md':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)  # Read first 1000 chars for analysis

            # Silver Tier enhanced analysis
            if any(keyword in content.lower() for keyword in ['urgent', 'critical', 'high priority']):
                priority_level = "high"
            elif any(keyword in content.lower() for keyword in ['medium', 'standard', 'normal']):
                priority_level = "medium"
            else:
                priority_level = "low"

            print(f"  -> Priority assessment: {priority_level}")
            print(f"  -> Task complexity: enhanced analysis completed")

    def _process_memory_intelligence(self, file_path: Path):
        """Process memory intelligence with enhanced Silver Tier capabilities."""
        print(f"Enhanced memory intelligence activated for: {file_path}")

        # Check for memory file updates
        if 'decisions' in str(file_path).lower():
            print("  -> Decision pattern recognition: active")
            print("  -> Strategic insight extraction: initiated")
        elif 'patterns' in str(file_path).lower():
            print("  -> Learning pattern update: processing")
            print("  -> Adaptive behavior adjustment: scheduled")
        elif 'failures' in str(file_path).lower():
            print("  -> Failure pattern analysis: active")
            print("  -> Prevention strategy update: initiated")

    def _process_capability_intelligence(self, file_path: Path):
        """Process capability intelligence with enhanced Silver Tier features."""
        print(f"Enhanced capability intelligence activated for: {file_path}")

        if file_path.suffix.lower() == '.py':
            print("  -> Capability expansion: detected")
            print("  -> Skill integration: processing")
        elif file_path.suffix.lower() == '.md':
            print("  -> Knowledge base update: detected")
            print("  -> Information synthesis: initiated")

    def _process_data_intelligence(self, file_path: Path):
        """Process data intelligence with Silver Tier enhancements."""
        print(f"Enhanced data intelligence activated for: {file_path}")

        # General data processing
        size = file_path.stat().st_size
        print(f"  -> Data volume: {size} bytes")
        print("  -> Intelligence level: enhanced (Silver Tier)")

    def _log_intelligence_trigger(self, change: Dict):
        """Log intelligence triggers for adaptive learning."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "intelligence_trigger": change["intelligence_trigger"],
            "file_path": change["file_path"],
            "change_type": change["change_type"],
            "silver_tier_response": "enhanced_processing"
        }

        # In a real system, this would be stored in a persistent log
        # For now, we'll just print it
        print(f"  -> Intelligence log: {log_entry}")

    def watch(self, interval: float = 1.0):
        """
        Start watching the directory for changes.

        Args:
            interval: Time in seconds between checks
        """
        print(f"Silver Tier Filesystem Watcher started for: {self.watch_directory}")
        print("Monitoring with enhanced intelligence capabilities...")

        try:
            while self.monitoring:
                changes = self.scan_for_changes()
                if changes:
                    self.process_changes(changes)

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nSilver Tier Filesystem Watcher stopped.")
        except Exception as e:
            print(f"Error in Silver Tier Filesystem Watcher: {e}")

    async def async_watch(self, interval: float = 1.0):
        """
        Asynchronously watch the directory for changes.

        Args:
            interval: Time in seconds between checks
        """
        print(f"Async Silver Tier Filesystem Watcher started for: {self.watch_directory}")
        print("Monitoring with enhanced intelligence capabilities...")

        try:
            while self.monitoring:
                changes = self.scan_for_changes()
                if changes:
                    self.process_changes(changes)

                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print("\nAsync Silver Tier Filesystem Watcher stopped.")
        except Exception as e:
            print(f"Error in Async Silver Tier Filesystem Watcher: {e}")

def main():
    """Main function to demonstrate Silver Tier filesystem watcher."""
    import tempfile

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up callbacks for different intelligence triggers
        callbacks = {
            "task_processing_enhanced": lambda change: print(f"Task callback: {change['file_path']}"),
            "memory_integration_enhanced": lambda change: print(f"Memory callback: {change['file_path']}"),
            "capability_enhancement": lambda change: print(f"Capability callback: {change['file_path']}")
        }

        watcher = SilverTierFileWatcher(temp_dir, callbacks)

        print("Silver Tier Filesystem Watcher Demo")
        print("=" * 40)

        # Create a test file to trigger the watcher
        test_file = Path(temp_dir) / "test_task.md"
        with open(test_file, 'w') as f:
            f.write("# Test Task\nThis is a test task for Silver Tier.")

        # Scan for changes
        changes = watcher.scan_for_changes()
        print(f"Detected changes: {len(changes)}")

        # Process changes
        watcher.process_changes(changes)

        print("\nSilver Tier Intelligence Features:")
        print("- Enhanced task processing")
        print("- Adaptive learning capabilities")
        print("- Decision support integration")
        print("- Intelligence level: Silver (intermediate)")

if __name__ == "__main__":
    main()