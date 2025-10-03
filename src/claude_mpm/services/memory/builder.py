#!/usr/bin/env python3
"""
Memory Builder Service
=====================

Builds agent memories from project documentation by parsing and extracting
memory-worthy content for appropriate agents.

This service provides:
- Documentation parsing (CLAUDE.md, QA.md, STRUCTURE.md, etc.)
- Content extraction and categorization
- Agent assignment based on content type
- Concise memory entry creation (< 100 chars)
- Batch building from multiple docs

WHY: Project documentation contains valuable patterns, guidelines, and knowledge
that agents should be aware of. This service automatically extracts and assigns
relevant information to appropriate agents.

DESIGN DECISION: Focuses on extracting actionable insights rather than copying
documentation verbatim. Creates concise learnings that fit memory constraints
while preserving essential information.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.mixins import LoggerMixin
from claude_mpm.core.shared.config_loader import ConfigLoader
from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.services.memory.router import MemoryRouter
from claude_mpm.services.project.analyzer import ProjectAnalyzer


class MemoryBuilder(LoggerMixin):
    """Builds agent memories from project documentation.

    WHY: Documentation contains patterns and guidelines that agents should know
    about. Manual memory creation is time-consuming and prone to inconsistency.
    This service automates the extraction and assignment process.

    DESIGN DECISION: Uses pattern matching and content analysis to extract
    actionable insights rather than copying raw documentation. Focuses on
    creating learnings that will actually be useful to agents.
    """

    # Documentation files to process
    DOC_FILES = {
        "CLAUDE.md": {
            "priority": "high",
            "sections": ["development guidelines", "key components", "common issues"],
            "agents": ["pm", "engineer"],
        },
        "docs/STRUCTURE.md": {
            "priority": "high",
            "sections": ["file placement", "design patterns", "directory structure"],
            "agents": ["engineer", "documentation"],
        },
        "docs/QA.md": {
            "priority": "high",
            "sections": ["testing", "quality assurance", "validation"],
            "agents": ["qa", "engineer"],
        },
        "docs/DEPLOY.md": {
            "priority": "medium",
            "sections": ["deployment", "versioning", "release"],
            "agents": ["engineer", "pm"],
        },
        "docs/VERSIONING.md": {
            "priority": "medium",
            "sections": ["version management", "semantic versioning"],
            "agents": ["engineer", "pm"],
        },
    }

    # Patterns for extracting actionable content
    EXTRACTION_PATTERNS = {
        "guidelines": [
            r"(?:must|should|always|never|avoid|ensure|remember to)\s+(.+?)(?:\.|$)",
            r"(?:important|note|warning|tip):\s*(.+?)(?:\.|$)",
            r"(?:do not|don\'t)\s+(.+?)(?:\.|$)",
        ],
        "patterns": [
            r"(?:pattern|approach|strategy|method):\s*(.+?)(?:\.|$)",
            r"(?:use|implement|follow)\s+(.+?)\s+(?:pattern|approach|for)",
            r"(?:follows|uses|implements)\s+(.+?)\s+(?:pattern|architecture)",
        ],
        "mistakes": [
            r"(?:common\s+)?(?:mistake|error|issue|problem):\s*(.+?)(?:\.|$)",
            r"(?:avoid|never|don\'t)\s+(.+?)(?:\.|$)",
            r"(?:pitfall|gotcha|warning):\s*(.+?)(?:\.|$)",
        ],
        "architecture": [
            r"(?:architecture|structure|design):\s*(.+?)(?:\.|$)",
            r"(?:component|service|module)\s+(.+?)\s+(?:provides|handles|manages)",
            r"(?:uses|implements|follows)\s+(.+?)\s+(?:architecture|pattern)",
        ],
    }

    def __init__(
        self, config: Optional[Config] = None, working_directory: Optional[Path] = None
    ):
        """Initialize the memory builder.

        Args:
            config: Optional Config object
            working_directory: Optional working directory for project-specific analysis
        """
        super().__init__()
        if config:
            self.config = config
        else:
            config_loader = ConfigLoader()
            self.config = config_loader.load_main_config()
        self.project_root = get_path_manager().project_root
        # Use current working directory by default, not project root
        self.working_directory = working_directory or Path(Path.cwd())
        self.memories_dir = self.working_directory / ".claude-mpm" / "memories"
        self.router = MemoryRouter(config)
        self.project_analyzer = ProjectAnalyzer(config, self.working_directory)

    def _get_dynamic_doc_files(self) -> Dict[str, Dict[str, Any]]:
        """Get documentation files to process based on project analysis.

        WHY: Instead of hardcoded file list, dynamically discover important files
        based on actual project structure and characteristics.

        Returns:
            Dict mapping file paths to processing configuration
        """
        dynamic_files = {}

        # Start with static important files
        static_files = self.DOC_FILES.copy()

        # Get project-specific important files
        try:
            important_files = self.project_analyzer.get_important_files_for_context()
            project_characteristics = self.project_analyzer.analyze_project()

            # Add configuration files
            for config_file in project_characteristics.important_configs:
                if config_file not in static_files:
                    file_ext = Path(config_file).suffix.lower()

                    if file_ext in [".json", ".toml", ".yaml", ".yml"]:
                        dynamic_files[config_file] = {
                            "priority": "medium",
                            "sections": ["configuration", "setup", "dependencies"],
                            "agents": ["engineer", "pm"],
                            "file_type": "config",
                        }

            # Add project-specific documentation
            for doc_file in important_files:
                if doc_file not in static_files and doc_file not in dynamic_files:
                    file_path = Path(doc_file)

                    # Determine processing config based on file name/path
                    if "api" in doc_file.lower() or "endpoint" in doc_file.lower():
                        dynamic_files[doc_file] = {
                            "priority": "high",
                            "sections": ["api", "endpoints", "integration"],
                            "agents": ["engineer", "integration"],
                            "file_type": "api_doc",
                        }
                    elif (
                        "architecture" in doc_file.lower()
                        or "design" in doc_file.lower()
                    ):
                        dynamic_files[doc_file] = {
                            "priority": "high",
                            "sections": ["architecture", "design", "patterns"],
                            "agents": ["engineer", "architect"],
                            "file_type": "architecture",
                        }
                    elif "test" in doc_file.lower():
                        dynamic_files[doc_file] = {
                            "priority": "medium",
                            "sections": ["testing", "quality"],
                            "agents": ["qa", "engineer"],
                            "file_type": "test_doc",
                        }
                    elif file_path.suffix.lower() == ".md":
                        # Generic markdown file
                        dynamic_files[doc_file] = {
                            "priority": "low",
                            "sections": ["documentation", "guidelines"],
                            "agents": ["pm", "engineer"],
                            "file_type": "markdown",
                        }

            # Add key source files for pattern analysis (limited selection)
            if project_characteristics.entry_points:
                for entry_point in project_characteristics.entry_points[
                    :2
                ]:  # Only first 2
                    if entry_point not in dynamic_files:
                        dynamic_files[entry_point] = {
                            "priority": "low",
                            "sections": ["patterns", "implementation"],
                            "agents": ["engineer"],
                            "file_type": "source",
                            "extract_patterns_only": True,  # Only extract patterns, not full content
                        }

        except Exception as e:
            self.logger.warning(f"Error getting dynamic doc files: {e}")

        # Merge static and dynamic files
        all_files = {**static_files, **dynamic_files}

        self.logger.debug(
            f"Processing {len(all_files)} documentation files ({len(static_files)} static, {len(dynamic_files)} dynamic)"
        )
        return all_files

    def build_from_documentation(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Build agent memories from project documentation.

        WHY: Documentation contains project-specific knowledge that agents need.
        This method extracts and assigns relevant information to appropriate agents.

        Args:
            force_rebuild: If True, rebuilds even if docs haven't changed

        Returns:
            Dict containing build results and statistics
        """
        try:
            results = {
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "files_processed": 0,
                "memories_created": 0,
                "memories_updated": 0,
                "agents_affected": set(),
                "files": {},
                "errors": [],
            }

            # Get dynamic list of files to process
            doc_files = self._get_dynamic_doc_files()

            # Process each documentation file
            for doc_path, doc_config in doc_files.items():
                file_path = self.project_root / doc_path

                if not file_path.exists():
                    self.logger.debug(f"Documentation file not found: {doc_path}")
                    continue

                # Check if rebuild is needed
                if not force_rebuild and not self._needs_rebuild(file_path):
                    self.logger.debug(f"Skipping {doc_path} - no changes detected")
                    continue

                file_result = self._process_documentation_file(file_path, doc_config)
                results["files"][doc_path] = file_result

                # Aggregate results
                if file_result.get("success"):
                    results["files_processed"] += 1
                    results["memories_created"] += file_result.get(
                        "memories_created", 0
                    )
                    results["memories_updated"] += file_result.get(
                        "memories_updated", 0
                    )
                    results["agents_affected"].update(
                        file_result.get("agents_affected", [])
                    )
                else:
                    results["errors"].append(
                        f"{doc_path}: {file_result.get('error', 'Unknown error')}"
                    )

            # Convert set to list for JSON serialization
            results["agents_affected"] = list(results["agents_affected"])
            results["total_agents_affected"] = len(results["agents_affected"])

            self.logger.info(
                f"Built memories from documentation: {results['files_processed']} files, {results['memories_created']} memories created"
            )
            return results

        except Exception as e:
            self.logger.error(f"Error building memories from documentation: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def extract_from_text(self, text: str, source: str) -> List[Dict[str, Any]]:
        """Extract memory-worthy content from text.

        WHY: Provides reusable text extraction logic that can be used for
        custom documentation or other text sources beyond standard files.

        Args:
            text: Text content to analyze
            source: Source identifier for context

        Returns:
            List of extracted memory items with metadata
        """
        try:
            extracted_items = []

            # Process each extraction pattern type
            for pattern_type, patterns in self.EXTRACTION_PATTERNS.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)

                    for match in matches:
                        content = match.group(1).strip()

                        # Clean and validate content
                        content = self._clean_extracted_content(content)
                        if not self._is_valid_memory_content(content):
                            continue

                        # Route to appropriate agent
                        routing_result = self.router.analyze_and_route(content)

                        extracted_item = {
                            "content": content,
                            "type": pattern_type,
                            "source": source,
                            "target_agent": routing_result.get("target_agent", "pm"),
                            "section": routing_result.get(
                                "section", "Recent Learnings"
                            ),
                            "confidence": routing_result.get("confidence", 0.5),
                            "pattern_matched": pattern,
                        }

                        extracted_items.append(extracted_item)

            # Remove near-duplicates
            unique_items = self._deduplicate_extracted_items(extracted_items)

            self.logger.debug(
                f"Extracted {len(unique_items)} unique items from {source}"
            )
            return unique_items

        except Exception as e:
            self.logger.error(f"Error extracting content from text: {e}")
            return []

    def build_agent_memory_from_items(
        self, agent_id: str, items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build or update agent memory from extracted items.

        WHY: Extracted items need to be properly integrated into agent memory
        files while respecting existing content and size limits.

        Args:
            agent_id: Target agent identifier
            items: List of extracted memory items

        Returns:
            Dict containing update results
        """
        try:
            from claude_mpm.services.agents.memory import get_memory_manager

            memory_manager = get_memory_manager(self.config)

            result = {
                "success": True,
                "agent_id": agent_id,
                "items_processed": 0,
                "items_added": 0,
                "items_skipped": 0,
                "sections_updated": set(),
                "errors": [],
            }

            # Filter items for this agent
            agent_items = [
                item for item in items if item.get("target_agent") == agent_id
            ]

            for item in agent_items:
                result["items_processed"] += 1

                try:
                    # Add to memory
                    section = item.get("section", "Recent Learnings")
                    content = item.get("content", "")

                    success = memory_manager.update_agent_memory(
                        agent_id, section, content
                    )

                    if success:
                        result["items_added"] += 1
                        result["sections_updated"].add(section)
                    else:
                        result["items_skipped"] += 1
                        result["errors"].append(f"Failed to add: {content[:50]}...")

                except Exception as e:
                    result["items_skipped"] += 1
                    result["errors"].append(f"Error processing item: {e!s}")

            # Convert set to list
            result["sections_updated"] = list(result["sections_updated"])

            return result

        except Exception as e:
            self.logger.error(f"Error building memory for {agent_id}: {e}")
            return {"success": False, "agent_id": agent_id, "error": str(e)}

    def _extract_from_config_file(
        self, content: str, file_path: Path, doc_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract memory-worthy information from configuration files.

        WHY: Configuration files contain important setup patterns, dependencies,
        and architectural decisions that agents should understand.

        Args:
            content: File content
            file_path: Path to the file
            doc_config: Processing configuration

        Returns:
            List of extracted memory items
        """
        extracted_items = []
        source = str(file_path.relative_to(self.project_root))

        try:
            file_ext = file_path.suffix.lower()

            if file_ext == ".json":
                # Parse JSON configuration
                import json

                config_data = json.loads(content)
                items = self._extract_from_json_config(config_data, source)
                extracted_items.extend(items)

            elif file_ext in [".toml"]:
                # Parse TOML configuration
                try:
                    try:
                        import tomllib
                    except ImportError:
                        import tomli as tomllib
                    with file_path.open("rb") as f:
                        config_data = tomllib.load(f)
                    items = self._extract_from_toml_config(config_data, source)
                    extracted_items.extend(items)
                except ImportError:
                    self.logger.warning(f"TOML parsing not available for {source}")

            elif file_ext in [".yaml", ".yml"]:
                # For YAML, fall back to text-based extraction for now
                items = self.extract_from_text(content, source)
                extracted_items.extend(items)

            # Also extract text patterns for comments and documentation
            text_items = self.extract_from_text(content, source)
            extracted_items.extend(text_items)

        except Exception as e:
            self.logger.warning(f"Error parsing config file {source}: {e}")
            # Fall back to text extraction
            extracted_items = self.extract_from_text(content, source)

        return extracted_items

    def _extract_from_json_config(
        self, config_data: dict, source: str
    ) -> List[Dict[str, Any]]:
        """Extract patterns from JSON configuration."""
        items = []

        # Extract dependencies information
        if "dependencies" in config_data:
            deps = config_data["dependencies"]
            if isinstance(deps, dict) and deps:
                dep_names = list(deps.keys())[:5]  # Limit to prevent overwhelming
                deps_str = ", ".join(dep_names)
                items.append(
                    {
                        "content": f"Key dependencies: {deps_str}",
                        "type": "dependency_info",
                        "source": source,
                        "target_agent": "engineer",
                        "section": "Current Technical Context",
                        "confidence": 0.8,
                    }
                )

        # Extract scripts (for package.json)
        if "scripts" in config_data:
            scripts = config_data["scripts"]
            if isinstance(scripts, dict):
                for script_name, script_cmd in list(scripts.items())[
                    :3
                ]:  # Limit to first 3
                    items.append(
                        {
                            "content": f"Build script '{script_name}': {script_cmd[:50]}{'...' if len(script_cmd) > 50 else ''}",
                            "type": "build_pattern",
                            "source": source,
                            "target_agent": "engineer",
                            "section": "Implementation Guidelines",
                            "confidence": 0.7,
                        }
                    )

        return items

    def _extract_from_toml_config(
        self, config_data: dict, source: str
    ) -> List[Dict[str, Any]]:
        """Extract patterns from TOML configuration."""
        items = []

        # Extract project metadata (for pyproject.toml)
        if "project" in config_data:
            project_info = config_data["project"]
            if "dependencies" in project_info:
                deps = project_info["dependencies"]
                if deps:
                    items.append(
                        {
                            "content": f"Python dependencies: {', '.join(deps[:5])}",
                            "type": "dependency_info",
                            "source": source,
                            "target_agent": "engineer",
                            "section": "Current Technical Context",
                            "confidence": 0.8,
                        }
                    )

        # Extract Rust dependencies (for Cargo.toml)
        if "dependencies" in config_data:
            deps = config_data["dependencies"]
            if isinstance(deps, dict) and deps:
                dep_names = list(deps.keys())[:5]
                items.append(
                    {
                        "content": f"Rust dependencies: {', '.join(dep_names)}",
                        "type": "dependency_info",
                        "source": source,
                        "target_agent": "engineer",
                        "section": "Current Technical Context",
                        "confidence": 0.8,
                    }
                )

        return items

    def _extract_from_source_file(
        self, content: str, file_path: Path, doc_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract patterns from source code files.

        WHY: Source files contain implementation patterns and architectural
        decisions that agents should be aware of, but we only extract high-level
        patterns rather than detailed code analysis.

        Args:
            content: File content
            file_path: Path to the file
            doc_config: Processing configuration

        Returns:
            List of extracted memory items
        """
        extracted_items = []
        source = str(file_path.relative_to(self.project_root))

        # Only extract patterns if specified
        if not doc_config.get("extract_patterns_only", False):
            return []

        file_ext = file_path.suffix.lower()

        # Language-specific pattern extraction
        if file_ext == ".py":
            items = self._extract_python_patterns(content, source)
            extracted_items.extend(items)
        elif file_ext in [".js", ".ts"]:
            items = self._extract_javascript_patterns(content, source)
            extracted_items.extend(items)

        return extracted_items[:3]  # Limit to prevent overwhelming

    def _extract_python_patterns(
        self, content: str, source: str
    ) -> List[Dict[str, Any]]:
        """Extract high-level patterns from Python source."""
        items = []

        # Check for common patterns
        if 'if __name__ == "__main__"' in content:
            items.append(
                {
                    "content": "Uses if __name__ == '__main__' pattern for script execution",
                    "type": "pattern",
                    "source": source,
                    "target_agent": "engineer",
                    "section": "Coding Patterns Learned",
                    "confidence": 0.8,
                }
            )

        if "from pathlib import Path" in content:
            items.append(
                {
                    "content": "Uses pathlib.Path for file operations (recommended pattern)",
                    "type": "pattern",
                    "source": source,
                    "target_agent": "engineer",
                    "section": "Coding Patterns Learned",
                    "confidence": 0.7,
                }
            )

        # Check for class definitions
        class_matches = re.findall(r"class\s+(\w+)", content)
        if class_matches:
            items.append(
                {
                    "content": f"Defines classes: {', '.join(class_matches[:3])}",
                    "type": "architecture",
                    "source": source,
                    "target_agent": "engineer",
                    "section": "Project Architecture",
                    "confidence": 0.6,
                }
            )

        return items

    def _extract_javascript_patterns(
        self, content: str, source: str
    ) -> List[Dict[str, Any]]:
        """Extract high-level patterns from JavaScript/TypeScript source."""
        items = []

        # Check for async patterns
        if "async function" in content or "async " in content:
            items.append(
                {
                    "content": "Uses async/await patterns for asynchronous operations",
                    "type": "pattern",
                    "source": source,
                    "target_agent": "engineer",
                    "section": "Coding Patterns Learned",
                    "confidence": 0.8,
                }
            )

        # Check for module patterns
        if "export " in content:
            items.append(
                {
                    "content": "Uses ES6 module export patterns",
                    "type": "pattern",
                    "source": source,
                    "target_agent": "engineer",
                    "section": "Coding Patterns Learned",
                    "confidence": 0.7,
                }
            )

        return items

    def _process_documentation_file(
        self, file_path: Path, doc_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single documentation file with enhanced file type support.

        Args:
            file_path: Path to documentation file
            doc_config: Configuration for this file type

        Returns:
            Processing results
        """
        try:
            # Read file content
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Handle different file types
            file_type = doc_config.get("file_type", "markdown")

            if file_type == "config":
                extracted_items = self._extract_from_config_file(
                    content, file_path, doc_config
                )
            elif file_type == "source":
                extracted_items = self._extract_from_source_file(
                    content, file_path, doc_config
                )
            else:
                # Default markdown/text processing
                extracted_items = self.extract_from_text(
                    content, str(file_path.relative_to(self.project_root))
                )

            result = {
                "success": True,
                "file_path": str(file_path),
                "content_length": len(content),
                "items_extracted": len(extracted_items),
                "memories_created": 0,
                "memories_updated": 0,
                "agents_affected": [],
                "agent_results": {},
            }

            # Group items by target agent
            agent_items = {}
            for item in extracted_items:
                agent = item.get("target_agent", "pm")
                if agent not in agent_items:
                    agent_items[agent] = []
                agent_items[agent].append(item)

            # Update each agent's memory
            for agent_id, items in agent_items.items():
                agent_result = self.build_agent_memory_from_items(agent_id, items)
                result["agent_results"][agent_id] = agent_result

                if agent_result.get("success"):
                    result["agents_affected"].append(agent_id)
                    result["memories_created"] += agent_result.get("items_added", 0)

            # Update last processed timestamp
            self._update_last_processed(file_path)

            return result

        except Exception as e:
            self.logger.error(f"Error processing documentation file {file_path}: {e}")
            return {"success": False, "file_path": str(file_path), "error": str(e)}

    def _needs_rebuild(self, file_path: Path) -> bool:
        """Check if documentation file needs to be processed.

        Args:
            file_path: Path to documentation file

        Returns:
            True if file needs processing
        """
        # Check if file was modified since last processing
        try:
            last_processed_file = self.memories_dir / ".last_processed.json"

            if not last_processed_file.exists():
                return True

            import json

            last_processed = json.loads(last_processed_file.read_text())

            file_key = str(file_path.relative_to(self.project_root))
            if file_key not in last_processed:
                return True

            last_processed_time = datetime.fromisoformat(last_processed[file_key])
            file_modified_time = datetime.fromtimestamp(
                file_path.stat().st_mtime, tz=timezone.utc
            )

            return file_modified_time > last_processed_time

        except Exception as e:
            self.logger.debug(f"Error checking rebuild status for {file_path}: {e}")
            return True  # Default to rebuilding if we can't determine

    def _update_last_processed(self, file_path: Path):
        """Update last processed timestamp for file.

        Args:
            file_path: Path to documentation file
        """
        try:
            self.memories_dir.mkdir(parents=True, exist_ok=True)
            last_processed_file = self.memories_dir / ".last_processed.json"

            # Load existing data
            if last_processed_file.exists():
                import json

                last_processed = json.loads(last_processed_file.read_text())
            else:
                last_processed = {}

            # Update timestamp
            file_key = str(file_path.relative_to(self.project_root))
            last_processed[file_key] = datetime.now(timezone.utc).isoformat()

            # Save back
            import json

            last_processed_file.write_text(json.dumps(last_processed, indent=2))

        except Exception as e:
            self.logger.warning(f"Error updating last processed timestamp: {e}")

    def _clean_extracted_content(self, content: str) -> str:
        """Clean and normalize extracted content.

        Args:
            content: Raw extracted content

        Returns:
            Cleaned content string
        """
        # Remove markdown formatting
        content = re.sub(r"[*_`#]+", "", content)

        # Remove extra whitespace
        content = re.sub(r"\s+", " ", content).strip()

        # Remove common prefixes that don't add value
        content = re.sub(
            r"^(?:note:|tip:|important:|warning:)\s*", "", content, flags=re.IGNORECASE
        )

        # Truncate to memory limit (with ellipsis if needed)
        if len(content) > 95:  # Leave room for ellipsis
            content = content[:95] + "..."

        return content

    def _is_valid_memory_content(self, content: str) -> bool:
        """Validate if content is suitable for memory storage.

        Args:
            content: Content to validate

        Returns:
            True if content is valid for memory
        """
        # Must have minimum length
        if len(content) < 10:
            return False

        # Must contain actionable information
        actionable_words = [
            "use",
            "avoid",
            "ensure",
            "follow",
            "implement",
            "check",
            "must",
            "should",
            "never",
            "always",
        ]
        if not any(word in content.lower() for word in actionable_words):
            return False

        # Avoid overly generic content
        generic_phrases = [
            "this is",
            "this document",
            "see above",
            "as mentioned",
            "for more info",
        ]
        return not any(phrase in content.lower() for phrase in generic_phrases)

    def _deduplicate_extracted_items(
        self, items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove near-duplicate extracted items.

        Args:
            items: List of extracted items

        Returns:
            Deduplicated list
        """
        from difflib import SequenceMatcher

        unique_items = []

        for item in items:
            content = item.get("content", "")
            is_duplicate = False

            # Check against existing unique items
            for unique_item in unique_items:
                unique_content = unique_item.get("content", "")
                similarity = SequenceMatcher(
                    None, content.lower(), unique_content.lower()
                ).ratio()

                if similarity > 0.8:  # 80% similarity threshold
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_items.append(item)

        return unique_items
