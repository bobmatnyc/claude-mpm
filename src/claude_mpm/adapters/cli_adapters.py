"""
CLI Adapters for alternative AI coding assistants.
Enables claude-mpm orchestration to work with Codex, Auggie, and Gemini CLI.
"""

import json
import shutil
import subprocess  # nosec B404 - required for CLI adapters
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CLIAdapter(ABC):
    """Base adapter for AI coding CLI tools."""

    name: str
    command: str

    @abstractmethod
    def invoke(self, prompt: str, **kwargs) -> str:
        """Execute prompt and return response text."""

    @abstractmethod
    def invoke_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Execute prompt and return structured response."""

    def is_available(self) -> bool:
        """Check if CLI is installed."""
        return shutil.which(self.command) is not None

    def _run(self, args: List[str], input_text: Optional[str] = None) -> str:
        """Run CLI command and return stdout."""
        result = subprocess.run(  # nosec B603 - args are controlled by adapter subclasses
            args,
            check=False,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"{self.name} error: {result.stderr}")
        return result.stdout


class ClaudeAdapter(CLIAdapter):
    """Claude Code CLI adapter (default)."""

    name = "claude"
    command = "claude"

    def invoke(self, prompt: str, **kwargs) -> str:
        return self._run(["claude", "-p", prompt])

    def invoke_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        output = self._run(["claude", "-p", "--output-format", "json", prompt])
        return json.loads(output)


class CodexAdapter(CLIAdapter):
    """OpenAI Codex CLI adapter.

    Install: npm i -g @openai/codex
    Auth: export OPENAI_API_KEY="sk-..."  # pragma: allowlist secret
    """

    name = "codex"
    command = "codex"

    def invoke(self, prompt: str, **kwargs) -> str:
        return self._run(["codex", "exec", prompt])

    def invoke_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        output = self._run(["codex", "exec", "--json", prompt])
        # Parse JSONL format, return all responses
        lines = [json.loads(line) for line in output.strip().split("\n") if line]
        return {"responses": lines, "final": lines[-1] if lines else {}}


class AuggieAdapter(CLIAdapter):
    """Augment Code Auggie CLI adapter.

    Install: npm install -g @augmentcode/auggie
    Auth: auggie login
    """

    name = "auggie"
    command = "auggie"

    def invoke(self, prompt: str, **kwargs) -> str:
        return self._run(["auggie", "--print", "--quiet", prompt])

    def invoke_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # Auggie doesn't have native JSON output for responses
        output = self.invoke(prompt, **kwargs)
        return {"response": output, "format": "text"}


class GeminiAdapter(CLIAdapter):
    """Google Gemini CLI adapter.

    Install: npm install -g @google/gemini-cli
    Auth: export GEMINI_API_KEY="..."
    """

    name = "gemini"
    command = "gemini"

    def invoke(self, prompt: str, model: str = "flash", **kwargs) -> str:
        return self._run(["gemini", "-m", model, "-p", prompt])

    def invoke_json(
        self, prompt: str, model: str = "flash", **kwargs
    ) -> Dict[str, Any]:
        output = self._run(["gemini", "-m", model, "-o", "json", prompt])
        return json.loads(output)


# Registry of available adapters
ADAPTERS: Dict[str, type] = {
    "claude": ClaudeAdapter,
    "codex": CodexAdapter,
    "auggie": AuggieAdapter,
    "gemini": GeminiAdapter,
}


def get_adapter(name: str = "claude") -> CLIAdapter:
    """Get adapter instance by name.

    Args:
        name: Adapter name (claude, codex, auggie, gemini)

    Returns:
        Instantiated adapter

    Raises:
        ValueError: If adapter name is unknown
    """
    if name not in ADAPTERS:
        raise ValueError(f"Unknown adapter: {name}. Available: {list(ADAPTERS.keys())}")
    return ADAPTERS[name]()


def get_available_adapters() -> List[str]:
    """Return list of installed/available CLI adapters."""
    return [name for name, cls in ADAPTERS.items() if cls().is_available()]
