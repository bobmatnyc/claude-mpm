from pathlib import Path

"""Context Preservation service for handling Claude conversation data.

This service specializes in parsing and preserving Claude's conversation
context, handling large .claude.json files efficiently.

Design Principles:
- Streaming JSON parsing for large files
- Memory-efficient processing
- Privacy-preserving extraction
- Graceful handling of corrupted data
"""

import gzip
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import ijson  # For streaming JSON parsing

from claude_mpm.services.core.base import BaseService


@dataclass
class ConversationContext:
    """Context information for a single conversation."""

    conversation_id: str
    title: str
    message_count: int
    last_message_time: float
    file_references: List[str] = field(default_factory=list)
    open_tabs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    is_active: bool = False


@dataclass
class ConversationState:
    """Claude conversation state and context."""

    active_conversation_id: Optional[str]
    active_conversation: Optional[ConversationContext]
    recent_conversations: List[ConversationContext]
    total_conversations: int
    total_storage_mb: float
    preferences: Dict[str, Any]
    open_files: List[str]
    recent_files: List[str]
    pinned_files: List[str]


class ContextPreservationService(BaseService):
    """Service for preserving and managing Claude conversation context."""

    def __init__(self, claude_dir: Optional[Path] = None):
        """Initialize Context Preservation service.

        Args:
            claude_dir: Claude configuration directory (default: ~/.claude)
        """
        super().__init__("ContextPreservation")

        # Claude configuration paths
        self.claude_dir = claude_dir or Path.home() / ".claude"
        self.claude_json_path = self.claude_dir / ".claude.json"
        self.claude_backup_dir = self.claude_dir / "backups"

        # Size thresholds
        self.large_file_threshold_mb = 100
        self.compression_threshold_mb = 50

        # Context extraction limits
        self.max_conversations_to_extract = 10
        self.max_messages_per_conversation = 100
        self.max_file_references = 1000

        # Statistics
        self.files_processed = 0
        self.total_size_processed_mb = 0.0

        self.log_info(f"Context Preservation initialized for: {self.claude_dir}")

    async def initialize(self) -> bool:
        """Initialize the Context Preservation service.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing Context Preservation service")

            # Ensure backup directory exists
            self.claude_backup_dir.mkdir(parents=True, exist_ok=True)

            # Check Claude configuration
            if self.claude_json_path.exists():
                size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)
                self.log_info(f"Found Claude configuration: {size_mb:.2f}MB")
            else:
                self.log_warning("Claude configuration not found")

            self._initialized = True
            self.log_info("Context Preservation service initialized successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize Context Preservation: {e}")
            return False

    async def parse_claude_json(
        self, extract_full: bool = False
    ) -> Optional[ConversationState]:
        """Parse Claude's .claude.json file safely.

        Args:
            extract_full: Whether to extract full conversation data

        Returns:
            ConversationState object or None if parsing failed
        """
        try:
            if not self.claude_json_path.exists():
                self.log_debug("Claude configuration file not found")
                return self._empty_conversation_state()

            file_size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)
            self.log_info(f"Parsing Claude configuration: {file_size_mb:.2f}MB")

            # Choose parsing strategy based on file size
            if file_size_mb > self.large_file_threshold_mb:
                self.log_info("Using streaming parser for large file")
                return await self._parse_large_claude_json(extract_full)
            return await self._parse_standard_claude_json(extract_full)

        except Exception as e:
            self.log_error(f"Failed to parse Claude JSON: {e}")
            return None

    async def extract_active_conversation(self) -> Optional[ConversationContext]:
        """Extract only the active conversation context.

        Returns:
            ConversationContext for active conversation or None
        """
        try:
            if not self.claude_json_path.exists():
                return None

            # Use streaming to find active conversation
            with self.claude_json_path.open("rb") as f:
                parser = ijson.parse(f)

                active_conv_id = None
                current_conv = {}

                for prefix, event, value in parser:
                    # Get active conversation ID
                    if prefix == "activeConversationId":
                        active_conv_id = value

                    # Parse conversations array
                    elif prefix.startswith("conversations.item"):
                        if event == "map_key":
                            pass
                        elif (
                            active_conv_id and current_conv.get("id") == active_conv_id
                        ):
                            # Found active conversation
                            return self._create_conversation_context(current_conv)

                return None

        except Exception as e:
            self.log_error(f"Failed to extract active conversation: {e}")
            return None

    async def compress_conversation_history(self, keep_recent_days: int = 7) -> bool:
        """Compress large conversation histories.

        Args:
            keep_recent_days: Days of recent conversations to keep uncompressed

        Returns:
            True if compression successful
        """
        try:
            if not self.claude_json_path.exists():
                return False

            file_size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)

            if file_size_mb < self.compression_threshold_mb:
                self.log_debug(f"File too small for compression: {file_size_mb:.2f}MB")
                return False

            self.log_info(f"Compressing conversation history: {file_size_mb:.2f}MB")

            # Create backup first
            await self._create_backup()

            # Load and filter conversations
            cutoff_time = datetime.now(timezone.utc).timestamp() - (
                keep_recent_days * 86400
            )

            with self.claude_json_path.open() as f:
                data = json.load(f)

            original_count = len(data.get("conversations", []))

            # Filter conversations
            recent_conversations = []
            archived_conversations = []

            for conv in data.get("conversations", []):
                updated_at = conv.get("updatedAt", 0) / 1000  # Convert from ms
                if updated_at >= cutoff_time:
                    recent_conversations.append(conv)
                else:
                    # Create minimal version for archive
                    archived_conversations.append(
                        {
                            "id": conv.get("id"),
                            "title": conv.get("title"),
                            "createdAt": conv.get("createdAt"),
                            "updatedAt": conv.get("updatedAt"),
                            "messageCount": len(conv.get("messages", [])),
                            "archived": True,
                        }
                    )

            # Update data with filtered conversations
            data["conversations"] = recent_conversations
            data["archivedConversations"] = archived_conversations

            # Write compressed version
            temp_path = self.claude_json_path.with_suffix(".tmp")
            with temp_path.open("w") as f:
                json.dump(data, f, separators=(",", ":"))  # Compact format

            # Replace original
            temp_path.replace(self.claude_json_path)

            new_size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)
            reduction_pct = ((file_size_mb - new_size_mb) / file_size_mb) * 100

            self.log_info(
                f"Compression complete: {original_count} -> {len(recent_conversations)} "
                f"conversations, {file_size_mb:.2f}MB -> {new_size_mb:.2f}MB "
                f"({reduction_pct:.1f}% reduction)"
            )

            return True

        except Exception as e:
            self.log_error(f"Failed to compress conversation history: {e}")
            return False

    async def handle_file_references(self, conversation: Dict[str, Any]) -> List[str]:
        """Extract and validate file references from conversation.

        Args:
            conversation: Conversation data dictionary

        Returns:
            List of valid file paths referenced in conversation
        """
        try:
            files = set()

            # Extract from messages
            for message in conversation.get("messages", [])[
                : self.max_messages_per_conversation
            ]:
                # Extract from content
                content = message.get("content", "")
                if isinstance(content, str):
                    files.update(self._extract_file_paths(content))

                # Extract from attachments
                for attachment in message.get("attachments", []):
                    if attachment.get("type") == "file":
                        file_path = attachment.get("path")
                        if file_path:
                            files.add(file_path)

            # Validate file existence
            valid_files = []
            for file_path in list(files)[: self.max_file_references]:
                try:
                    if Path(file_path).exists():
                        valid_files.append(file_path)
                except Exception:
                    pass  # Invalid path

            return valid_files

        except Exception as e:
            self.log_error(f"Failed to handle file references: {e}")
            return []

    async def preserve_user_preferences(self) -> Dict[str, Any]:
        """Extract and preserve user preferences and settings.

        Returns:
            Dictionary of user preferences
        """
        try:
            if not self.claude_json_path.exists():
                return {}

            # Use streaming to extract preferences
            preferences = {}

            with self.claude_json_path.open("rb") as f:
                parser = ijson.parse(f)

                for prefix, event, value in parser:
                    if prefix.startswith("preferences"):
                        # Extract preference key and value
                        if event == "map_key":
                            current_key = value
                        elif event in ("string", "number", "boolean"):
                            preferences[current_key] = value

            self.log_debug(f"Preserved {len(preferences)} user preferences")
            return preferences

        except Exception as e:
            self.log_error(f"Failed to preserve user preferences: {e}")
            return {}

    async def _parse_standard_claude_json(
        self, extract_full: bool
    ) -> ConversationState:
        """Parse Claude JSON using standard JSON parser."""
        try:
            with self.claude_json_path.open() as f:
                data = json.load(f)

            return await self._extract_conversation_state(data, extract_full)

        except json.JSONDecodeError as e:
            self.log_error(f"JSON decode error: {e}")
            return self._empty_conversation_state()

    async def _parse_large_claude_json(self, extract_full: bool) -> ConversationState:
        """Parse large Claude JSON using streaming parser."""
        try:
            # Extract key data using streaming
            active_conv_id = None
            conversations = []
            preferences = {}
            open_files = []

            with self.claude_json_path.open("rb") as f:
                parser = ijson.parse(f)

                conversation_count = 0
                current_conv = {}
                in_conversation = False

                for prefix, event, value in parser:
                    # Limit conversations extracted
                    if conversation_count >= self.max_conversations_to_extract:
                        break

                    # Extract active conversation ID
                    if prefix == "activeConversationId":
                        active_conv_id = value

                    # Extract conversations
                    elif prefix.startswith("conversations.item"):
                        if event == "start_map":
                            in_conversation = True
                            current_conv = {}
                        elif event == "end_map":
                            if in_conversation and current_conv:
                                conversations.append(current_conv)
                                conversation_count += 1
                            in_conversation = False
                            current_conv = {}
                        elif in_conversation and event == "map_key":
                            current_key = value
                        elif in_conversation and current_key:
                            current_conv[current_key] = value

                    # Extract open files
                    elif prefix.startswith("openFiles.item"):
                        if event == "string":
                            open_files.append(value)

            # Find active conversation
            active_conv = None
            recent_convs = []

            for conv in conversations:
                if conv.get("id") == active_conv_id:
                    active_conv = self._create_conversation_context(conv)
                else:
                    recent_convs.append(self._create_conversation_context(conv))

            file_size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)

            return ConversationState(
                active_conversation_id=active_conv_id,
                active_conversation=active_conv,
                recent_conversations=recent_convs[:5],
                total_conversations=len(conversations),
                total_storage_mb=file_size_mb,
                preferences=preferences,
                open_files=open_files[:100],
                recent_files=[],
                pinned_files=[],
            )

        except Exception as e:
            self.log_error(f"Failed to parse large Claude JSON: {e}")
            return self._empty_conversation_state()

    async def _extract_conversation_state(
        self, data: Dict[str, Any], extract_full: bool
    ) -> ConversationState:
        """Extract conversation state from parsed data."""
        try:
            conversations = data.get("conversations", [])
            active_conv_id = data.get("activeConversationId")

            # Find active conversation
            active_conv = None
            if active_conv_id:
                for conv in conversations:
                    if conv.get("id") == active_conv_id:
                        active_conv = self._create_conversation_context(conv)
                        break

            # Get recent conversations
            recent_convs = []
            if extract_full:
                sorted_convs = sorted(
                    conversations, key=lambda c: c.get("updatedAt", 0), reverse=True
                )[: self.max_conversations_to_extract]

                for conv in sorted_convs:
                    if conv.get("id") != active_conv_id:
                        recent_convs.append(self._create_conversation_context(conv))

            file_size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)

            return ConversationState(
                active_conversation_id=active_conv_id,
                active_conversation=active_conv,
                recent_conversations=recent_convs,
                total_conversations=len(conversations),
                total_storage_mb=file_size_mb,
                preferences=data.get("preferences", {}),
                open_files=data.get("openFiles", [])[:100],
                recent_files=data.get("recentFiles", [])[:100],
                pinned_files=data.get("pinnedFiles", [])[:50],
            )

        except Exception as e:
            self.log_error(f"Failed to extract conversation state: {e}")
            return self._empty_conversation_state()

    def _create_conversation_context(self, conv: Dict[str, Any]) -> ConversationContext:
        """Create ConversationContext from conversation data."""
        return ConversationContext(
            conversation_id=conv.get("id", ""),
            title=conv.get("title", "Untitled"),
            created_at=conv.get("createdAt", 0) / 1000,  # Convert from ms
            updated_at=conv.get("updatedAt", 0) / 1000,
            message_count=len(conv.get("messages", [])),
            total_tokens=conv.get("totalTokens", 0),
            max_tokens=conv.get("maxTokens", 100000),
            referenced_files=[],  # Would need full extraction
            open_tabs=conv.get("openTabs", []),
            tags=conv.get("tags", []),
            is_active=False,
        )

    def _empty_conversation_state(self) -> ConversationState:
        """Create empty conversation state."""
        return ConversationState(
            active_conversation_id=None,
            active_conversation=None,
            recent_conversations=[],
            total_conversations=0,
            total_storage_mb=0.0,
            preferences={},
            open_files=[],
            recent_files=[],
            pinned_files=[],
        )

    def _extract_file_paths(self, content: str) -> List[str]:
        """Extract file paths from message content."""
        import re

        files = set()

        # Common file path patterns
        patterns = [
            r'[\'"`]([/\\]?(?:[a-zA-Z]:)?[/\\]?[\w\-_./\\]+\.\w+)[\'"`]',
            r"(?:^|\s)([/\\]?(?:[a-zA-Z]:)?[/\\]?[\w\-_./\\]+\.\w+)(?:\s|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            files.update(matches)

        return list(files)

    async def _create_backup(self) -> Path:
        """Create backup of Claude configuration."""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_name = f"claude_backup_{timestamp}.json"

            # Compress if large
            file_size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.compression_threshold_mb:
                backup_name += ".gz"
                backup_path = self.claude_backup_dir / backup_name

                with self.claude_json_path.open("rb") as f_in:
                    with gzip.open(backup_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                backup_path = self.claude_backup_dir / backup_name
                shutil.copy2(self.claude_json_path, backup_path)

            self.log_info(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            self.log_error(f"Failed to create backup: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get context preservation statistics.

        Returns:
            Dictionary containing statistics
        """
        claude_size_mb = 0.0
        if self.claude_json_path.exists():
            claude_size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)

        backup_count = 0
        backup_size_mb = 0.0
        if self.claude_backup_dir.exists():
            backups = list(self.claude_backup_dir.glob("claude_backup_*.json*"))
            backup_count = len(backups)
            backup_size_mb = sum(f.stat().st_size for f in backups) / (1024 * 1024)

        return {
            "claude_config_exists": self.claude_json_path.exists(),
            "claude_config_size_mb": round(claude_size_mb, 2),
            "is_large_file": claude_size_mb > self.large_file_threshold_mb,
            "backup_count": backup_count,
            "total_backup_size_mb": round(backup_size_mb, 2),
            "files_processed": self.files_processed,
            "total_size_processed_mb": round(self.total_size_processed_mb, 2),
        }
