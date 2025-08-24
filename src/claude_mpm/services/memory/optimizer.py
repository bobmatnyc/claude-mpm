#!/usr/bin/env python3
"""
Memory Optimizer Service
=======================

Optimizes agent memory files by removing duplicates, consolidating related items,
and reorganizing by priority/relevance.

This service provides:
- Duplicate detection and removal
- Related item consolidation
- Priority-based reorganization
- Per-agent optimization strategies
- Size optimization within limits

WHY: Agent memory files accumulate information over time and can become cluttered
with duplicates, outdated information, or poorly organized content. This service
maintains memory quality while preserving important learnings.

DESIGN DECISION: Uses conservative optimization strategies that preserve information
rather than aggressively removing content. Better to keep potentially useful
information than lose important insights.
"""

import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.config import Config
from claude_mpm.core.mixins import LoggerMixin
from claude_mpm.core.unified_paths import get_path_manager


class MemoryOptimizer(LoggerMixin):
    """Optimizes agent memory files through deduplication and reorganization.

    WHY: Memory files need maintenance to stay useful. This service provides
    automated cleanup while preserving valuable information and maintaining
    the structured format agents expect.

    DESIGN DECISION: Uses similarity thresholds and conservative merging to
    avoid losing important nuances in learnings while removing clear duplicates.
    """

    # Similarity threshold for considering items duplicates
    SIMILARITY_THRESHOLD = 0.85

    # Minimum similarity for consolidation
    CONSOLIDATION_THRESHOLD = 0.70

    # Priority keywords for sorting (higher priority items kept/moved up)
    PRIORITY_KEYWORDS = {
        "high": [
            "critical",
            "important",
            "essential",
            "required",
            "must",
            "always",
            "never",
        ],
        "medium": ["should", "recommended", "prefer", "avoid", "consider"],
        "low": ["note", "tip", "hint", "example", "reference"],
    }

    def __init__(
        self, config: Optional[Config] = None, working_directory: Optional[Path] = None
    ):
        """Initialize the memory optimizer.

        Args:
            config: Optional Config object
            working_directory: Optional working directory. If not provided, uses current working directory.
        """
        super().__init__()
        self.config = config or Config()
        self.project_root = get_path_manager().get_project_root()
        # Use current working directory by default, not project root
        self.working_directory = working_directory or Path(os.getcwd())
        self.memories_dir = self.working_directory / ".claude-mpm" / "memories"

    def optimize_agent_memory(self, agent_id: str) -> Dict[str, Any]:
        """Optimize memory for a specific agent.

        WHY: Individual agent memories can be optimized independently, allowing
        for targeted cleanup of specific agents without affecting others.

        Args:
            agent_id: The agent identifier

        Returns:
            Dict containing optimization results and statistics
        """
        try:
            memory_file = self.memories_dir / f"{agent_id}_agent.md"

            if not memory_file.exists():
                return {
                    "success": False,
                    "agent_id": agent_id,
                    "error": "Memory file not found",
                }

            # Load original content
            original_content = memory_file.read_text(encoding="utf-8")
            original_size = len(original_content)

            # Parse memory structure
            sections = self._parse_memory_sections(original_content)

            # Optimize each section
            optimized_sections = {}
            optimization_stats = {
                "duplicates_removed": 0,
                "items_consolidated": 0,
                "items_reordered": 0,
                "sections_optimized": 0,
            }

            for section_name, items in sections.items():
                if section_name.lower() in ["header", "metadata"]:
                    # Preserve header sections as-is
                    optimized_sections[section_name] = items
                    continue

                optimized_items, section_stats = self._optimize_section(items, agent_id)
                optimized_sections[section_name] = optimized_items

                # Aggregate stats
                for key in optimization_stats:
                    if key in section_stats:
                        optimization_stats[key] += section_stats[key]

                if (
                    section_stats.get("duplicates_removed", 0) > 0
                    or section_stats.get("items_consolidated", 0) > 0
                ):
                    optimization_stats["sections_optimized"] += 1

            # Rebuild memory content
            optimized_content = self._rebuild_memory_content(
                optimized_sections, agent_id
            )
            optimized_size = len(optimized_content)

            # Create backup before saving
            backup_path = self._create_backup(memory_file)

            # Save optimized content
            memory_file.write_text(optimized_content, encoding="utf-8")

            result = {
                "success": True,
                "agent_id": agent_id,
                "original_size": original_size,
                "optimized_size": optimized_size,
                "size_reduction": original_size - optimized_size,
                "size_reduction_percent": (
                    round(((original_size - optimized_size) / original_size) * 100, 1)
                    if original_size > 0
                    else 0
                ),
                "backup_created": str(backup_path),
                "timestamp": datetime.now().isoformat(),
                **optimization_stats,
            }

            self.logger.info(f"Optimized memory for {agent_id}: {optimization_stats}")
            return result

        except Exception as e:
            self.logger.error(f"Error optimizing memory for {agent_id}: {e}")
            return {"success": False, "agent_id": agent_id, "error": str(e)}

    def optimize_all_memories(self) -> Dict[str, Any]:
        """Optimize all agent memory files.

        WHY: Bulk optimization allows maintenance of the entire memory system
        in one operation, providing comprehensive cleanup and consistency.

        Returns:
            Dict containing results for all agents
        """
        try:
            if not self.memories_dir.exists():
                return {"success": False, "error": "Memory directory not found"}

            memory_files = list(self.memories_dir.glob("*_agent.md"))
            results = {}

            total_stats = {
                "agents_processed": 0,
                "agents_optimized": 0,
                "total_size_before": 0,
                "total_size_after": 0,
                "total_duplicates_removed": 0,
                "total_items_consolidated": 0,
            }

            for memory_file in memory_files:
                agent_id = memory_file.stem.replace("_agent", "")
                result = self.optimize_agent_memory(agent_id)
                results[agent_id] = result

                total_stats["agents_processed"] += 1

                if result.get("success"):
                    total_stats["agents_optimized"] += 1
                    total_stats["total_size_before"] += result.get("original_size", 0)
                    total_stats["total_size_after"] += result.get("optimized_size", 0)
                    total_stats["total_duplicates_removed"] += result.get(
                        "duplicates_removed", 0
                    )
                    total_stats["total_items_consolidated"] += result.get(
                        "items_consolidated", 0
                    )

            # Calculate overall statistics
            total_reduction = (
                total_stats["total_size_before"] - total_stats["total_size_after"]
            )
            total_reduction_percent = (
                round((total_reduction / total_stats["total_size_before"]) * 100, 1)
                if total_stats["total_size_before"] > 0
                else 0
            )

            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "agents": results,
                "summary": {
                    **total_stats,
                    "total_size_reduction": total_reduction,
                    "total_size_reduction_percent": total_reduction_percent,
                },
            }

        except Exception as e:
            self.logger.error(f"Error optimizing all memories: {e}")
            return {"success": False, "error": str(e)}

    def analyze_optimization_opportunities(
        self, agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze potential optimization opportunities without making changes.

        WHY: Users may want to understand what optimizations would be performed
        before actually running them, allowing for informed decisions.

        Args:
            agent_id: Optional specific agent to analyze

        Returns:
            Dict containing analysis results
        """
        try:
            if agent_id:
                return self._analyze_single_agent(agent_id)
            return self._analyze_all_agents()

        except Exception as e:
            self.logger.error(f"Error analyzing optimization opportunities: {e}")
            return {"success": False, "error": str(e)}

    def _parse_memory_sections(self, content: str) -> Dict[str, List[str]]:
        """Parse memory content into sections and items.

        Args:
            content: Memory file content

        Returns:
            Dict mapping section names to lists of items
        """
        lines = content.split("\n")
        sections = {}
        current_section = "header"
        current_items = []

        for line in lines:
            if line.startswith("## "):
                # Save previous section
                if current_section:
                    sections[current_section] = current_items

                # Start new section
                section_name = line[3:].split("(")[0].strip()
                current_section = section_name
                current_items = [line]  # Include the header

            else:
                current_items.append(line)

        # Save last section
        if current_section:
            sections[current_section] = current_items

        return sections

    def _optimize_section(
        self, items: List[str], agent_id: str
    ) -> Tuple[List[str], Dict[str, int]]:
        """Optimize a single section by removing duplicates and consolidating.

        Args:
            items: List of section content lines
            agent_id: Agent identifier for context

        Returns:
            Tuple of (optimized_items, stats)
        """
        stats = {"duplicates_removed": 0, "items_consolidated": 0, "items_reordered": 0}

        # Separate header and bullet points
        header_lines = []
        bullet_points = []
        other_lines = []

        for line in items:
            stripped = line.strip()
            if stripped.startswith("- "):
                bullet_points.append(line)
            elif stripped.startswith(("## ", "<!--")):
                header_lines.append(line)
            else:
                other_lines.append(line)

        if not bullet_points:
            return items, stats

        # Remove duplicates
        deduplicated_points, duplicates_removed = self._remove_duplicates(bullet_points)
        stats["duplicates_removed"] = duplicates_removed

        # Consolidate similar items
        consolidated_points, items_consolidated = self._consolidate_similar_items(
            deduplicated_points
        )
        stats["items_consolidated"] = items_consolidated

        # Reorder by priority
        reordered_points = self._reorder_by_priority(consolidated_points)
        if reordered_points != consolidated_points:
            stats["items_reordered"] = 1

        # Rebuild section
        optimized_items = header_lines + other_lines + reordered_points

        return optimized_items, stats

    def _remove_duplicates(self, bullet_points: List[str]) -> Tuple[List[str], int]:
        """Remove duplicate bullet points.

        Args:
            bullet_points: List of bullet point lines

        Returns:
            Tuple of (deduplicated_points, count_removed)
        """
        seen_content = set()
        unique_points = []
        duplicates_removed = 0

        for point in bullet_points:
            # Normalize content for comparison
            content = point.strip().lower().replace("- ", "")
            content_normalized = re.sub(r"\s+", " ", content).strip()

            if content_normalized not in seen_content:
                seen_content.add(content_normalized)
                unique_points.append(point)
            else:
                duplicates_removed += 1
                self.logger.debug(f"Removed duplicate: {point.strip()[:50]}...")

        return unique_points, duplicates_removed

    def _consolidate_similar_items(
        self, bullet_points: List[str]
    ) -> Tuple[List[str], int]:
        """Consolidate similar bullet points.

        Args:
            bullet_points: List of bullet point lines

        Returns:
            Tuple of (consolidated_points, count_consolidated)
        """
        if len(bullet_points) < 2:
            return bullet_points, 0

        consolidated = []
        items_consolidated = 0
        used_indices = set()

        for i, point_a in enumerate(bullet_points):
            if i in used_indices:
                continue

            content_a = point_a.strip().replace("- ", "")
            similar_items = [point_a]
            similar_indices = {i}

            # Find similar items
            for j, point_b in enumerate(bullet_points[i + 1 :], i + 1):
                if j in used_indices:
                    continue

                content_b = point_b.strip().replace("- ", "")
                similarity = SequenceMatcher(
                    None, content_a.lower(), content_b.lower()
                ).ratio()

                if similarity >= self.CONSOLIDATION_THRESHOLD:
                    similar_items.append(point_b)
                    similar_indices.add(j)

            # Consolidate if we found similar items
            if len(similar_items) > 1:
                consolidated_content = self._merge_similar_items(similar_items)
                consolidated.append(f"- {consolidated_content}")
                items_consolidated += len(similar_items) - 1
                self.logger.debug(f"Consolidated {len(similar_items)} similar items")
            else:
                consolidated.append(point_a)

            used_indices.update(similar_indices)

        return consolidated, items_consolidated

    def _merge_similar_items(self, similar_items: List[str]) -> str:
        """Merge similar items into a single consolidated item.

        Args:
            similar_items: List of similar bullet points

        Returns:
            Consolidated content string
        """
        # Take the longest/most detailed item as base
        contents = [item.strip().replace("- ", "") for item in similar_items]
        base_content = max(contents, key=len)

        # Look for additional details in other items
        all_words = set()
        for content in contents:
            all_words.update(content.lower().split())

        base_words = set(base_content.lower().split())
        additional_words = all_words - base_words

        # If there are meaningful additional words, add them
        if additional_words and len(additional_words) < 5:  # Don't add too much
            additional_text = " (" + ", ".join(sorted(additional_words)) + ")"
            return base_content + additional_text

        return base_content

    def _reorder_by_priority(self, bullet_points: List[str]) -> List[str]:
        """Reorder bullet points by priority/importance.

        Args:
            bullet_points: List of bullet point lines

        Returns:
            Reordered list of bullet points
        """

        def get_priority_score(point: str) -> int:
            content = point.lower()
            score = 0

            # High priority keywords
            for keyword in self.PRIORITY_KEYWORDS["high"]:
                if keyword in content:
                    score += 3

            # Medium priority keywords
            for keyword in self.PRIORITY_KEYWORDS["medium"]:
                if keyword in content:
                    score += 2

            # Low priority keywords
            for keyword in self.PRIORITY_KEYWORDS["low"]:
                if keyword in content:
                    score += 1

            # Length-based priority (more detailed items are often more important)
            if len(content) > 100:
                score += 1

            return score

        # Sort by priority score (descending) then alphabetically
        return sorted(bullet_points, key=lambda x: (-get_priority_score(x), x.lower()))

    def _rebuild_memory_content(
        self, sections: Dict[str, List[str]], agent_id: str
    ) -> str:
        """Rebuild memory content from optimized sections.

        Args:
            sections: Dict of section names to content lines
            agent_id: Agent identifier

        Returns:
            Rebuilt memory content string
        """
        content_lines = []

        # Add header if it exists
        if "header" in sections:
            content_lines.extend(sections["header"])

        # Add sections in a logical order
        section_order = [
            "Project Architecture",
            "Coding Patterns Learned",
            "Implementation Guidelines",
            "Domain-Specific Knowledge",
            "Effective Strategies",
            "Common Mistakes to Avoid",
            "Integration Points",
            "Performance Considerations",
            "Current Technical Context",
            "Recent Learnings",
        ]

        # Add ordered sections
        for section_name in section_order:
            if section_name in sections and section_name != "header":
                if content_lines and content_lines[-1].strip() != "":
                    content_lines.append("")  # Add spacing
                content_lines.extend(sections[section_name])

        # Add any remaining sections not in the order
        for section_name, section_content in sections.items():
            if section_name not in section_order and section_name != "header":
                if content_lines and content_lines[-1].strip() != "":
                    content_lines.append("")
                content_lines.extend(section_content)

        # Update timestamp
        content = "\n".join(content_lines)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return re.sub(
            r"<!-- Last Updated: .+ \| Auto-updated by: .+ -->",
            f"<!-- Last Updated: {timestamp} | Auto-updated by: optimizer -->",
            content,
        )

    def _create_backup(self, memory_file: Path) -> Path:
        """Create backup of memory file before optimization.

        Args:
            memory_file: Path to memory file

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{memory_file.stem}_backup_{timestamp}{memory_file.suffix}"
        backup_path = memory_file.parent / backup_name

        backup_path.write_text(
            memory_file.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.logger.debug(f"Created backup: {backup_path}")

        return backup_path

    def _analyze_single_agent(self, agent_id: str) -> Dict[str, Any]:
        """Analyze optimization opportunities for a single agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Analysis results
        """
        memory_file = self.memories_dir / f"{agent_id}_agent.md"

        if not memory_file.exists():
            return {
                "success": False,
                "agent_id": agent_id,
                "error": "Memory file not found",
            }

        content = memory_file.read_text(encoding="utf-8")
        sections = self._parse_memory_sections(content)

        analysis = {
            "success": True,
            "agent_id": agent_id,
            "file_size": len(content),
            "sections": len(
                [s for s in sections if s.lower() not in ["header", "metadata"]]
            ),
            "opportunities": [],
        }

        # Analyze each section for opportunities
        for section_name, items in sections.items():
            if section_name.lower() in ["header", "metadata"]:
                continue

            bullet_points = [line for line in items if line.strip().startswith("- ")]

            if len(bullet_points) > 1:
                # Check for duplicates
                unique_points, duplicates = self._remove_duplicates(bullet_points)
                if duplicates > 0:
                    analysis["opportunities"].append(
                        f"{section_name}: {duplicates} duplicate items"
                    )

                # Check for similar items
                consolidated, consolidated_count = self._consolidate_similar_items(
                    unique_points
                )
                if consolidated_count > 0:
                    analysis["opportunities"].append(
                        f"{section_name}: {consolidated_count} items can be consolidated"
                    )

        return analysis

    def _analyze_all_agents(self) -> Dict[str, Any]:
        """Analyze optimization opportunities for all agents.

        Returns:
            Analysis results for all agents
        """
        if not self.memories_dir.exists():
            return {"success": False, "error": "Memory directory not found"}

        memory_files = list(self.memories_dir.glob("*_agent.md"))
        agents_analysis = {}

        for memory_file in memory_files:
            agent_id = memory_file.stem.replace("_agent", "")
            agents_analysis[agent_id] = self._analyze_single_agent(agent_id)

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "agents_analyzed": len(agents_analysis),
            "agents": agents_analysis,
        }
