"""Cross-process correlation storage using .claude-mpm directory."""

import json
import time
from pathlib import Path


def get_correlation_dir() -> Path:
    """Get correlation directory in project's .claude-mpm folder."""
    # Use CWD's .claude-mpm directory (where hooks run from)
    cwd = Path.cwd()
    return cwd / ".claude-mpm" / "correlations"


TTL_SECONDS = 3600  # 1 hour


class CorrelationManager:
    """Manages correlation IDs across separate hook processes."""

    @staticmethod
    def store(session_id: str, tool_call_id: str, tool_name: str) -> None:
        """Store correlation data for later retrieval by post_tool."""
        correlation_dir = get_correlation_dir()
        correlation_dir.mkdir(parents=True, exist_ok=True)
        filepath = correlation_dir / f"correlation_{session_id}.json"
        data = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "timestamp": time.time(),
        }
        filepath.write_text(json.dumps(data))

    @staticmethod
    def retrieve(session_id: str) -> str | None:
        """Retrieve and delete correlation data from temp file."""
        correlation_dir = get_correlation_dir()
        filepath = correlation_dir / f"correlation_{session_id}.json"
        if not filepath.exists():
            return None
        try:
            data = json.loads(filepath.read_text())
            filepath.unlink()  # Delete after reading
            return data.get("tool_call_id")
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def cleanup_old() -> None:
        """Remove correlation files older than TTL."""
        correlation_dir = get_correlation_dir()
        if not correlation_dir.exists():
            return
        now = time.time()
        for filepath in correlation_dir.glob("correlation_*.json"):
            try:
                if now - filepath.stat().st_mtime > TTL_SECONDS:
                    filepath.unlink()
            except OSError:
                pass
