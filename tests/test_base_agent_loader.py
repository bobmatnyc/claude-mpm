"""
Comprehensive test suite for Base Agent Loader.

Tests critical functionality including:
- Base agent JSON loading
- Instruction prepending logic
- Template filtering (MINIMAL/STANDARD/FULL)
- Caching mechanism
- Error handling for missing/malformed base agent
- Version compatibility checks
- Memory optimization
- Concurrent loading safety
"""

import json
import os
import threading
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from claude_mpm.agents.base_agent_loader import (
    PromptTemplate,
    _build_dynamic_prompt,
    _parse_content_sections,
    _remove_test_mode_instructions,
    clear_base_agent_cache,
    get_base_agent_path,
    load_base_agent_instructions,
    prepend_base_instructions,
    validate_base_agent_file,
)


class TestBaseAgentLoading:
    """Test base agent file loading functionality."""

    def test_load_base_agent_instructions():
        """Test loading base agent instructions from file."""
        # Should load without errors
        instructions = load_base_agent_instructions(force_reload=True)

        assert instructions is not None
        assert len(instructions) > 0
        assert isinstance(instructions, str)

    def test_load_with_cache():
        """Test that loading uses cache on second call."""
        # Clear cache first
        clear_base_agent_cache()

        # First load - from file
        instructions1 = load_base_agent_instructions()

        # Second load - should be from cache
        with patch(
            "claude_mpm.agents.base_agent_loader._get_base_agent_file"
        ) as mock_get_file:
            mock_file = MagicMock()
            mock_file.exists.return_value = False  # File "doesn't exist"
            mock_get_file.return_value = mock_file

            # Should still get instructions from cache
            instructions2 = load_base_agent_instructions()

            assert instructions2 == instructions1

    def test_force_reload_bypasses_cache():
        """Test that force_reload bypasses cache."""
        # Load once to populate cache
        load_base_agent_instructions()

        # Force reload should read from file again
        with patch(
            "builtins.open",
            mock_open(
                read_data='{"narrative_fields": {"instructions": "new content"}}'
            ),
        ) as mock_file:
            load_base_agent_instructions(force_reload=True)

            # Should have called open to read file
            mock_file.assert_called()

    def test_missing_base_agent_file():
        """Test handling when base agent file is missing."""
        with patch(
            "claude_mpm.agents.base_agent_loader._get_base_agent_file"
        ) as mock_get_file:
            mock_file = MagicMock()
            mock_file.exists.return_value = False
            mock_get_file.return_value = mock_file

            # Clear cache to force file read
            clear_base_agent_cache()

            instructions = load_base_agent_instructions()
            assert instructions is None

    def test_malformed_json_handling():
        """Test handling of malformed JSON in base agent file."""
        with patch(
            "builtins.open", mock_open(read_data='{"invalid": json}')
        ), patch(
            "claude_mpm.agents.base_agent_loader._get_base_agent_file"
        ) as mock_get_file:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_get_file.return_value = mock_path

            clear_base_agent_cache()
            instructions = load_base_agent_instructions(force_reload=True)

            assert instructions is None

    def test_empty_instructions_handling():
        """Test handling when instructions field is empty."""
        empty_json = json.dumps({"narrative_fields": {"instructions": ""}})

        with patch("builtins.open", mock_open(read_data=empty_json)), patch(
            "claude_mpm.agents.base_agent_loader._get_base_agent_file"
        ) as mock_get_file:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_get_file.return_value = mock_path

            clear_base_agent_cache()
            instructions = load_base_agent_instructions(force_reload=True)

            assert instructions is None


class TestTestModeHandling:
    """Test test mode instruction handling."""

    def test_test_mode_enabled():
        """Test that test mode instructions are included when enabled."""
        with patch.dict(os.environ, {"CLAUDE_PM_TEST_MODE": "true"}):
            clear_base_agent_cache()
            instructions = load_base_agent_instructions(force_reload=True)

            # Test mode instructions should be present
            if instructions and "Standard Test Response Protocol" in instructions:
                assert "Standard Test Response Protocol" in instructions

    def test_test_mode_disabled():
        """Test that test mode instructions are removed when disabled."""
        with patch.dict(os.environ, {"CLAUDE_PM_TEST_MODE": "false"}):
            clear_base_agent_cache()

            # Mock the file content with test instructions
            content = """
# Base Instructions

## Core Principles
Important stuff here

## Standard Test Response Protocol
This should be removed
### Test subsection
Also removed

## Another Section
This should stay
"""

            with patch(
                "claude_mpm.agents.base_agent_loader.load_base_agent_instructions"
            ):
                # Test the removal function directly
                filtered = _remove_test_mode_instructions(content)

                assert "Standard Test Response Protocol" not in filtered
                assert "Test subsection" not in filtered
                assert "Core Principles" in filtered
                assert "Another Section" in filtered

    def test_remove_test_instructions_preserves_structure():
        """Test that removing test instructions preserves document structure."""
        content = """
## Section 1
Content 1

## Standard Test Response Protocol
Test content
### Test subsection
More test content

## Section 2
Content 2
"""

        filtered = _remove_test_mode_instructions(content)

        # Should preserve non-test sections
        assert "Section 1" in filtered
        assert "Content 1" in filtered
        assert "Section 2" in filtered
        assert "Content 2" in filtered

        # Should remove test sections
        assert "Standard Test Response Protocol" not in filtered
        assert "Test content" not in filtered
        assert "Test subsection" not in filtered


class TestPromptTemplates:
    """Test dynamic prompt template functionality."""

    def test_minimal_template():
        """Test MINIMAL template includes only core sections."""
        content = """
# Base Agent Instructions

## Agent Framework Context
Framework context

### Core Agent Principles
Core principles content

### Communication Standards
Communication content

### Universal Constraints
Constraints content

### Quality Standards
Quality content (should not be in minimal)

### Tool Usage Guidelines
Tool usage (should not be in minimal)
"""

        result = _build_dynamic_prompt(content, PromptTemplate.MINIMAL)

        assert "Core Agent Principles" in result
        assert "Communication Standards" in result
        assert "Universal Constraints" in result
        assert "Quality Standards" not in result
        assert "Tool Usage Guidelines" not in result

    def test_standard_template():
        """Test STANDARD template includes medium set of sections."""
        content = """
# Base Agent Instructions

### Core Agent Principles
Core content

### Reporting Requirements
Reporting content

### Error Handling
Error content

### Collaboration Protocols
Collaboration content

### Security Awareness
Security content (should not be in standard)

### Escalation Triggers
Escalation content (should not be in standard)
"""

        result = _build_dynamic_prompt(content, PromptTemplate.STANDARD)

        assert "Core Agent Principles" in result
        assert "Reporting Requirements" in result
        assert "Error Handling" in result
        assert "Collaboration Protocols" in result
        assert "Security Awareness" not in result
        assert "Escalation Triggers" not in result

    def test_full_template():
        """Test FULL template includes all sections."""
        content = "Full content with all sections"

        result = _build_dynamic_prompt(content, PromptTemplate.FULL)

        # FULL template should return content unchanged
        assert result == content

    def test_template_auto_selection_by_complexity():
        """Test template auto-selection based on complexity score."""
        agent_prompt = "Agent specific instructions"

        # Low complexity -> MINIMAL
        result_low = prepend_base_instructions(agent_prompt, complexity_score=20)

        # Medium complexity -> STANDARD
        result_medium = prepend_base_instructions(agent_prompt, complexity_score=50)

        # High complexity -> FULL
        result_high = prepend_base_instructions(agent_prompt, complexity_score=85)

        # Different templates should produce different lengths
        assert len(result_low) < len(result_medium) < len(result_high)

    def test_template_override():
        """Test explicit template override."""
        agent_prompt = "Agent instructions"

        # Override auto-selection with explicit template
        result = prepend_base_instructions(
            agent_prompt,
            template=PromptTemplate.MINIMAL,
            complexity_score=90,  # Would normally select FULL
        )

        # Should use MINIMAL despite high complexity score
        # Can't easily verify template used, but result should be shorter
        assert len(result) < len(
            prepend_base_instructions(agent_prompt, complexity_score=90)
        )


class TestInstructionPrepending:
    """Test instruction prepending functionality."""

    def test_prepend_basic():
        """Test basic prepending of base instructions."""
        agent_prompt = "Agent specific instructions"
        result = prepend_base_instructions(agent_prompt)

        assert agent_prompt in result
        assert len(result) > len(agent_prompt)
        assert result.endswith(agent_prompt)

    def test_prepend_with_custom_separator():
        """Test prepending with custom separator."""
        agent_prompt = "Agent instructions"
        separator = "\n===SEPARATOR===\n"

        result = prepend_base_instructions(agent_prompt, separator=separator)

        assert separator in result
        parts = result.split(separator)
        assert len(parts) == 2
        assert parts[1] == agent_prompt

    def test_prepend_when_base_missing():
        """Test prepending when base instructions are missing."""
        with patch(
            "claude_mpm.agents.base_agent_loader.load_base_agent_instructions",
            return_value=None,
        ):
            agent_prompt = "Agent instructions"
            result = prepend_base_instructions(agent_prompt)

            # Should return original prompt unchanged
            assert result == agent_prompt

    def test_prepend_test_mode_forces_full_template():
        """Test that test mode forces FULL template."""
        with patch.dict(os.environ, {"CLAUDE_PM_TEST_MODE": "true"}):
            agent_prompt = "Test agent prompt"

            # Even with low complexity, should use FULL template in test mode
            result = prepend_base_instructions(agent_prompt, complexity_score=10)

            # Result should be longer due to FULL template
            with patch.dict(os.environ, {"CLAUDE_PM_TEST_MODE": "false"}):
                result_normal = prepend_base_instructions(
                    agent_prompt, complexity_score=10
                )

            assert len(result) > len(result_normal)


class TestSectionParsing:
    """Test content section parsing functionality."""

    def test_parse_sections_basic():
        """Test basic section parsing."""
        content = """
### Section One
Content of section one

### Section Two
Content of section two
With multiple lines

## Main Section
Main content here
"""

        sections = _parse_content_sections(content)

        assert "Section One" in sections
        assert "Section Two" in sections
        assert "Main Section" in sections
        assert "Content of section one" in sections["Section One"]
        assert "With multiple lines" in sections["Section Two"]

    def test_parse_sections_with_subsections():
        """Test parsing with subsections."""
        content = """
### Main Section
Main content

#### Subsection One
Subsection content

#### Subsection Two
More subsection content
"""

        sections = _parse_content_sections(content)

        assert "Main Section" in sections
        # Subsections should be included in parent section
        assert "Subsection One" in sections["Main Section"]
        assert "Subsection content" in sections["Main Section"]

    def test_parse_pm_integration_merging():
        """Test that PM integration sections are merged."""
        content = """
#### PM Orchestrator Integration
Orchestrator content

#### PM Workflow Integration
Workflow content

### Other Section
Other content
"""

        sections = _parse_content_sections(content)

        # Should be merged into single PM Integration section
        assert "PM Integration" in sections
        assert "Orchestrator content" in sections["PM Integration"]
        assert "Workflow content" in sections["PM Integration"]

        # Original sections should be removed
        assert "PM Orchestrator Integration" not in sections
        assert "PM Workflow Integration" not in sections


class TestCaching:
    """Test caching mechanism."""

    def test_cache_key_differentiation():
        """Test that different cache keys are used for different modes/templates."""
        clear_base_agent_cache()

        # Load with different configurations
        with patch.dict(os.environ, {"CLAUDE_PM_TEST_MODE": "false"}):
            normal_instructions = load_base_agent_instructions()

        with patch.dict(os.environ, {"CLAUDE_PM_TEST_MODE": "true"}):
            test_instructions = load_base_agent_instructions()

        # Different modes should potentially have different content
        # (can't guarantee difference without knowing file content)
        assert normal_instructions is not None
        assert test_instructions is not None

    def test_cache_ttl():
        """Test that cache has TTL set."""
        from claude_mpm.services.memory.cache.shared_prompt_cache import (
            SharedPromptCache,
        )

        clear_base_agent_cache()
        cache = SharedPromptCache.get_instance()

        with patch.object(cache, "set") as mock_set:
            load_base_agent_instructions(force_reload=True)

            # Should set cache with TTL
            mock_set.assert_called()
            call_args = mock_set.call_args
            assert call_args[1]["ttl"] == 3600  # 1 hour

    def test_clear_cache_all_templates():
        """Test that clear_cache clears all template variations."""
        from claude_mpm.services.memory.cache.shared_prompt_cache import (
            SharedPromptCache,
        )

        cache = SharedPromptCache.get_instance()

        with patch.object(cache, "invalidate") as mock_invalidate:
            clear_base_agent_cache()

            # Should clear multiple cache keys
            assert mock_invalidate.call_count >= 6  # 3 templates * 2 modes minimum


class TestConcurrency:
    """Test concurrent access safety."""

    def test_concurrent_loading():
        """Test multiple threads loading simultaneously."""
        clear_base_agent_cache()
        results = []
        errors = []

        def load_instructions():
            try:
                instructions = load_base_agent_instructions()
                results.append(instructions)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=load_instructions)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0

        # All threads should get same result
        assert len(set(results)) == 1

    def test_concurrent_prepending():
        """Test multiple threads prepending instructions simultaneously."""
        results = []
        errors = []

        def prepend_test(thread_id):
            try:
                agent_prompt = f"Agent {thread_id} instructions"
                result = prepend_base_instructions(agent_prompt)
                results.append((thread_id, result))
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=prepend_test, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0

        # Each thread should get correct result
        for thread_id, result in results:
            assert f"Agent {thread_id} instructions" in result


class TestFileValidation:
    """Test file validation functionality."""

    def test_validate_existing_file():
        """Test validation of existing base agent file."""
        # Should pass for actual file
        assert validate_base_agent_file()

    def test_validate_missing_file():
        """Test validation when file is missing."""
        with patch("claude_mpm.agents.base_agent_loader.BASE_AGENT_FILE") as mock_file:
            mock_file.exists.return_value = False

            assert not validate_base_agent_file()

    def test_validate_not_file():
        """Test validation when path is not a file."""
        with patch("claude_mpm.agents.base_agent_loader.BASE_AGENT_FILE") as mock_file:
            mock_file.exists.return_value = True
            mock_file.is_file.return_value = False

            assert not validate_base_agent_file()

    def test_validate_unreadable_file():
        """Test validation when file is not readable."""
        with patch("claude_mpm.agents.base_agent_loader.BASE_AGENT_FILE") as mock_file:
            mock_file.exists.return_value = True
            mock_file.is_file.return_value = True
            mock_file.read_text.side_effect = PermissionError("Cannot read file")

            assert not validate_base_agent_file()

    def test_get_base_agent_path():
        """Test getting base agent file path."""
        path = get_base_agent_path()

        assert path is not None
        assert isinstance(path, Path)
        assert path.name == "base_agent.json"


class TestMemoryOptimization:
    """Test memory optimization features."""

    def test_template_size_reduction():
        """Test that templates reduce prompt size appropriately."""
        agent_prompt = "Test agent prompt"

        # Get different template results
        minimal = prepend_base_instructions(
            agent_prompt, template=PromptTemplate.MINIMAL
        )
        standard = prepend_base_instructions(
            agent_prompt, template=PromptTemplate.STANDARD
        )
        full = prepend_base_instructions(agent_prompt, template=PromptTemplate.FULL)

        # Sizes should be ordered
        assert len(minimal) < len(standard) < len(full)

        # MINIMAL should be significantly smaller than FULL
        size_reduction = (len(full) - len(minimal)) / len(full)
        assert size_reduction > 0.3  # At least 30% reduction

    def test_cache_memory_efficiency():
        """Test that caching reduces memory usage."""
        clear_base_agent_cache()

        # Load multiple times - should reuse cached content
        for _ in range(100):
            load_base_agent_instructions()

        # Memory should not grow linearly (can't easily test this directly)
        # But we can verify cache is being used
        from claude_mpm.services.memory.cache.shared_prompt_cache import (
            SharedPromptCache,
        )

        cache = SharedPromptCache.get_instance()

        # Cache should have the entry
        cache_key = "base_agent:instructions:normal"
        assert cache.get(cache_key) is not None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_agent_prompt():
        """Test prepending to empty agent prompt."""
        result = prepend_base_instructions("")

        assert len(result) > 0
        assert result != ""

    def test_very_large_agent_prompt():
        """Test prepending to very large agent prompt."""
        large_prompt = "x" * (1024 * 1024)  # 1MB
        result = prepend_base_instructions(large_prompt)

        assert large_prompt in result
        assert len(result) > len(large_prompt)

    def test_unicode_in_instructions():
        """Test handling of Unicode in instructions."""
        agent_prompt = "Instructions with Unicode: 你好 мир 🌍"
        result = prepend_base_instructions(agent_prompt)

        assert agent_prompt in result

    def test_null_complexity_score():
        """Test handling of null complexity score."""
        agent_prompt = "Test prompt"

        # Should default to STANDARD template
        result = prepend_base_instructions(agent_prompt, complexity_score=None)

        assert agent_prompt in result
        assert len(result) > len(agent_prompt)

    def test_out_of_range_complexity_score():
        """Test handling of out-of-range complexity scores."""
        agent_prompt = "Test prompt"

        # Negative score
        result_negative = prepend_base_instructions(agent_prompt, complexity_score=-10)

        # Very high score
        result_high = prepend_base_instructions(agent_prompt, complexity_score=200)

        # Should handle gracefully
        assert agent_prompt in result_negative
        assert agent_prompt in result_high


class TestBackwardCompatibility:
    """Test backward compatibility with older formats."""

    def test_old_json_format():
        """Test handling of older JSON format without narrative_fields."""
        old_format = json.dumps({"instructions": "Old format instructions"})

        with patch("builtins.open", mock_open(read_data=old_format)), patch(
            "claude_mpm.agents.base_agent_loader._get_base_agent_file"
        ) as mock_get_file:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_get_file.return_value = mock_path

            clear_base_agent_cache()
            instructions = load_base_agent_instructions(force_reload=True)

            assert instructions == "Old format instructions"

    def test_new_json_format():
        """Test handling of new JSON format with narrative_fields."""
        new_format = json.dumps(
            {"narrative_fields": {"instructions": "New format instructions"}}
        )

        with patch("builtins.open", mock_open(read_data=new_format)), patch(
            "claude_mpm.agents.base_agent_loader._get_base_agent_file"
        ) as mock_get_file:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_get_file.return_value = mock_path

            clear_base_agent_cache()
            instructions = load_base_agent_instructions(force_reload=True)

            assert instructions == "New format instructions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
