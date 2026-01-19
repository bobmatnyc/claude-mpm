"""Entity extraction from conversation messages.

Extracts structured entities like files, functions, errors, and commands
from conversation content for enhanced search and filtering.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities that can be extracted.

    Attributes:
        FILE: File path (e.g., "src/auth.py")
        FUNCTION: Function or method name (e.g., "login()")
        CLASS: Class name (e.g., "UserService")
        ERROR: Error type or message (e.g., "ValueError")
        COMMAND: Shell command (e.g., "pytest tests/")
        URL: Web URL (e.g., "https://example.com")
        PACKAGE: Package or module name (e.g., "requests")
    """

    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    ERROR = "error"
    COMMAND = "command"
    URL = "url"
    PACKAGE = "package"


@dataclass
class Entity:
    """Extracted entity from conversation.

    Attributes:
        type: Entity type
        value: Entity value (file path, function name, etc.)
        context: Surrounding context (optional)
        metadata: Additional metadata

    Example:
        >>> entity = Entity(
        ...     type=EntityType.FILE,
        ...     value="src/auth.py",
        ...     context="Fix the login bug in auth.py"
        ... )
    """

    type: EntityType
    value: str
    context: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self) -> None:
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "value": self.value,
            "context": self.context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """Create Entity from dictionary."""
        return cls(
            type=EntityType(data["type"]),
            value=data["value"],
            context=data.get("context", ""),
            metadata=data.get("metadata", {}),
        )


class EntityExtractor:
    """Extracts entities from conversation messages.

    Uses regex patterns to identify files, functions, errors, commands, etc.

    Example:
        >>> extractor = EntityExtractor()
        >>> entities = extractor.extract("Fix the login bug in src/auth.py")
        >>> entities[0].type
        <EntityType.FILE: 'file'>
        >>> entities[0].value
        'src/auth.py'
    """

    # File patterns (common extensions and paths)
    FILE_PATTERNS = [
        r"\b[\w/\-\.]+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|go|rs|rb|php|cs|swift|kt|md|txt|json|yaml|yml|toml|xml|html|css|scss|sh|bash)\b",
        r"\b(?:src|lib|tests?|scripts?|docs?|config)/[\w/\-\.]+\b",
    ]

    # Function patterns (with parens or common prefixes)
    FUNCTION_PATTERNS = [
        r"\b[a-z_][a-z0-9_]*\(\)",
        r"\bdef\s+([a-z_][a-z0-9_]*)",
        r"\bfunction\s+([a-z_][a-z0-9_]*)",
        r"\basync\s+(?:def|function)\s+([a-z_][a-z0-9_]*)",
    ]

    # Class patterns (PascalCase)
    CLASS_PATTERNS = [
        r"\bclass\s+([A-Z][a-zA-Z0-9_]*)",
        r"\b([A-Z][a-zA-Z0-9_]+(?:Service|Controller|Manager|Handler|Repository|Model|View))\b",
    ]

    # Error patterns
    ERROR_PATTERNS = [
        r"\b([A-Z][a-zA-Z]*Error)\b",
        r"\b([A-Z][a-zA-Z]*Exception)\b",
        r"error:\s+(.+?)(?:\n|$)",
    ]

    # Command patterns (common CLI tools)
    COMMAND_PATTERNS = [
        r"\b(?:npm|yarn|pnpm|pip|poetry|cargo|go|make|docker|kubectl|git)\s+[\w\-]+",
        r"\bpytest\s+[\w/\-\.]+",
        r"\bpython\s+[\w/\-\.]+",
    ]

    # URL patterns
    URL_PATTERN = r"https?://[\w\.\-/\?=&#%]+"

    # Package patterns
    PACKAGE_PATTERNS = [
        r"\bimport\s+([\w\.]+)",
        r"\bfrom\s+([\w\.]+)\s+import",
        r"\brequire\(['\"]([\w\-@/]+)['\"]",
        r"\buse\s+([\w:]+)",
    ]

    def extract(self, text: str) -> List[Entity]:
        """Extract all entities from text.

        Args:
            text: Text to extract entities from

        Returns:
            List of extracted entities

        Example:
            >>> entities = extractor.extract("Fix the login bug in src/auth.py")
        """
        entities: List[Entity] = []

        # Extract files
        for pattern in self.FILE_PATTERNS:
            for match in re.finditer(pattern, text):
                entities.append(
                    Entity(
                        type=EntityType.FILE,
                        value=match.group(0),
                        context=self._get_context(text, match.start(), match.end()),
                    )
                )

        # Extract functions
        for pattern in self.FUNCTION_PATTERNS:
            for match in re.finditer(pattern, text):
                # Use group 1 if capturing group exists, else group 0
                value = match.group(1) if match.lastindex else match.group(0)
                entities.append(
                    Entity(
                        type=EntityType.FUNCTION,
                        value=value.rstrip("()"),  # Remove parens
                        context=self._get_context(text, match.start(), match.end()),
                    )
                )

        # Extract classes
        for pattern in self.CLASS_PATTERNS:
            for match in re.finditer(pattern, text):
                value = match.group(1) if match.lastindex else match.group(0)
                entities.append(
                    Entity(
                        type=EntityType.CLASS,
                        value=value,
                        context=self._get_context(text, match.start(), match.end()),
                    )
                )

        # Extract errors
        for pattern in self.ERROR_PATTERNS:
            for match in re.finditer(pattern, text):
                value = match.group(1) if match.lastindex else match.group(0)
                entities.append(
                    Entity(
                        type=EntityType.ERROR,
                        value=value.strip(),
                        context=self._get_context(text, match.start(), match.end()),
                    )
                )

        # Extract commands
        for pattern in self.COMMAND_PATTERNS:
            for match in re.finditer(pattern, text):
                entities.append(
                    Entity(
                        type=EntityType.COMMAND,
                        value=match.group(0),
                        context=self._get_context(text, match.start(), match.end()),
                    )
                )

        # Extract URLs
        for match in re.finditer(self.URL_PATTERN, text):
            entities.append(
                Entity(
                    type=EntityType.URL,
                    value=match.group(0),
                    context=self._get_context(text, match.start(), match.end()),
                )
            )

        # Extract packages
        for pattern in self.PACKAGE_PATTERNS:
            for match in re.finditer(pattern, text):
                value = match.group(1) if match.lastindex else match.group(0)
                entities.append(
                    Entity(
                        type=EntityType.PACKAGE,
                        value=value,
                        context=self._get_context(text, match.start(), match.end()),
                    )
                )

        # Deduplicate entities (same type + value)
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity.type, entity.value)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        logger.debug("Extracted %d unique entities from text", len(unique_entities))
        return unique_entities

    def _get_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Get surrounding context for entity.

        Args:
            text: Full text
            start: Entity start position
            end: Entity end position
            window: Characters to include before/after

        Returns:
            Context string with entity highlighted
        """
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)

        context = text[context_start:context_end]

        # Truncate at sentence boundaries if possible
        if context_start > 0 and ". " in context[:window]:
            context = context.split(". ", 1)[1]
        if context_end < len(text) and ". " in context[-window:]:
            context = context.rsplit(". ", 1)[0] + "."

        return context.strip()

    def filter_by_type(
        self, entities: List[Entity], entity_type: EntityType
    ) -> List[Entity]:
        """Filter entities by type.

        Args:
            entities: List of entities to filter
            entity_type: Type to filter for

        Returns:
            Filtered list of entities

        Example:
            >>> files = extractor.filter_by_type(entities, EntityType.FILE)
        """
        return [e for e in entities if e.type == entity_type]

    def get_unique_values(
        self, entities: List[Entity], entity_type: EntityType
    ) -> List[str]:
        """Get unique entity values for a type.

        Args:
            entities: List of entities
            entity_type: Type to extract values for

        Returns:
            List of unique values

        Example:
            >>> files = extractor.get_unique_values(entities, EntityType.FILE)
            ['src/auth.py', 'tests/test_auth.py']
        """
        return list({e.value for e in entities if e.type == entity_type})
