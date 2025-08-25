"""
Tests for Memory Output Formatter Service
==========================================

WHY: These tests verify that the MemoryOutputFormatter service correctly
formats memory-related data for display in various formats, handling edge
cases and ensuring consistent emoji usage across outputs.

DESIGN DECISIONS:
- Test each format method independently
- Verify JSON/YAML/table output generation
- Test quiet and verbose modes
- Cover edge cases (empty data, null values, large data sets)
- Ensure interface compliance
"""

import json
import yaml
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from claude_mpm.services.cli.memory_output_formatter import (
    IMemoryOutputFormatter,
    MemoryOutputFormatter
)


class TestMemoryOutputFormatter(unittest.TestCase):
    """Test suite for MemoryOutputFormatter service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.formatter = MemoryOutputFormatter(quiet=False)
        self.quiet_formatter = MemoryOutputFormatter(quiet=True)
    
    def test_interface_compliance(self):
        """Test that MemoryOutputFormatter implements IMemoryOutputFormatter."""
        self.assertIsInstance(self.formatter, IMemoryOutputFormatter)
    
    def test_format_status_healthy(self):
        """Test formatting healthy memory status."""
        status_data = {
            "success": True,
            "system_health": "healthy",
            "memory_directory": "/project/.claude/memories",
            "system_enabled": True,
            "auto_learning": True,
            "total_agents": 5,
            "total_size_kb": 42.5,
            "agents": {
                "engineer": {
                    "size_kb": 8.5,
                    "size_limit_kb": 20,
                    "size_utilization": 42.5,
                    "sections": 3,
                    "items": 15,
                    "last_modified": "2024-01-15T10:30:00Z",
                    "auto_learning": True
                }
            }
        }
        
        output = self.formatter.format_status(status_data)
        
        # Check key elements are present
        self.assertIn("Agent Memory System Status", output)
        self.assertIn("✅", output)  # Healthy status
        self.assertIn("Memory Directory: /project/.claude/memories", output)
        self.assertIn("Total Agents: 5", output)
        self.assertIn("engineer", output)
        self.assertIn("42.5%", output)  # Utilization
    
    def test_format_status_quiet_mode(self):
        """Test status formatting in quiet mode (no emojis)."""
        status_data = {
            "success": True,
            "system_health": "healthy",
            "total_agents": 2,
            "total_size_kb": 15.0
        }
        
        output = self.quiet_formatter.format_status(status_data)
        
        # Check no emojis, only text markers
        self.assertNotIn("✅", output)
        self.assertNotIn("🧠", output)
        self.assertIn("[OK]", output)
        self.assertIn("[MEMORY]", output)
    
    def test_format_status_with_optimization_opportunities(self):
        """Test status formatting with optimization opportunities."""
        status_data = {
            "success": True,
            "system_health": "needs_optimization",
            "optimization_opportunities": [
                "Agent 'engineer' has 50+ duplicate items",
                "Agent 'qa' memory file exceeds 90% capacity",
                "Agent 'research' has stale entries older than 30 days"
            ]
        }
        
        output = self.formatter.format_status(status_data)
        
        self.assertIn("Optimization Opportunities (3)", output)
        self.assertIn("duplicate items", output)
        self.assertIn("exceeds 90% capacity", output)
    
    def test_format_memory_view_full(self):
        """Test formatting full memory view."""
        memory_content = """## Project Architecture
- Use dependency injection
- Follow SOLID principles

## Common Mistakes
- Avoid global state
- Don't mix concerns"""
        
        output = self.formatter.format_memory_view("engineer", memory_content, "full")
        
        self.assertIn("engineer", output)
        self.assertIn("Project Architecture", output)
        self.assertIn("Use dependency injection", output)
    
    def test_format_memory_view_detailed(self):
        """Test formatting detailed memory view with sections."""
        memory_content = """## Project Architecture
- Pattern 1
- Pattern 2
- Pattern 3
- Pattern 4
- Pattern 5
- Pattern 6
- Pattern 7
- Pattern 8
- Pattern 9
- Pattern 10
- Pattern 11"""
        
        output = self.formatter.format_memory_view("engineer", memory_content, "detailed")
        
        self.assertIn("Project Architecture (11 items)", output)
        self.assertIn("Pattern 1", output)
        self.assertIn("... and 1 more", output)  # Should show first 10
    
    def test_format_memory_view_empty(self):
        """Test formatting empty memory view."""
        output = self.formatter.format_memory_view("engineer", "", "detailed")
        
        self.assertIn("No memory found", output)
        self.assertIn("engineer", output)
    
    def test_format_optimization_results_single_agent(self):
        """Test formatting optimization results for a single agent."""
        results = {
            "agent_id": "engineer",
            "original_size": 10240,
            "optimized_size": 7168,
            "size_reduction": 3072,
            "size_reduction_percent": 30,
            "duplicates_removed": 15,
            "items_consolidated": 8,
            "backup_created": "/project/.claude/memories/backups/engineer_backup.md"
        }
        
        output = self.formatter.format_optimization_results(results, is_single_agent=True)
        
        self.assertIn("Optimization completed for engineer", output)
        self.assertIn("10,240 bytes", output)
        self.assertIn("30%", output)
        self.assertIn("Duplicates removed: 15", output)
        self.assertIn("backup", output)
    
    def test_format_optimization_results_bulk(self):
        """Test formatting bulk optimization results."""
        results = {
            "summary": {
                "agents_processed": 5,
                "agents_optimized": 4,
                "total_size_before": 51200,
                "total_size_after": 35840,
                "total_size_reduction": 15360,
                "total_size_reduction_percent": 30,
                "total_duplicates_removed": 45,
                "total_items_consolidated": 20
            },
            "agents": {
                "engineer": {
                    "success": True,
                    "size_reduction_percent": 35,
                    "duplicates_removed": 20
                },
                "qa": {
                    "success": False,
                    "error": "File locked"
                }
            }
        }
        
        output = self.formatter.format_optimization_results(results, is_single_agent=False)
        
        self.assertIn("Bulk optimization completed", output)
        self.assertIn("Agents processed: 5", output)
        self.assertIn("51,200 bytes", output)
        self.assertIn("engineer: 35% reduction", output)
        self.assertIn("qa: ❌ File locked", output)
    
    def test_format_cross_reference_with_patterns(self):
        """Test formatting cross-reference analysis with common patterns."""
        cross_ref_data = {
            "success": True,
            "common_patterns": [
                {
                    "pattern": "use dependency injection",
                    "agents": ["engineer", "qa", "architect"],
                    "count": 3
                },
                {
                    "pattern": "follow solid principles",
                    "agents": ["engineer", "architect"],
                    "count": 2
                }
            ],
            "agent_correlations": {
                "engineer-architect": 15,
                "engineer-qa": 8,
                "qa-architect": 5
            }
        }
        
        output = self.formatter.format_cross_reference(cross_ref_data)
        
        self.assertIn("Common patterns found (2)", output)
        self.assertIn("use dependency injection", output)
        self.assertIn("Found in: engineer, qa, architect", output)
        self.assertIn("Agent knowledge correlations", output)
        self.assertIn("engineer-architect: 15 common items", output)
    
    def test_format_cross_reference_with_query(self):
        """Test formatting cross-reference with query matches."""
        cross_ref_data = {
            "success": True,
            "query_matches": [
                {
                    "agent": "engineer",
                    "matches": [
                        "Use dependency injection for services",
                        "Inject dependencies via constructor",
                        "Avoid service locator pattern"
                    ]
                }
            ]
        }
        
        output = self.formatter.format_cross_reference(cross_ref_data, query="dependency")
        
        self.assertIn("Searching for: 'dependency'", output)
        self.assertIn("Query matches for 'dependency'", output)
        self.assertIn("engineer", output)
        self.assertIn("Use dependency injection", output)
    
    def test_format_as_json(self):
        """Test JSON formatting."""
        data = {
            "agent": "engineer",
            "memories": ["pattern1", "pattern2"],
            "size": 1024
        }
        
        output = self.formatter.format_as_json(data)
        parsed = json.loads(output)
        
        self.assertEqual(parsed["agent"], "engineer")
        self.assertEqual(len(parsed["memories"]), 2)
        self.assertIn("\n", output)  # Pretty printed
    
    def test_format_as_json_compact(self):
        """Test compact JSON formatting."""
        data = {"key": "value"}
        
        output = self.formatter.format_as_json(data, pretty=False)
        
        self.assertNotIn("\n", output)
        self.assertEqual(output, '{"key": "value"}')
    
    def test_format_as_yaml(self):
        """Test YAML formatting."""
        data = {
            "agents": {
                "engineer": {
                    "memories": 15,
                    "sections": ["architecture", "patterns"]
                }
            }
        }
        
        output = self.formatter.format_as_yaml(data)
        parsed = yaml.safe_load(output)
        
        self.assertEqual(parsed["agents"]["engineer"]["memories"], 15)
        self.assertIn("architecture", parsed["agents"]["engineer"]["sections"])
    
    def test_format_as_table(self):
        """Test table formatting."""
        headers = ["Agent", "Size (KB)", "Items"]
        rows = [
            ["engineer", "8.5", "15"],
            ["qa", "5.2", "8"],
            ["architect", "12.1", "22"]
        ]
        
        output = self.formatter.format_as_table(headers, rows)
        
        # Check headers
        self.assertIn("Agent", output)
        self.assertIn("Size (KB)", output)
        
        # Check data
        self.assertIn("engineer", output)
        self.assertIn("8.5", output)
        self.assertIn("architect", output)
        
        # Check separator line
        lines = output.split("\n")
        self.assertIn("-", lines[1])
    
    def test_format_build_results_success(self):
        """Test formatting successful build results."""
        results = {
            "success": True,
            "files_processed": 12,
            "memories_created": 45,
            "memories_updated": 8,
            "total_agents_affected": 5,
            "agents_affected": ["engineer", "qa", "architect"],
            "files": {
                "README.md": {
                    "success": True,
                    "items_extracted": 10,
                    "memories_created": 5
                }
            }
        }
        
        output = self.formatter.format_build_results(results)
        
        self.assertIn("Successfully processed documentation", output)
        self.assertIn("Files processed: 12", output)
        self.assertIn("Memories created: 45", output)
        self.assertIn("Affected agents: engineer, qa, architect", output)
        self.assertIn("README.md: 10 items extracted", output)
    
    def test_format_build_results_with_errors(self):
        """Test formatting build results with errors."""
        results = {
            "success": True,
            "files_processed": 5,
            "errors": [
                "Failed to parse docs/broken.md",
                "Permission denied: docs/private.md"
            ]
        }
        
        output = self.formatter.format_build_results(results)
        
        self.assertIn("Errors encountered", output)
        self.assertIn("Failed to parse", output)
        self.assertIn("Permission denied", output)
    
    def test_format_agent_memories_summary(self):
        """Test formatting agent memories summary."""
        agent_memories = {
            "engineer": {
                "Architecture": ["pattern1", "pattern2", "pattern3"],
                "Guidelines": ["guide1", "guide2"]
            },
            "qa": {
                "Testing": ["test1", "test2"]
            }
        }
        
        output = self.formatter.format_agent_memories_summary(agent_memories)
        
        self.assertIn("Found memories for 2 agents", output)
        self.assertIn("engineer", output)
        self.assertIn("2 sections, 5 total items", output)
        self.assertIn("Architecture: 3 items", output)
    
    def test_format_agent_memories_detailed(self):
        """Test formatting detailed agent memories."""
        agent_memories = {
            "engineer": {
                "Patterns": [
                    "Use dependency injection",
                    "Follow SOLID principles",
                    "Apply DRY principle",
                    "Use composition over inheritance"
                ]
            }
        }
        
        output = self.formatter.format_agent_memories_summary(agent_memories, format_type="detailed")
        
        self.assertIn("Patterns:", output)
        self.assertIn("Use dependency injection", output)
        self.assertIn("... and 1 more", output)  # Shows first 3
    
    def test_parse_memory_content(self):
        """Test internal memory content parsing."""
        content = """## Project Architecture
- Pattern 1
- Pattern 2

## Memory Usage: 5KB

## Guidelines
- Guide 1
- Guide 2
- Guide 3"""
        
        sections = self.formatter._parse_memory_content(content)
        
        self.assertEqual(len(sections), 2)  # Should skip "Memory Usage"
        self.assertIn("Project Architecture", sections)
        self.assertEqual(len(sections["Project Architecture"]), 2)
        self.assertEqual(len(sections["Guidelines"]), 3)
    
    def test_find_common_patterns(self):
        """Test finding common patterns across agents."""
        agent_memories = {
            "engineer": {
                "Patterns": [
                    "Use dependency injection",
                    "Follow SOLID principles",
                    "Apply DRY principle"
                ]
            },
            "architect": {
                "Design": [
                    "use dependency injection",  # Same but lowercase
                    "follow solid principles",
                    "Use microservices"
                ]
            },
            "qa": {
                "Testing": [
                    "Apply DRY principle",
                    "Test edge cases"
                ]
            }
        }
        
        patterns = self.formatter._find_common_patterns(agent_memories)
        
        # Should find patterns that appear in multiple agents
        self.assertGreater(len(patterns), 0)
        
        # Check that common patterns are found (case-insensitive)
        pattern_texts = [p[0] for p in patterns]
        self.assertIn("use dependency injection", pattern_texts)
    
    def test_edge_case_empty_data(self):
        """Test handling of empty data structures."""
        # Empty status
        output = self.formatter.format_status({})
        self.assertIn("Agent Memory System Status", output)
        
        # Empty cross-reference
        output = self.formatter.format_cross_reference({})
        self.assertIn("Cross-Reference Analysis", output)
        
        # Empty build results
        output = self.formatter.format_build_results({})
        self.assertIn("Memory Building", output)
    
    def test_edge_case_null_values(self):
        """Test handling of null/None values."""
        status_data = {
            "success": True,
            "system_health": None,
            "memory_directory": None,
            "total_agents": None,
            "agents": {}
        }
        
        output = self.formatter.format_status(status_data)
        
        # Should handle None values gracefully
        self.assertIn("unknown", output.lower())
        self.assertNotIn("None", output)
    
    def test_large_data_sets(self):
        """Test handling of large data sets."""
        # Create large agent list
        large_agents = {}
        for i in range(100):
            large_agents[f"agent_{i}"] = {
                "size_kb": i * 0.1,
                "size_limit_kb": 20,
                "size_utilization": i,
                "sections": 5,
                "items": i * 2
            }
        
        status_data = {
            "success": True,
            "agents": large_agents
        }
        
        output = self.formatter.format_status(status_data)
        
        # Should handle large data without issues
        self.assertIn("agent_0", output)
        self.assertIn("agent_99", output)
    
    def test_special_characters_handling(self):
        """Test handling of special characters in content."""
        memory_content = """## Special Characters
- Use `code` blocks
- Handle "quotes" properly
- Support unicode: 日本語 🎉
- HTML chars: <div> & </div>"""
        
        output = self.formatter.format_memory_view("test", memory_content, "detailed")
        
        # Should preserve special characters
        self.assertIn("`code`", output)
        self.assertIn('"quotes"', output)
        self.assertIn("日本語", output)
        self.assertIn("<div>", output)


if __name__ == "__main__":
    unittest.main()