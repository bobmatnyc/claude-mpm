#!/usr/bin/env python3
"""
Memory Analyzer
==============

Provides memory analysis, status reporting, and cross-reference capabilities.

This module provides:
- Memory system status and health monitoring
- Cross-reference analysis between agent memories
- Memory metrics and usage statistics
- Raw memory data access for external tools
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryAnalyzer:
    """Analyzes memory system status and provides reporting capabilities.

    WHY: Memory system needs monitoring, analysis, and reporting capabilities
    for maintenance, optimization, and debugging purposes.
    """

    def __init__(
        self,
        memories_dir: Path,
        memory_limits: Dict[str, Any],
        agent_overrides: Dict[str, Any],
        get_agent_limits_func,
        get_agent_auto_learning_func,
        content_manager,
    ):
        """Initialize the memory analyzer.

        Args:
            memories_dir: Path to memories directory
            memory_limits: Default memory limits
            agent_overrides: Agent-specific overrides
            get_agent_limits_func: Function to get agent-specific limits
            get_agent_auto_learning_func: Function to get agent auto-learning setting
            content_manager: MemoryContentManager instance
        """
        self.memories_dir = memories_dir
        self.memory_limits = memory_limits
        self.agent_overrides = agent_overrides
        self._get_agent_limits = get_agent_limits_func
        self._get_agent_auto_learning = get_agent_auto_learning_func
        self.content_manager = content_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_memory_status(self) -> Dict[str, Any]:
        """Get comprehensive memory system status.

        WHY: Provides detailed overview of memory system health, file sizes,
        optimization opportunities, and agent-specific statistics for monitoring
        and maintenance purposes.

        Returns:
            Dict containing comprehensive memory system status
        """
        try:
            status = {
                "system_enabled": True,  # Assume enabled if analyzer is created
                "auto_learning": True,  # Default value
                "memory_directory": str(self.memories_dir),
                "total_agents": 0,
                "total_size_kb": 0,
                "agents": {},
                "optimization_opportunities": [],
                "system_health": "healthy",
            }

            if not self.memories_dir.exists():
                status["system_health"] = "no_memory_dir"
                return status

            memory_files = list(self.memories_dir.glob("*_agent.md"))
            status["total_agents"] = len(memory_files)

            total_size = 0
            for file_path in memory_files:
                stat = file_path.stat()
                size_kb = stat.st_size / 1024
                total_size += stat.st_size

                agent_id = file_path.stem.replace("_agent", "")
                limits = self._get_agent_limits(agent_id)

                # Analyze file content
                try:
                    content = file_path.read_text()
                    section_count = len(
                        [
                            line
                            for line in content.splitlines()
                            if line.startswith("## ")
                        ]
                    )
                    learning_count = len(
                        [
                            line
                            for line in content.splitlines()
                            if line.strip().startswith("- ")
                        ]
                    )

                    agent_status = {
                        "size_kb": round(size_kb, 2),
                        "size_limit_kb": limits["max_file_size_kb"],
                        "size_utilization": min(
                            100, round((size_kb / limits["max_file_size_kb"]) * 100, 1)
                        ),
                        "sections": section_count,
                        "items": learning_count,
                        "last_modified": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                        "auto_learning": self._get_agent_auto_learning(agent_id),
                    }

                    # Check for optimization opportunities
                    if size_kb > limits["max_file_size_kb"] * 0.8:
                        status["optimization_opportunities"].append(
                            f"{agent_id}: High memory usage ({size_kb:.1f}KB)"
                        )

                    if section_count > limits["max_sections"] * 0.8:
                        status["optimization_opportunities"].append(
                            f"{agent_id}: Many sections ({section_count})"
                        )

                    status["agents"][agent_id] = agent_status

                except Exception as e:
                    status["agents"][agent_id] = {"error": str(e)}

            status["total_size_kb"] = round(total_size / 1024, 2)

            # Determine overall system health
            if len(status["optimization_opportunities"]) > 3:
                status["system_health"] = "needs_optimization"
            elif status["total_size_kb"] > 100:  # More than 100KB total
                status["system_health"] = "high_usage"

            return status

        except Exception as e:
            self.logger.error(f"Error getting memory status: {e}")
            return {"success": False, "error": str(e)}

    def cross_reference_memories(self, query: Optional[str] = None) -> Dict[str, Any]:
        """Find common patterns and cross-references across agent memories.

        WHY: Different agents may have learned similar or related information.
        Cross-referencing helps identify knowledge gaps, redundancies, and
        opportunities for knowledge sharing between agents.

        Args:
            query: Optional query to filter cross-references

        Returns:
            Dict containing cross-reference analysis results
        """
        try:
            cross_refs = {
                "common_patterns": [],
                "knowledge_gaps": [],
                "redundancies": [],
                "agent_correlations": {},
                "query_matches": [] if query else None,
            }

            if not self.memories_dir.exists():
                return cross_refs

            memory_files = list(self.memories_dir.glob("*_agent.md"))
            agent_memories = {}

            # Load all agent memories
            for file_path in memory_files:
                agent_id = file_path.stem.replace("_agent", "")
                try:
                    content = file_path.read_text()
                    agent_memories[agent_id] = content
                except Exception as e:
                    self.logger.warning(f"Error reading memory for {agent_id}: {e}")
                    continue

            # Find common patterns across agents
            all_lines = []
            agent_lines = {}

            for agent_id, content in agent_memories.items():
                lines = [
                    line.strip()
                    for line in content.splitlines()
                    if line.strip().startswith("- ")
                ]
                agent_lines[agent_id] = lines
                all_lines.extend([(line, agent_id) for line in lines])

            # Look for similar content (basic similarity check)
            line_counts = {}
            for line, agent_id in all_lines:
                # Normalize line for comparison
                normalized = line.lower().replace("- ", "").strip()
                if len(normalized) > 20:  # Only check substantial lines
                    if normalized not in line_counts:
                        line_counts[normalized] = []
                    line_counts[normalized].append(agent_id)

            # Find patterns appearing in multiple agents
            for line, agents in line_counts.items():
                if len(set(agents)) > 1:  # Appears in multiple agents
                    cross_refs["common_patterns"].append(
                        {
                            "pattern": line[:100] + "..." if len(line) > 100 else line,
                            "agents": list(set(agents)),
                            "count": len(agents),
                        }
                    )

            # Query-specific matches
            if query:
                query_lower = query.lower()
                for agent_id, content in agent_memories.items():
                    matches = []
                    for line in content.splitlines():
                        if query_lower in line.lower():
                            matches.append(line.strip())

                    if matches:
                        cross_refs["query_matches"].append(
                            {
                                "agent": agent_id,
                                "matches": matches[:5],
                            }  # Limit to first 5 matches
                        )

            # Calculate agent correlations (agents with similar knowledge domains)
            for agent_a in agent_memories:
                for agent_b in agent_memories:
                    if agent_a < agent_b:  # Avoid duplicates
                        common_count = len(
                            [
                                line
                                for line in line_counts.values()
                                if agent_a in line and agent_b in line
                            ]
                        )

                        if common_count > 0:
                            correlation_key = f"{agent_a}+{agent_b}"
                            cross_refs["agent_correlations"][
                                correlation_key
                            ] = common_count

            return cross_refs

        except Exception as e:
            self.logger.error(f"Error cross-referencing memories: {e}")
            return {"success": False, "error": str(e)}

    def get_all_memories_raw(self) -> Dict[str, Any]:
        """Get all agent memories in structured format.

        WHY: This provides programmatic access to all agent memories, allowing
        external tools, scripts, or APIs to retrieve and process the complete
        memory state of the system.

        Returns:
            Dict containing structured memory data for all agents
        """
        try:
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "total_agents": 0,
                "total_size_bytes": 0,
                "agents": {},
            }

            # Ensure directory exists
            if not self.memories_dir.exists():
                return {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "total_agents": 0,
                    "total_size_bytes": 0,
                    "agents": {},
                    "message": "No memory directory found",
                }

            # Find all agent memory files
            memory_files = list(self.memories_dir.glob("*_agent.md"))
            result["total_agents"] = len(memory_files)

            # Process each agent memory file
            for file_path in sorted(memory_files):
                agent_id = file_path.stem.replace("_agent", "")

                try:
                    # Get file stats
                    stat = file_path.stat()
                    file_size = stat.st_size
                    result["total_size_bytes"] += file_size

                    # Load and parse memory content
                    memory_content = file_path.read_text(encoding="utf-8")

                    if memory_content:
                        sections = self.content_manager.parse_memory_content_to_dict(
                            memory_content
                        )

                        # Count total items across all sections
                        total_items = sum(len(items) for items in sections.values())

                        result["agents"][agent_id] = {
                            "agent_id": agent_id,
                            "file_path": str(file_path),
                            "file_size_bytes": file_size,
                            "file_size_kb": round(file_size / 1024, 2),
                            "last_modified": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                            "sections_count": len(sections),
                            "total_items": total_items,
                            "auto_learning": self._get_agent_auto_learning(agent_id),
                            "size_limits": self._get_agent_limits(agent_id),
                            "sections": sections,
                            "raw_content": memory_content,
                        }
                    else:
                        result["agents"][agent_id] = {
                            "agent_id": agent_id,
                            "file_path": str(file_path),
                            "file_size_bytes": file_size,
                            "file_size_kb": round(file_size / 1024, 2),
                            "last_modified": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                            "error": "Could not load memory content",
                            "sections": {},
                            "raw_content": "",
                        }

                except Exception as e:
                    self.logger.error(
                        f"Error processing memory for agent {agent_id}: {e}"
                    )
                    result["agents"][agent_id] = {
                        "agent_id": agent_id,
                        "file_path": str(file_path),
                        "error": str(e),
                        "sections": {},
                        "raw_content": "",
                    }

            result["total_size_kb"] = round(result["total_size_bytes"] / 1024, 2)
            return result

        except Exception as e:
            self.logger.error(f"Error getting all memories raw: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_memory_metrics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get memory usage metrics.

        Args:
            agent_id: Optional specific agent ID, or None for all

        Returns:
            Dictionary with memory metrics
        """
        import re

        metrics = {
            "total_memories": 0,
            "total_size_kb": 0,
            "agent_metrics": {},
            "limits": self.memory_limits.copy(),
        }

        try:
            if agent_id:
                # Get metrics for specific agent
                memory_path = self.memories_dir / f"{agent_id}_agent.md"
                if memory_path.exists():
                    content = memory_path.read_text(encoding="utf-8")
                    size_kb = len(content.encode("utf-8")) / 1024
                    sections = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)

                    metrics["agent_metrics"][agent_id] = {
                        "size_kb": round(size_kb, 2),
                        "sections": len(sections),
                        "exists": True,
                    }
                    metrics["total_memories"] = 1
                    metrics["total_size_kb"] = round(size_kb, 2)
            else:
                # Get metrics for all agents
                for memory_file in self.memories_dir.glob("*_agent.md"):
                    agent_name = memory_file.stem.replace("_agent", "")
                    content = memory_file.read_text(encoding="utf-8")
                    size_kb = len(content.encode("utf-8")) / 1024
                    sections = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)

                    metrics["agent_metrics"][agent_name] = {
                        "size_kb": round(size_kb, 2),
                        "sections": len(sections),
                        "exists": True,
                    }
                    metrics["total_memories"] += 1
                    metrics["total_size_kb"] += size_kb

                metrics["total_size_kb"] = round(metrics["total_size_kb"], 2)

        except Exception as e:
            self.logger.error(f"Failed to get memory metrics: {e}")

        return metrics
