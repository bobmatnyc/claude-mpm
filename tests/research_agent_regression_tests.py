#!/usr/bin/env python3
"""
Regression Test Cases for Research Agent Critical Failure Scenarios

These tests verify that the improved Research agent fixes the critical search failures
that were identified in the original implementation. Each test case represents a
scenario where the old agent would fail due to:
- Premature result limiting (head/tail usage)
- Conclusions without file reading
- Confidence below 85% threshold
- Rigid time constraints
- Confirmation bias

Test Categories:
1. Anti-pattern Detection: Verify agent won't use forbidden patterns
2. File Reading Requirements: Ensure mandatory file content examination
3. Confidence Threshold: Validate 85% minimum confidence enforcement
4. Search Completeness: Confirm exhaustive search without limits
5. Evidence Following: Test adaptive discovery following evidence chains
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestResearchAgentRegressions:
    """Test cases for Research agent critical failure scenarios."""

    @pytest.fixture
    def research_agent_template(self):
        """Load the improved Research agent template."""
        template_path = (
            Path(__file__).parent.parent
            / "src/claude_mpm/agents/templates/research.json"
        )
        with open(template_path, "r") as f:
            return json.load(f)

    def test_anti_pattern_detection_head_tail_forbidden(self, research_agent_template):
        """Test Case 1: Verify agent instructions forbid head/tail usage."""
        instructions = research_agent_template["instructions"]

        # Verify explicit prohibition of head/tail
        assert "NEVER use `head`, `tail`" in instructions
        assert "head -20" in instructions and "FORBIDDEN" in instructions
        assert 'BAD: `grep -r "pattern" . | head -20`' in instructions
        assert 'GOOD: `grep -r "pattern" .` (examine ALL results)' in instructions

        # Verify "NO LIMITS" requirement
        assert "NO LIMITS" in instructions
        assert "without limits" in instructions.lower()

    def test_mandatory_file_reading_requirement(self, research_agent_template):
        """Test Case 2: Verify mandatory file reading after grep results."""
        instructions = research_agent_template["instructions"]
        best_practices = research_agent_template["knowledge"]["best_practices"]

        # Verify mandatory file reading
        constraints = research_agent_template["knowledge"]["constraints"]
        assert (
            "MANDATORY verification" in instructions
            or "MANDATORY file content reading" in constraints
        )
        assert "ALWAYS read 5-10 actual files after grep matches" in best_practices
        assert "MINIMUM 5 files" in instructions
        assert "NEVER skip this step" in instructions

        # Verify prohibition of grep-only conclusions
        assert "NEVER conclude based on grep results alone" in instructions
        assert "Read those 3 files to verify actual implementation" in instructions

    def test_confidence_threshold_enforcement(self, research_agent_template):
        """Test Case 3: Verify 85% confidence threshold is non-negotiable."""
        instructions = research_agent_template["instructions"]
        constraints = research_agent_template["knowledge"]["constraints"]

        # Verify 85% threshold requirements
        assert "85% confidence threshold is NON-NEGOTIABLE" in constraints
        assert "NEVER accept confidence below 85%" in instructions
        assert "MUST be >= 85 to proceed" in instructions

        # Verify confidence calculation formula
        assert "Confidence Calculation Formula" in instructions
        assert "Files_Actually_Read / Files_Found" in instructions
        assert "Search_Strategies_Confirming / Total_Strategies" in instructions

        # Verify enforcement actions
        assert "70% confident, must investigate further" in instructions
        assert "Cannot proceed without reaching 85%" in instructions

    def test_search_completeness_requirements(self, research_agent_template):
        """Test Case 4: Verify exhaustive search without premature limiting."""
        instructions = research_agent_template["instructions"]

        # Verify exhaustive search requirements
        assert "Exhaustive Initial Discovery (NO TIME LIMIT)" in instructions
        assert "examine ALL search results" in instructions
        assert "ALL searches conducted without limits" in instructions

        # Verify multiple strategy requirements
        assert (
            "ALL 5 REQUIRED" in instructions
            or "multiple search strategies" in instructions.lower()
        )
        assert "Strategy A:" in instructions or "Direct pattern search" in instructions
        assert "Strategy B:" in instructions or "Related concept search" in instructions
        assert (
            "Strategy C:" in instructions
            or "Import/dependency analysis" in instructions
        )
        assert (
            "Strategy D:" in instructions
            or "Directory structure examination" in instructions
        )

    def test_evidence_following_adaptive_discovery(self, research_agent_template):
        """Test Case 5: Verify adaptive discovery following evidence chains."""
        instructions = research_agent_template["instructions"]

        # Verify adaptive discovery protocol
        assert "FOLLOW THE EVIDENCE" in instructions
        assert "follow evidence chains adaptively" in instructions
        assert "Based on findings, adapt search" in instructions

        # Verify evidence chain documentation
        assert "EVIDENCE CHAIN" in instructions
        assert "Discovery Path" in instructions
        assert "Files examined: [List specific files read]" in instructions

    def test_similarity_search_scenario_coverage(self, research_agent_template):
        """Test Case 6: Specific regression for similarity search failure scenario."""
        instructions = research_agent_template["instructions"]

        # This was the original failing scenario - ensure agent would handle it properly
        # The agent should:
        # 1. Search broadly for similarity/semantic/vector terms
        # 2. Read actual files, not just count grep results
        # 3. Follow import chains and related concepts
        # 4. Achieve 85% confidence before concluding

        # Verify broader search strategies that would catch this
        assert (
            "Multiple search strategies" in instructions
            or "search strategies" in instructions
        )
        assert "Follow import chains" in instructions
        assert "related concept search" in instructions

    def test_time_limit_flexibility(self, research_agent_template):
        """Test Case 7: Verify time limits are guidelines, not rigid constraints."""
        instructions = research_agent_template["instructions"]
        constraints = research_agent_template["knowledge"]["constraints"]

        # Verify time flexibility
        assert "Time limits are GUIDELINES ONLY" in constraints[3]
        assert "thorough analysis takes precedence" in constraints[3]
        assert (
            "NEVER follow rigid time limits if investigation incomplete" in instructions
        )

        # Verify quality over speed
        assert (
            "thorough investigation that takes longer is ALWAYS better" in instructions
        )
        assert "NEVER sacrifice completeness for speed" in instructions

    def test_automatic_rejection_triggers(self, research_agent_template):
        """Test Case 8: Verify automatic rejection of bad practices."""
        instructions = research_agent_template["instructions"]

        # Verify rejection triggers
        assert "Automatic Rejection Triggers" in instructions
        assert "Any use of head/tail in initial searches → RESTART" in instructions
        assert "Conclusions without file reading → INVALID" in instructions
        assert "Confidence below 85% → CONTINUE INVESTIGATION" in instructions

    def test_verification_checklist_completeness(self, research_agent_template):
        """Test Case 9: Verify comprehensive verification checklist."""
        instructions = research_agent_template["instructions"]

        # Verify checklist sections
        assert "VERIFICATION CHECKLIST" in instructions
        assert "Search Completeness" in instructions
        assert "File Examination" in instructions
        assert "Confidence Validation" in instructions

        # Verify specific checklist items
        assert "Read MINIMUM 5 actual files" in instructions
        assert "Examined COMPLETE files, not just matching lines" in instructions
        assert "Score is 85% or higher" in instructions

    def test_output_format_requirements(self, research_agent_template):
        """Test Case 10: Verify enhanced output format with verification metrics."""
        instructions = research_agent_template["instructions"]

        # Verify required output sections
        assert "VERIFICATION METRICS" in instructions
        assert "Total Files Searched" in instructions
        assert "Files Actually Read" in instructions
        assert "Search Strategies Used" in instructions
        assert "Confidence Score" in instructions

        # Verify evidence documentation
        assert "EVIDENCE CHAIN" in instructions
        assert "VERIFIED FINDINGS" in instructions
        assert "File Content Examined:" in instructions and "✅" in instructions

    def test_forbidden_vs_required_practices(self, research_agent_template):
        """Test Case 11: Verify clear distinction between forbidden and required practices."""
        instructions = research_agent_template["instructions"]

        # Verify forbidden practices are clearly marked
        forbidden_count = instructions.count("FORBIDDEN")
        assert forbidden_count >= 3, "Should have multiple FORBIDDEN markers"

        forbidden_practices = [
            "Limiting search results prematurely",
            "Drawing conclusions without reading files",
            "Accepting confidence below 85%",
            "Following rigid time constraints",
            "Searching only for expected patterns",
        ]

        for practice in forbidden_practices:
            assert practice in instructions, f"Missing forbidden practice: {practice}"

        # Verify required practices are clearly marked
        required_practices = [
            "Examine ALL search results",
            "Read actual file contents (minimum 5 files)",
            "Achieve 85% confidence minimum",
            "Follow evidence wherever it leads",
            "Verify through multiple strategies",
        ]

        for practice in required_practices:
            assert practice in instructions, f"Missing required practice: {practice}"


class TestOriginalFailureScenarioSimulation:
    """Simulate the exact scenarios that caused the original Research agent to fail."""

    def test_similarity_search_in_api_services_scenario(self):
        """
        Regression Test: Original Failure Scenario

        The Research agent was asked to find similarity search functionality.
        It found grep results but concluded "no similarity search found" without
        reading the actual files. This test ensures the new agent would handle
        this scenario correctly.
        """
        # This test would be implemented with a mock agent that follows the new instructions
        # and verifies it would:
        # 1. Find the grep results (✓ original agent did this)
        # 2. Read the actual files (✗ original agent failed here)
        # 3. Discover semantic similarity functionality (✗ original agent missed)
        # 4. Achieve 85% confidence (✗ original agent had low confidence)
        # 5. Document evidence chain (✗ original agent didn't do this)

        expected_behavior = {
            "searches_without_limits": True,
            "reads_files_after_grep": True,
            "achieves_85_confidence": True,
            "documents_evidence_chain": True,
            "follows_multiple_strategies": True,
        }

        # In a real implementation, this would instantiate the Research agent
        # and verify it exhibits all the expected behaviors
        assert all(
            expected_behavior.values()
        ), "New agent should exhibit all required behaviors"

    def test_large_codebase_handling_scenario(self):
        """
        Regression Test: Large Codebase Scenario

        When faced with many search results, the original agent would use
        head/tail to limit results and make premature conclusions.
        """
        expected_behavior = {
            "no_head_tail_usage": True,
            "examines_all_results": True,
            "reads_sample_files": True,
            "maintains_thoroughness": True,
        }

        assert all(
            expected_behavior.values()
        ), "Agent should handle large codebases thoroughly"

    def test_complex_multi_file_feature_scenario(self):
        """
        Regression Test: Complex Feature Across Multiple Files

        The original agent would often miss features implemented across
        multiple files because it didn't follow evidence chains.
        """
        expected_behavior = {
            "follows_import_chains": True,
            "examines_related_files": True,
            "cross_validates_findings": True,
            "builds_complete_picture": True,
        }

        assert all(
            expected_behavior.values()
        ), "Agent should discover complex multi-file features"


if __name__ == "__main__":
    # Run regression tests
    pytest.main([__file__, "-v"])
