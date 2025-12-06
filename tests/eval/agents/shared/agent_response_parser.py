"""
Agent Response Parser - Generic parser for all agent types.

This module extends the PM response parser pattern to handle BASE_AGENT
and specialized agent responses. It extracts:
- Tool usage patterns
- Verification events (BASE_AGENT requirement)
- Memory capture (JSON response format)
- Agent-specific behavioral patterns
- Circuit breaker violations

Design Decision: Generic parser with agent-type-specific extensions

Rationale: All agents share BASE_AGENT patterns (verification, memory, response format),
but specialized agents have additional behavioral requirements. Using polymorphism
allows extending base parsing logic without duplication.

Trade-offs:
- Complexity: Single parser vs. agent-specific parsers
- Maintainability: Centralized logic easier to update
- Extensibility: New agent types require minimal changes

Example:
    parser = AgentResponseParser()
    analysis = parser.parse(response_text, agent_type="engineer")
    assert analysis.verification_events  # BASE_AGENT pattern
    assert analysis.net_loc_delta <= 0  # Engineer-specific pattern
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class AgentType(str, Enum):
    """Agent types in Claude MPM framework."""

    BASE = "base"  # BASE_AGENT_TEMPLATE.md only
    RESEARCH = "research"  # BASE_AGENT + BASE_RESEARCH.md
    ENGINEER = "engineer"  # BASE_AGENT + BASE_ENGINEER.md
    QA = "qa"  # BASE_AGENT + BASE_QA.md
    OPS = "ops"  # BASE_AGENT + BASE_OPS.md
    DOCUMENTATION = "documentation"  # BASE_AGENT + BASE_DOCUMENTATION.md
    PROMPT_ENGINEER = "prompt_engineer"  # BASE_AGENT + BASE_PROMPT_ENGINEER.md
    PM = "pm"  # BASE_AGENT + BASE_PM.md (already tested in Phase 1)


@dataclass
class ToolUsage:
    """Represents a tool call detected in agent response."""

    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    line_number: Optional[int] = None
    context: str = ""  # Surrounding text for context


@dataclass
class VerificationEvent:
    """
    Represents a verification action (BASE_AGENT requirement).

    BASE_AGENT requires: "Always verify - test functions, APIs, file edits"
    """

    verification_type: str  # "file_edit", "test_execution", "api_call", etc.
    verified: bool  # Did agent verify the action?
    verification_tool: Optional[str] = None  # Tool used for verification (e.g., "Read")
    action_tool: Optional[str] = None  # Original action tool (e.g., "Edit")
    line_number: Optional[int] = None
    context: str = ""


@dataclass
class MemoryCapture:
    """
    Represents memory capture from JSON response format.

    BASE_AGENT requires JSON block with:
    - task_completed: bool
    - instructions: str
    - results: str
    - files_modified: List[str]
    - tools_used: List[str]
    - remember: Optional[List[str]]
    """

    json_block_present: bool
    task_completed: Optional[bool] = None
    instructions: Optional[str] = None
    results: Optional[str] = None
    files_modified: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    remember: Optional[List[str]] = None
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class AgentResponseAnalysis:
    """
    Complete analysis of agent response.

    Contains both BASE_AGENT common patterns and agent-specific patterns.
    """

    agent_type: AgentType
    tools_used: List[ToolUsage]
    verification_events: List[VerificationEvent]
    memory_capture: MemoryCapture
    violations: List[str] = field(default_factory=list)

    # Scores (0.0-1.0)
    verification_compliance_score: float = 0.0
    memory_protocol_score: float = 0.0

    # Agent-specific fields (populated based on agent_type)
    agent_specific_data: Dict[str, Any] = field(default_factory=dict)


class AgentResponseParser:
    """
    Generic agent response parser for all agent types.

    Parses BASE_AGENT common patterns and delegates to agent-specific
    parsers for specialized behavioral patterns.

    Performance:
    - Time Complexity: O(n) where n is response text length
    - Space Complexity: O(m) where m is number of matches (tools, patterns)

    Optimization Opportunities:
    1. Compile regex patterns once (done in __init__)
    2. Use generators for large responses (not needed for typical agent responses)
    3. Cache parsed results if same response parsed multiple times (future)
    """

    # BASE_AGENT tool patterns (all agents can use these)
    BASE_TOOL_PATTERNS = {
        "Task": r"Task\s*\(\s*agent\s*=\s*['\"](\w+)['\"]",
        "Edit": r"Edit\s*\(",
        "Write": r"Write\s*\(",
        "Read": r"Read\s*\(",
        "Bash": r"Bash\s*\(",
        "Grep": r"Grep\s*\(",
        "Glob": r"Glob\s*\(",
        "WebFetch": r"WebFetch\s*\(",
        "WebSearch": r"WebSearch\s*\(",
        "Skill": r"Skill\s*\(",
        "SlashCommand": r"SlashCommand\s*\(",
    }

    # Verification patterns (BASE_AGENT requirement)
    VERIFICATION_PATTERNS = {
        "file_verification": r"Read.*after.*(?:Edit|Write)",
        "test_verification": r"(?:pytest|npm test|vitest).*(?:passed|failed|completed)",
        "api_verification": r"(?:curl|http|api).*(?:response|status|result)",
        "bash_verification": r"(?:echo|cat|ls).*verify",
    }

    # Memory protocol patterns
    JSON_BLOCK_PATTERN = r"```json\s*(\{.*?\})\s*```"

    def __init__(self):
        """Initialize parser with compiled regex patterns."""
        self._compiled_tools = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.BASE_TOOL_PATTERNS.items()
        }
        self._compiled_verification = {
            name: re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for name, pattern in self.VERIFICATION_PATTERNS.items()
        }
        self._json_pattern = re.compile(self.JSON_BLOCK_PATTERN, re.DOTALL)

    def parse(
        self, response_text: str, agent_type: AgentType | str = AgentType.BASE
    ) -> AgentResponseAnalysis:
        """
        Parse agent response and return complete analysis.

        Args:
            response_text: Full agent response text
            agent_type: Type of agent (for specialized parsing)

        Returns:
            AgentResponseAnalysis with all extracted information

        Example:
            parser = AgentResponseParser()
            analysis = parser.parse(response, agent_type="engineer")
            print(f"Verification score: {analysis.verification_compliance_score}")
            print(f"Memory protocol score: {analysis.memory_protocol_score}")
        """
        # Convert string to enum if needed
        if isinstance(agent_type, str):
            agent_type = AgentType(agent_type)

        # Parse BASE_AGENT common patterns
        tools_used = self._extract_tools(response_text)
        verification_events = self._extract_verification_events(response_text, tools_used)
        memory_capture = self._extract_memory_capture(response_text)
        violations = self._detect_base_violations(response_text, tools_used)

        # Calculate BASE_AGENT scores
        verification_score = self._calculate_verification_score(verification_events, tools_used)
        memory_score = self._calculate_memory_protocol_score(memory_capture)

        # Create base analysis
        analysis = AgentResponseAnalysis(
            agent_type=agent_type,
            tools_used=tools_used,
            verification_events=verification_events,
            memory_capture=memory_capture,
            violations=violations,
            verification_compliance_score=verification_score,
            memory_protocol_score=memory_score,
        )

        # Parse agent-specific patterns
        if agent_type == AgentType.RESEARCH:
            analysis.agent_specific_data = self._parse_research_agent(response_text, tools_used)
        elif agent_type == AgentType.ENGINEER:
            analysis.agent_specific_data = self._parse_engineer_agent(response_text, tools_used)
        elif agent_type == AgentType.QA:
            analysis.agent_specific_data = self._parse_qa_agent(response_text, tools_used)
        elif agent_type == AgentType.OPS:
            analysis.agent_specific_data = self._parse_ops_agent(response_text, tools_used)
        elif agent_type == AgentType.DOCUMENTATION:
            analysis.agent_specific_data = self._parse_documentation_agent(response_text)
        elif agent_type == AgentType.PROMPT_ENGINEER:
            analysis.agent_specific_data = self._parse_prompt_engineer_agent(response_text)

        return analysis

    def _extract_tools(self, text: str) -> List[ToolUsage]:
        """Extract all tool usage from response text."""
        tools = []

        for tool_name, pattern in self._compiled_tools.items():
            for match in pattern.finditer(text):
                line_num = text[: match.start()].count("\n") + 1
                # Extract context (50 chars before/after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                tool = ToolUsage(
                    tool_name=tool_name,
                    parameters={},  # Could parse parameters if needed
                    line_number=line_num,
                    context=context,
                )
                tools.append(tool)

        return tools

    def _extract_verification_events(
        self, text: str, tools_used: List[ToolUsage]
    ) -> List[VerificationEvent]:
        """
        Extract verification events (BASE_AGENT requirement).

        BASE_AGENT requires: "Always verify - test functions, APIs, file edits"

        Detection Strategy:
        1. File verification: Read after Edit/Write
        2. Test verification: Test execution with result checking
        3. API verification: API call with response validation
        """
        events = []

        # Check for file verification (Read after Edit/Write)
        edit_tools = [t for t in tools_used if t.tool_name in ["Edit", "Write"]]
        read_tools = [t for t in tools_used if t.tool_name == "Read"]

        for edit_tool in edit_tools:
            # Look for Read tool after this Edit/Write
            verified = any(
                read_tool.line_number and edit_tool.line_number and read_tool.line_number > edit_tool.line_number
                for read_tool in read_tools
            )

            event = VerificationEvent(
                verification_type="file_edit",
                verified=verified,
                verification_tool="Read" if verified else None,
                action_tool=edit_tool.tool_name,
                line_number=edit_tool.line_number,
                context=edit_tool.context,
            )
            events.append(event)

        # Check for test verification
        bash_tools = [t for t in tools_used if t.tool_name == "Bash"]
        for bash_tool in bash_tools:
            if any(
                keyword in bash_tool.context.lower()
                for keyword in ["pytest", "npm test", "vitest", "jest"]
            ):
                # Check if result was verified (look for pass/fail mentions)
                verified = any(
                    result in text[bash_tool.line_number or 0 :]
                    for result in ["passed", "failed", "completed", "success", "error"]
                )

                event = VerificationEvent(
                    verification_type="test_execution",
                    verified=verified,
                    verification_tool="Bash",
                    action_tool="Bash",
                    line_number=bash_tool.line_number,
                    context=bash_tool.context,
                )
                events.append(event)

        return events

    def _extract_memory_capture(self, text: str) -> MemoryCapture:
        """
        Extract memory capture from JSON response format.

        BASE_AGENT requires JSON block with specific fields.
        """
        match = self._json_pattern.search(text)

        if not match:
            return MemoryCapture(
                json_block_present=False,
                validation_errors=["No JSON block found in response"],
            )

        try:
            json_data = json.loads(match.group(1))

            validation_errors = []

            # Validate required fields
            if "task_completed" not in json_data:
                validation_errors.append("Missing required field: task_completed")
            if "instructions" not in json_data:
                validation_errors.append("Missing required field: instructions")
            if "results" not in json_data:
                validation_errors.append("Missing required field: results")

            return MemoryCapture(
                json_block_present=True,
                task_completed=json_data.get("task_completed"),
                instructions=json_data.get("instructions"),
                results=json_data.get("results"),
                files_modified=json_data.get("files_modified", []),
                tools_used=json_data.get("tools_used", []),
                remember=json_data.get("remember"),
                validation_errors=validation_errors,
            )

        except json.JSONDecodeError as e:
            return MemoryCapture(
                json_block_present=True,
                validation_errors=[f"Invalid JSON: {str(e)}"],
            )

    def _detect_base_violations(
        self, text: str, tools_used: List[ToolUsage]
    ) -> List[str]:
        """Detect BASE_AGENT violations."""
        violations = []

        # Check for unverified claims (assertions without evidence)
        assertion_patterns = [
            r"\b(is|are)\s+(working|complete|done|ready|successful)\b",
            r"\b(works|deployed|running|fixed|implemented)\b",
            r"\bshould\s+(work|be|complete)\b",
            r"\blooks\s+(good|correct|fine)\b",
        ]

        for pattern_str in assertion_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            matches = pattern.finditer(text)
            for match in matches:
                # Check if this assertion has verification nearby (±100 chars)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]

                has_verification = any(
                    keyword in context.lower()
                    for keyword in ["verified", "tested", "confirmed", "checked"]
                )

                if not has_verification:
                    line_num = text[:match.start()].count('\n') + 1
                    violations.append(
                        f"Unverified assertion at line {line_num}: "
                        f"'{match.group(0)}'"
                    )

        return violations

    def _calculate_verification_score(
        self, events: List[VerificationEvent], tools_used: List[ToolUsage]
    ) -> float:
        """
        Calculate verification compliance score (0.0-1.0).

        Score based on % of actions that were verified.
        """
        if not events:
            return 1.0  # No verifiable actions = no violations

        verified_count = sum(1 for e in events if e.verified)
        return verified_count / len(events)

    def _calculate_memory_protocol_score(self, memory: MemoryCapture) -> float:
        """
        Calculate memory protocol compliance score (0.0-1.0).

        Score based on JSON block presence and completeness.
        """
        if not memory.json_block_present:
            return 0.0

        if memory.validation_errors:
            # Partial credit for having JSON block but missing fields
            return 0.5

        return 1.0

    # ========================================================================
    # AGENT-SPECIFIC PARSERS
    # ========================================================================

    def _parse_research_agent(
        self, text: str, tools_used: List[ToolUsage]
    ) -> Dict[str, Any]:
        """
        Parse research agent specific patterns.

        Research agent requirements (BASE_RESEARCH.md):
        - Files >20KB must use document_summarizer
        - 3-5 file max sampling strategy
        - grep/glob for discovery, not full reads
        """
        data = {
            "file_size_checks": self._detect_pattern(text, r"file.*size|check.*size|>.*KB|>.*20"),
            "files_read_count": len([t for t in tools_used if t.tool_name == "Read"]),
            "sampling_strategy_used": self._detect_pattern(text, r"sampl(e|ing)|grep|glob|pattern"),
            "document_summarizer_used": self._detect_pattern(text, r"document_summarizer"),
            "max_files_threshold": 5,  # Research agent should read ≤5 files
        }

        # Check violations
        if data["files_read_count"] > data["max_files_threshold"]:
            data["violation"] = f"Read {data['files_read_count']} files (max: {data['max_files_threshold']})"

        return data

    def _parse_engineer_agent(
        self, text: str, tools_used: List[ToolUsage]
    ) -> Dict[str, Any]:
        """
        Parse engineer agent specific patterns.

        Engineer agent requirements (BASE_ENGINEER.md):
        - Code minimization: Target ≤0 net LOC
        - Search before create (80% time)
        - No mock data in production
        - No silent fallbacks
        """
        data = {
            "search_tools_used": len(
                [t for t in tools_used if t.tool_name in ["Grep", "Glob", "WebSearch"]]
            ),
            "write_tools_used": len([t for t in tools_used if t.tool_name in ["Edit", "Write"]]),
            "vector_search_used": any("vector" in t.context.lower() for t in tools_used),
            "consolidation_mentioned": self._detect_pattern(text, r"consolidat(e|ion)|reuse|duplicate"),
            "loc_delta_mentioned": self._detect_pattern(text, r"LOC|lines.*code|net.*lines"),
            "mock_data_detected": self._detect_pattern(text, r"mock.*data|dummy.*data|fallback.*data"),
        }

        # Check search-before-create pattern
        if data["write_tools_used"] > 0 and data["search_tools_used"] == 0:
            data["violation"] = "Write/Edit without prior search (violates search-first protocol)"

        return data

    def _parse_qa_agent(self, text: str, tools_used: List[ToolUsage]) -> Dict[str, Any]:
        """
        Parse QA agent specific patterns.

        QA agent requirements (BASE_QA.md):
        - CRITICAL: No watch mode (CI=true for npm test)
        - Process cleanup verification
        - Memory-efficient testing (3-5 files max)
        """
        bash_tools = [t for t in tools_used if t.tool_name == "Bash"]

        data = {
            "test_execution_count": len(
                [
                    t
                    for t in bash_tools
                    if any(
                        keyword in t.context.lower()
                        for keyword in ["pytest", "npm test", "vitest", "jest"]
                    )
                ]
            ),
            "ci_mode_used": any("CI=true" in t.context for t in bash_tools),
            "watch_mode_detected": self._detect_pattern(text, r"vitest(?!\s+run)|--watch|watch.*mode"),
            "process_cleanup_verified": self._detect_pattern(text, r"ps aux|pkill|process.*cleanup"),
            "package_json_checked": any("package.json" in t.context for t in tools_used if t.tool_name == "Read"),
        }

        # Check critical violation: watch mode
        if data["watch_mode_detected"]:
            data["violation"] = "CRITICAL: Watch mode detected (violates QA safe execution protocol)"

        return data

    def _parse_ops_agent(self, text: str, tools_used: List[ToolUsage]) -> Dict[str, Any]:
        """
        Parse ops agent specific patterns.

        Ops agent requirements (BASE_OPS.md):
        - Deployment safety: Environment validation, rollback preparation
        - Infrastructure focus: Docker, Kubernetes, CI/CD
        - Security: Secrets management, vulnerability scanning
        """
        data = {
            "deployment_tools_used": self._detect_pattern(text, r"docker|kubectl|helm|terraform"),
            "environment_validation": self._detect_pattern(text, r"environment|env.*var|config.*check"),
            "rollback_mentioned": self._detect_pattern(text, r"rollback|revert|restore"),
            "health_checks": self._detect_pattern(text, r"health.*check|readiness|liveness"),
            "secrets_management": self._detect_pattern(text, r"secret|credential|key.*vault"),
        }

        return data

    def _parse_documentation_agent(self, text: str) -> Dict[str, Any]:
        """
        Parse documentation agent specific patterns.

        Documentation agent requirements (BASE_DOCUMENTATION.md):
        - Clarity, completeness, examples
        - Audience awareness
        """
        data = {
            "examples_included": self._detect_pattern(text, r"example|e\.g\.|for instance"),
            "code_blocks": len(re.findall(r"```", text)) // 2,  # Pairs of backticks
            "audience_awareness": self._detect_pattern(text, r"user|developer|beginner|advanced"),
        }

        return data

    def _parse_prompt_engineer_agent(self, text: str) -> Dict[str, Any]:
        """
        Parse prompt engineer agent specific patterns.

        Prompt Engineer agent requirements (BASE_PROMPT_ENGINEER.md):
        - Prompt optimization: Token efficiency
        - Testing: A/B testing, success metrics
        """
        data = {
            "token_efficiency_mentioned": self._detect_pattern(text, r"token|efficiency|optimize.*prompt"),
            "testing_mentioned": self._detect_pattern(text, r"test|A/B|baseline|metric"),
            "prompt_examples": len(re.findall(r"prompt.*:", text, re.IGNORECASE)),
        }

        return data

    def _detect_pattern(self, text: str, pattern: str) -> bool:
        """Helper to detect pattern in text."""
        return bool(re.search(pattern, text, re.IGNORECASE))


def parse_agent_response(
    response_text: str, agent_type: AgentType | str = AgentType.BASE
) -> AgentResponseAnalysis:
    """
    Convenience function to parse agent response.

    Args:
        response_text: Agent response text
        agent_type: Type of agent (for specialized parsing)

    Returns:
        AgentResponseAnalysis with extracted information

    Example:
        analysis = parse_agent_response(response, agent_type="research")
        print(f"Files read: {analysis.agent_specific_data['files_read_count']}")
    """
    parser = AgentResponseParser()
    return parser.parse(response_text, agent_type)
