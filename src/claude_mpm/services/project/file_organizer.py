"""
FileOrganizer — file classification and movement.
==================================================

Key improvement over the original monolithic class: *classify()* is separated
from execution so tests can exercise classification logic without touching the
filesystem.
"""

from pathlib import Path

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level constant (previously inline inside organize_misplaced_files)
# ---------------------------------------------------------------------------

PROTECTED_ROOT_FILES: frozenset[str] = frozenset(
    {
        "setup.py",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "requirements.txt",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "Makefile",
        "makefile",
        "Dockerfile",
        "docker-compose.yml",
        ".gitignore",
        ".gitattributes",
        "LICENSE",
        "README.md",
        "README.rst",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "CLAUDE.md",
        "CODE.md",
        "DEVELOPER.md",
        "STRUCTURE.md",
        "OPS.md",
        ".env.example",
        ".env.sample",
        "VERSION",
        "BUILD_NUMBER",
    }
)


class FileOrganizer:
    """Classify and (optionally) move misplaced files in *project_path*."""

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, file: Path) -> tuple[str | None, str, str]:
        """Return *(target_dir, confidence, reason)* for a single *file*.

        *confidence* is one of ``"high"``, ``"medium"``, or ``"low"``.
        *target_dir* is ``None`` when the file should stay where it is.
        """
        file_lower = file.name.lower()
        target_dir: str | None = None
        confidence = "low"
        reason = ""

        # Test files (high confidence)
        if "test" in file_lower and file.suffix == ".py":
            if file_lower.startswith("test_") or file_lower.endswith("_test.py"):
                target_dir = "tests"
                confidence = "high"
                reason = "Test file pattern detected"

        # Shell/bash scripts (high confidence)
        elif file.suffix in (".sh", ".bash"):
            target_dir = "scripts"
            confidence = "high"
            reason = "Shell script file"

        # Python scripts (medium confidence)
        elif file.suffix == ".py" and any(
            pattern in file_lower for pattern in ("script", "run", "cli", "tool")
        ):
            target_dir = "scripts"
            confidence = "medium"
            reason = "Python script pattern detected"

        # Temporary/log files (high confidence)
        elif file.suffix in (".log", ".tmp", ".temp", ".cache"):
            target_dir = "tmp"
            confidence = "high"
            reason = "Temporary/log file"
        elif file_lower.startswith(("tmp_", "temp_", "test_output", "debug_")):
            target_dir = "tmp"
            confidence = "high"
            reason = "Temporary file pattern"

        # Documentation files (medium confidence)
        elif (
            file.suffix in (".md", ".rst", ".txt")
            and file.name not in PROTECTED_ROOT_FILES
        ):
            if any(
                pattern in file_lower
                for pattern in ("notes", "draft", "todo", "spec", "design")
            ):
                target_dir = "docs"
                confidence = "medium"
                reason = "Documentation file pattern"

        # Data files (medium confidence)
        elif file.suffix in (".csv", ".json", ".xml", ".yaml", ".yml"):
            if file.suffix in (".yaml", ".yml") and any(
                pattern in file_lower for pattern in ("config", "settings")
            ):
                confidence = "low"
            else:
                target_dir = "data"
                confidence = "medium"
                reason = "Data file"

        # Build artifacts (high confidence)
        elif file.suffix in (".whl", ".tar.gz", ".zip") and "dist" not in str(
            file.parent
        ):
            target_dir = "dist"
            confidence = "high"
            reason = "Build artifact"

        # Example files (medium confidence)
        elif "example" in file_lower or "sample" in file_lower:
            target_dir = "examples"
            confidence = "medium"
            reason = "Example file pattern"

        return target_dir, confidence, reason

    def propose_moves(self, auto_safe: bool = True) -> list[dict]:
        """Return a list of proposed move dicts without touching the filesystem."""
        moves: list[dict] = []

        root_files = list(self.project_path.glob("*"))
        for file in root_files:
            if file.is_file() and file.name not in PROTECTED_ROOT_FILES:
                target_dir, confidence, reason = self.classify(file)
                if target_dir is None:
                    continue

                should_move = (
                    confidence == "high"
                    if auto_safe
                    else confidence in ("high", "medium")
                )
                if should_move:
                    target_path = self.project_path / target_dir / file.name
                    moves.append(
                        {
                            "source": str(file.relative_to(self.project_path)),
                            "target": str(target_path.relative_to(self.project_path)),
                            "reason": reason,
                            "confidence": confidence,
                        }
                    )

        # Deeply nested test files (non-safe mode only)
        if not auto_safe:
            for test_file in self.project_path.rglob("*test*.py"):
                if "tests" in test_file.parts or "test" in test_file.parts:
                    continue
                if any(
                    part in test_file.parts
                    for part in ("node_modules", "venv", ".venv", "site-packages")
                ):
                    continue
                target_path = self.project_path / "tests" / test_file.name
                moves.append(
                    {
                        "source": str(test_file.relative_to(self.project_path)),
                        "target": str(target_path.relative_to(self.project_path)),
                        "reason": "Test file found outside tests directory",
                        "confidence": "medium",
                    }
                )

        return moves

    def execute_moves(self, moves: list[dict]) -> dict:
        """Physically move files according to a pre-computed *moves* list.

        Returns ``{"completed": [...], "errors": [...]}``.
        """
        completed: list[dict] = []
        errors: list[dict] = []

        for move in moves:
            source = self.project_path / move["source"]
            target = self.project_path / move["target"]
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                source.rename(target)
                completed.append(move)
                logger.info(f"Moved {move['source']} → {move['target']}")
            except Exception as exc:
                errors.append({"file": move["source"], "error": str(exc)})
                logger.error(f"Failed to move {move['source']}: {exc}")

        return {"completed": completed, "errors": errors}

    def organize(self, dry_run: bool = True, auto_safe: bool = True) -> dict:
        """High-level entry point: propose or execute moves.

        This method preserves the original public interface expected by the
        thin coordinator (and indirectly by the callers).
        """
        moves = self.propose_moves(auto_safe=auto_safe)
        skipped: list[dict] = []

        # Collect low-confidence skips for reporting purposes
        root_files = list(self.project_path.glob("*"))
        for file in root_files:
            if file.is_file() and file.name not in PROTECTED_ROOT_FILES:
                target_dir, confidence, _ = self.classify(file)
                if target_dir is None:
                    continue
                should_move = (
                    confidence == "high"
                    if auto_safe
                    else confidence in ("high", "medium")
                )
                if not should_move and confidence != "low":
                    skipped.append(
                        {
                            "file": file.name,
                            "suggested_dir": target_dir,
                            "confidence": confidence,
                            "reason": "Low confidence move — skipped (use --no-auto-safe to include)",
                        }
                    )

        if dry_run:
            return {
                "dry_run": True,
                "auto_safe": auto_safe,
                "proposed_moves": moves,
                "completed_moves": [],
                "skipped": skipped,
                "errors": [],
                "total": len(moves),
                "total_skipped": len(skipped),
                "total_errors": 0,
            }

        result = self.execute_moves(moves)
        return {
            "dry_run": False,
            "auto_safe": auto_safe,
            "proposed_moves": [],
            "completed_moves": result["completed"],
            "skipped": skipped,
            "errors": result["errors"],
            "total": len(result["completed"]),
            "total_skipped": len(skipped),
            "total_errors": len(result["errors"]),
        }
