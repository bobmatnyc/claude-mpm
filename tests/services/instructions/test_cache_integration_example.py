"""Integration example showing how InstructionCacheService will be used.

This demonstrates the new content-based API for caching assembled instructions.
"""

import tempfile
from pathlib import Path

from claude_mpm.services.instructions.instruction_cache_service import (
    InstructionCacheService,
)


def test_cache_assembled_instruction_workflow():
    """Example workflow showing how caller assembles and caches instructions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)

        # Step 1: Caller assembles the complete instruction (this happens elsewhere)
        # This would be done by agent_deployment.py or interactive_session.py
        base_pm = "# BASE PM Instructions\n\nCore PM guidelines..."
        pm_instructions = "\n\n# PM Instructions\n\nProject-specific PM guidance..."
        workflow = "\n\n# Workflow\n\nTicket management workflow..."
        capabilities = (
            "\n\n# Agent Capabilities\n\n- Research Agent\n- Engineer Agent..."
        )
        temporal_context = "\n\n# Temporal Context\n\nCurrent date: 2025-11-30..."

        # Assemble complete instruction
        assembled_instruction = (
            base_pm + pm_instructions + workflow + capabilities + temporal_context
        )

        # Step 2: Initialize cache service
        cache_service = InstructionCacheService(project_root=project_root)

        # Step 3: Update cache with assembled content
        result = cache_service.update_cache(instruction_content=assembled_instruction)

        assert result["updated"] is True
        assert result["reason"] == "content_changed"
        assert "content_hash" in result
        assert "content_size_kb" in result

        # Step 4: Get cache file path to pass to Claude Code
        cache_file = cache_service.get_cache_path()
        assert cache_file.exists()

        # This path would be passed to Claude Code via --system-prompt-file
        # Example: claude --system-prompt-file {cache_file} ...

        # Step 5: Verify cache content matches
        cached_content = cache_file.read_text()
        assert cached_content == assembled_instruction

        # Step 6: Second call with same content skips update (performance optimization)
        result2 = cache_service.update_cache(instruction_content=assembled_instruction)
        assert result2["updated"] is False
        assert result2["reason"] == "cache_valid"

        # Step 7: Update with new content (e.g., temporal context changed)
        new_temporal = "\n\n# Temporal Context\n\nCurrent date: 2025-12-01..."
        updated_instruction = (
            base_pm + pm_instructions + workflow + capabilities + new_temporal
        )

        result3 = cache_service.update_cache(instruction_content=updated_instruction)
        assert result3["updated"] is True
        assert result3["reason"] == "content_changed"

        # Cache now has updated content
        cached_content_new = cache_file.read_text()
        assert cached_content_new == updated_instruction
        assert cached_content_new != cached_content


def test_cache_metadata_structure():
    """Verify cache metadata includes all required fields."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)

        cache_service = InstructionCacheService(project_root=project_root)

        # Create cache
        content = "# Assembled Instruction\n\nComplete instruction content..."
        cache_service.update_cache(instruction_content=content)

        # Verify metadata
        info = cache_service.get_cache_info()

        assert info["cache_exists"] is True
        assert info["content_type"] == "assembled_instruction"
        assert "content_hash" in info
        assert "content_size_bytes" in info
        assert "components" in info
        assert "cached_at" in info

        # Verify components list
        assert "BASE_PM.md" in info["components"]
        assert "PM_INSTRUCTIONS.md" in info["components"]
        assert "WORKFLOW.md" in info["components"]
        assert "agent_capabilities" in info["components"]
        assert "temporal_context" in info["components"]
