"""
PM Response Capture Utilities.

Captures actual PM agent responses from test scenarios for evaluation.
Supports both synchronous and asynchronous PM interactions, with response
storage in JSON format for replay testing.

Design Decision: Response Capture Architecture
- Captured responses stored in tests/eval/responses/ directory
- JSON format with metadata (timestamp, scenario ID, PM version)
- Separate capture and replay for CI/CD flexibility
- Privacy-aware: configurable PII redaction

Trade-offs:
- Storage: Local file storage vs. database (chose files for simplicity)
- Format: JSON vs. binary (chose JSON for human readability)
- Metadata: Lightweight vs. comprehensive (chose comprehensive for debugging)
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PMResponseMetadata:
    """Metadata for captured PM response."""
    scenario_id: str
    timestamp: str
    pm_version: str
    test_category: str
    input_hash: str
    capture_mode: str  # "live" or "replay"


@dataclass
class PMResponse:
    """Captured PM agent response with full context."""
    scenario_id: str
    input: str
    response: Dict[str, Any]
    metadata: PMResponseMetadata
    metrics: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario_id": self.scenario_id,
            "input": self.input,
            "response": self.response,
            "metadata": asdict(self.metadata),
            "metrics": self.metrics or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PMResponse":
        """Create from dictionary loaded from JSON."""
        metadata_dict = data["metadata"]
        metadata = PMResponseMetadata(**metadata_dict)

        return cls(
            scenario_id=data["scenario_id"],
            input=data["input"],
            response=data["response"],
            metadata=metadata,
            metrics=data.get("metrics"),
        )


class PMResponseCapture:
    """
    Capture and store PM agent responses for testing.

    Supports:
    - Response capture from live PM agent interactions
    - Metadata collection (timestamp, version, scenario)
    - Storage in JSON format for replay
    - PII redaction for sensitive data

    Example:
        >>> capture = PMResponseCapture(responses_dir="tests/eval/responses")
        >>> response = capture.capture_response(
        ...     scenario_id="url_linear",
        ...     input_text="verify https://linear.app/issue/JJF-62",
        ...     pm_response={"content": "...", "tools_used": ["Task"]},
        ...     category="ticketing"
        ... )
        >>> print(response.metadata.timestamp)
        2025-12-05T17:30:00Z
    """

    def __init__(
        self,
        responses_dir: str = "tests/eval/responses",
        pm_version: str = "5.0.9",
        redact_pii: bool = True,
    ):
        """
        Initialize response capture system.

        Args:
            responses_dir: Directory to store captured responses
            pm_version: PM agent version identifier
            redact_pii: Enable PII redaction in responses
        """
        self.responses_dir = Path(responses_dir)
        self.pm_version = pm_version
        self.redact_pii = redact_pii

        # Create directory structure
        self.responses_dir.mkdir(parents=True, exist_ok=True)
        (self.responses_dir / "ticketing").mkdir(exist_ok=True)
        (self.responses_dir / "circuit_breakers").mkdir(exist_ok=True)
        (self.responses_dir / "performance").mkdir(exist_ok=True)

    def capture_response(
        self,
        scenario_id: str,
        input_text: str,
        pm_response: Dict[str, Any],
        category: str = "general",
        metrics: Optional[Dict[str, float]] = None,
        redact_fn: Optional[Callable[[str], str]] = None,
    ) -> PMResponse:
        """
        Capture PM response with metadata.

        Args:
            scenario_id: Unique scenario identifier
            input_text: User input/prompt that triggered response
            pm_response: PM agent's response data
            category: Test category (ticketing, circuit_breakers, etc.)
            metrics: Optional evaluation metrics
            redact_fn: Custom redaction function for PII

        Returns:
            PMResponse object with captured data and metadata
        """
        # Apply redaction if enabled
        if self.redact_pii:
            if redact_fn:
                input_text = redact_fn(input_text)
                pm_response = self._redact_dict(pm_response, redact_fn)
            else:
                input_text = self._default_redact(input_text)
                pm_response = self._redact_dict(
                    pm_response,
                    self._default_redact
                )

        # Generate input hash for change detection
        input_hash = hashlib.sha256(input_text.encode()).hexdigest()[:16]

        # Create metadata
        metadata = PMResponseMetadata(
            scenario_id=scenario_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            pm_version=self.pm_version,
            test_category=category,
            input_hash=input_hash,
            capture_mode="live",
        )

        # Create response object
        response = PMResponse(
            scenario_id=scenario_id,
            input=input_text,
            response=pm_response,
            metadata=metadata,
            metrics=metrics,
        )

        # Save to file
        self._save_response(response, category)

        return response

    def _save_response(self, response: PMResponse, category: str):
        """Save response to JSON file."""
        category_dir = self.responses_dir / category
        category_dir.mkdir(exist_ok=True)

        filename = f"{response.scenario_id}_{response.metadata.input_hash}.json"
        filepath = category_dir / filename

        with open(filepath, "w") as f:
            json.dump(response.to_dict(), f, indent=2)

    def load_response(
        self,
        scenario_id: str,
        category: str = "general",
        input_hash: Optional[str] = None,
    ) -> Optional[PMResponse]:
        """
        Load captured response from storage.

        Args:
            scenario_id: Scenario identifier
            category: Test category
            input_hash: Optional input hash for specific version

        Returns:
            PMResponse if found, None otherwise
        """
        category_dir = self.responses_dir / category

        if not category_dir.exists():
            return None

        # Find matching response file
        if input_hash:
            filename = f"{scenario_id}_{input_hash}.json"
            filepath = category_dir / filename
            if filepath.exists():
                return self._load_from_file(filepath)
        else:
            # Load most recent response for scenario
            pattern = f"{scenario_id}_*.json"
            matching_files = list(category_dir.glob(pattern))

            if matching_files:
                # Sort by modification time, newest first
                latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)
                return self._load_from_file(latest_file)

        return None

    def _load_from_file(self, filepath: Path) -> PMResponse:
        """Load response from JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return PMResponse.from_dict(data)

    def list_responses(
        self,
        category: Optional[str] = None,
        scenario_id: Optional[str] = None,
    ) -> List[PMResponse]:
        """
        List all captured responses with optional filtering.

        Args:
            category: Filter by test category
            scenario_id: Filter by scenario ID

        Returns:
            List of PMResponse objects
        """
        responses = []

        search_dirs = []
        if category:
            category_dir = self.responses_dir / category
            if category_dir.exists():
                search_dirs.append(category_dir)
        else:
            # Search all category directories
            search_dirs = [
                d for d in self.responses_dir.iterdir() if d.is_dir()
            ]

        for directory in search_dirs:
            pattern = f"{scenario_id}_*.json" if scenario_id else "*.json"
            for filepath in directory.glob(pattern):
                try:
                    response = self._load_from_file(filepath)
                    responses.append(response)
                except Exception as e:
                    print(f"Warning: Failed to load {filepath}: {e}")

        # Sort by timestamp, newest first
        responses.sort(
            key=lambda r: r.metadata.timestamp,
            reverse=True
        )

        return responses

    def _default_redact(self, text: str) -> str:
        """
        Default PII redaction function.

        Redacts:
        - Email addresses
        - API keys
        - Tokens
        - URLs with sensitive paths
        """
        import re

        # Redact email addresses
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[REDACTED_EMAIL]',
            text
        )

        # Redact API keys (common patterns)
        text = re.sub(
            r'(?:api[_-]?key|token|secret)[\s:=]+[\'"]?([A-Za-z0-9_\-]{20,})[\'"]?',
            r'\1=[REDACTED_KEY]',
            text,
            flags=re.IGNORECASE
        )

        # Redact URLs with potential secrets
        text = re.sub(
            r'https?://[^\s]+\?[^\s]*(?:token|key|secret)=[^\s&]+',
            '[REDACTED_URL]',
            text
        )

        return text

    def _redact_dict(
        self,
        data: Dict[str, Any],
        redact_fn: Callable[[str], str]
    ) -> Dict[str, Any]:
        """Recursively redact strings in dictionary."""
        result = {}

        for key, value in data.items():
            if isinstance(value, str):
                result[key] = redact_fn(value)
            elif isinstance(value, dict):
                result[key] = self._redact_dict(value, redact_fn)
            elif isinstance(value, list):
                result[key] = [
                    self._redact_dict(item, redact_fn) if isinstance(item, dict)
                    else redact_fn(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value

        return result


class AsyncPMResponseCapture(PMResponseCapture):
    """
    Async version of PM response capture for async test scenarios.

    Example:
        >>> async def test_async_pm():
        ...     capture = AsyncPMResponseCapture()
        ...     response = await capture.capture_response_async(
        ...         scenario_id="async_test",
        ...         input_text="test input",
        ...         pm_response_coro=get_pm_response("test input")
        ...     )
    """

    async def capture_response_async(
        self,
        scenario_id: str,
        input_text: str,
        pm_response_coro,
        category: str = "general",
        metrics: Optional[Dict[str, float]] = None,
    ) -> PMResponse:
        """
        Capture PM response from async coroutine.

        Args:
            scenario_id: Unique scenario identifier
            input_text: User input/prompt
            pm_response_coro: Coroutine that returns PM response
            category: Test category
            metrics: Optional evaluation metrics

        Returns:
            PMResponse object with captured data
        """
        # Await the PM response
        pm_response = await pm_response_coro

        # Use synchronous capture for storage
        return self.capture_response(
            scenario_id=scenario_id,
            input_text=input_text,
            pm_response=pm_response,
            category=category,
            metrics=metrics,
        )


def get_responses_dir() -> Path:
    """Get the responses directory path."""
    return Path(__file__).parent.parent / "responses"


def get_golden_responses_dir() -> Path:
    """Get the golden responses directory path."""
    return Path(__file__).parent.parent / "golden_responses"


# Convenience functions
def capture_pm_response(
    scenario_id: str,
    input_text: str,
    pm_response: Dict[str, Any],
    category: str = "general",
    **kwargs
) -> PMResponse:
    """
    Convenience function to capture PM response.

    Example:
        >>> response = capture_pm_response(
        ...     scenario_id="test_1",
        ...     input_text="create ticket",
        ...     pm_response={"content": "...", "tools": ["Task"]},
        ...     category="ticketing"
        ... )
    """
    capture = PMResponseCapture(**kwargs)
    return capture.capture_response(
        scenario_id=scenario_id,
        input_text=input_text,
        pm_response=pm_response,
        category=category,
    )


def load_pm_response(
    scenario_id: str,
    category: str = "general",
    **kwargs
) -> Optional[PMResponse]:
    """
    Convenience function to load captured PM response.

    Example:
        >>> response = load_pm_response(
        ...     scenario_id="test_1",
        ...     category="ticketing"
        ... )
    """
    capture = PMResponseCapture(**kwargs)
    return capture.load_response(scenario_id, category)
