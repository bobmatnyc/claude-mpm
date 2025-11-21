"""Hook Error Memory System.

This module provides error detection and memory for hook execution to prevent
repeated errors and provide helpful diagnostics.

WHY this is needed:
- Hook processor can encounter transient or persistent errors
- Repeated failing commands waste resources and clutter logs
- Users need actionable suggestions to fix configuration issues
- System should learn from errors and prevent repetition

DESIGN DECISION: Store errors in JSON file rather than database because:
- Simple, human-readable format
- Easy to inspect and manually clear
- No additional dependencies
- Fast read/write for small datasets
- Users can easily delete to retry failed commands
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.logger import get_logger


class HookErrorMemory:
    """Tracks and prevents repeated hook execution errors.

    WHY this design:
    - Detects common error patterns automatically
    - Stores error history to prevent repetition
    - Provides actionable fix suggestions
    - Allows manual retry by clearing memory
    - Minimal performance overhead (<1ms per check)
    """

    # Error pattern definitions with detection regexes
    ERROR_PATTERNS = [
        (r"no such file or directory[:\s]+(.+?)(?:\n|$)", "file_not_found"),
        (r"command not found[:\s]+(.+?)(?:\n|$)", "command_not_found"),
        (r"permission denied[:\s]+(.+?)(?:\n|$)", "permission_denied"),
        (r"syntax error", "syntax_error"),
        (r"Error:\s*\(eval\):(\d+):\s*(.+?)(?:\n|$)", "eval_error"),
        (r"Error:\s*(.+?)(?:\n|$)", "general_error"),
    ]

    def __init__(self, memory_file: Optional[Path] = None):
        """Initialize hook error memory.

        Args:
            memory_file: Path to memory file (default: .claude-mpm/hook_errors.json)
        """
        self.logger = get_logger("hook_error_memory")

        # Use default location if not specified
        if memory_file is None:
            memory_file = Path.cwd() / ".claude-mpm" / "hook_errors.json"

        self.memory_file = memory_file
        self.errors: Dict[str, Any] = self._load_errors()

    def _load_errors(self) -> Dict[str, Any]:
        """Load previously encountered errors from disk.

        Returns:
            Dictionary of error records
        """
        if not self.memory_file.exists():
            return {}

        try:
            content = self.memory_file.read_text()
            if not content.strip():
                return {}
            return json.loads(content)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse error memory file: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading error memory: {e}")
            return {}

    def _save_errors(self):
        """Persist errors to disk."""
        try:
            # Ensure directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)

            # Write with pretty formatting for human readability
            self.memory_file.write_text(json.dumps(self.errors, indent=2))
        except Exception as e:
            self.logger.error(f"Failed to save error memory: {e}")

    def detect_error(
        self, output: str, stderr: str, returncode: int
    ) -> Optional[Dict[str, str]]:
        """Detect if output contains an error.

        WHY check both stdout and stderr:
        - Some commands write errors to stdout
        - Some write to stderr
        - Return code alone isn't enough (some hooks return non-zero on purpose)

        Args:
            output: Standard output from command
            stderr: Standard error from command
            returncode: Exit code from command

        Returns:
            Dict with error info if detected, None otherwise
        """
        # Combine output sources for comprehensive error detection
        combined_output = f"{output}\n{stderr}"

        # Try each pattern in order of specificity
        for pattern, error_type in self.ERROR_PATTERNS:
            match = re.search(pattern, combined_output, re.IGNORECASE | re.MULTILINE)
            if match:
                # Extract details from the match
                details = match.group(1) if match.groups() else match.group(0)

                return {
                    "type": error_type,
                    "pattern": pattern,
                    "match": match.group(0).strip(),
                    "details": details.strip() if details else "",
                    "returncode": returncode,
                }

        # If no pattern matched but returncode is non-zero, record as generic error
        if returncode != 0 and combined_output.strip():
            return {
                "type": "unknown_error",
                "pattern": "non-zero exit code",
                "match": f"Exit code: {returncode}",
                "details": combined_output[:200].strip(),  # First 200 chars
                "returncode": returncode,
            }

        return None

    def record_error(self, error_info: Dict[str, str], hook_type: str):
        """Record an error to prevent future repetition.

        WHY use composite key:
        - Same error type can occur with different details
        - Want to track specific error instances
        - Hook type context helps with diagnosis

        Args:
            error_info: Error information from detect_error()
            hook_type: Type of hook that failed (e.g., "PreToolUse")
        """
        # Create unique key for this error
        key = f"{error_info['type']}:{hook_type}:{error_info['details']}"

        now = datetime.now(timezone.utc).isoformat()

        if key in self.errors:
            # Update existing error
            self.errors[key]["count"] += 1
            self.errors[key]["last_seen"] = now
        else:
            # Record new error
            self.errors[key] = {
                "type": error_info["type"],
                "hook_type": hook_type,
                "details": error_info["details"],
                "match": error_info["match"],
                "returncode": error_info.get("returncode", 1),
                "count": 1,
                "first_seen": now,
                "last_seen": now,
            }

        self._save_errors()
        self.logger.debug(
            f"Recorded error: {error_info['type']} (count: {self.errors[key]['count']})"
        )

    def is_known_failing_hook(self, hook_type: str) -> Optional[Dict[str, Any]]:
        """Check if a hook type is known to fail repeatedly.

        WHY check for 2+ failures:
        - Single failure could be transient
        - 2+ failures indicate persistent issue
        - Balance between retry attempts and error prevention

        Args:
            hook_type: Type of hook to check

        Returns:
            Error data if hook is known to fail, None otherwise
        """
        # Find any errors for this hook type with 2+ occurrences
        for key, error_data in self.errors.items():
            if error_data["hook_type"] == hook_type and error_data["count"] >= 2:
                return error_data

        return None

    def should_skip_hook(self, hook_type: str, threshold: int = 2) -> bool:
        """Determine if a hook should be skipped due to repeated failures.

        Args:
            hook_type: Type of hook to check
            threshold: Minimum failure count to skip (default: 2)

        Returns:
            True if hook should be skipped
        """
        error_data = self.is_known_failing_hook(hook_type)
        return error_data is not None and error_data["count"] >= threshold

    def suggest_fix(self, error_info: Dict[str, str]) -> str:
        """Suggest a fix for the detected error.

        WHY provide suggestions:
        - Users need actionable guidance
        - Common errors have known solutions
        - Reduces support burden
        - Improves user experience

        Args:
            error_info: Error information from detect_error()

        Returns:
            Human-readable fix suggestion
        """
        error_type = error_info["type"]
        details = error_info.get("details", "")

        suggestions = {
            "file_not_found": f"""File not found: {details}

Possible fixes:
1. Check if the file exists: ls -la {details}
2. Verify the path is correct in your hook configuration
3. If it's a script, ensure it's executable: chmod +x {details}
4. Clear error memory to retry: rm {self.memory_file}
""",
            "command_not_found": f"""Command not found: {details}

Possible fixes:
1. Install the missing command
2. Check if it's in your PATH: which {details}
3. Update hook configuration to use absolute path
4. Remove the hook if no longer needed
""",
            "permission_denied": f"""Permission denied: {details}

Possible fixes:
1. Check file permissions: ls -la {details}
2. Make file executable: chmod +x {details}
3. Run with appropriate privileges
4. Check file ownership
""",
            "syntax_error": """Syntax error in hook configuration or script

Possible fixes:
1. Review hook configuration in .claude-mpm/config
2. Check script syntax if using shell hooks
3. Validate JSON configuration format
4. Check for typos in hook definitions
""",
            "eval_error": f"""Error in hook execution: {details}

Possible fixes:
1. Review hook handler logs for details
2. Check hook configuration syntax
3. Verify all required dependencies are available
4. Test hook handler manually: python {details}
""",
            "general_error": f"""Error during hook execution: {error_info.get("match", "Unknown error")}

Possible fixes:
1. Check logs for detailed error information
2. Verify hook configuration is correct
3. Ensure all dependencies are installed
4. Clear error memory to retry: rm {self.memory_file}
""",
        }

        return suggestions.get(
            error_type, f"Unknown error type: {error_type}\n\nDetails: {details}"
        )

    def clear_errors(self, hook_type: Optional[str] = None):
        """Clear error memory to allow retry of failed hooks.

        Args:
            hook_type: If specified, only clear errors for this hook type
        """
        if hook_type is None:
            # Clear all errors
            count = len(self.errors)
            self.errors.clear()
            self._save_errors()
            self.logger.info(f"Cleared all {count} error records")
        else:
            # Clear errors for specific hook type
            keys_to_remove = [
                key
                for key, data in self.errors.items()
                if data["hook_type"] == hook_type
            ]
            for key in keys_to_remove:
                del self.errors[key]
            self._save_errors()
            self.logger.info(
                f"Cleared {len(keys_to_remove)} error records for {hook_type}"
            )

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all recorded errors.

        Returns:
            Dictionary with error statistics and details
        """
        if not self.errors:
            return {
                "total_errors": 0,
                "unique_errors": 0,
                "errors_by_type": {},
                "errors_by_hook": {},
            }

        errors_by_type = {}
        errors_by_hook = {}

        total_count = 0

        for error_data in self.errors.values():
            error_type = error_data["type"]
            hook_type = error_data["hook_type"]
            count = error_data["count"]

            total_count += count

            errors_by_type[error_type] = errors_by_type.get(error_type, 0) + count
            errors_by_hook[hook_type] = errors_by_hook.get(hook_type, 0) + count

        return {
            "total_errors": total_count,
            "unique_errors": len(self.errors),
            "errors_by_type": errors_by_type,
            "errors_by_hook": errors_by_hook,
            "memory_file": str(self.memory_file),
        }


# Global instance
_hook_error_memory: Optional[HookErrorMemory] = None


def get_hook_error_memory(memory_file: Optional[Path] = None) -> HookErrorMemory:
    """Get the global hook error memory instance.

    Args:
        memory_file: Optional custom memory file path

    Returns:
        HookErrorMemory instance
    """
    global _hook_error_memory
    if _hook_error_memory is None:
        _hook_error_memory = HookErrorMemory(memory_file)
    return _hook_error_memory


def clear_hook_errors(hook_type: Optional[str] = None):
    """Convenience function to clear hook error memory.

    Args:
        hook_type: If specified, only clear errors for this hook type
    """
    memory = get_hook_error_memory()
    memory.clear_errors(hook_type)
