"""
Integration tests for Prompt-Engineer Agent.

Tests multi-step workflows and scenario-based behavioral validation:
1. Anti-Pattern Detection (5 scenarios)
2. Token Efficiency (4 scenarios)
3. Refactoring Quality (3 scenarios)
4. Claude 4.5 Alignment (4 scenarios)

Total: 16 scenarios + 3 integration workflow tests
"""

import json
from pathlib import Path

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.prompt_engineer import (
    AntiPatternDetectionMetric,
    RefactoringQualityMetric,
    TokenEfficiencyMetric,
)


# Fixtures for scenario loading
@pytest.fixture
def scenarios_path() -> Path:
    """Return path to scenarios JSON file."""
    return (
        Path(__file__).parent.parent.parent
        / "scenarios"
        / "prompt_engineer"
        / "prompt_engineer_scenarios.json"
    )


@pytest.fixture
def scenarios_data(scenarios_path: Path) -> dict:
    """Load scenarios from JSON file."""
    with open(scenarios_path) as f:
        return json.load(f)


@pytest.fixture
def all_scenarios(scenarios_data: dict) -> list[dict]:
    """Return all scenarios from the data."""
    return scenarios_data["scenarios"]


@pytest.fixture
def anti_pattern_scenarios(all_scenarios: list[dict]) -> list[dict]:
    """Return anti-pattern detection scenarios."""
    return [s for s in all_scenarios if s["category"] == "Anti-Pattern Detection"]


@pytest.fixture
def token_efficiency_scenarios(all_scenarios: list[dict]) -> list[dict]:
    """Return token efficiency scenarios."""
    return [s for s in all_scenarios if s["category"] == "Token Efficiency"]


@pytest.fixture
def refactoring_scenarios(all_scenarios: list[dict]) -> list[dict]:
    """Return refactoring quality scenarios."""
    return [s for s in all_scenarios if s["category"] == "Refactoring Quality"]


@pytest.fixture
def claude45_scenarios(all_scenarios: list[dict]) -> list[dict]:
    """Return Claude 4.5 alignment scenarios."""
    return [s for s in all_scenarios if s["category"] == "Claude 4.5 Alignment"]


class TestScenarioFileIntegrity:
    """Test scenario file structure and validity."""

    def test_scenario_file_exists(self, scenarios_path: Path):
        """Verify scenario file exists."""
        assert scenarios_path.exists(), f"Scenario file not found: {scenarios_path}"

    def test_scenario_count(self, all_scenarios: list[dict]):
        """Verify expected number of scenarios."""
        assert len(all_scenarios) == 16, (
            f"Expected 16 scenarios, got {len(all_scenarios)}"
        )

    def test_category_counts(
        self,
        anti_pattern_scenarios: list[dict],
        token_efficiency_scenarios: list[dict],
        refactoring_scenarios: list[dict],
        claude45_scenarios: list[dict],
    ):
        """Verify scenario counts per category."""
        assert len(anti_pattern_scenarios) == 5, "Expected 5 anti-pattern scenarios"
        assert len(token_efficiency_scenarios) == 4, (
            "Expected 4 token efficiency scenarios"
        )
        assert len(refactoring_scenarios) == 3, "Expected 3 refactoring scenarios"
        assert len(claude45_scenarios) == 4, "Expected 4 Claude 4.5 scenarios"

    def test_scenario_structure(self, all_scenarios: list[dict]):
        """Verify all scenarios have required fields."""
        required_fields = [
            "id",
            "category",
            "name",
            "description",
            "input",
            "expected_behaviors",
            "metric",
            "threshold",
            "compliant_mock_response",
            "non_compliant_mock_response",
        ]

        for scenario in all_scenarios:
            for field in required_fields:
                assert field in scenario, (
                    f"Missing {field} in scenario {scenario.get('id', 'unknown')}"
                )

    def test_unique_scenario_ids(self, all_scenarios: list[dict]):
        """Verify all scenario IDs are unique."""
        ids = [s["id"] for s in all_scenarios]
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"

    def test_valid_metrics(self, all_scenarios: list[dict]):
        """Verify all scenarios reference valid metrics."""
        valid_metrics = [
            "AntiPatternDetectionMetric",
            "TokenEfficiencyMetric",
            "RefactoringQualityMetric",
        ]

        for scenario in all_scenarios:
            assert scenario["metric"] in valid_metrics, (
                f"Invalid metric {scenario['metric']} in {scenario['id']}"
            )


class TestAntiPatternScenarios:
    """Test anti-pattern detection scenarios."""

    @pytest.fixture
    def metric(self) -> AntiPatternDetectionMetric:
        """Create anti-pattern detection metric."""
        return AntiPatternDetectionMetric(threshold=0.85)

    def test_emoji_detection_compliant(
        self, anti_pattern_scenarios: list[dict], metric: AntiPatternDetectionMetric
    ):
        """Test emoji detection with compliant response."""
        scenario = next(s for s in anti_pattern_scenarios if "Emoji" in s["name"])
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"], (
            f"Score {score} below threshold {scenario['threshold']}"
        )
        assert metric.is_successful()

    def test_emoji_detection_non_compliant(
        self, anti_pattern_scenarios: list[dict], metric: AntiPatternDetectionMetric
    ):
        """Test emoji detection with non-compliant response."""
        scenario = next(s for s in anti_pattern_scenarios if "Emoji" in s["name"])
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["non_compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score < scenario["threshold"], (
            "Non-compliant response should score below threshold"
        )

    def test_overspecification_detection(
        self, anti_pattern_scenarios: list[dict], metric: AntiPatternDetectionMetric
    ):
        """Test over-specification detection."""
        scenario = next(
            s for s in anti_pattern_scenarios if "Over-Specification" in s["name"]
        )
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_generic_prompt_detection(
        self, anti_pattern_scenarios: list[dict], metric: AntiPatternDetectionMetric
    ):
        """Test generic prompt detection."""
        scenario = next(s for s in anti_pattern_scenarios if "Generic" in s["name"])
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_cache_hostile_detection(
        self, anti_pattern_scenarios: list[dict], metric: AntiPatternDetectionMetric
    ):
        """Test cache-hostile pattern detection."""
        scenario = next(s for s in anti_pattern_scenarios if "Cache" in s["name"])
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_negative_instruction_detection(
        self, anti_pattern_scenarios: list[dict], metric: AntiPatternDetectionMetric
    ):
        """Test negative instruction detection."""
        scenario = next(s for s in anti_pattern_scenarios if "Negative" in s["name"])
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]


class TestTokenEfficiencyScenarios:
    """Test token efficiency scenarios."""

    @pytest.fixture
    def metric(self) -> TokenEfficiencyMetric:
        """Create token efficiency metric."""
        return TokenEfficiencyMetric(threshold=0.80)

    def test_token_reduction_compliant(
        self, token_efficiency_scenarios: list[dict], metric: TokenEfficiencyMetric
    ):
        """Test token reduction with compliant response."""
        scenario = next(
            s for s in token_efficiency_scenarios if "Reduction" in s["name"]
        )
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_cache_optimization(
        self, token_efficiency_scenarios: list[dict], metric: TokenEfficiencyMetric
    ):
        """Test cache optimization."""
        scenario = next(
            s for s in token_efficiency_scenarios if "Cache Optimization" in s["name"]
        )
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_redundancy_elimination(
        self, token_efficiency_scenarios: list[dict], metric: TokenEfficiencyMetric
    ):
        """Test redundancy elimination."""
        scenario = next(
            s for s in token_efficiency_scenarios if "Redundancy" in s["name"]
        )
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_structural_optimization(
        self, token_efficiency_scenarios: list[dict], metric: TokenEfficiencyMetric
    ):
        """Test structural optimization."""
        scenario = next(
            s for s in token_efficiency_scenarios if "Structural" in s["name"]
        )
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]


class TestRefactoringScenarios:
    """Test refactoring quality scenarios."""

    @pytest.fixture
    def metric(self) -> RefactoringQualityMetric:
        """Create refactoring quality metric."""
        return RefactoringQualityMetric(threshold=0.80)

    def test_before_after_comparison(
        self, refactoring_scenarios: list[dict], metric: RefactoringQualityMetric
    ):
        """Test before/after comparison."""
        scenario = next(s for s in refactoring_scenarios if "Before/After" in s["name"])
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_quality_rubric(
        self, refactoring_scenarios: list[dict], metric: RefactoringQualityMetric
    ):
        """Test quality rubric application."""
        scenario = next(s for s in refactoring_scenarios if "Rubric" in s["name"])
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_prioritization(
        self, refactoring_scenarios: list[dict], metric: RefactoringQualityMetric
    ):
        """Test improvement prioritization."""
        scenario = next(
            s for s in refactoring_scenarios if "Prioritization" in s["name"]
        )
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]


class TestClaude45Scenarios:
    """Test Claude 4.5 alignment scenarios."""

    @pytest.fixture
    def metric(self) -> RefactoringQualityMetric:
        """Create refactoring quality metric for Claude 4.5 tests."""
        return RefactoringQualityMetric(threshold=0.80)

    def test_extended_thinking(
        self, claude45_scenarios: list[dict], metric: RefactoringQualityMetric
    ):
        """Test extended thinking configuration."""
        scenario = next(
            s for s in claude45_scenarios if "Extended Thinking" in s["name"]
        )
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_parallel_tools(
        self, claude45_scenarios: list[dict], metric: RefactoringQualityMetric
    ):
        """Test parallel tool execution."""
        scenario = next(s for s in claude45_scenarios if "Parallel" in s["name"])
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_structured_output(
        self, claude45_scenarios: list[dict], metric: RefactoringQualityMetric
    ):
        """Test structured output enforcement."""
        scenario = next(
            s for s in claude45_scenarios if "Structured Output" in s["name"]
        )
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]

    def test_professional_style(
        self, claude45_scenarios: list[dict], metric: RefactoringQualityMetric
    ):
        """Test professional communication style."""
        scenario = next(s for s in claude45_scenarios if "Professional" in s["name"])
        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output=scenario["compliant_mock_response"],
        )

        score = metric.measure(test_case)

        assert score >= scenario["threshold"]


class TestPromptEngineerWorkflows:
    """Integration tests for multi-step prompt engineering workflows."""

    def test_complete_prompt_refactoring_workflow(self):
        """Test end-to-end prompt refactoring workflow."""
        anti_pattern_metric = AntiPatternDetectionMetric(threshold=0.85)
        token_metric = TokenEfficiencyMetric(threshold=0.80)
        refactor_metric = RefactoringQualityMetric(threshold=0.80)

        # Workflow: Analyze → Optimize → Refactor → Validate
        workflow_response = """
        ## Complete Prompt Refactoring Workflow

        ### Step 1: Anti-Pattern Analysis
        Detected issues:
        - Emoji anti-patterns found - removing all decorative emojis
        - Over-specification with 700 lines - need consolidation
        - Generic language detected - adding specific criteria
        - Cache-hostile variable data in system prompt
        - Negative instructions ("Don't X") - converting to positive framing

        ### Step 2: Token Efficiency Optimization
        - Original: 1000 tokens
        - Optimized: 300 tokens
        - Reduction: 70%
        - Cache hit rate improved to 95% with static separation
        - Removed all redundant duplicate content
        - Applied DRY principle throughout
        - XML tags for complex sections, markdown for navigation

        ### Step 3: Refactoring Quality
        Before: 700 lines, score 2.5/5
        After: 150 lines, score 4.5/5
        Improvement: 78% reduction, +80% quality

        Quality Rubric (8 criteria):
        - Clarity: 5/5
        - Specificity: 5/5
        - Measurable: 4/5
        - Actionable: 5/5
        - Correctness: 5/5
        - Consistency: 4/5
        - Completeness: 4/5
        - Maintainability: 5/5

        Prioritized improvements by impact:
        1. Critical: Remove emojis (high priority)
        2. Essential: Add structure (must-have)
        3. Important: Reduce verbosity

        ### Step 4: Claude 4.5 Alignment
        Applied 2025 best practices:
        - Extended thinking: 16k budget
        - Parallel tool execution enabled
        - Structured output with XML schema
        - No emojis, direct communication

        Each change justified because it improves clarity and efficiency.
        Based on research, structured prompts perform better.
        """

        test_case = LLMTestCase(
            input="Complete prompt refactoring workflow",
            actual_output=workflow_response,
        )

        # All metrics should pass
        anti_score = anti_pattern_metric.measure(test_case)
        token_score = token_metric.measure(test_case)
        refactor_score = refactor_metric.measure(test_case)

        assert anti_score >= 0.85, f"Anti-pattern score {anti_score} below 0.85"
        assert token_score >= 0.80, f"Token score {token_score} below 0.80"
        assert refactor_score >= 0.80, f"Refactor score {refactor_score} below 0.80"

    def test_anti_pattern_elimination_workflow(self):
        """Test anti-pattern detection and elimination workflow."""
        metric = AntiPatternDetectionMetric(threshold=0.85)

        workflow_response = """
        ## Anti-Pattern Elimination Workflow

        ### Phase 1: Detection
        Comprehensive anti-pattern analysis:

        #### Emoji Anti-Patterns
        Found decorative emojis - removing all. Emoji-free professional communication.

        #### Over-Specification
        Detected 700+ lines of micro-instructions. Reduce verbosity, consolidate to 150 lines.

        #### Generic Language
        Vague prompts lack specific context. Adding measurable criteria.

        #### Cache-Hostile Patterns
        Variable data in system prompt causes 80% cache miss. Separate for 95% cache hit.

        #### Negative Instructions
        "Don't X" patterns converted to positive "Do Y" affirmative framing.

        ### Phase 2: Elimination
        Applied fixes for each anti-pattern category:
        - All emojis removed
        - 78% line reduction achieved
        - Specific success metrics added
        - Static/variable content separated
        - All negative instructions rewritten positively

        ### Phase 3: Validation
        All anti-patterns eliminated:
        - Zero emojis remaining
        - Under 200 lines total
        - 100% specific, measurable criteria
        - 95% cache efficiency
        - 100% positive framing
        """

        test_case = LLMTestCase(
            input="Eliminate all anti-patterns from this prompt",
            actual_output=workflow_response,
        )

        score = metric.measure(test_case)

        assert score >= 0.85
        assert metric.is_successful()

    def test_token_optimization_workflow(self):
        """Test comprehensive token optimization workflow."""
        metric = TokenEfficiencyMetric(threshold=0.80)

        workflow_response = """
        ## Token Optimization Workflow

        ### Analysis Phase
        Current token usage analysis:
        - Total: 2000 tokens
        - Redundant: 800 tokens (40%)
        - Verbose: 400 tokens (20%)
        - Essential: 800 tokens (40%)

        ### Optimization Phase

        #### Token Reduction
        - Before: 2000 tokens
        - After: 600 tokens
        - Reduction: 70%

        Applied techniques:
        - Removed verbose explanations
        - Consolidated similar instructions
        - Eliminated filler phrases

        #### Cache Optimization
        - Separated static from variable content
        - Static prefix (500 tokens) - cacheable
        - Dynamic section (100 tokens) - per-request
        - Cache hit rate: 95%

        #### Redundancy Elimination
        - Merged 5 duplicate rule sets
        - Applied DRY principle
        - Single source of truth
        - Consolidated repeated examples

        #### Structural Optimization
        ```xml
        <instructions>
          <core>Essential rules</core>
        </instructions>
        ```

        ```markdown
        ## Navigation
        - Section 1
        - Section 2
        ```

        ### Results
        - 70% token reduction
        - 95% cache efficiency
        - Zero redundancy
        - Clean XML/markdown structure
        """

        test_case = LLMTestCase(
            input="Optimize tokens in this prompt",
            actual_output=workflow_response,
        )

        score = metric.measure(test_case)

        assert score >= 0.80
        assert metric.is_successful()
