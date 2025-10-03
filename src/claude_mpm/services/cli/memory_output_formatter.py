"""
Memory Output Formatter Service
===============================

WHY: This service consolidates all memory display and formatting logic that was
previously duplicated throughout the memory.py command file, reducing code by ~250 lines
and providing consistent, reusable formatting across the entire memory subsystem.

DESIGN DECISIONS:
- Extract all formatting methods from memory.py into a reusable service
- Support multiple output formats (text, json, yaml, table)
- Implement quiet and verbose modes for flexible output control
- Maintain consistent emoji usage across all memory displays
- Follow established service patterns with interface-based design
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ...core.logger import get_logger


class IMemoryOutputFormatter(ABC):
    """Interface for memory output formatting service."""

    @abstractmethod
    def format_status(self, status_data: Dict[str, Any], verbose: bool = False) -> str:
        """Format memory status display."""

    @abstractmethod
    def format_memory_view(
        self, agent_id: str, memory_content: str, format_type: str = "detailed"
    ) -> str:
        """Format memory viewing output."""

    @abstractmethod
    def format_optimization_results(
        self, results: Dict[str, Any], is_single_agent: bool = True
    ) -> str:
        """Format optimization output."""

    @abstractmethod
    def format_cross_reference(
        self, cross_ref_data: Dict[str, Any], query: Optional[str] = None
    ) -> str:
        """Format pattern analysis output."""

    @abstractmethod
    def format_as_json(self, data: Dict[str, Any], pretty: bool = True) -> str:
        """Format data as JSON."""

    @abstractmethod
    def format_as_yaml(self, data: Dict[str, Any]) -> str:
        """Format data as YAML."""

    @abstractmethod
    def format_as_table(self, headers: List[str], rows: List[List[Any]]) -> str:
        """Format data as a table."""

    @abstractmethod
    def format_build_results(self, results: Dict[str, Any]) -> str:
        """Format memory build results."""

    @abstractmethod
    def format_agent_memories_summary(
        self, agent_memories: Dict[str, Dict], format_type: str = "summary"
    ) -> str:
        """Format summary of all agent memories."""


class MemoryOutputFormatter(IMemoryOutputFormatter):
    """Implementation of memory output formatting service."""

    def __init__(self, quiet: bool = False):
        """
        Initialize the memory output formatter.

        Args:
            quiet: If True, minimize output (no emojis, minimal formatting)
        """
        self.quiet = quiet
        self.logger = get_logger(__name__)

        # Emoji mappings for consistent usage
        self.emojis = {
            "success": "✅" if not quiet else "[OK]",
            "error": "❌" if not quiet else "[ERROR]",
            "warning": "⚠️" if not quiet else "[WARN]",
            "info": "[INFO]️" if not quiet else "[INFO]",
            "memory": "🧠" if not quiet else "[MEMORY]",
            "file": "📁" if not quiet else "[FILE]",
            "agent": "🤖" if not quiet else "[AGENT]",
            "stats": "📊" if not quiet else "[STATS]",
            "clean": "🧹" if not quiet else "[CLEAN]",
            "optimize": "🔧" if not quiet else "[OPTIMIZE]",
            "build": "📚" if not quiet else "[BUILD]",
            "link": "🔗" if not quiet else "[LINK]",
            "search": "🔍" if not quiet else "[SEARCH]",
            "target": "🎯" if not quiet else "[TARGET]",
            "book": "📖" if not quiet else "[SECTION]",
            "page": "📋" if not quiet else "[PAGE]",
            "handshake": "🤝" if not quiet else "[CORRELATION]",
            "cycle": "🔄" if not quiet else "[PATTERN]",
            "rocket": "🚀" if not quiet else "[INIT]",
            "disk": "💾" if not quiet else "[SIZE]",
            "green": "🟢" if not quiet else "[LOW]",
            "yellow": "🟡" if not quiet else "[MED]",
            "red": "🔴" if not quiet else "[HIGH]",
            "empty": "📭" if not quiet else "[EMPTY]",
            "note": "📝" if not quiet else "[NOTE]",
        }

    def format_status(self, status_data: Dict[str, Any], verbose: bool = False) -> str:
        """Format memory status display."""
        lines = []
        lines.append("Agent Memory System Status")
        lines.append("-" * 80)

        if not status_data.get("success", True):
            lines.append(
                f"{self.emojis['error']} Error getting status: {status_data.get('error', 'Unknown error')}"
            )
            return "\n".join(lines)

        # System overview
        system_health = status_data.get("system_health")
        if system_health is None:
            system_health = "unknown"
        health_emoji = {
            "healthy": self.emojis["success"],
            "needs_optimization": self.emojis["warning"],
            "high_usage": self.emojis["stats"],
            "no_memory_dir": self.emojis["file"],
        }.get(system_health, self.emojis["info"])

        lines.append(
            f"{self.emojis['memory']} Memory System Health: {health_emoji} {system_health}"
        )

        # Handle null/None values properly
        memory_dir = status_data.get("memory_directory")
        lines.append(
            f"{self.emojis['file']} Memory Directory: {memory_dir if memory_dir is not None else 'Unknown'}"
        )

        lines.append(
            f"{self.emojis['optimize']} System Enabled: {'Yes' if status_data.get('system_enabled', True) else 'No'}"
        )
        lines.append(
            f"{self.emojis['build']} Auto Learning: {'Yes' if status_data.get('auto_learning', True) else 'No'}"
        )

        total_agents = status_data.get("total_agents")
        lines.append(
            f"{self.emojis['stats']} Total Agents: {total_agents if total_agents is not None else 'Unknown'}"
        )

        lines.append(
            f"{self.emojis['disk']} Total Size: {status_data.get('total_size_kb', 0):.1f} KB"
        )
        lines.append("")

        # Optimization opportunities
        opportunities = status_data.get("optimization_opportunities", [])
        if opportunities:
            lines.append(
                f"{self.emojis['warning']} Optimization Opportunities ({len(opportunities)}):"
            )
            limit = 10 if verbose else 5
            for opportunity in opportunities[:limit]:
                lines.append(f"   • {opportunity}")
            if len(opportunities) > limit:
                lines.append(f"   ... and {len(opportunities) - limit} more")
            lines.append("")

        # Per-agent details
        agents = status_data.get("agents", {})
        if agents:
            lines.append(f"{self.emojis['page']} Agent Memory Details:")
            for agent_id, agent_info in sorted(agents.items()):
                if "error" in agent_info:
                    lines.append(
                        f"   {self.emojis['error']} {agent_id}: Error - {agent_info['error']}"
                    )
                    continue

                size_kb = agent_info.get("size_kb", 0)
                size_limit = agent_info.get("size_limit_kb", 8)
                utilization = agent_info.get("size_utilization", 0)
                sections = agent_info.get("sections", 0)
                items = agent_info.get("items", 0)
                last_modified = agent_info.get("last_modified", "Unknown")
                auto_learning = agent_info.get("auto_learning", True)

                # Format last modified time
                try:
                    dt = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
                    last_modified_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    last_modified_str = last_modified

                # Status indicator based on usage
                if utilization > 90:
                    status_emoji = self.emojis["red"]
                elif utilization > 70:
                    status_emoji = self.emojis["yellow"]
                else:
                    status_emoji = self.emojis["green"]

                lines.append(f"   {status_emoji} {agent_id}")
                lines.append(
                    f"      Size: {size_kb:.1f} KB / {size_limit} KB ({utilization:.1f}%)"
                )
                lines.append(f"      Content: {sections} sections, {items} items")
                lines.append(f"      Auto-learning: {'On' if auto_learning else 'Off'}")
                lines.append(f"      Last modified: {last_modified_str}")

                if verbose and agent_info.get("recent_items"):
                    lines.append("      Recent items:")
                    for item in agent_info["recent_items"][:3]:
                        lines.append(f"        - {item}")
        else:
            lines.append(f"{self.emojis['empty']} No agent memories found")

        return "\n".join(lines)

    def format_memory_view(
        self, agent_id: str, memory_content: str, format_type: str = "detailed"
    ) -> str:
        """Format memory viewing output."""
        lines = []

        if not memory_content:
            lines.append(
                f"{self.emojis['empty']} No memory found for agent: {agent_id}"
            )
            return "\n".join(lines)

        lines.append(f"{self.emojis['agent']} Agent: {agent_id}")
        lines.append("-" * 40)

        if format_type == "full":
            lines.append(memory_content)
        else:
            # Parse and display memory sections
            sections = self._parse_memory_content(memory_content)

            for section_name, items in sections.items():
                if items:
                    lines.append(
                        f"\n{self.emojis['build']} {section_name} ({len(items)} items):"
                    )
                    limit = 10 if format_type == "detailed" else 5
                    for i, item in enumerate(items[:limit], 1):
                        lines.append(f"   {i}. {item}")
                    if len(items) > limit:
                        lines.append(f"   ... and {len(items) - limit} more")

        return "\n".join(lines)

    def format_optimization_results(
        self, results: Dict[str, Any], is_single_agent: bool = True
    ) -> str:
        """Format optimization output."""
        lines = []

        if is_single_agent:
            agent_id = results.get("agent_id", "unknown")
            original_size = results.get("original_size", 0)
            optimized_size = results.get("optimized_size", 0)
            size_reduction = results.get("size_reduction", 0)
            size_reduction_percent = results.get("size_reduction_percent", 0)

            lines.append(
                f"{self.emojis['success']} Optimization completed for {agent_id}"
            )
            lines.append(f"   Original size: {original_size:,} bytes")
            lines.append(f"   Optimized size: {optimized_size:,} bytes")
            lines.append(
                f"   Size reduction: {size_reduction:,} bytes ({size_reduction_percent}%)"
            )

            duplicates = results.get("duplicates_removed", 0)
            consolidated = results.get("items_consolidated", 0)
            reordered = results.get("items_reordered", 0)

            if duplicates > 0:
                lines.append(f"   Duplicates removed: {duplicates}")
            if consolidated > 0:
                lines.append(f"   Items consolidated: {consolidated}")
            if reordered > 0:
                lines.append(f"   Sections reordered: {reordered}")

            backup_path = results.get("backup_created")
            if backup_path:
                lines.append(f"   Backup created: {backup_path}")
        else:
            # Bulk optimization results
            summary = results.get("summary", {})

            lines.append(f"{self.emojis['success']} Bulk optimization completed")
            lines.append(f"   Agents processed: {summary.get('agents_processed', 0)}")
            lines.append(f"   Agents optimized: {summary.get('agents_optimized', 0)}")
            lines.append(
                f"   Total size before: {summary.get('total_size_before', 0):,} bytes"
            )
            lines.append(
                f"   Total size after: {summary.get('total_size_after', 0):,} bytes"
            )
            lines.append(
                f"   Total reduction: {summary.get('total_size_reduction', 0):,} bytes ({summary.get('total_size_reduction_percent', 0)}%)"
            )
            lines.append(
                f"   Total duplicates removed: {summary.get('total_duplicates_removed', 0)}"
            )
            lines.append(
                f"   Total items consolidated: {summary.get('total_items_consolidated', 0)}"
            )

            # Per-agent summary
            agents_results = results.get("agents", {})
            if agents_results:
                lines.append(f"\n{self.emojis['stats']} Per-agent results:")
                for agent_id, agent_result in agents_results.items():
                    if agent_result.get("success"):
                        reduction = agent_result.get("size_reduction_percent", 0)
                        duplicates = agent_result.get("duplicates_removed", 0)
                        consolidated = agent_result.get("items_consolidated", 0)

                        status_parts = []
                        if duplicates > 0:
                            status_parts.append(f"{duplicates} dupes")
                        if consolidated > 0:
                            status_parts.append(f"{consolidated} consolidated")

                        status = f" ({', '.join(status_parts)})" if status_parts else ""
                        lines.append(f"   {agent_id}: {reduction}% reduction{status}")
                    else:
                        error = agent_result.get("error", "Unknown error")
                        lines.append(f"   {agent_id}: {self.emojis['error']} {error}")

        return "\n".join(lines)

    def format_cross_reference(
        self, cross_ref_data: Dict[str, Any], query: Optional[str] = None
    ) -> str:
        """Format pattern analysis output."""
        lines = []
        lines.append(f"{self.emojis['link']} Memory Cross-Reference Analysis")
        lines.append("-" * 80)

        if query:
            lines.append(f"{self.emojis['search']} Searching for: '{query}'")
        else:
            lines.append(
                f"{self.emojis['search']} Analyzing all agent memories for patterns..."
            )

        if cross_ref_data.get("success") is False:
            lines.append(
                f"{self.emojis['error']} Analysis failed: {cross_ref_data.get('error', 'Unknown error')}"
            )
            return "\n".join(lines)

        # Display common patterns
        common_patterns = cross_ref_data.get("common_patterns", [])
        if common_patterns:
            lines.append(
                f"\n{self.emojis['cycle']} Common patterns found ({len(common_patterns)}):"
            )
            for pattern in common_patterns[:10]:
                agents = ", ".join(pattern["agents"])
                lines.append(f"   • {pattern['pattern']}")
                lines.append(f"     Found in: {agents} ({pattern['count']} instances)")
        else:
            lines.append(f"\n{self.emojis['cycle']} No common patterns found")

        # Display query matches if query was provided
        if query and cross_ref_data.get("query_matches"):
            lines.append(f"\n{self.emojis['target']} Query matches for '{query}':")
            for match in cross_ref_data["query_matches"]:
                lines.append(f"   {self.emojis['page']} {match['agent']}:")
                for line in match["matches"][:3]:
                    lines.append(f"      • {line}")

        # Display agent correlations
        correlations = cross_ref_data.get("agent_correlations", {})
        if correlations:
            lines.append(f"\n{self.emojis['handshake']} Agent knowledge correlations:")
            sorted_correlations = sorted(
                correlations.items(), key=lambda x: x[1], reverse=True
            )
            for agents, count in sorted_correlations[:5]:
                lines.append(f"   {agents}: {count} common items")
        else:
            lines.append(
                f"\n{self.emojis['handshake']} No significant correlations found"
            )

        return "\n".join(lines)

    def format_as_json(self, data: Dict[str, Any], pretty: bool = True) -> str:
        """Format data as JSON."""
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)

    def format_as_yaml(self, data: Dict[str, Any]) -> str:
        """Format data as YAML."""
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)

    def format_as_table(self, headers: List[str], rows: List[List[Any]]) -> str:
        """Format data as a table."""
        lines = []

        # Calculate column widths
        col_widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Create header
        header_line = " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # Add rows
        for row in rows:
            row_line = " | ".join(
                str(cell).ljust(w) for cell, w in zip(row, col_widths)
            )
            lines.append(row_line)

        return "\n".join(lines)

    def format_build_results(self, results: Dict[str, Any]) -> str:
        """Format memory build results."""
        lines = []
        lines.append(f"{self.emojis['build']} Memory Building from Documentation")
        lines.append("-" * 80)

        if results.get("success"):
            lines.append(
                f"{self.emojis['success']} Successfully processed documentation"
            )
            lines.append(f"   Files processed: {results.get('files_processed', 0)}")
            lines.append(f"   Memories created: {results.get('memories_created', 0)}")
            lines.append(f"   Memories updated: {results.get('memories_updated', 0)}")
            lines.append(
                f"   Agents affected: {results.get('total_agents_affected', 0)}"
            )

            if results.get("agents_affected"):
                lines.append(
                    f"   Affected agents: {', '.join(results['agents_affected'])}"
                )

            # Show file-specific results
            files_results = results.get("files", {})
            if files_results:
                lines.append(f"\n{self.emojis['page']} File processing details:")
                for file_path, file_result in files_results.items():
                    if file_result.get("success"):
                        extracted = file_result.get("items_extracted", 0)
                        created = file_result.get("memories_created", 0)
                        lines.append(
                            f"   {file_path}: {extracted} items extracted, {created} memories created"
                        )

            if results.get("errors"):
                lines.append(f"\n{self.emojis['warning']} Errors encountered:")
                for error in results["errors"]:
                    lines.append(f"   {error}")
        else:
            lines.append(
                f"{self.emojis['error']} Build failed: {results.get('error', 'Unknown error')}"
            )

        return "\n".join(lines)

    def format_agent_memories_summary(
        self, agent_memories: Dict[str, Dict], format_type: str = "summary"
    ) -> str:
        """Format summary of all agent memories."""
        lines = []

        if not agent_memories:
            lines.append(f"{self.emojis['empty']} No agent memories found")
            return "\n".join(lines)

        lines.append(
            f"{self.emojis['stats']} Found memories for {len(agent_memories)} agents"
        )
        lines.append("")

        total_items = 0
        for agent_id, sections in sorted(agent_memories.items()):
            item_count = sum(len(items) for items in sections.values())
            total_items += item_count

            lines.append(f"{self.emojis['agent']} {agent_id}")
            lines.append(
                f"   {self.emojis['build']} {len(sections)} sections, {item_count} total items"
            )

            if format_type == "summary":
                # Show section summary
                for section_name, items in sections.items():
                    if items:
                        lines.append(f"      • {section_name}: {len(items)} items")
            elif format_type == "detailed":
                for section_name, items in sections.items():
                    if items:
                        lines.append(f"\n   {self.emojis['book']} {section_name}:")
                        for item in items[:3]:
                            lines.append(f"      • {item}")
                        if len(items) > 3:
                            lines.append(f"      ... and {len(items) - 3} more")
            lines.append("")

        lines.append(
            f"{self.emojis['stats']} Total: {total_items} memory items across {len(agent_memories)} agents"
        )

        # Show cross-references if we have multiple agents
        if len(agent_memories) > 1:
            lines.append(
                f"\n{self.emojis['link']} Cross-References and Common Patterns:"
            )
            common_patterns = self._find_common_patterns(agent_memories)
            if common_patterns:
                lines.append(f"\n{self.emojis['cycle']} Most Common Patterns:")
                for pattern, count, agents in common_patterns[:5]:
                    lines.append(
                        f"   • {pattern[:80]}{'...' if len(pattern) > 80 else ''}"
                    )
                    lines.append(f"     Found in: {', '.join(agents)} ({count} agents)")
            else:
                lines.append("   No common patterns found across agents")

        return "\n".join(lines)

    def _parse_memory_content(self, content: str) -> Dict[str, List[str]]:
        """Parse memory content into sections and items."""
        sections = {}
        current_section = None
        current_items = []

        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("## ") and not line.startswith("## Memory Usage"):
                # New section
                if current_section and current_items:
                    sections[current_section] = current_items.copy()

                current_section = line[3:].strip()
                current_items = []
            elif line.startswith("- ") and current_section:
                # Item in current section
                item = line[2:].strip()
                if item and len(item) > 5:  # Filter out very short items
                    current_items.append(item)

        # Add final section
        if current_section and current_items:
            sections[current_section] = current_items

        return sections

    def _find_common_patterns(
        self, agent_memories: Dict[str, Dict]
    ) -> List[Tuple[str, int, List[str]]]:
        """Find common patterns across agent memories."""
        pattern_agents = {}

        # Collect all patterns and which agents have them
        for agent_id, sections in agent_memories.items():
            seen_patterns = set()

            for _section_name, items in sections.items():
                for item in items:
                    # Normalize item for comparison (lowercase, basic cleanup)
                    normalized = item.lower().strip()
                    if len(normalized) > 10 and normalized not in seen_patterns:
                        if normalized not in pattern_agents:
                            pattern_agents[normalized] = []
                        pattern_agents[normalized].append(agent_id)
                        seen_patterns.add(normalized)

        # Find patterns that appear in multiple agents
        common_patterns = []
        for pattern, agents in pattern_agents.items():
            if len(agents) > 1:
                common_patterns.append((pattern, len(agents), agents))

        # Sort by number of agents
        common_patterns.sort(key=lambda x: x[1], reverse=True)

        return common_patterns
