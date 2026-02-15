"""Tests for AgentNameNormalizer - Phase 1 fixes for issue #299.

These tests verify:
1. Stripping of -agent/_agent suffix before alias lookup
2. Extended alias coverage for all 48+ agents
3. Proper normalization of various agent name formats
"""

import pytest

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer


class TestAgentSuffixStripping:
    """Tests for stripping -agent and _agent suffixes."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            # -agent suffix stripping (hyphen)
            ("research-agent", "Research"),
            ("engineer-agent", "Engineer"),
            ("qa-agent", "QA"),
            ("security-agent", "Security"),
            ("documentation-agent", "Documentation"),
            ("ops-agent", "Ops"),
            ("python-engineer-agent", "Python Engineer"),
            ("data-engineer-agent", "Data Engineer"),
            # _agent suffix stripping (underscore)
            ("research_agent", "Research"),
            ("engineer_agent", "Engineer"),
            ("qa_agent", "QA"),
            ("security_agent", "Security"),
            ("documentation_agent", "Documentation"),
            ("ops_agent", "Ops"),
            ("python_engineer_agent", "Python Engineer"),
            ("data_engineer_agent", "Data Engineer"),
            # Mixed case with suffix
            ("Research-Agent", "Research"),
            ("ENGINEER_AGENT", "Engineer"),
            # Double suffix (edge case)
            ("research_agent_agent", "Research"),
        ],
    )
    def test_agent_suffix_stripping(self, input_name: str, expected: str) -> None:
        """Test that -agent and _agent suffixes are properly stripped."""
        result = AgentNameNormalizer.normalize(input_name)
        assert result == expected, f"Expected '{expected}', got '{result}'"


class TestExtendedAliases:
    """Tests for extended alias coverage (48+ agents)."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            # Core agents
            ("research", "Research"),
            ("engineer", "Engineer"),
            ("qa", "QA"),
            ("security", "Security"),
            ("documentation", "Documentation"),
            ("ops", "Ops"),
            ("version_control", "Version Control"),
            ("data_engineer", "Data Engineer"),
            ("architect", "Architect"),
            ("pm", "PM"),
            # Language-specific engineers
            ("python_engineer", "Python Engineer"),
            ("python-engineer", "Python Engineer"),
            ("golang_engineer", "Golang Engineer"),
            ("golang-engineer", "Golang Engineer"),
            ("java_engineer", "Java Engineer"),
            ("javascript_engineer", "JavaScript Engineer"),
            ("typescript_engineer", "TypeScript Engineer"),
            ("rust_engineer", "Rust Engineer"),
            ("ruby_engineer", "Ruby Engineer"),
            ("php_engineer", "PHP Engineer"),
            ("phoenix_engineer", "Phoenix Engineer"),
            ("nestjs_engineer", "NestJS Engineer"),
            # Frontend engineers
            ("react_engineer", "React Engineer"),
            ("react-engineer", "React Engineer"),
            ("nextjs_engineer", "NextJS Engineer"),
            ("nextjs-engineer", "NextJS Engineer"),
            ("svelte_engineer", "Svelte Engineer"),
            # Mobile/Desktop engineers
            ("dart_engineer", "Dart Engineer"),
            ("tauri_engineer", "Tauri Engineer"),
            # Specialized engineers
            ("prompt_engineer", "Prompt Engineer"),
            ("refactoring_engineer", "Refactoring Engineer"),
            ("web_ui", "Web UI"),
            ("imagemagick", "ImageMagick"),
            # QA variants
            ("api_qa", "API QA"),
            ("api-qa", "API QA"),
            ("web_qa", "Web QA"),
            ("web-qa", "Web QA"),
            ("real_user", "Real User"),
            # Ops variants
            ("clerk_ops", "Clerk Ops"),
            ("digitalocean_ops", "DigitalOcean Ops"),
            ("gcp_ops", "GCP Ops"),
            ("local_ops", "Local Ops"),
            ("vercel_ops", "Vercel Ops"),
            ("project_organizer", "Project Organizer"),
            ("agentic_coder_optimizer", "Agentic Coder Optimizer"),
            ("tmux", "Tmux"),
            # Universal agents
            ("code_analyzer", "Code Analyzer"),
            ("content", "Content"),
            ("memory_manager", "Memory Manager"),
            ("product_owner", "Product Owner"),
            ("ticketing", "Ticketing"),
            # MPM-specific agents
            ("mpm_agent_manager", "MPM Agent Manager"),
            ("mpm-agent-manager", "MPM Agent Manager"),
            ("mpm_skills_manager", "MPM Skills Manager"),
            ("mpm-skills-manager", "MPM Skills Manager"),
        ],
    )
    def test_extended_aliases(self, input_name: str, expected: str) -> None:
        """Test that all 48+ agent aliases are properly recognized."""
        result = AgentNameNormalizer.normalize(input_name)
        assert result == expected, f"Expected '{expected}', got '{result}'"


class TestShorthandAliases:
    """Tests for shorthand aliases that map to canonical agents."""

    @pytest.mark.parametrize(
        "shorthand,expected",
        [
            # Language shorthands
            ("python", "Python Engineer"),
            ("golang", "Golang Engineer"),
            ("java", "Java Engineer"),
            ("javascript", "JavaScript Engineer"),
            ("typescript", "TypeScript Engineer"),
            ("rust", "Rust Engineer"),
            ("ruby", "Ruby Engineer"),
            ("php", "PHP Engineer"),
            ("phoenix", "Phoenix Engineer"),
            ("nestjs", "NestJS Engineer"),
            # Framework shorthands
            ("react", "React Engineer"),
            ("nextjs", "NextJS Engineer"),
            ("next", "NextJS Engineer"),
            ("svelte", "Svelte Engineer"),
            ("dart", "Dart Engineer"),
            ("flutter", "Dart Engineer"),  # Flutter -> Dart Engineer
            ("tauri", "Tauri Engineer"),
            # Ops shorthands
            ("clerk", "Clerk Ops"),
            ("digitalocean", "DigitalOcean Ops"),
            ("gcp", "GCP Ops"),
            ("local", "Local Ops"),
            ("vercel", "Vercel Ops"),
            # Other shorthands
            ("analyzer", "Code Analyzer"),
            ("po", "Product Owner"),
            ("refactoring", "Refactoring Engineer"),
        ],
    )
    def test_shorthand_aliases(self, shorthand: str, expected: str) -> None:
        """Test that shorthand aliases resolve correctly."""
        result = AgentNameNormalizer.normalize(shorthand)
        assert result == expected, f"Expected '{expected}', got '{result}'"


class TestTavilyResearch:
    """Tests for tavily_research alias (special case)."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("tavily_research", "Research"),
            ("tavily-research", "Research"),
            ("Tavily_Research", "Research"),
        ],
    )
    def test_tavily_research_maps_to_research(
        self, input_name: str, expected: str
    ) -> None:
        """Test that tavily_research maps to Research agent."""
        result = AgentNameNormalizer.normalize(input_name)
        assert result == expected


class TestToKeyFormat:
    """Tests for to_key format conversion."""

    @pytest.mark.parametrize(
        "input_name,expected_key",
        [
            ("Research", "research"),
            ("Python Engineer", "python_engineer"),
            ("python-engineer", "python_engineer"),
            ("python_engineer", "python_engineer"),
            ("Version Control", "version_control"),
            ("MPM Agent Manager", "mpm_agent_manager"),
            ("API QA", "api_qa"),
        ],
    )
    def test_to_key_format(self, input_name: str, expected_key: str) -> None:
        """Test conversion to key format."""
        result = AgentNameNormalizer.to_key(input_name)
        assert result == expected_key


class TestToTaskFormat:
    """Tests for to_task_format conversion (hyphenated lowercase)."""

    @pytest.mark.parametrize(
        "input_name,expected_task_format",
        [
            ("Research", "research"),
            ("Python Engineer", "python-engineer"),
            ("Version Control", "version-control"),
            ("Data Engineer", "data-engineer"),
            ("MPM Agent Manager", "mpm-agent-manager"),
            ("API QA", "api-qa"),
        ],
    )
    def test_to_task_format(self, input_name: str, expected_task_format: str) -> None:
        """Test conversion to task format."""
        result = AgentNameNormalizer.to_task_format(input_name)
        assert result == expected_task_format


class TestFromTaskFormat:
    """Tests for from_task_format conversion."""

    @pytest.mark.parametrize(
        "task_format,expected",
        [
            ("research", "Research"),
            ("python-engineer", "Python Engineer"),
            ("version-control", "Version Control"),
            ("data-engineer", "Data Engineer"),
            ("mpm-agent-manager", "MPM Agent Manager"),
            ("api-qa", "API QA"),
        ],
    )
    def test_from_task_format(self, task_format: str, expected: str) -> None:
        """Test conversion from task format."""
        result = AgentNameNormalizer.from_task_format(task_format)
        assert result == expected


class TestRoundTrip:
    """Tests for round-trip conversion consistency."""

    @pytest.mark.parametrize(
        "canonical_name",
        [
            "Research",
            "Engineer",
            "Python Engineer",
            "Version Control",
            "Data Engineer",
            "API QA",
            "MPM Agent Manager",
        ],
    )
    def test_round_trip_to_task_and_back(self, canonical_name: str) -> None:
        """Test that to_task_format -> from_task_format preserves canonical name."""
        task_format = AgentNameNormalizer.to_task_format(canonical_name)
        result = AgentNameNormalizer.from_task_format(task_format)
        assert result == canonical_name


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_string_defaults_to_engineer(self) -> None:
        """Test that empty string defaults to Engineer."""
        assert AgentNameNormalizer.normalize("") == "Engineer"

    def test_whitespace_only_defaults_to_engineer(self) -> None:
        """Test that whitespace-only string defaults to Engineer."""
        assert AgentNameNormalizer.normalize("   ") == "Engineer"

    def test_unknown_agent_defaults_to_engineer(self) -> None:
        """Test that unknown agent name defaults to Engineer."""
        assert AgentNameNormalizer.normalize("completely_unknown_agent") == "Engineer"

    def test_extra_whitespace_trimmed(self) -> None:
        """Test that extra whitespace is trimmed."""
        assert AgentNameNormalizer.normalize("  research  ") == "Research"

    def test_case_insensitive(self) -> None:
        """Test that normalization is case-insensitive."""
        assert AgentNameNormalizer.normalize("RESEARCH") == "Research"
        assert AgentNameNormalizer.normalize("Research") == "Research"
        assert AgentNameNormalizer.normalize("research") == "Research"
        assert AgentNameNormalizer.normalize("ReSeArCh") == "Research"
