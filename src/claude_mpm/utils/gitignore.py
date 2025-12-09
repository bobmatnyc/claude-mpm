"""GitIgnore management utilities.

This module provides functionality to safely manage .gitignore entries,
ensuring claude-mpm configuration directories are excluded from version control.

Design Decisions:
- In-memory set for duplicate detection (O(1) lookups)
- Preserves existing file formatting and comments
- Adds section headers for clarity
- Handles edge cases (missing newlines, empty files, etc.)

Trade-offs:
- Simplicity: File append vs. full parse/rewrite (chosen append for safety)
- Performance: Read entire file vs. streaming (file is small, simplicity wins)
- Safety: Non-destructive append only, never modifies existing entries
"""

from pathlib import Path
from typing import List, Set, Tuple

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class GitIgnoreManager:
    """Manages .gitignore file updates safely and non-destructively.

    Design Pattern: Builder pattern for fluent API
    - Initialize with project directory
    - Call ensure_entries() to add patterns
    - Returns summary of changes made

    Performance:
    - Time Complexity: O(n) where n = existing .gitignore lines
    - Space Complexity: O(n) for storing unique entries in set
    - Expected Performance: <1ms for typical .gitignore files (<1000 lines)

    Error Handling:
    - FileNotFoundError: Creates new .gitignore if missing
    - PermissionError: Propagated to caller for appropriate handling
    - UnicodeDecodeError: Logged and treated as binary file (skip)
    """

    def __init__(self, project_dir: Path):
        """Initialize with project directory.

        Args:
            project_dir: Path to project root (where .gitignore lives)
        """
        self.project_dir = Path(project_dir)
        self.gitignore_path = self.project_dir / ".gitignore"

    def ensure_entries(self, entries: List[str]) -> Tuple[List[str], List[str]]:
        """Ensure specified entries exist in .gitignore.

        Non-destructive operation that:
        1. Reads existing entries (if file exists)
        2. Identifies which entries are missing
        3. Appends only missing entries with section header
        4. Preserves all existing content and formatting

        Args:
            entries: List of gitignore patterns to add (e.g., [".claude-mpm/"])

        Returns:
            Tuple of (added_entries, existing_entries)
            - added_entries: Patterns that were added to .gitignore
            - existing_entries: Patterns that were already present

        Example:
            >>> manager = GitIgnoreManager(Path("."))
            >>> added, existing = manager.ensure_entries([".claude-mpm/"])
            >>> print(f"Added: {added}, Already present: {existing}")
            Added: ['.claude-mpm/'], Already present: []
        """
        # Read existing entries
        existing = self._read_existing_entries()

        # Determine what needs to be added
        to_add = [e for e in entries if e not in existing]
        already_present = [e for e in entries if e in existing]

        if to_add:
            self._append_entries(to_add)
            logger.info(f"Added {len(to_add)} entries to .gitignore: {to_add}")

        if already_present:
            logger.debug(f"Entries already in .gitignore: {already_present}")

        return to_add, already_present

    def _read_existing_entries(self) -> Set[str]:
        """Read existing .gitignore entries.

        Parses .gitignore file and extracts all non-comment, non-blank patterns.
        Handles edge cases:
        - File doesn't exist -> returns empty set
        - File is binary -> logs warning, returns empty set
        - File has no newline at end -> handled correctly

        Returns:
            Set of existing gitignore patterns (stripped, normalized)
        """
        if not self.gitignore_path.exists():
            logger.debug(".gitignore does not exist, will create new file")
            return set()

        try:
            with open(self.gitignore_path, encoding="utf-8") as f:
                # Strip whitespace and comments, filter blanks
                entries = {
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                }

            logger.debug(f"Found {len(entries)} existing entries in .gitignore")
            return entries

        except UnicodeDecodeError:
            logger.warning(
                f".gitignore appears to be binary, cannot parse: {self.gitignore_path}"
            )
            return set()
        except Exception as e:
            logger.error(f"Error reading .gitignore: {e}")
            raise

    def _append_entries(self, entries: List[str]) -> None:
        """Append entries to .gitignore with proper formatting.

        Handles formatting edge cases:
        - Ensures blank line before new section (if file exists and isn't empty)
        - Adds section header comment for clarity
        - Ensures each entry on its own line
        - Handles missing trailing newline in existing file

        Args:
            entries: List of patterns to append

        Raises:
            PermissionError: If cannot write to .gitignore
            OSError: If disk is full or other I/O error
        """
        mode = "a" if self.gitignore_path.exists() else "w"

        try:
            with open(self.gitignore_path, mode, encoding="utf-8") as f:
                # Add blank line before entries if file exists and isn't empty
                if mode == "a" and self.gitignore_path.stat().st_size > 0:
                    # Check if last line has newline
                    with open(self.gitignore_path, "rb") as check:
                        check.seek(-1, 2)  # Seek to last byte
                        last_byte = check.read(1)
                        if last_byte != b"\n":
                            f.write("\n")

                    f.write("\n# Claude MPM configuration\n")
                else:
                    # New file or empty file - add header without extra blank line
                    f.write("# Claude MPM configuration\n")

                for entry in entries:
                    f.write(f"{entry}\n")

            logger.info(f"Updated .gitignore at {self.gitignore_path}")

        except PermissionError:
            logger.error(
                f"Permission denied writing to .gitignore: {self.gitignore_path}"
            )
            raise
        except OSError as e:
            logger.error(f"I/O error writing to .gitignore: {e}")
            raise


def ensure_claude_mpm_gitignore(project_dir: str = ".") -> dict:
    """Ensure claude-mpm directories are in .gitignore.

    Convenience function that wraps GitIgnoreManager to add standard
    claude-mpm configuration directories to .gitignore.

    Standard Entries Added:
    - .claude-mpm/: Main configuration directory
    - .claude/agents/: Agent runtime files

    Args:
        project_dir: Project directory path (default: current directory)

    Returns:
        Dictionary with operation results:
        - added: List of patterns that were added
        - existing: List of patterns that were already present
        - gitignore_path: Path to the .gitignore file

    Example:
        >>> result = ensure_claude_mpm_gitignore()
        >>> if result["added"]:
        ...     print(f"Added {len(result['added'])} entries to .gitignore")

    Error Handling:
        - PermissionError: Returns error dict with status="error"
        - FileNotFoundError on parent dir: Returns error dict
        - All other exceptions: Propagated to caller
    """
    try:
        manager = GitIgnoreManager(Path(project_dir))

        # Standard claude-mpm entries
        entries_to_add = [
            ".claude-mpm/",
            ".claude/agents/",
            ".mcp.json",
            ".claude.json",
            ".claude/",
        ]

        added, existing = manager.ensure_entries(entries_to_add)

        return {
            "status": "success",
            "added": added,
            "existing": existing,
            "gitignore_path": str(manager.gitignore_path),
        }

    except PermissionError as e:
        logger.error(f"Permission denied updating .gitignore: {e}")
        return {
            "status": "error",
            "error": f"Permission denied: {e}",
            "added": [],
            "existing": [],
        }
    except FileNotFoundError as e:
        logger.error(f"Project directory not found: {e}")
        return {
            "status": "error",
            "error": f"Directory not found: {e}",
            "added": [],
            "existing": [],
        }
