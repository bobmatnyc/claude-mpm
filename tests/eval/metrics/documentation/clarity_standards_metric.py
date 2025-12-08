"""
Clarity Standards Metric for Documentation Agent Testing.

This metric evaluates Documentation Agent compliance with clarity and writing standards:
- Active voice usage (25%): Direct, imperative instructions
- Jargon handling (20%): Acronym definitions, glossary references
- Code examples (30%): Runnable examples with language hints
- Conciseness (25%): Avoids redundant phrases, direct language
- Completeness bonus (+15%): All required sections present

Scoring Algorithm (weighted):
1. Active Voice (25%): Detects active voice patterns, avoids passive constructions
2. Jargon Handling (20%): Checks acronym definitions, technical term explanations
3. Code Examples (30%): Validates code blocks with language hints, practical examples
4. Conciseness (25%): Detects redundant phrases, checks for direct language
5. Completeness Bonus (+15%): Checks for 5 required sections

Threshold: 0.85 (85% compliance required)

Example:
    metric = ClarityStandardsMetric(threshold=0.85)
    test_case = LLMTestCase(
        input="Document the authentication API",
        actual_output='''# API Authentication

        Send a POST request to `/auth/login` with credentials:

        ```bash
        curl -X POST https://api.example.com/auth/login \\
          -H "Content-Type: application/json" \\
          -d '{"username": "user", "password": "pass"}'
        ```

        The API returns a JWT token (JSON Web Token). Include this token
        in subsequent requests.

        ## Troubleshooting
        - Error 401: Invalid credentials
        - Error 429: Rate limit exceeded
        '''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class ClarityStandardsMetric(BaseMetric):
    """
    DeepEval metric for Documentation Agent clarity standards compliance.

    Evaluates:
    1. Active voice usage (25%): Direct instructions, imperative mood
    2. Jargon handling (20%): Acronym definitions, glossary references
    3. Code examples (30%): Runnable examples with language hints
    4. Conciseness (25%): Avoids redundant phrases, direct language
    5. Completeness bonus (+15%): Required sections present

    Scoring:
    - 1.0: Perfect compliance (all components well-covered)
    - 0.85-0.99: Excellent (threshold pass)
    - 0.70-0.84: Good (below threshold)
    - 0.0-0.69: Poor (significant gaps)
    """

    # Active voice patterns (25% weight)
    ACTIVE_VOICE_PATTERNS: List[str] = [
        r'\b(?:Run|Execute|Send|Configure|Install|Create|Delete|Update|Add|Remove)\b',
        r'\bYou (?:can|should|must|will|need to)\b',
        r'^\s*(?:To|For) \w+',  # Imperative mood
        r'\b(?:Use|Set|Get|Make|Call|Start|Stop)\b',
        r'\b(?:Click|Navigate|Select|Choose|Enter)\b',
    ]

    # Passive voice anti-patterns (negative scoring)
    PASSIVE_VOICE_PATTERNS: List[str] = [
        r'(?:can|should|must|will) be \w+ed',
        r'(?:is|are|was|were) \w+ed\b',
        r'(?:is|are|was|were) (?:used|created|configured|performed)',
        r'should be',
        r'will be',
    ]

    # Jargon handling patterns (20% weight)
    ACRONYM_DEFINITION_PATTERNS: List[str] = [
        r'\b[A-Z]{2,}\s*\([^)]+\)',  # "PKCE (Proof Key...)"
        r'\b\w+\s*\(([A-Z]{2,})\)',  # "Proof Key (PKCE)"
        r'\b[A-Z]{2,}:\s*\w+',  # "JWT: JSON Web Token"
        r'stands for',
        r'means\s+(?:that|the)',
    ]

    GLOSSARY_PATTERNS: List[str] = [
        r'glossary',
        r'defined as',
        r'\*\*\w+\*\*:\s',  # **Term**: definition
        r'## (?:Glossary|Terms|Definitions)',
        r'See\s+\[.*\]\(',  # Links to definitions
    ]

    # Code example patterns (30% weight)
    CODE_BLOCK_PATTERNS: List[str] = [
        r'```(?:python|javascript|typescript|bash|sh|go|rust|java|c\+\+|ruby|php|sql)',
        r'```\w+\n',  # Any code block with language
    ]

    EXAMPLE_PATTERNS: List[str] = [
        r'## (?:Example|Usage|Quick Start)',
        r'### Example:',
        r'For example[,:]',
        r'Example:',
        r'Usage:',
        r'Code snippet:',
        r'Sample:',
    ]

    # Conciseness anti-patterns (25% weight - negative scoring)
    REDUNDANT_PHRASES: List[str] = [
        r'in order to',
        r'it should be noted that',
        r'it is important to note',
        r'generally speaking',
        r'for the purpose of',
        r'in the event that',
        r'due to the fact that',
        r'at this point in time',
        r'in a timely manner',
        r'as a matter of fact',
        r'the fact that',
        r'in actual fact',
    ]

    DIRECT_LANGUAGE_PATTERNS: List[str] = [
        r'^\s*\d+\.\s+',  # Numbered lists
        r'^\s*[-*]\s+',   # Bullet points
        r'## \w+',  # Clear headings
        r'\*\*\w+\*\*:',  # Bold terms
    ]

    # Completeness patterns (bonus +15%)
    REQUIRED_SECTIONS: List[str] = [
        r'## (?:Overview|Purpose|Introduction)',
        r'## (?:Quick Start|Getting Started|Installation)',
        r'## (?:Reference|API|Configuration|Detailed)',
        r'## Troubleshooting',
        r'## (?:Changelog|Version History|Changes)',
    ]

    def __init__(self, threshold: float = 0.85):
        """
        Initialize ClarityStandardsMetric.

        Args:
            threshold: Minimum score to pass (default: 0.85 for 85% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Clarity Standards"

    @property
    def score(self) -> Optional[float]:
        """Get the computed score."""
        return self._score

    @property
    def reason(self) -> Optional[str]:
        """Get the reason for the score."""
        return self._reason

    def is_successful(self) -> bool:
        """Check if metric passes threshold."""
        if self._success is None:
            return False
        return self._success

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure clarity standards compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.15 (with bonus)
        """
        output = test_case.actual_output

        # Calculate component scores
        active_voice_score = self._score_active_voice(output)
        jargon_handling_score = self._score_jargon_handling(output)
        code_examples_score = self._score_code_examples(output)
        conciseness_score = self._score_conciseness(output)
        completeness_bonus = self._score_completeness(output)

        # Weighted average (base score)
        base_score = (
            active_voice_score * 0.25 +
            jargon_handling_score * 0.20 +
            code_examples_score * 0.30 +
            conciseness_score * 0.25
        )

        # Add completeness bonus (up to +15%)
        final_score = base_score + completeness_bonus

        # Cap at 1.0 for threshold comparison
        capped_score = min(final_score, 1.0)

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            active_voice_score,
            jargon_handling_score,
            code_examples_score,
            conciseness_score,
            completeness_bonus,
            output
        )
        epsilon = 1e-9
        self._success = capped_score >= (self.threshold - epsilon)

        return final_score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure (delegates to sync)."""
        return self.measure(test_case)

    # ========================================================================
    # COMPONENT SCORING METHODS
    # ========================================================================

    def _score_active_voice(self, output: str) -> float:
        """
        Score active voice usage (25% weight).

        Detects:
        - Active voice patterns: "Run the", "Execute", "Send"
        - Passive voice anti-patterns: "should be run", "is configured"

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        active_matches = sum(
            1 for pattern in self.ACTIVE_VOICE_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        )

        passive_matches = sum(
            1 for pattern in self.PASSIVE_VOICE_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        total_voice_indicators = active_matches + passive_matches

        # No voice indicators - neutral score
        if total_voice_indicators == 0:
            return 0.5

        # Calculate active voice ratio
        active_ratio = active_matches / total_voice_indicators

        # Score based on ratio
        if active_ratio >= 0.9:
            return 1.0  # >90% active voice
        if active_ratio >= 0.7:
            return 0.8  # 70-90% active voice
        if active_ratio >= 0.5:
            return 0.6  # 50-70% active voice
        return 0.3  # <50% active voice (passive dominates)

    def _score_jargon_handling(self, output: str) -> float:
        """
        Score jargon handling (20% weight).

        Detects:
        - Acronym definitions: "JWT (JSON Web Token)"
        - Glossary references: "See glossary", "defined as"
        - Term explanations: **Term**: definition

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        acronym_matches = sum(
            1 for pattern in self.ACRONYM_DEFINITION_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        glossary_matches = sum(
            1 for pattern in self.GLOSSARY_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        )

        total_jargon_handling = acronym_matches + glossary_matches

        # Check for presence of undefined acronyms (basic check)
        # Count 2+ consecutive capital letters not in code blocks
        potential_acronyms = len(re.findall(r'\b[A-Z]{2,}\b', output))

        if total_jargon_handling == 0:
            # No jargon handling detected
            if potential_acronyms > 0:
                return 0.0  # Acronyms present but not defined
            return 0.7  # No acronyms, neutral

        # Score based on handling coverage
        if total_jargon_handling >= 5:
            return 1.0  # Excellent jargon handling
        if total_jargon_handling >= 3:
            return 0.85  # Good jargon handling
        if total_jargon_handling >= 2:
            return 0.7  # Acceptable jargon handling
        return 0.5  # Minimal jargon handling

    def _score_code_examples(self, output: str) -> float:
        """
        Score code examples (30% weight - HIGHEST).

        Detects:
        - Code blocks with language hints: ```python, ```bash
        - Example sections: ## Example, ### Usage
        - Practical usage demonstrations

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        code_block_matches = sum(
            1 for pattern in self.CODE_BLOCK_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        example_section_matches = sum(
            1 for pattern in self.EXAMPLE_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        )

        total_examples = code_block_matches + example_section_matches

        if total_examples == 0:
            return 0.0  # No examples

        # Score based on example coverage
        if total_examples >= 5:
            return 1.0  # Multiple comprehensive examples
        if total_examples >= 3:
            return 0.85  # Good example coverage
        if total_examples >= 2:
            return 0.7  # Acceptable examples
        return 0.5  # Minimal examples

    def _score_conciseness(self, output: str) -> float:
        """
        Score conciseness (25% weight).

        Detects:
        - Redundant phrases (negative): "in order to", "it should be noted"
        - Direct language (positive): numbered lists, bullet points, headings

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        redundant_matches = sum(
            1 for pattern in self.REDUNDANT_PHRASES
            if re.search(pattern, output, re.IGNORECASE)
        )

        direct_language_matches = sum(
            1 for pattern in self.DIRECT_LANGUAGE_PATTERNS
            if re.search(pattern, output, re.MULTILINE)
        )

        # Penalize redundant phrases heavily
        if redundant_matches >= 5:
            return 0.3  # Very verbose
        if redundant_matches >= 3:
            return 0.6  # Somewhat verbose
        if redundant_matches >= 1:
            return 0.8  # Minor redundancy

        # Reward direct language
        if direct_language_matches >= 5:
            return 1.0  # Very concise and structured
        if direct_language_matches >= 3:
            return 0.9  # Well-structured
        return 0.8  # Acceptable structure

    def _score_completeness(self, output: str) -> float:
        """
        Score completeness bonus (+15% maximum).

        Detects required sections:
        1. Overview/Purpose
        2. Quick Start
        3. Reference/API
        4. Troubleshooting
        5. Changelog

        Args:
            output: Agent output text

        Returns:
            Bonus score from 0.0 to 0.15
        """
        section_matches = [
            pattern for pattern in self.REQUIRED_SECTIONS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        ]

        section_count = len(section_matches)

        if section_count == 5:
            return 0.15  # All required sections
        if section_count == 4:
            return 0.10  # Most sections
        if section_count == 3:
            return 0.05  # Some sections
        return 0.0  # Few or no sections

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        active_voice_score: float,
        jargon_handling_score: float,
        code_examples_score: float,
        conciseness_score: float,
        completeness_bonus: float,
        output: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            active_voice_score: Active voice component score
            jargon_handling_score: Jargon handling component score
            code_examples_score: Code examples component score
            conciseness_score: Conciseness component score
            completeness_bonus: Completeness bonus score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Active voice issues
        if active_voice_score < 0.5:
            reasons.append(
                "Passive voice dominates (should use active voice: 'Run the command' vs 'The command should be run')"
            )
        elif active_voice_score < 0.7:
            reasons.append(
                "Mixed voice usage (increase active voice percentage)"
            )

        # Jargon handling issues
        if jargon_handling_score < 0.5:
            reasons.append(
                "Acronyms/jargon not explained (define on first use: 'JWT (JSON Web Token)')"
            )
        elif jargon_handling_score < 0.7:
            reasons.append(
                "Limited jargon explanations (define more technical terms)"
            )

        # Code examples issues
        if code_examples_score < 0.5:
            reasons.append(
                "Missing code examples (include runnable examples with language hints: ```python)"
            )
        elif code_examples_score < 0.7:
            reasons.append(
                "Few code examples (add more practical usage examples)"
            )

        # Conciseness issues
        if conciseness_score < 0.5:
            reasons.append(
                "Verbose writing detected (remove redundant phrases like 'in order to', 'it should be noted')"
            )
        elif conciseness_score < 0.7:
            reasons.append(
                "Some redundancy (simplify language: 'to' instead of 'in order to')"
            )

        # Completeness feedback
        if completeness_bonus < 0.05:
            reasons.append(
                "Missing required sections (should include: Overview, Quick Start, Reference, Troubleshooting, Changelog)"
            )
        elif completeness_bonus < 0.10:
            reasons.append(
                "Some required sections missing (need 4-5 sections)"
            )

        # Success message
        if not reasons:
            return "Excellent clarity - active voice, clear examples, concise writing, complete structure"

        return "; ".join(reasons)


def create_clarity_standards_metric(threshold: float = 0.85) -> ClarityStandardsMetric:
    """
    Factory function to create clarity standards metric.

    Args:
        threshold: Minimum passing score (default: 0.85 for 85% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_clarity_standards_metric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document API endpoint",
            actual_output="Send a POST request... ```bash\\ncurl...\\n```"
        )
        score = metric.measure(test_case)
    """
    return ClarityStandardsMetric(threshold=threshold)
