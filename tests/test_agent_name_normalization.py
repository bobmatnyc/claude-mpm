"""Comprehensive tests for agent name normalization across TodoWrite and Task tools.

This test ensures that the agent loader can handle various agent name formats
as used by the PM agent in TodoWrite tasks, including capitalized names,
lowercase names, aliases, and space-separated names.
"""

import logging
import unittest

from claude_mpm.agents.agent_loader import (
    get_agent_prompt,
    get_agent_prompt_with_model_info,
)
from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestAgentNameNormalizer(unittest.TestCase):
    """Test the AgentNameNormalizer class functionality."""

    def test_normalize_basic_names():
        """Test normalization of basic agent names."""
        test_cases = [
            # Input -> Expected output
            ("research", "Research"),
            ("Research", "Research"),
            ("RESEARCH", "Research"),
            ("engineer", "Engineer"),
            ("Engineer", "Engineer"),
            ("qa", "QA"),
            ("QA", "QA"),
            ("Qa", "QA"),
            ("security", "Security"),
            ("documentation", "Documentation"),
            ("ops", "Ops"),
            ("version_control", "Version Control"),
            ("version control", "Version Control"),
            ("Version Control", "Version Control"),
            ("data_engineer", "Data Engineer"),
            ("data engineer", "Data Engineer"),
            ("Data Engineer", "Data Engineer"),
        ]

        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                result = AgentNameNormalizer.normalize(input_name)
                self.assertEqual(
                    result,
                    expected,
                    f"Failed to normalize '{input_name}' to '{expected}', got '{result}'",
                )

    def test_normalize_aliases():
        """Test normalization of agent aliases."""
        test_cases = [
            # Aliases -> Expected canonical name
            ("researcher", "Research"),
            ("dev", "Engineer"),
            ("developer", "Engineer"),
            ("engineering", "Engineer"),
            ("quality", "QA"),
            ("testing", "QA"),
            ("test", "QA"),
            ("sec", "Security"),
            ("docs", "Documentation"),
            ("doc", "Documentation"),
            ("operations", "Ops"),
            ("devops", "Ops"),
            ("git", "Version Control"),
            ("vcs", "Version Control"),
            ("data", "Data Engineer"),
            ("architect", "Architect"),
            ("architecture", "Architect"),
            ("arch", "Architect"),
            ("pm", "PM"),
            ("PM", "PM"),
            ("project_manager", "PM"),
            ("project manager", "PM"),
        ]

        for alias, expected in test_cases:
            with self.subTest(alias=alias):
                result = AgentNameNormalizer.normalize(alias)
                self.assertEqual(
                    result,
                    expected,
                    f"Failed to normalize alias '{alias}' to '{expected}', got '{result}'",
                )

    def test_normalize_edge_cases():
        """Test edge cases in normalization."""
        # Empty string
        self.assertEqual(AgentNameNormalizer.normalize(""), "Engineer")

        # Unknown agent
        self.assertEqual(AgentNameNormalizer.normalize("unknown_agent"), "Engineer")

        # With extra spaces
        self.assertEqual(AgentNameNormalizer.normalize("  research  "), "Research")

        # With hyphens
        self.assertEqual(
            AgentNameNormalizer.normalize("version-control"), "Version Control"
        )
        self.assertEqual(
            AgentNameNormalizer.normalize("data-engineer"), "Data Engineer"
        )

    def test_to_key_format():
        """Test conversion to key format."""
        test_cases = [
            ("Research", "research"),
            ("Version Control", "version_control"),
            ("Data Engineer", "data_engineer"),
            ("QA", "qa"),
            ("version-control", "version_control"),  # Hyphen to underscore
        ]

        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                result = AgentNameNormalizer.to_key(input_name)
                self.assertEqual(result, expected)

    def test_to_todo_prefix():
        """Test TODO prefix generation."""
        test_cases = [
            ("research", "[Research]"),
            ("engineer", "[Engineer]"),
            ("version_control", "[Version Control]"),
            ("data-engineer", "[Data Engineer]"),
            ("qa", "[QA]"),
        ]

        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                result = AgentNameNormalizer.to_todo_prefix(input_name)
                self.assertEqual(result, expected)

    def test_extract_from_todo():
        """Test extracting agent names from TODO text."""
        test_cases = [
            ("[Research] Analyze patterns", "Research"),
            ("[Engineer] Implement feature", "Engineer"),
            ("[Version Control] Create release", "Version Control"),
            ("[Data Engineer] Build pipeline", "Data Engineer"),
            ("[QA] Run tests", "QA"),
            # With extra spaces
            ("  [Research]  Analyze patterns", "Research"),
            # Without prefix
            ("Implement feature", None),
            # Invalid prefix
            ("[Unknown] Do something", "Engineer"),  # Falls back to default
        ]

        for todo_text, expected in test_cases:
            with self.subTest(todo=todo_text):
                result = AgentNameNormalizer.extract_from_todo(todo_text)
                self.assertEqual(result, expected)

    def test_validate_todo_format():
        """Test TODO format validation."""
        # Valid formats
        valid_todos = [
            "[Research] Analyze patterns",
            "[Engineer] Implement feature",
            "[Version Control] Create release",
            "[Data Engineer] Build pipeline",
            "[QA] Run tests",
            "[Security] Audit code",
            "[Documentation] Update README",
            "[Ops] Deploy service",
        ]

        for todo in valid_todos:
            with self.subTest(todo=todo):
                is_valid, error = AgentNameNormalizer.validate_todo_format(todo)
                self.assertTrue(is_valid, f"Todo '{todo}' should be valid")
                self.assertIsNone(error)

        # Invalid formats - Note: Unknown agents get normalized to Engineer, so they're technically valid
        invalid_todos = [
            "Implement feature",  # No prefix
            "[] Empty prefix",  # Empty prefix
        ]

        for todo in invalid_todos:
            with self.subTest(todo=todo):
                is_valid, error = AgentNameNormalizer.validate_todo_format(todo)
                self.assertFalse(is_valid, f"Todo '{todo}' should be invalid")
                self.assertIsNotNone(error)

        # Test that unknown agents get normalized but are still valid
        unknown_agent_todo = "[Unknown] Do something"
        is_valid, error = AgentNameNormalizer.validate_todo_format(unknown_agent_todo)
        self.assertTrue(
            is_valid, "Unknown agents should be normalized to Engineer and be valid"
        )

    def test_to_task_format():
        """Test conversion to Task tool format."""
        test_cases = [
            # TodoWrite format -> Task format
            ("Research", "research"),
            ("Engineer", "engineer"),
            ("QA", "qa"),
            ("Security", "security"),
            ("Documentation", "documentation"),
            ("Ops", "ops"),
            ("Version Control", "version-control"),
            ("Data Engineer", "data-engineer"),
            ("Architect", "architect"),
            ("PM", "pm"),
            # Already in lowercase
            ("research", "research"),
            ("version control", "version-control"),
        ]

        for todo_format, expected_task_format in test_cases:
            with self.subTest(input=todo_format):
                result = AgentNameNormalizer.to_task_format(todo_format)
                self.assertEqual(
                    result,
                    expected_task_format,
                    f"Failed to convert '{todo_format}' to task format '{expected_task_format}', got '{result}'",
                )

    def test_from_task_format():
        """Test conversion from Task tool format to TodoWrite format."""
        test_cases = [
            # Task format -> TodoWrite format
            ("research", "Research"),
            ("engineer", "Engineer"),
            ("qa", "QA"),
            ("security", "Security"),
            ("documentation", "Documentation"),
            ("ops", "Ops"),
            ("version-control", "Version Control"),
            ("data-engineer", "Data Engineer"),
            ("architect", "Architect"),
            ("pm", "PM"),
            # Already in canonical format
            ("Research", "Research"),
            ("Version Control", "Version Control"),
        ]

        for task_format, expected_todo_format in test_cases:
            with self.subTest(input=task_format):
                result = AgentNameNormalizer.from_task_format(task_format)
                self.assertEqual(
                    result,
                    expected_todo_format,
                    f"Failed to convert '{task_format}' from task format to '{expected_todo_format}', got '{result}'",
                )

    def test_colorize():
        """Test agent name colorization."""
        # Just test that it adds color codes
        result = AgentNameNormalizer.colorize("research")
        self.assertIn("\033[", result)  # Contains color code
        self.assertIn("Research", result)  # Contains normalized name
        self.assertIn("\033[0m", result)  # Contains reset code

        # Test with custom text
        result = AgentNameNormalizer.colorize("research", "Custom Text")
        self.assertIn("Custom Text", result)
        self.assertNotIn("Research", result)


class TestAgentLoaderNormalization(unittest.TestCase):
    """Test that agent_loader correctly uses AgentNameNormalizer."""

    def test_capitalized_names_in_loader():
        """Test that agent loader handles capitalized names (as used by PM)."""
        test_names = [
            "Engineer",
            "Research",
            "QA",
            "Security",
            "Documentation",
            "Ops",
            "Version Control",
            "Data Engineer",
        ]

        for name in test_names:
            with self.subTest(agent=name):
                try:
                    prompt = get_agent_prompt(name)
                    self.assertIsNotNone(prompt, f"Failed to load agent: {name}")
                    self.assertGreater(
                        len(prompt), 100, f"Agent {name} has suspiciously short prompt"
                    )
                except ValueError as e:
                    # PM agent might have empty instructions
                    if "pm_agent" in str(e).lower():
                        self.skipTest("PM agent has empty instructions")
                    else:
                        raise

    def test_lowercase_names_in_loader():
        """Test that agent loader handles lowercase names."""
        test_names = [
            "engineer",
            "research",
            "qa",
            "security",
            "documentation",
            "ops",
        ]

        for name in test_names:
            with self.subTest(agent=name):
                prompt = get_agent_prompt(name)
                self.assertIsNotNone(prompt, f"Failed to load agent: {name}")
                self.assertGreater(len(prompt), 100)

    def test_aliases_in_loader():
        """Test that agent loader handles aliases."""
        test_aliases = [
            ("dev", True),
            ("developer", True),
            ("engineering", True),
            ("docs", True),
            ("testing", True),
            ("quality", True),
        ]

        for alias, should_work in test_aliases:
            with self.subTest(alias=alias):
                if should_work:
                    prompt = get_agent_prompt(alias)
                    self.assertIsNotNone(
                        prompt, f"Failed to load agent via alias: {alias}"
                    )
                    self.assertGreater(len(prompt), 100)

    def test_direct_agent_ids_in_loader():
        """Test that direct agent IDs still work."""
        test_ids = [
            "engineer_agent",
            "research_agent",
            "qa_agent",
            "documentation_agent",
        ]

        for agent_id in test_ids:
            with self.subTest(agent_id=agent_id):
                prompt = get_agent_prompt(agent_id)
                self.assertIsNotNone(prompt, f"Failed to load agent: {agent_id}")
                self.assertGreater(len(prompt), 100)

    def test_invalid_names_fail_in_loader():
        """Test that truly invalid agent names fail appropriately."""
        invalid_names = [
            "completely_invalid_agent",
            "not_an_agent",
            "unknown_agent",
        ]

        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as cm:
                    get_agent_prompt(name)
                self.assertIn("No agent found", str(cm.exception))

    def test_normalization_consistency_in_loader():
        """Test that different formats load the same agent content."""
        # These should all load the engineer agent
        engineer_variants = ["Engineer", "engineer", "ENGINEER", "engineering", "dev"]

        prompts = []
        for variant in engineer_variants:
            prompt = get_agent_prompt(variant)
            prompts.append(prompt)

        # All prompts should be identical
        first_prompt = prompts[0]
        for i, prompt in enumerate(prompts[1:], 1):
            self.assertEqual(
                prompt,
                first_prompt,
                f"Variant '{engineer_variants[i]}' loaded different content than '{engineer_variants[0]}'",
            )

    def test_with_model_info_normalized():
        """Test that get_agent_prompt_with_model_info works with normalized names."""
        test_names = ["Engineer", "Research", "QA"]

        for name in test_names:
            with self.subTest(agent=name):
                prompt, model, config = get_agent_prompt_with_model_info(name)
                self.assertIsNotNone(prompt, f"No prompt for {name}")
                self.assertIsNotNone(model, f"No model for {name}")
                self.assertIsNotNone(config, f"No config for {name}")
                self.assertIn("selection_method", config)


class TestIntegrationScenarios(unittest.TestCase):
    """Test end-to-end integration scenarios."""

    def test_todo_to_task_flow():
        """Test the flow from TodoWrite format to Task format."""
        # Simulate TodoWrite creating todos
        todos = [
            "[Research] Investigate best practices",
            "[Version Control] Create release v2.0",
            "[Data Engineer] Build ETL pipeline",
            "[QA] Run integration tests",
        ]

        # Extract agents and convert to Task format
        for todo in todos:
            agent = AgentNameNormalizer.extract_from_todo(todo)
            self.assertIsNotNone(agent)

            # Convert to Task format
            task_format = AgentNameNormalizer.to_task_format(agent)

            # Verify Task format
            self.assertIsInstance(task_format, str)
            self.assertEqual(task_format, task_format.lower())
            self.assertNotIn(" ", task_format)  # No spaces, uses hyphens

            # Verify round-trip conversion
            back_to_todo = AgentNameNormalizer.from_task_format(task_format)
            self.assertEqual(back_to_todo, agent)

    def test_all_agents_coverage():
        """Ensure all agent types are properly handled."""
        all_agents = [
            "Research",
            "Engineer",
            "QA",
            "Security",
            "Documentation",
            "Ops",
            "Version Control",
            "Data Engineer",
            "Architect",
            "PM",
        ]

        for agent in all_agents:
            with self.subTest(agent=agent):
                # Test TODO prefix
                prefix = AgentNameNormalizer.to_todo_prefix(agent)
                self.assertEqual(prefix, f"[{agent}]")

                # Test Task format
                task_format = AgentNameNormalizer.to_task_format(agent)
                self.assertTrue(task_format.islower() or "-" in task_format)

                # Test extraction
                todo = f"{prefix} Some task"
                extracted = AgentNameNormalizer.extract_from_todo(todo)
                self.assertEqual(extracted, agent)

                # Test round-trip
                back = AgentNameNormalizer.from_task_format(task_format)
                self.assertEqual(back, agent)


if __name__ == "__main__":
    unittest.main(verbosity=2)
