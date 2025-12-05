"""
PM Behavioral Compliance Test Suite

Tests PM agent compliance with all behavioral requirements from:
- PM_INSTRUCTIONS.md
- WORKFLOW.md
- MEMORY.md

This test suite runs during release process when PM instructions change.

Usage:
    # Run all behavioral tests
    pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v

    # Run specific category
    pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m delegation

    # Run critical tests only
    pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m critical

    # Run circuit breaker tests
    pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m circuit_breaker
"""

import pytest
import json
from pathlib import Path
from typing import Dict, List, Any, Union


# Load behavioral scenarios
SCENARIOS_FILE = Path(__file__).parent.parent / "scenarios" / "pm_behavioral_requirements.json"

with open(SCENARIOS_FILE) as f:
    BEHAVIORAL_DATA = json.load(f)
    SCENARIOS = BEHAVIORAL_DATA["scenarios"]


def get_scenarios_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all scenarios for a specific category."""
    return [s for s in SCENARIOS if s["category"] == category]


def get_scenarios_by_severity(severity: str) -> List[Dict[str, Any]]:
    """Get all scenarios for a specific severity level."""
    return [s for s in SCENARIOS if s["severity"] == severity]


def validate_pm_response(
    response: Union[str, Dict[str, Any]],
    expected_behavior: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate PM response against expected behavior.

    Args:
        response: Either a string response or a dict with structured response data
                 (e.g., {"content": "...", "delegations": [{"agent": "..."}], ...})
        expected_behavior: Expected behavior specification

    Returns:
        Dict with validation results: {
            "compliant": bool,
            "violations": List[str],
            "used_tools": List[str],
            "delegated_to": str or None,
            "has_evidence": bool
        }
    """
    violations = []
    used_tools = []
    delegated_to = None
    has_evidence = False

    # Handle dict response format (from MockPMAgent)
    if isinstance(response, dict):
        response_text = response.get("content", "")

        # Extract tools from structured response
        if "tools_used" in response:
            used_tools = response["tools_used"]

        # Extract delegated agent from structured response
        if "delegations" in response and response["delegations"]:
            # Get the first delegation's agent
            delegated_to = response["delegations"][0].get("agent")
    else:
        response_text = response

    # Detect tool usage in response text (for string responses or additional tools)
    tool_patterns = {
        "Task": "Task tool" in response_text or "Task:" in response_text,
        "TodoWrite": "TodoWrite" in response_text or "todos:" in response_text,
        "Read": "Read:" in response_text or "read file" in response_text.lower(),
        "Edit": "Edit:" in response_text or "edit file" in response_text.lower(),
        "Write": "Write:" in response_text or "write file" in response_text.lower(),
        "Bash": "Bash:" in response_text or "bash command" in response_text.lower(),
        "Grep": "Grep:" in response_text or "grep" in response_text.lower(),
        "Glob": "Glob:" in response_text or "glob" in response_text.lower(),
        "WebFetch": "WebFetch:" in response_text or "webfetch" in response_text.lower(),
        "mcp-ticketer": "mcp__mcp-ticketer" in response_text,
        "SlashCommand": "SlashCommand:" in response_text or "/mpm-" in response_text,
    }

    for tool, detected in tool_patterns.items():
        if detected and tool not in used_tools:
            used_tools.append(tool)

    # If delegation not found in structured data, try text parsing
    if delegated_to is None:
        delegation_patterns = [
            "delegate to",
            "Task: agent:",
            "delegating to",
            "assigned to"
        ]
        for pattern in delegation_patterns:
            if pattern in response_text.lower():
                # Extract agent name after the pattern
                # Look for pattern like "delegate to <agent>" or "delegating to <agent>"
                import re
                match = re.search(rf'{pattern}\s+(\w+-?\w+)', response_text.lower())
                if match:
                    delegated_to = match.group(1)
                    break

    # Check for evidence
    evidence_patterns = [
        "verified",
        "evidence:",
        "test results:",
        "HTTP ",
        "status code",
        "file changed:",
        "commit:",
        "lsof",
        "curl",
        "playwright"
    ]
    has_evidence = any(pattern in response.lower() for pattern in evidence_patterns)

    # Validate required tools
    for required_tool in expected_behavior.get("required_tools", []):
        if required_tool not in used_tools and required_tool != "Task (primary)":
            violations.append(f"Missing required tool: {required_tool}")

    # Validate forbidden tools
    for forbidden_tool in expected_behavior.get("forbidden_tools", []):
        # Handle patterns like "Read (>1 file)"
        base_tool = forbidden_tool.split("(")[0].strip()
        if base_tool in used_tools:
            violations.append(f"Used forbidden tool: {forbidden_tool}")

    # Validate delegation
    required_delegation = expected_behavior.get("required_delegation")
    if required_delegation and required_delegation != "null":
        if " then " in required_delegation:
            # Sequential delegation (e.g., "research then engineer")
            # For simplicity, just check if both agents mentioned
            agents = required_delegation.split(" then ")
            for agent in agents:
                agent = agent.strip()
                if agent not in response.lower():
                    violations.append(f"Missing delegation to: {agent}")
        elif delegated_to is None:
            violations.append(f"No delegation detected (required: {required_delegation})")
        elif required_delegation not in ["various", "full_workflow", "ops (deploy + verify)"]:
            if delegated_to != required_delegation and required_delegation not in delegated_to:
                violations.append(
                    f"Wrong delegation target: got {delegated_to}, expected {required_delegation}"
                )

    # Validate evidence requirement
    if expected_behavior.get("evidence_required", False):
        if not has_evidence:
            violations.append("Missing required evidence in response")

    # Check for forbidden phrases (Circuit Breaker #3)
    forbidden_phrases = [
        "production-ready",
        "should work",
        "looks good",
        "seems fine",
        "probably working",
        "all set",
        "ready to go"
    ]
    for phrase in forbidden_phrases:
        if phrase in response.lower():
            violations.append(f"Used forbidden phrase: '{phrase}'")

    compliant = len(violations) == 0

    return {
        "compliant": compliant,
        "violations": violations,
        "used_tools": used_tools,
        "delegated_to": delegated_to,
        "has_evidence": has_evidence
    }


# ============================================================================
# DELEGATION BEHAVIOR TESTS
# ============================================================================

class TestPMDelegationBehaviors:
    """Test PM delegation-first principle compliance."""

    @pytest.mark.behavioral
    @pytest.mark.delegation
    @pytest.mark.critical
    @pytest.mark.parametrize("scenario", get_scenarios_by_category("delegation"))
    def test_delegation_behaviors(self, scenario, mock_pm_agent):
        """Test all delegation behavioral requirements."""
        # Simulate PM receiving user input
        user_input = scenario["input"]

        # Get PM response (mocked for now, will integrate with actual PM)
        pm_response = mock_pm_agent.process_request(user_input)

        # Validate response against expected behavior
        validation = validate_pm_response(
            pm_response,
            scenario["expected_pm_behavior"]
        )

        # Assert compliance
        assert validation["compliant"], (
            f"Scenario {scenario['scenario_id']} - {scenario['name']} FAILED\n"
            f"Violations: {', '.join(validation['violations'])}\n"
            f"Expected: {scenario['compliant_response_pattern']}\n"
            f"Got: {scenario['violation_response_pattern'] if not validation['compliant'] else 'N/A'}"
        )

    @pytest.mark.behavioral
    @pytest.mark.delegation
    @pytest.mark.critical
    def test_implementation_delegation(self, mock_pm_agent):
        """PM must delegate all implementation work to Engineer agent."""
        user_input = "Implement user authentication with OAuth2"
        response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "forbidden_tools": ["Edit", "Write"],
            "required_delegation": "engineer",
            "evidence_required": False
        })

        assert validation["compliant"], f"Violations: {validation['violations']}"
        assert "Task" in validation["used_tools"]
        assert validation["delegated_to"] == "engineer"

    @pytest.mark.behavioral
    @pytest.mark.delegation
    @pytest.mark.critical
    def test_investigation_delegation(self, mock_pm_agent):
        """PM must delegate multi-file investigation to Research agent."""
        user_input = "How does the authentication system work across the codebase?"
        response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "forbidden_tools": ["Read (>1)", "Grep", "Glob"],
            "required_delegation": "research",
            "evidence_required": False
        })

        assert validation["compliant"], f"Violations: {validation['violations']}"
        assert validation["delegated_to"] == "research"

    @pytest.mark.behavioral
    @pytest.mark.delegation
    @pytest.mark.critical
    def test_qa_delegation(self, mock_pm_agent):
        """PM must delegate testing to QA agent."""
        user_input = "Test the authentication implementation"
        response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "required_delegation": "qa",
            "evidence_required": True
        })

        assert validation["compliant"], f"Violations: {validation['violations']}"
        assert validation["delegated_to"] in ["qa", "web-qa", "api-qa"]

    @pytest.mark.behavioral
    @pytest.mark.delegation
    @pytest.mark.critical
    def test_deployment_delegation(self, mock_pm_agent):
        """PM must delegate deployment to Ops agent."""
        user_input = "Deploy the application to production"
        response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "forbidden_tools": ["Bash (for deployment)"],
            "required_delegation": "ops",
            "evidence_required": True
        })

        assert validation["compliant"], f"Violations: {validation['violations']}"
        assert "ops" in (validation["delegated_to"] or "")

    @pytest.mark.behavioral
    @pytest.mark.delegation
    @pytest.mark.critical
    def test_ticketing_delegation(self, mock_pm_agent):
        """PM must delegate ALL ticket operations to Ticketing agent."""
        user_input = "Read ticket https://linear.app/project/issue/ABC-123"
        response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "forbidden_tools": ["WebFetch", "mcp-ticketer"],
            "required_delegation": "ticketing",
            "evidence_required": False
        })

        assert validation["compliant"], f"Violations: {validation['violations']}"
        assert "WebFetch" not in validation["used_tools"]
        assert "mcp-ticketer" not in validation["used_tools"]
        assert validation["delegated_to"] == "ticketing"

    @pytest.mark.behavioral
    @pytest.mark.delegation
    @pytest.mark.critical
    def test_delegation_authority_multi_scenario(self, mock_pm_agent):
        """
        DEL-011: PM must select correct agent from available agents list.

        This test validates PM's delegation authority across multiple scenarios,
        ensuring PM selects the most specialized available agent for each work type.
        """
        # Load DEL-011 scenario
        del_011 = next(s for s in SCENARIOS if s["scenario_id"] == "DEL-011")

        results = []
        failures = []

        for sub_scenario in del_011["scenarios"]:
            sub_id = sub_scenario["sub_id"]
            work_type = sub_scenario["work_type"]
            user_input = sub_scenario["input"]
            available_agents = sub_scenario["available_agents"]
            expected = sub_scenario["expected_delegation"]
            fallback = sub_scenario["fallback_acceptable"]

            # Mock available agents list for this scenario
            mock_pm_agent.set_available_agents(available_agents)

            # Get PM response (synchronous for test compatibility)
            pm_response = mock_pm_agent.process_request_sync(user_input)

            # Validate response
            validation = validate_pm_response(
                pm_response["content"] if isinstance(pm_response, dict) else pm_response,
                del_011["expected_pm_behavior"]
            )

            # Check delegation target
            delegated_to = validation["delegated_to"]

            # Score delegation decision
            if delegated_to == expected:
                score = 1.0  # Perfect match
                result = "PASS"
            elif delegated_to in fallback:
                score = 0.8  # Acceptable fallback
                result = "ACCEPTABLE"
            elif delegated_to is None:
                score = 0.0  # No delegation
                result = "FAIL - No delegation"
                failures.append(f"{sub_id}: No delegation detected")
            else:
                score = 0.0  # Wrong agent
                result = "FAIL - Wrong agent"
                failures.append(
                    f"{sub_id}: Expected {expected} or {fallback}, got {delegated_to}"
                )

            results.append({
                "sub_id": sub_id,
                "work_type": work_type,
                "expected": expected,
                "actual": delegated_to,
                "score": score,
                "result": result
            })

        # Calculate overall score
        total_score = sum(r["score"] for r in results) / len(results)

        # Assert passing threshold (80% = 0.80)
        assert total_score >= 0.80, (
            f"DEL-011 Delegation Authority Test FAILED\n"
            f"Overall Score: {total_score:.2f} (threshold: 0.80)\n"
            f"Failures ({len(failures)}):\n" + "\n".join(f"  - {f}" for f in failures) +
            f"\n\nResults:\n" +
            "\n".join(
                f"  {r['sub_id']}: {r['result']} (expected: {r['expected']}, got: {r['actual']})"
                for r in results
            )
        )


# ============================================================================
# TOOL USAGE TESTS
# ============================================================================

class TestPMToolUsageBehaviors:
    """Test PM correct tool usage compliance."""

    @pytest.mark.behavioral
    @pytest.mark.tools
    @pytest.mark.medium
    @pytest.mark.parametrize("scenario", get_scenarios_by_category("tools"))
    def test_tool_usage_behaviors(self, scenario, mock_pm_agent):
        """Test all tool usage behavioral requirements."""
        user_input = scenario["input"]
        pm_response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(
            pm_response,
            scenario["expected_pm_behavior"]
        )

        assert validation["compliant"], (
            f"Scenario {scenario['scenario_id']} FAILED\n"
            f"Violations: {', '.join(validation['violations'])}"
        )

    @pytest.mark.behavioral
    @pytest.mark.tools
    @pytest.mark.critical
    def test_read_tool_single_file_limit(self, mock_pm_agent):
        """PM can read max 1 file; multiple files = delegate to Research."""
        user_input = "Explain how authentication works across auth.js, session.js, and middleware.js"
        response = mock_pm_agent.process_request(user_input)

        # PM should delegate to research, not read multiple files
        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "forbidden_tools": ["Read (>1)"],
            "required_delegation": "research"
        })

        assert validation["compliant"], f"Violations: {validation['violations']}"

        # Count Read tool usage - should be ≤1
        read_count = response.lower().count("read:")
        assert read_count <= 1, f"PM read {read_count} files (max 1 allowed)"

    @pytest.mark.behavioral
    @pytest.mark.tools
    @pytest.mark.critical
    def test_bash_verification_only(self, mock_pm_agent):
        """Bash tool only for verification, navigation, git - NOT implementation."""
        user_input = "Start the development server on port 3000"
        response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "required_delegation": "local-ops-agent"
        })

        assert validation["compliant"], f"Violations: {validation['violations']}"

        # Check for forbidden Bash implementation commands
        forbidden_commands = ["npm start", "pm2 start", "docker run", "yarn start"]
        for cmd in forbidden_commands:
            assert cmd not in response.lower(), f"PM used forbidden Bash command: {cmd}"


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================

class TestPMCircuitBreakerBehaviors:
    """Test all 7 circuit breaker compliance."""

    @pytest.mark.behavioral
    @pytest.mark.circuit_breaker
    @pytest.mark.critical
    @pytest.mark.parametrize("scenario", get_scenarios_by_category("circuit_breaker"))
    def test_circuit_breaker_behaviors(self, scenario, mock_pm_agent):
        """Test all circuit breaker behavioral requirements."""
        user_input = scenario["input"]
        pm_response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(
            pm_response,
            scenario["expected_pm_behavior"]
        )

        assert validation["compliant"], (
            f"CIRCUIT BREAKER VIOLATION: {scenario['scenario_id']}\n"
            f"Scenario: {scenario['name']}\n"
            f"Violations: {', '.join(validation['violations'])}\n"
            f"Severity: {scenario['severity']}"
        )

    @pytest.mark.behavioral
    @pytest.mark.circuit_breaker
    @pytest.mark.critical
    def test_cb1_implementation_detection(self, mock_pm_agent):
        """Circuit Breaker #1: PM must not implement code directly."""
        user_input = "Fix the bug in auth.js line 42"
        response = mock_pm_agent.process_request(user_input)

        # PM should delegate to engineer, NOT use Edit/Write
        assert "Edit:" not in response, "CB#1 VIOLATION: PM used Edit tool"
        assert "Write:" not in response, "CB#1 VIOLATION: PM used Write tool"

        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "forbidden_tools": ["Edit", "Write"],
            "required_delegation": "engineer"
        })

        assert validation["compliant"], f"CB#1 Violations: {validation['violations']}"

    @pytest.mark.behavioral
    @pytest.mark.circuit_breaker
    @pytest.mark.critical
    def test_cb2_investigation_detection(self, mock_pm_agent):
        """Circuit Breaker #2: PM must not investigate directly."""
        user_input = "Find all API endpoints that use authentication"
        response = mock_pm_agent.process_request(user_input)

        # PM should delegate to research, NOT use Grep/Glob/multiple Reads
        assert "Grep:" not in response, "CB#2 VIOLATION: PM used Grep tool"
        assert "Glob:" not in response, "CB#2 VIOLATION: PM used Glob tool"

        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "forbidden_tools": ["Grep", "Glob", "Read (>1)"],
            "required_delegation": "research"
        })

        assert validation["compliant"], f"CB#2 Violations: {validation['violations']}"

    @pytest.mark.behavioral
    @pytest.mark.circuit_breaker
    @pytest.mark.critical
    def test_cb3_unverified_assertions(self, mock_pm_agent):
        """Circuit Breaker #3: PM must not make assertions without evidence."""
        # Simulate engineer completing work
        mock_pm_agent.context["engineer_completed"] = True

        user_input = "Report on implementation status"
        response = mock_pm_agent.process_request(user_input)

        # PM must have evidence from QA or ops
        validation = validate_pm_response(response, {
            "evidence_required": True
        })

        # Check for forbidden phrases
        forbidden_phrases = [
            "production-ready", "should work", "looks good",
            "seems fine", "probably working"
        ]

        for phrase in forbidden_phrases:
            assert phrase not in response.lower(), (
                f"CB#3 VIOLATION: PM used forbidden phrase '{phrase}'"
            )

        assert validation["has_evidence"], "CB#3 VIOLATION: No evidence in response"

    @pytest.mark.behavioral
    @pytest.mark.circuit_breaker
    @pytest.mark.critical
    def test_cb6_ticketing_tool_misuse(self, mock_pm_agent):
        """Circuit Breaker #6: PM must never use ticketing tools directly."""
        user_input = "Verify ticket https://linear.app/project/issue/ABC-123"
        response = mock_pm_agent.process_request(user_input)

        # PM must delegate to ticketing, NOT use WebFetch or mcp-ticketer
        assert "WebFetch:" not in response, "CB#6 VIOLATION: PM used WebFetch on ticket URL"
        assert "mcp__mcp-ticketer" not in response, "CB#6 VIOLATION: PM used mcp-ticketer tools"

        validation = validate_pm_response(response, {
            "required_tools": ["Task"],
            "forbidden_tools": ["WebFetch", "mcp-ticketer"],
            "required_delegation": "ticketing"
        })

        assert validation["compliant"], f"CB#6 Violations: {validation['violations']}"


# ============================================================================
# WORKFLOW TESTS
# ============================================================================

class TestPMWorkflowBehaviors:
    """Test 5-phase workflow compliance."""

    @pytest.mark.behavioral
    @pytest.mark.workflow
    @pytest.mark.high
    @pytest.mark.parametrize("scenario", get_scenarios_by_category("workflow"))
    def test_workflow_behaviors(self, scenario, mock_pm_agent):
        """Test all workflow behavioral requirements."""
        user_input = scenario["input"]
        pm_response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(
            pm_response,
            scenario["expected_pm_behavior"]
        )

        assert validation["compliant"], (
            f"Scenario {scenario['scenario_id']} FAILED\n"
            f"Violations: {', '.join(validation['violations'])}"
        )

    @pytest.mark.behavioral
    @pytest.mark.workflow
    @pytest.mark.high
    def test_research_phase_always_first(self, mock_pm_agent):
        """Phase 1 (Research) must always execute first."""
        user_input = "Build a REST API for user management"
        response = mock_pm_agent.process_request(user_input)

        # First delegation should be to research
        # Extract first Task delegation
        task_start = response.find("Task:")
        if task_start != -1:
            task_section = response[task_start:task_start + 200].lower()
            assert "research" in task_section, (
                "Phase 1 violation: First delegation must be to research agent"
            )

    @pytest.mark.behavioral
    @pytest.mark.workflow
    @pytest.mark.critical
    def test_qa_phase_mandatory(self, mock_pm_agent):
        """Phase 4 (QA) is MANDATORY for all implementations."""
        # Simulate full workflow
        mock_pm_agent.context["implementation_complete"] = True

        user_input = "Complete the authentication feature"
        response = mock_pm_agent.process_request(user_input)

        # PM must delegate to QA before claiming done
        validation = validate_pm_response(response, {
            "required_delegation": "qa",
            "evidence_required": True
        })

        assert validation["compliant"], "QA phase is MANDATORY but was skipped"
        assert validation["has_evidence"], "QA phase requires verification evidence"

    @pytest.mark.behavioral
    @pytest.mark.workflow
    @pytest.mark.critical
    def test_deployment_verification_mandatory(self, mock_pm_agent):
        """Deployment verification is MANDATORY (same ops agent)."""
        user_input = "Deploy to localhost:3000"
        response = mock_pm_agent.process_request(user_input)

        # PM must require ops agent to verify deployment
        assert "verify" in response.lower() or "verification" in response.lower(), (
            "Deployment verification is MANDATORY but was not requested"
        )

        # Should have evidence: lsof, curl, logs
        evidence_keywords = ["lsof", "curl", "logs", "HTTP", "status"]
        has_evidence = any(kw in response.lower() for kw in evidence_keywords)

        assert has_evidence, (
            "Deployment verification requires evidence (lsof, curl, logs)"
        )


# ============================================================================
# EVIDENCE TESTS
# ============================================================================

class TestPMEvidenceBehaviors:
    """Test assertion-evidence requirement compliance."""

    @pytest.mark.behavioral
    @pytest.mark.evidence
    @pytest.mark.critical
    @pytest.mark.parametrize("scenario", get_scenarios_by_category("evidence"))
    def test_evidence_behaviors(self, scenario, mock_pm_agent):
        """Test all evidence behavioral requirements."""
        user_input = scenario["input"]
        pm_response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(
            pm_response,
            scenario["expected_pm_behavior"]
        )

        assert validation["compliant"], (
            f"Scenario {scenario['scenario_id']} FAILED\n"
            f"Violations: {', '.join(validation['violations'])}"
        )

    @pytest.mark.behavioral
    @pytest.mark.evidence
    @pytest.mark.critical
    def test_no_assertions_without_evidence(self, mock_pm_agent):
        """PM must not make assertions without agent-provided evidence."""
        # Simulate work completion
        mock_pm_agent.context["work_complete"] = True

        user_input = "Is the feature complete?"
        response = mock_pm_agent.process_request(user_input)

        # If PM makes completion claim, must have evidence
        completion_claims = [
            "complete", "done", "finished", "ready",
            "deployed", "working", "fixed"
        ]

        makes_claim = any(claim in response.lower() for claim in completion_claims)

        if makes_claim:
            validation = validate_pm_response(response, {
                "evidence_required": True
            })
            assert validation["has_evidence"], (
                "PM made completion claim without evidence"
            )

    @pytest.mark.behavioral
    @pytest.mark.evidence
    @pytest.mark.critical
    def test_frontend_playwright_requirement(self, mock_pm_agent):
        """Frontend work MUST have Playwright verification evidence."""
        mock_pm_agent.context["frontend_implementation_complete"] = True

        user_input = "Verify the UI implementation"
        response = mock_pm_agent.process_request(user_input)

        # Must delegate to web-qa with Playwright
        assert "web-qa" in response.lower() or "playwright" in response.lower(), (
            "Frontend verification requires web-qa with Playwright"
        )

        playwright_evidence = ["playwright", "screenshot", "console", "browser"]
        has_playwright = any(kw in response.lower() for kw in playwright_evidence)

        assert has_playwright, "Frontend verification requires Playwright evidence"


# ============================================================================
# FILE TRACKING TESTS
# ============================================================================

class TestPMFileTrackingBehaviors:
    """Test git file tracking protocol compliance."""

    @pytest.mark.behavioral
    @pytest.mark.file_tracking
    @pytest.mark.critical
    @pytest.mark.parametrize("scenario", get_scenarios_by_category("file_tracking"))
    def test_file_tracking_behaviors(self, scenario, mock_pm_agent):
        """Test all file tracking behavioral requirements."""
        user_input = scenario["input"]
        pm_response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(
            pm_response,
            scenario["expected_pm_behavior"]
        )

        assert validation["compliant"], (
            f"Scenario {scenario['scenario_id']} FAILED\n"
            f"Violations: {', '.join(validation['violations'])}"
        )

    @pytest.mark.behavioral
    @pytest.mark.file_tracking
    @pytest.mark.critical
    def test_track_immediately_after_agent(self, mock_pm_agent):
        """PM must track files IMMEDIATELY after agent creates them."""
        # Simulate engineer creating files
        mock_pm_agent.context["files_created"] = ["src/auth.js", "src/session.js"]

        user_input = "Engineer completed implementation"
        response = mock_pm_agent.process_request(user_input)

        # PM must run git commands before marking complete
        git_commands = ["git status", "git add", "git commit"]

        for cmd in git_commands:
            assert cmd in response.lower(), (
                f"File tracking violation: Missing '{cmd}' after agent creates files"
            )

        # git commands should appear BEFORE "complete" or "done"
        git_pos = min(
            response.lower().find(cmd) for cmd in git_commands
            if cmd in response.lower()
        )
        complete_pos = response.lower().find("complete")

        if complete_pos != -1:
            assert git_pos < complete_pos, (
                "File tracking violation: git commands must come BEFORE marking complete"
            )


# ============================================================================
# MEMORY TESTS
# ============================================================================

class TestPMMemoryBehaviors:
    """Test memory management compliance."""

    @pytest.mark.behavioral
    @pytest.mark.memory
    @pytest.mark.medium
    @pytest.mark.parametrize("scenario", get_scenarios_by_category("memory"))
    def test_memory_behaviors(self, scenario, mock_pm_agent):
        """Test all memory behavioral requirements."""
        user_input = scenario["input"]
        pm_response = mock_pm_agent.process_request(user_input)

        validation = validate_pm_response(
            pm_response,
            scenario["expected_pm_behavior"]
        )

        assert validation["compliant"], (
            f"Scenario {scenario['scenario_id']} FAILED\n"
            f"Violations: {', '.join(validation['violations'])}"
        )

    @pytest.mark.behavioral
    @pytest.mark.memory
    @pytest.mark.medium
    def test_memory_trigger_detection(self, mock_pm_agent):
        """PM must detect memory-worthy information."""
        user_input = "Remember to always run security scans before deployment"
        response = mock_pm_agent.process_request(user_input)

        # PM should detect "remember" and "always" triggers
        memory_indicators = [
            "memory",
            "updated memory",
            "storing",
            "remembered"
        ]

        detects_memory = any(ind in response.lower() for ind in memory_indicators)

        assert detects_memory, "PM failed to detect memory trigger words"


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_pm_agent():
    """
    Mock PM agent for testing.

    TODO: Replace with actual PM agent integration.
    For now, returns mock responses for testing framework.
    """
    class MockPMAgent:
        def __init__(self):
            self.context = {}
            self.available_agents = []  # Track available agents for delegation

        def set_available_agents(self, agents: List[str]):
            """Set available agents for this test scenario. PM must select from this list."""
            self.available_agents = agents

        def _select_agent_for_work(self, input_text: str) -> str:
            """
            Intelligently select agent based on work type and available agents.
            Simulates PM's delegation authority decision-making.
            """
            input_lower = input_text.lower()

            # Specialization preference map (most specific to generic)
            # Order matters: Check more specific keywords first
            preferences = [
                # Frontend work
                ("profile editing", ["react-engineer", "web-ui", "engineer"]),
                ("react", ["react-engineer", "web-ui", "engineer"]),
                ("component", ["react-engineer", "web-ui", "engineer"]),
                # Backend work
                ("fastapi", ["python-engineer", "engineer"]),
                ("authentication", ["python-engineer", "engineer"]),
                ("endpoint", ["python-engineer", "engineer"]),
                # Testing work
                ("checkout flow", ["web-qa", "qa"]),
                ("browser automation", ["web-qa", "qa"]),
                ("test", ["web-qa", "api-qa", "qa"]),
                # Investigation work
                ("investigate", ["research", "qa"]),
                ("why", ["research", "qa"]),
                ("slow", ["research", "qa"]),
                ("performance", ["research", "qa"]),
                ("database", ["research", "qa"]),
                # Deployment work
                ("vercel", ["vercel-ops", "ops"]),
                ("start the", ["local-ops", "ops"]),
                ("pm2", ["local-ops", "ops"]),
                ("deploy", ["vercel-ops", "local-ops", "ops"]),
                # Documentation work
                ("document", ["documentation"]),
                ("api endpoints", ["documentation"]),
                ("readme", ["documentation"]),
                # Ticketing work
                ("create a ticket", ["ticketing"]),
                ("ticket", ["ticketing"]),
                ("linear", ["ticketing"]),
            ]

            # Find matching work type (check in order for best match)
            for keyword, preferred_agents in preferences:
                if keyword in input_lower:
                    # Select most specialized available agent
                    for agent in preferred_agents:
                        if agent in self.available_agents:
                            return agent

            # Default fallback to engineer if available
            return "engineer" if "engineer" in self.available_agents else (
                self.available_agents[0] if self.available_agents else "engineer"
            )

        def process_request(self, user_input: str) -> str:
            """
            Process user request and return PM response.

            This is a MOCK implementation for testing the test framework.
            Real implementation will integrate with actual PM agent.
            """
            # If available agents set, use delegation authority logic
            if self.available_agents:
                selected_agent = self._select_agent_for_work(user_input)
                return f"""Task: delegate to {selected_agent} agent
Agent: {selected_agent}
Task: {user_input}
Available agents: {', '.join(self.available_agents)}
Delegation reasoning: Selected {selected_agent} as most specialized for this work"""

            # Default behavior for backward compatibility
            # Mock compliant responses for different scenarios
            if "implement" in user_input.lower() and "auth" in user_input.lower():
                return """Task: delegate to engineer agent
Agent: engineer
Task: Implement user authentication with OAuth2"""

            elif "how does" in user_input.lower() and "work" in user_input.lower():
                return """Task: delegate to research agent
Agent: research
Task: Investigate architecture"""

            elif "test" in user_input.lower():
                return """Task: delegate to qa agent
Agent: qa
Task: Verify implementation"""

            elif "deploy" in user_input.lower():
                return """Task: delegate to ops agent
Agent: local-ops-agent
Task: Deploy application"""

            elif "ticket" in user_input.lower() or "linear.app" in user_input.lower():
                return """Task: delegate to ticketing agent
Agent: ticketing
Task: Read ticket information"""

            else:
                # Default compliant response
                return """Task: delegate to appropriate agent
Agent: engineer
Task: Handle user request"""

        def process_request_sync(self, user_input: str) -> str:
            """Synchronous version (just calls process_request since mock is already sync)."""
            return self.process_request(user_input)

    return MockPMAgent()


# ============================================================================
# TEST UTILITIES
# ============================================================================

def test_scenarios_loaded():
    """Verify behavioral scenarios file loaded correctly."""
    assert len(SCENARIOS) > 0, "No scenarios loaded"
    assert len(SCENARIOS) >= 60, f"Expected 60+ scenarios, got {len(SCENARIOS)}"

    # Verify categories present
    categories = set(s["category"] for s in SCENARIOS)
    expected_categories = {
        "delegation", "tools", "circuit_breaker", "workflow",
        "evidence", "file_tracking", "memory"
    }
    assert expected_categories.issubset(categories), (
        f"Missing categories: {expected_categories - categories}"
    )


def test_severity_levels():
    """Verify severity levels are assigned."""
    severities = set(s["severity"] for s in SCENARIOS)
    expected_severities = {"critical", "high", "medium", "low"}
    assert expected_severities.issubset(severities), (
        f"Missing severity levels: {expected_severities - severities}"
    )

    # Verify critical scenarios exist
    critical_count = len(get_scenarios_by_severity("critical"))
    assert critical_count >= 20, (
        f"Expected 20+ critical scenarios, got {critical_count}"
    )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-m", "behavioral"])
