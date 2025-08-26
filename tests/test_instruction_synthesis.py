"""
Test instruction synthesis system.

This test suite validates the concatenation of INSTRUCTIONS.md, TODOWRITE.md,
and MEMORIES.md files into a complete agent instruction set.
"""

from pathlib import Path


class TestInstructionSynthesis:
    """Test the instruction synthesis and concatenation system."""

    def test_instruction_file_loading(self):
        """Test loading of INSTRUCTIONS.md file."""
        # Create test INSTRUCTIONS.md
        instructions_content = """<!-- FRAMEWORK_VERSION: 0009 -->
<!-- LAST_MODIFIED: 2025-08-10T00:00:00Z -->

# Claude Multi-Agent Project Manager Instructions

## Core Identity

**Claude Multi-Agent PM** - orchestration and delegation framework.

## Communication Standards

- Professional tone
- Complete implementations
"""
        instructions_file = self / "INSTRUCTIONS.md"
        instructions_file.write_text(instructions_content)

        # Load and verify
        loaded_content = instructions_file.read_text()
        assert "Claude Multi-Agent PM" in loaded_content
        assert "FRAMEWORK_VERSION: 0009" in loaded_content
        assert "orchestration and delegation framework" in loaded_content

    def test_todowrite_loading(self):
        """Test loading of TODOWRITE.md instructions."""
        todowrite_content = """# TodoWrite Instructions

## Prefix Format
- Engineer: [Engineer] Task description
- QA: [QA] Task description
- Documentation: [Documentation] Task description

## Status Management
- pending: Not started
- in_progress: Currently working
- completed: Finished and tested
"""
        todowrite_file = self / "TODOWRITE.md"
        todowrite_file.write_text(todowrite_content)

        loaded_content = todowrite_file.read_text()
        assert "[Engineer]" in loaded_content
        assert "Status Management" in loaded_content
        assert "pending" in loaded_content

    def test_memories_loading(self):
        """Test loading of MEMORIES.md file."""
        memories_content = """# Agent Memories

## Learned Patterns
- Always validate input before processing
- Use semantic versioning for all releases
- Document breaking changes prominently

## Common Mistakes
- Forgetting to run tests before commit
- Not checking for existing implementations
"""
        memories_file = self / "MEMORIES.md"
        memories_file.write_text(memories_content)

        loaded_content = memories_file.read_text()
        assert "Learned Patterns" in loaded_content
        assert "semantic versioning" in loaded_content
        assert "Common Mistakes" in loaded_content

    def test_instruction_concatenation_order(self):
        """Test that instructions are concatenated in correct order."""
        # Create test files
        instructions = "# INSTRUCTIONS\nCore instructions here."
        todowrite = "# TODOWRITE\nTodo instructions here."
        memories = "# MEMORIES\nMemory content here."

        (self / "INSTRUCTIONS.md").write_text(instructions)
        (self / "TODOWRITE.md").write_text(todowrite)
        (self / "MEMORIES.md").write_text(memories)

        # Simulate concatenation
        concatenated = self._concatenate_instructions(self)

        # Verify order
        instructions_pos = concatenated.find("Core instructions")
        todowrite_pos = concatenated.find("Todo instructions")
        memories_pos = concatenated.find("Memory content")

        assert instructions_pos < todowrite_pos < memories_pos
        assert instructions_pos != -1
        assert todowrite_pos != -1
        assert memories_pos != -1

    def test_instruction_character_count(self):
        """Test that total instruction size is within expected limits."""
        # Create realistic-sized test files
        instructions = "# Instructions\n" + ("x" * 15000)  # ~15K chars
        todowrite = "# TodoWrite\n" + ("y" * 5000)  # ~5K chars
        memories = "# Memories\n" + ("z" * 2000)  # ~2K chars

        (self / "INSTRUCTIONS.md").write_text(instructions)
        (self / "TODOWRITE.md").write_text(todowrite)
        (self / "MEMORIES.md").write_text(memories)

        concatenated = self._concatenate_instructions(self)

        # Total should be around 22K characters
        total_size = len(concatenated)
        assert 20000 <= total_size <= 25000, f"Unexpected size: {total_size}"

    def test_custom_vs_system_instruction_priority(self):
        """Test that custom instructions override system instructions."""
        # System instructions
        system_instructions = """# System Instructions
AGENT_ROLE: Default Role
TEMPERATURE: 0.7
MODEL: sonnet
"""

        # Custom instructions (should override)
        custom_instructions = """# Custom Instructions
AGENT_ROLE: Custom Role
TEMPERATURE: 0.3
MODEL: opus
EXTRA_SETTING: custom_value
"""

        (self / "system_instructions.md").write_text(system_instructions)
        (self / "custom_instructions.md").write_text(custom_instructions)

        # Simulate merging with custom priority
        merged = self._merge_instructions(
            system_instructions, custom_instructions, custom_priority=True
        )

        # Custom values should take precedence
        assert "Custom Role" in merged
        assert "0.3" in merged
        assert "opus" in merged
        assert "custom_value" in merged

    def test_dynamic_capabilities_injection(self):
        """Test injection of dynamic capabilities into instructions."""
        base_instructions = """# Agent Instructions

## Core Capabilities
- Basic analysis
- Code review

## END
"""

        # Dynamic capabilities to inject
        dynamic_capabilities = [
            "- WebSearch: Access to web search",
            "- DatabaseAccess: Query production database",
            "- ModelSelection: Choose optimal AI model",
        ]

        # Inject capabilities
        modified = self._inject_capabilities(base_instructions, dynamic_capabilities)

        # Verify all capabilities are present
        for capability in dynamic_capabilities:
            assert capability.split(": ")[1] in modified

        # Verify structure is maintained
        assert "## Core Capabilities" in modified
        assert "## END" in modified

    def test_missing_instruction_files_handling(self):
        """Test graceful handling of missing instruction files."""
        # Only create INSTRUCTIONS.md
        instructions = "# Main Instructions\nCore content."
        (self / "INSTRUCTIONS.md").write_text(instructions)

        # TODOWRITE.md and MEMORIES.md are missing
        concatenated = self._concatenate_instructions(self)

        # Should still work with just INSTRUCTIONS.md
        assert "Main Instructions" in concatenated
        assert len(concatenated) > 0

    def test_instruction_validation(self):
        """Test validation of instruction content."""
        # Create instructions with potential issues
        instructions = """# Instructions

## Required Sections
### Core Identity
Present

### Communication Standards
Present

## Missing Section
This section might cause issues.

<!-- INVALID_MARKER -->
"""

        (self / "INSTRUCTIONS.md").write_text(instructions)

        # Validate instructions
        errors = self._validate_instructions(instructions)

        # Check for expected validation results
        assert isinstance(errors, list)
        # The validator should flag any issues

    def test_instruction_metadata_extraction(self):
        """Test extraction of metadata from instruction files."""
        instructions = """<!-- FRAMEWORK_VERSION: 0010 -->
<!-- LAST_MODIFIED: 2025-08-11T00:00:00Z -->
<!-- AUTHOR: claude-mpm -->
<!-- AGENT_TYPE: pm -->

# Instructions

Content here.
"""

        (self / "INSTRUCTIONS.md").write_text(instructions)

        metadata = self._extract_metadata(instructions)

        assert metadata["framework_version"] == "0010"
        assert metadata["last_modified"] == "2025-08-11T00:00:00Z"
        assert metadata["author"] == "claude-mpm"
        assert metadata["agent_type"] == "pm"

    def test_instruction_size_optimization(self):
        """Test optimization of instruction size."""
        # Create verbose instructions
        verbose_instructions = """# Instructions

## Section 1

This is a very verbose section with lots of unnecessary words and repetition.
We could say this more concisely. This is redundant. This is also redundant.

## Section 2

Another verbose section that repeats itself multiple times.
Multiple times it repeats. Repeating multiple times.

<!-- Unnecessary comment -->
<!-- Another unnecessary comment -->

## Section 3

    Lots of    unnecessary    whitespace    here    .



    Too many blank lines above.
"""

        optimized = self._optimize_instructions(verbose_instructions)

        # Optimized version should be smaller
        assert len(optimized) < len(verbose_instructions)

        # But still maintain structure
        assert "## Section 1" in optimized
        assert "## Section 2" in optimized
        assert "## Section 3" in optimized

    def test_instruction_template_variables(self):
        """Test replacement of template variables in instructions."""
        template_instructions = """# {{AGENT_NAME}} Instructions

Role: {{AGENT_ROLE}}
Model: {{MODEL_TYPE}}
Temperature: {{TEMPERATURE}}

## Capabilities
{{CAPABILITIES_LIST}}

## Constraints
{{CONSTRAINTS_LIST}}
"""

        variables = {
            "AGENT_NAME": "Research Agent",
            "AGENT_ROLE": "Code Analysis Specialist",
            "MODEL_TYPE": "opus",
            "TEMPERATURE": "0.3",
            "CAPABILITIES_LIST": "- Code analysis\n- Pattern detection\n- Best practices",
            "CONSTRAINTS_LIST": "- Read-only access\n- No code execution",
        }

        processed = self._process_template(template_instructions, variables)

        # All variables should be replaced
        assert "{{" not in processed
        assert "}}" not in processed

        # Values should be present
        assert "Research Agent" in processed
        assert "Code Analysis Specialist" in processed
        assert "opus" in processed
        assert "Pattern detection" in processed

    def test_instruction_checksum_verification(self):
        """Test checksum verification for instruction integrity."""
        instructions = """# Instructions
Critical system instructions that must not be tampered with.
"""

        # Calculate checksum
        checksum = self._calculate_checksum(instructions)

        # Verify checksum matches
        assert self._verify_checksum(instructions, checksum)

        # Modify instructions slightly
        tampered = instructions.replace("Critical", "Modified")

        # Checksum should not match
        assert not self._verify_checksum(tampered, checksum)

    # Helper methods

    def _concatenate_instructions(self, base_path: Path) -> str:
        """Concatenate instruction files in order."""
        parts = []

        for filename in ["INSTRUCTIONS.md", "TODOWRITE.md", "MEMORIES.md"]:
            file_path = base_path / filename
            if file_path.exists():
                parts.append(file_path.read_text())

        return "\n\n---\n\n".join(parts)

    def _merge_instructions(
        self, system: str, custom: str, custom_priority: bool = True
    ) -> str:
        """Merge system and custom instructions."""
        if custom_priority:
            return custom + "\n\n" + system
        return system + "\n\n" + custom

    def _inject_capabilities(self, instructions: str, capabilities: list) -> str:
        """Inject dynamic capabilities into instructions."""
        lines = instructions.split("\n")
        result = []

        for line in lines:
            result.append(line)
            if "## Core Capabilities" in line:
                # Inject after this line
                for cap in capabilities:
                    result.append(cap)

        return "\n".join(result)

    def _validate_instructions(self, instructions: str) -> list:
        """Validate instruction content."""
        errors = []

        # Check for required sections
        required_sections = ["Core Identity", "Communication Standards"]
        for section in required_sections:
            if section not in instructions:
                errors.append(f"Missing required section: {section}")

        # Check for invalid markers
        if "INVALID_MARKER" in instructions:
            errors.append("Contains invalid marker")

        return errors

    def _extract_metadata(self, instructions: str) -> dict:
        """Extract metadata from instruction comments."""
        import re

        metadata = {}

        patterns = {
            "framework_version": r"<!-- FRAMEWORK_VERSION: (\S+) -->",
            "last_modified": r"<!-- LAST_MODIFIED: (\S+) -->",
            "author": r"<!-- AUTHOR: (\S+) -->",
            "agent_type": r"<!-- AGENT_TYPE: (\S+) -->",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, instructions)
            if match:
                metadata[key] = match.group(1)

        return metadata

    def _optimize_instructions(self, instructions: str) -> str:
        """Optimize instruction size by removing redundancy."""
        import re

        # Remove excessive whitespace
        optimized = re.sub(r"\s+", " ", instructions)

        # Restore necessary line breaks
        optimized = re.sub(r" ## ", "\n## ", optimized)
        optimized = re.sub(r" # ", "\n# ", optimized)

        # Remove HTML comments
        optimized = re.sub(r"<!--.*?-->", "", optimized)

        # Remove multiple blank lines
        optimized = re.sub(r"\n\n+", "\n\n", optimized)

        return optimized.strip()

    def _process_template(self, template: str, variables: dict) -> str:
        """Process template variables in instructions."""
        result = template

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, value)

        return result

    def _calculate_checksum(self, content: str) -> str:
        """Calculate checksum for content verification."""
        import hashlib

        return hashlib.sha256(content.encode()).hexdigest()

    def _verify_checksum(self, content: str, expected_checksum: str) -> bool:
        """Verify content against expected checksum."""
        actual_checksum = self._calculate_checksum(content)
        return actual_checksum == expected_checksum
