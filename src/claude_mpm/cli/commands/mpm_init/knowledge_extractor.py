"""
Project Knowledge Extractor for Enhanced /mpm-init Update Mode
==============================================================

This module extracts project knowledge from multiple sources:
- Git history (architectural decisions, tech stack changes, workflows)
- Session logs (.claude-mpm/responses/*.json)
- Memory files (.claude-mpm/memories/*.md)

Used to enhance CLAUDE.md updates with accumulated project insights.

Author: Claude MPM Development Team
Created: 2025-12-13
"""

import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class ProjectKnowledgeExtractor:
    """Extract project knowledge from git, logs, and memory files."""

    def __init__(self, project_path: Path):
        """
        Initialize knowledge extractor.

        Args:
            project_path: Path to the project root directory
        """
        self.project_path = project_path
        self.claude_mpm_dir = project_path / ".claude-mpm"
        self.is_git_repo = (project_path / ".git").is_dir()

    def extract_all(self, days: int = 90) -> Dict[str, Any]:
        """
        Extract knowledge from all sources.

        Args:
            days: Number of days to analyze git history (default: 90)

        Returns:
            Dict containing all extracted knowledge
        """
        return {
            "git_insights": self.extract_from_git(days),
            "log_insights": self.extract_from_logs(),
            "memory_insights": self.extract_from_memory(),
        }

    def extract_from_git(self, days: int = 90) -> Dict[str, Any]:
        """
        Extract insights from git history.

        Focus on:
        - Architectural patterns from commit messages
        - Tech stack changes (new dependencies, migrations)
        - Common workflows (build, test, deploy patterns)
        - Hot files (frequently modified = important)

        Args:
            days: Number of days to analyze

        Returns:
            Dict with git insights including patterns, workflows, tech changes
        """
        if not self.is_git_repo:
            return {
                "available": False,
                "message": "Not a git repository",
            }

        insights = {
            "available": True,
            "architectural_decisions": [],
            "tech_stack_changes": [],
            "workflow_patterns": [],
            "hot_files": [],
        }

        try:
            # Get recent commits
            since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
                "%Y-%m-%d"
            )

            # Get commit messages with file stats
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--since={since_date}",
                    "--pretty=format:%s|||%b",
                    "--stat",
                    "--no-merges",
                ],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                insights["architectural_decisions"] = (
                    self._extract_architectural_patterns(result.stdout)
                )
                insights["tech_stack_changes"] = self._extract_tech_changes(
                    result.stdout
                )
                insights["workflow_patterns"] = self._extract_workflow_patterns(
                    result.stdout
                )

            # Get file change frequency
            freq_result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--since={since_date}",
                    "--pretty=format:",
                    "--name-only",
                    "--no-merges",
                ],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=False,
            )

            if freq_result.returncode == 0 and freq_result.stdout:
                insights["hot_files"] = self._identify_hot_files(freq_result.stdout)

        except Exception as e:
            logger.warning(f"Failed to extract git insights: {e}")
            insights["error"] = str(e)

        return insights

    def extract_from_logs(self) -> Dict[str, Any]:
        """
        Extract learnings from session logs.

        Parse .claude-mpm/responses/*.json for:
        - pm_summary fields with completed work
        - tasks arrays showing what was built
        - stop_event data with context

        Returns:
            Dict with extracted learnings from session logs
        """
        insights = {
            "available": False,
            "learnings": [],
            "completed_tasks": [],
            "common_patterns": [],
        }

        responses_dir = self.claude_mpm_dir / "responses"
        if not responses_dir.exists():
            return insights

        insights["available"] = True

        try:
            # Find all JSON response files
            json_files = list(responses_dir.glob("*.json"))

            for json_file in json_files[:50]:  # Limit to 50 most recent
                try:
                    with open(json_file, encoding="utf-8") as f:
                        data = json.load(f)

                    # Extract PM summaries
                    if data.get("pm_summary"):
                        insights["learnings"].append(
                            {
                                "source": "pm_summary",
                                "timestamp": json_file.stem,
                                "content": data["pm_summary"],
                            }
                        )

                    # Extract task information
                    if "tasks" in data and isinstance(data["tasks"], list):
                        for task in data["tasks"]:
                            if isinstance(task, dict) and "description" in task:
                                insights["completed_tasks"].append(task["description"])

                    # Extract stop event context
                    if "stop_event" in data and isinstance(data["stop_event"], dict):
                        stop_event = data["stop_event"]
                        if "context" in stop_event:
                            insights["learnings"].append(
                                {
                                    "source": "stop_event",
                                    "timestamp": json_file.stem,
                                    "content": stop_event["context"],
                                }
                            )

                except Exception as e:
                    logger.debug(f"Failed to parse {json_file}: {e}")
                    continue

            # Identify common patterns in completed tasks
            if insights["completed_tasks"]:
                insights["common_patterns"] = self._identify_task_patterns(
                    insights["completed_tasks"]
                )

        except Exception as e:
            logger.warning(f"Failed to extract log insights: {e}")
            insights["error"] = str(e)

        return insights

    def extract_from_memory(self) -> Dict[str, Any]:
        """
        Extract accumulated knowledge from memory files.

        Parse .claude-mpm/memories/*.md for:
        - Project Architecture sections
        - Implementation Guidelines
        - Common Mistakes to Avoid
        - Current Technical Context

        Returns:
            Dict with extracted memory insights
        """
        insights = {
            "available": False,
            "architectural_knowledge": [],
            "implementation_guidelines": [],
            "common_mistakes": [],
            "technical_context": [],
        }

        memories_dir = self.claude_mpm_dir / "memories"
        if not memories_dir.exists():
            return insights

        insights["available"] = True

        try:
            # Find all markdown memory files (exclude README)
            memory_files = [
                f for f in memories_dir.glob("*.md") if f.name != "README.md"
            ]

            for memory_file in memory_files:
                try:
                    with open(memory_file, encoding="utf-8") as f:
                        content = f.read()

                    agent_name = memory_file.stem.replace("_memories", "")

                    # Parse memory sections
                    sections = self._parse_memory_sections(content)

                    # Extract by section type
                    if "Project Architecture" in sections:
                        insights["architectural_knowledge"].extend(
                            self._extract_memory_items(
                                sections["Project Architecture"], agent_name
                            )
                        )

                    if "Implementation Guidelines" in sections:
                        insights["implementation_guidelines"].extend(
                            self._extract_memory_items(
                                sections["Implementation Guidelines"], agent_name
                            )
                        )

                    if "Common Mistakes to Avoid" in sections:
                        insights["common_mistakes"].extend(
                            self._extract_memory_items(
                                sections["Common Mistakes to Avoid"], agent_name
                            )
                        )

                    if "Current Technical Context" in sections:
                        insights["technical_context"].extend(
                            self._extract_memory_items(
                                sections["Current Technical Context"], agent_name
                            )
                        )

                except Exception as e:
                    logger.debug(f"Failed to parse {memory_file}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract memory insights: {e}")
            insights["error"] = str(e)

        return insights

    # Private helper methods

    def _extract_architectural_patterns(self, git_log: str) -> List[str]:
        """Extract architectural decisions from commit messages."""
        patterns = []

        # Patterns indicating architectural changes
        arch_keywords = [
            r"add(?:ed)?\s+(\w+\s+(?:pattern|architecture|design))",
            r"refactor(?:ed)?\s+to\s+(\w+)",
            r"migrat(?:e|ed)\s+(?:to|from)\s+(\w+)",
            r"implement(?:ed)?\s+(\w+\s+(?:pattern|architecture))",
            r"introduc(?:e|ed)\s+(\w+\s+(?:layer|service|handler))",
        ]

        for pattern in arch_keywords:
            matches = re.finditer(pattern, git_log, re.IGNORECASE)
            for match in matches:
                decision = match.group(1).strip()
                if decision and decision not in patterns:
                    patterns.append(decision)

        return patterns[:15]  # Limit to top 15

    def _extract_tech_changes(self, git_log: str) -> List[str]:
        """Extract tech stack changes from commit messages."""
        changes = []

        # Patterns indicating tech stack changes
        tech_keywords = [
            r"add(?:ed)?\s+(?:dependency|package|library):\s*(\w+)",
            r"upgrad(?:e|ed)\s+(\w+)\s+(?:to|from)",
            r"switch(?:ed)?\s+(?:to|from)\s+(\w+)",
            r"replac(?:e|ed)\s+(\w+)\s+with\s+(\w+)",
            r"remov(?:e|ed)\s+(\w+)\s+dependency",
        ]

        for pattern in tech_keywords:
            matches = re.finditer(pattern, git_log, re.IGNORECASE)
            for match in matches:
                # Get first captured group
                change = match.group(1).strip() if match.group(1) else ""
                if change and change not in changes:
                    changes.append(change)

        return changes[:15]  # Limit to top 15

    def _extract_workflow_patterns(self, git_log: str) -> List[str]:
        """Extract common workflows from commit messages."""
        workflows = []

        # Patterns indicating workflows
        workflow_keywords = [
            r"(?:build|test|deploy|lint|format):\s+(.+?)(?:\n|$)",
            r"add(?:ed)?\s+(?:script|command)\s+(?:for|to)\s+(.+?)(?:\n|$)",
            r"automat(?:e|ed)\s+(.+?)(?:\n|$)",
            r"(?:ci|cd):\s+(.+?)(?:\n|$)",
        ]

        for pattern in workflow_keywords:
            matches = re.finditer(pattern, git_log, re.IGNORECASE)
            for match in matches:
                workflow = match.group(1).strip()
                if workflow and len(workflow) < 100 and workflow not in workflows:
                    workflows.append(workflow)

        return workflows[:10]  # Limit to top 10

    def _identify_hot_files(self, file_list: str) -> List[Dict[str, Any]]:
        """Identify frequently modified files (hot spots)."""
        # Count file modifications
        files = [f.strip() for f in file_list.split("\n") if f.strip()]
        file_counts = Counter(files)

        # Return top 20 most modified files
        hot_files = []
        for file_path, count in file_counts.most_common(20):
            # Skip certain files
            if any(
                skip in file_path
                for skip in [".lock", "package-lock", "poetry.lock", ".min."]
            ):
                continue

            hot_files.append(
                {
                    "path": file_path,
                    "modifications": count,
                }
            )

        return hot_files

    def _identify_task_patterns(self, tasks: List[str]) -> List[str]:
        """Identify common patterns in completed tasks."""
        # Extract common words/phrases
        words = []
        for task in tasks:
            # Extract keywords (simple approach)
            task_words = re.findall(r"\b[a-z]{4,}\b", task.lower())
            words.extend(task_words)

        # Count word frequency
        word_counts = Counter(words)

        # Return top 10 most common (excluding stopwords)
        stopwords = {
            "with",
            "from",
            "this",
            "that",
            "have",
            "been",
            "were",
            "will",
            "their",
            "about",
        }
        patterns = [
            word
            for word, _count in word_counts.most_common(20)
            if word not in stopwords
        ]

        return patterns[:10]

    def _parse_memory_sections(self, content: str) -> Dict[str, str]:
        """Parse markdown memory file into sections."""
        sections = {}
        current_section = None
        current_content = []

        for line in content.split("\n"):
            # Check for section headers (## Section Name)
            if line.startswith("## "):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()

                # Start new section
                current_section = line[3:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _extract_memory_items(self, section_content: str, agent_name: str) -> List[str]:
        """Extract individual items from memory section."""
        items = []

        # Split by bullet points or numbered lists
        lines = section_content.split("\n")
        for line in lines:
            line = line.strip()

            # Match bullet points or numbered lists
            if line.startswith(("-", "*", "•")) or re.match(r"^\d+\.", line):
                # Remove bullet/number
                item = re.sub(r"^[-*•]\s*", "", line)
                item = re.sub(r"^\d+\.\s*", "", item)
                item = item.strip()

                if item:
                    # Prefix with agent name for context
                    items.append(f"[{agent_name}] {item}")

        return items


__all__ = ["ProjectKnowledgeExtractor"]
