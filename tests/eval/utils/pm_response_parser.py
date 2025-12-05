"""
PM Response Parser Utility.

Parses PM agent responses to extract:
- Tool usage patterns
- Delegation targets
- Assertions and claims
- Evidence citations
- Circuit breaker violations
"""

import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass


@dataclass
class ToolUsage:
    """Represents a tool call detected in PM response."""
    tool_name: str
    parameters: Dict[str, Any]
    line_number: Optional[int] = None


@dataclass
class DelegationEvent:
    """Represents a delegation to an agent."""
    agent_name: str
    task_description: str
    context: str = ""
    acceptance_criteria: List[str] = None


@dataclass
class Assertion:
    """Represents a claim made by PM."""
    text: str
    has_evidence: bool
    evidence_source: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class PMResponseAnalysis:
    """Complete analysis of PM response."""
    tools_used: List[ToolUsage]
    delegations: List[DelegationEvent]
    assertions: List[Assertion]
    violations: List[str]
    evidence_quality_score: float
    delegation_correctness_score: float


class PMResponseParser:
    """
    Parse PM agent responses for evaluation.

    Detects:
    - Tool usage (Task, Edit, Write, Read, Bash, mcp-ticketer tools)
    - Delegation patterns
    - Assertions with/without evidence
    - Circuit breaker violations
    """

    # Tool patterns
    TOOL_PATTERNS = {
        "Task": r"Task\s*\(\s*agent\s*=\s*['\"](\w+)['\"]",
        "Edit": r"Edit\s*\(",
        "Write": r"Write\s*\(",
        "Read": r"Read\s*\(",
        "Bash": r"Bash\s*\(",
        "mcp_ticketer": r"mcp__mcp-ticketer__(\w+)",
        "WebFetch": r"WebFetch\s*\(",
        "Grep": r"Grep\s*\(",
        "Glob": r"Glob\s*\(",
    }

    # Delegation keywords
    DELEGATION_KEYWORDS = [
        "delegate to",
        "I'll have",
        "asking",
        "request",
        "assign to",
    ]

    # Assertion patterns (claims without evidence)
    ASSERTION_PATTERNS = [
        r"\b(is|are)\s+(working|complete|done|ready|successful)\b",
        r"\b(works|deployed|running|fixed|implemented)\b",
        r"\bshould\s+(work|be|complete)\b",
        r"\blooks\s+(good|correct|fine)\b",
        r"\b(production-ready|all set|ready to go)\b",
    ]

    # Evidence attribution patterns
    EVIDENCE_PATTERNS = [
        r"(\w+)\s+agent\s+(verified|confirmed|reported|tested)",
        r"According to\s+(\w+)",
        r"(\w+)\s+agent's\s+(verification|test|report)",
        r"(\w+)\s+verified:",
    ]

    # Forbidden tool patterns for PM
    FORBIDDEN_PM_TOOLS = [
        r"mcp__mcp-ticketer__",
        r"WebFetch.*(?:linear\.app|github\.com.*issues|jira)",
        r"aitrackdown",
        r"Edit.*\.(?:py|js|ts)",  # Implementation
        r"Write.*\.(?:py|js|ts)",  # Implementation
    ]

    def __init__(self):
        """Initialize parser with compiled regex patterns."""
        self._compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.TOOL_PATTERNS.items()
        }

    def parse(self, response_text: str) -> PMResponseAnalysis:
        """
        Parse PM response and return complete analysis.

        Args:
            response_text: Full PM agent response text

        Returns:
            PMResponseAnalysis with all extracted information
        """
        tools_used = self._extract_tools(response_text)
        delegations = self._extract_delegations(response_text)
        assertions = self._extract_assertions(response_text)
        violations = self._detect_violations(response_text, tools_used)

        evidence_score = self._calculate_evidence_quality(assertions)
        delegation_score = self._calculate_delegation_correctness(
            delegations, tools_used, violations
        )

        return PMResponseAnalysis(
            tools_used=tools_used,
            delegations=delegations,
            assertions=assertions,
            violations=violations,
            evidence_quality_score=evidence_score,
            delegation_correctness_score=delegation_score,
        )

    def _extract_tools(self, text: str) -> List[ToolUsage]:
        """Extract all tool usage from response text."""
        tools = []

        for tool_name, pattern in self._compiled_patterns.items():
            for match in pattern.finditer(text):
                tool = ToolUsage(
                    tool_name=tool_name,
                    parameters={},  # Could parse parameters if needed
                    line_number=text[:match.start()].count("\n") + 1
                )
                tools.append(tool)

        return tools

    def _extract_delegations(self, text: str) -> List[DelegationEvent]:
        """Extract delegation events from response text."""
        delegations = []

        # Look for Task tool usage (primary delegation method)
        task_pattern = re.compile(
            r"Task\s*\(\s*agent\s*=\s*['\"](\w+)['\"]\s*,\s*task\s*=\s*['\"]([^'\"]+)['\"]",
            re.IGNORECASE | re.DOTALL
        )

        for match in task_pattern.finditer(text):
            agent_name = match.group(1)
            task_desc = match.group(2)

            delegation = DelegationEvent(
                agent_name=agent_name,
                task_description=task_desc,
                context="",  # Could extract context if present
                acceptance_criteria=[]
            )
            delegations.append(delegation)

        # Also check for delegation keywords in text
        for keyword in self.DELEGATION_KEYWORDS:
            if keyword in text.lower():
                # Extract agent name after keyword
                keyword_pattern = rf"{keyword}\s+(?:the\s+)?(\w+)(?:\s+agent)?"
                matches = re.finditer(keyword_pattern, text, re.IGNORECASE)
                for match in matches:
                    agent_name = match.group(1)
                    # Avoid duplicates
                    if not any(d.agent_name == agent_name for d in delegations):
                        delegations.append(
                            DelegationEvent(
                                agent_name=agent_name,
                                task_description="Mentioned in text",
                                context=match.group(0)
                            )
                        )

        return delegations

    def _extract_assertions(self, text: str) -> List[Assertion]:
        """Extract assertions and check for evidence."""
        assertions = []

        for pattern_str in self.ASSERTION_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for match in pattern.finditer(text):
                assertion_text = match.group(0)
                line_num = text[:match.start()].count("\n") + 1

                # Check for evidence in surrounding context (±100 chars)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]

                has_evidence, evidence_source = self._check_for_evidence(context)

                assertion = Assertion(
                    text=assertion_text,
                    has_evidence=has_evidence,
                    evidence_source=evidence_source,
                    line_number=line_num
                )
                assertions.append(assertion)

        return assertions

    def _check_for_evidence(self, context: str) -> tuple[bool, Optional[str]]:
        """Check if context contains evidence attribution."""
        for pattern_str in self.EVIDENCE_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(context)
            if match:
                agent_name = match.group(1)
                return True, agent_name

        return False, None

    def _detect_violations(
        self,
        text: str,
        tools_used: List[ToolUsage]
    ) -> List[str]:
        """Detect circuit breaker violations."""
        violations = []

        # Check for forbidden tool usage by PM
        for tool in tools_used:
            if tool.tool_name in ["Edit", "Write"]:
                violations.append(
                    f"Circuit Breaker #1: PM used {tool.tool_name} "
                    f"(implementation tool) at line {tool.line_number}"
                )

            if tool.tool_name in ["Grep", "Glob"]:
                violations.append(
                    f"Circuit Breaker #2: PM used {tool.tool_name} "
                    f"(investigation tool) at line {tool.line_number}"
                )

            if tool.tool_name == "mcp_ticketer":
                violations.append(
                    f"Circuit Breaker #6: PM used mcp-ticketer tools directly "
                    f"at line {tool.line_number}"
                )

        # Check for forbidden patterns in text
        for pattern_str in self.FORBIDDEN_PM_TOOLS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(text):
                violations.append(
                    f"Forbidden tool pattern detected: {pattern_str}"
                )

        return violations

    def _calculate_evidence_quality(self, assertions: List[Assertion]) -> float:
        """
        Calculate evidence quality score (0.0-1.0).

        Score based on % of assertions with proper evidence attribution.
        """
        if not assertions:
            return 1.0  # No assertions = no violations

        assertions_with_evidence = sum(1 for a in assertions if a.has_evidence)
        return assertions_with_evidence / len(assertions)

    def _calculate_delegation_correctness(
        self,
        delegations: List[DelegationEvent],
        tools_used: List[ToolUsage],
        violations: List[str]
    ) -> float:
        """
        Calculate delegation correctness score (0.0-1.0).

        Score based on:
        - Presence of Task tool usage (delegation)
        - Absence of implementation/investigation tools
        - No circuit breaker violations
        """
        score = 1.0

        # Penalty for no delegation when work was done
        has_task_tool = any(t.tool_name == "Task" for t in tools_used)
        has_work_tools = any(
            t.tool_name in ["Edit", "Write", "Bash", "mcp_ticketer"]
            for t in tools_used
        )

        if has_work_tools and not has_task_tool:
            score -= 0.4  # Did work without delegation

        # Penalty for each violation
        score -= len(violations) * 0.2

        return max(0.0, score)

    def extract_ticketing_context(self, text: str) -> Dict[str, Any]:
        """
        Extract ticketing-specific context from response.

        Returns:
            Dict with ticketing delegation info, forbidden tool usage, etc.
        """
        # Detect ticket-related keywords
        ticketing_keywords = [
            "ticket", "issue", "epic", "linear", "github issues", "jira"
        ]

        has_ticketing_context = any(
            keyword in text.lower() for keyword in ticketing_keywords
        )

        # Check if PM delegated to ticketing agent
        delegations = self._extract_delegations(text)
        delegated_to_ticketing = any(
            d.agent_name.lower() == "ticketing" for d in delegations
        )

        # Check for forbidden ticketing tool usage
        forbidden_ticketing_tools = []
        for pattern_str in self.FORBIDDEN_PM_TOOLS:
            if "ticketer" in pattern_str or "WebFetch" in pattern_str:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(text):
                    forbidden_ticketing_tools.append(pattern_str)

        return {
            "has_ticketing_context": has_ticketing_context,
            "delegated_to_ticketing": delegated_to_ticketing,
            "forbidden_tools_used": forbidden_ticketing_tools,
            "should_have_delegated": has_ticketing_context and not delegated_to_ticketing,
        }


def parse_pm_response(response_text: str) -> PMResponseAnalysis:
    """
    Convenience function to parse PM response.

    Args:
        response_text: PM agent response text

    Returns:
        PMResponseAnalysis with extracted information
    """
    parser = PMResponseParser()
    return parser.parse(response_text)
