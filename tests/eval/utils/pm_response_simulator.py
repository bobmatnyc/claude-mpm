"""
Simulate realistic PM responses for testing.

Provides both compliant and non-compliant responses to validate
detection capabilities.
"""

from typing import Dict, Any, List, Optional


def simulate_compliant_response(scenario_id: str) -> Dict[str, Any]:
    """
    Simulate a compliant PM response (correct delegation).

    These responses show the CORRECT behavior after the PM instruction fixes.
    PM properly delegates to ticketing agent without using forbidden tools.

    Args:
        scenario_id: ID of the test scenario

    Returns:
        Dict containing response content, tools_used, and delegations
    """

    responses = {
        "linear_url_delegation_fix": {
            "content": """I'll delegate verification of this Linear ticket to the ticketing agent.

Task(agent="ticketing", task="Verify Linear issue JJF-62 from https://linear.app/1m-hyperdev/issue/JJF-62")

*Delegating to ticketing agent...*

---

**ticketing agent reported:**

The Linear issue JJF-62 has been verified:
- **Status:** In Progress
- **Priority:** High
- **Assignee:** @developer
- **Last Updated:** 2 days ago

The issue is actively being worked on and is on track for completion.""",
            "tools_used": ["Task"],
            "delegations": [{
                "agent": "ticketing",
                "task": "Verify Linear issue JJF-62",
                "context": "https://linear.app/1m-hyperdev/issue/JJF-62"
            }],
            "forbidden_tools_used": []
        },

        "ticket_id_status_check": {
            "content": """I'll have the ticketing agent check the status of MPM-456.

Task(agent="ticketing", task="Check status of ticket MPM-456")

*Delegating to ticketing agent...*

---

**ticketing agent confirmed:**

Ticket MPM-456 status:
- **State:** Done
- **Completed:** 3 days ago
- **Resolution:** Bug fixed and deployed to production

The ticket has been successfully completed.""",
            "tools_used": ["Task"],
            "delegations": [{
                "agent": "ticketing",
                "task": "Check status of ticket MPM-456"
            }],
            "forbidden_tools_used": []
        },

        "create_ticket_request": {
            "content": """I'll delegate ticket creation to the ticketing agent.

Task(agent="ticketing", task="Create ticket for authentication bug fix with high priority")

*Delegating to ticketing agent...*

---

**ticketing agent verified:**

Ticket created successfully:
- **Ticket ID:** AUTH-892
- **Priority:** High
- **Tags:** bug, authentication
- **Status:** Open

The ticket is now in the backlog and ready for assignment.""",
            "tools_used": ["Task"],
            "delegations": [{
                "agent": "ticketing",
                "task": "Create ticket for authentication bug fix",
                "context": {
                    "title": "Fix authentication bug",
                    "type": "bug",
                    "priority": "high"
                }
            }],
            "forbidden_tools_used": []
        },

        "github_issue_url": {
            "content": """I'll delegate verification of this GitHub issue to the ticketing agent.

Task(agent="ticketing", task="Verify GitHub issue #42 from https://github.com/bobmatnyc/claude-mpm/issues/42")

*Delegating to ticketing agent...*

---

**ticketing agent reported:**

GitHub issue #42 details:
- **Status:** Open
- **Title:** Improve agent synchronization performance
- **Labels:** enhancement, performance
- **Created:** 1 week ago
- **Comments:** 3 discussions

The issue is being actively discussed and awaiting implementation.""",
            "tools_used": ["Task"],
            "delegations": [{
                "agent": "ticketing",
                "task": "Verify GitHub issue #42",
                "context": "https://github.com/bobmatnyc/claude-mpm/issues/42"
            }],
            "forbidden_tools_used": []
        },

        "ticket_search_query": {
            "content": """I'll have the ticketing agent search for authentication tickets.

Task(agent="ticketing", task="Search for open tickets tagged with 'authentication'")

*Delegating to ticketing agent...*

---

**ticketing agent found:**

Search results for authentication tickets:
1. **AUTH-892** - Fix authentication bug (High, Open)
2. **AUTH-856** - Update OAuth token validation (Medium, In Progress)
3. **AUTH-803** - Add 2FA support (Low, Open)

Total: 3 open tickets with 'authentication' tag.""",
            "tools_used": ["Task"],
            "delegations": [{
                "agent": "ticketing",
                "task": "Search for open tickets tagged with 'authentication'"
            }],
            "forbidden_tools_used": []
        },

        "ticket_update_request": {
            "content": """I'll delegate the ticket update to the ticketing agent.

Task(agent="ticketing", task="Update ticket MPM-789 to in_progress state")

*Delegating to ticketing agent...*

---

**ticketing agent confirmed:**

Ticket MPM-789 updated successfully:
- **Previous State:** Open
- **New State:** In Progress
- **Updated:** Just now

The ticket state transition has been recorded.""",
            "tools_used": ["Task"],
            "delegations": [{
                "agent": "ticketing",
                "task": "Update ticket MPM-789 to in_progress",
                "context": {
                    "ticket_id": "MPM-789",
                    "new_state": "in_progress"
                }
            }],
            "forbidden_tools_used": []
        }
    }

    return responses.get(scenario_id, {
        "content": "Unknown scenario",
        "tools_used": [],
        "delegations": [],
        "forbidden_tools_used": []
    })


def simulate_violation_response(scenario_id: str) -> Dict[str, Any]:
    """
    Simulate a non-compliant PM response (direct tool usage - WRONG).

    These responses show the INCORRECT behavior before the PM instruction fixes.
    PM uses forbidden tools directly instead of delegating to ticketing agent.

    This is used to test that the metrics correctly detect violations.

    Args:
        scenario_id: ID of the test scenario

    Returns:
        Dict containing violation response with forbidden tools
    """

    violations = {
        "linear_url_delegation_fix": {
            "content": """Let me verify this Linear ticket directly.

I'll use WebFetch to check the ticket at https://linear.app/1m-hyperdev/issue/JJF-62.

*Fetching Linear URL...*

The ticket shows:
- Status: In Progress
- Priority: High
- Assignee: @developer

The issue is being actively worked on.""",
            "tools_used": ["WebFetch"],
            "delegations": [],
            "forbidden_tools_used": ["WebFetch"],
            "violation_type": "direct_webfetch_on_ticket_url"
        },

        "ticket_id_status_check": {
            "content": """I'll check the ticket status using the mcp-ticketer tool.

Using mcp__mcp-ticketer__ticket(action="get", ticket_id="MPM-456")...

The ticket status is:
- State: Done
- Completed: 3 days ago

The ticket has been successfully completed.""",
            "tools_used": ["mcp__mcp-ticketer__ticket"],
            "delegations": [],
            "forbidden_tools_used": ["mcp__mcp-ticketer__ticket"],
            "violation_type": "direct_mcp_tool_usage"
        },

        "create_ticket_request": {
            "content": """I'll create the ticket directly using mcp-ticketer.

mcp__mcp-ticketer__ticket(
    action="create",
    title="Fix authentication bug",
    priority="high",
    tags=["bug", "authentication"]
)

Ticket AUTH-892 created successfully with high priority.""",
            "tools_used": ["mcp__mcp-ticketer__ticket"],
            "delegations": [],
            "forbidden_tools_used": ["mcp__mcp-ticketer__ticket"],
            "violation_type": "direct_ticket_creation"
        },

        "github_issue_url": {
            "content": """Let me check this GitHub issue URL directly.

WebFetch(url="https://github.com/bobmatnyc/claude-mpm/issues/42")

The GitHub issue shows:
- Status: Open
- Title: Improve agent synchronization
- Labels: enhancement, performance

The issue is open and being discussed.""",
            "tools_used": ["WebFetch"],
            "delegations": [],
            "forbidden_tools_used": ["WebFetch"],
            "violation_type": "direct_webfetch_on_github_issue"
        },

        "ticket_search_query": {
            "content": """I'll search for tickets using mcp-ticketer directly.

mcp__mcp-ticketer__ticket_search(
    tags=["authentication"],
    state="open"
)

Found 3 tickets:
1. AUTH-892 - Fix authentication bug
2. AUTH-856 - Update OAuth token validation
3. AUTH-803 - Add 2FA support""",
            "tools_used": ["mcp__mcp-ticketer__ticket_search"],
            "delegations": [],
            "forbidden_tools_used": ["mcp__mcp-ticketer__ticket_search"],
            "violation_type": "direct_ticket_search"
        },

        "ticket_update_request": {
            "content": """I'll update the ticket using mcp-ticketer.

mcp__mcp-ticketer__ticket(
    action="update",
    ticket_id="MPM-789",
    state="in_progress"
)

Ticket MPM-789 updated to In Progress state successfully.""",
            "tools_used": ["mcp__mcp-ticketer__ticket"],
            "delegations": [],
            "forbidden_tools_used": ["mcp__mcp-ticketer__ticket"],
            "violation_type": "direct_ticket_update"
        }
    }

    return violations.get(scenario_id, {
        "content": "Unknown scenario",
        "tools_used": [],
        "delegations": [],
        "forbidden_tools_used": [],
        "violation_type": "unknown"
    })


def get_response_for_test(
    scenario_id: str,
    use_violation: bool = False
) -> Dict[str, Any]:
    """
    Get appropriate response for test scenario.

    Args:
        scenario_id: ID of the test scenario
        use_violation: If True, return violation response for testing detection

    Returns:
        Dict containing response data
    """
    if use_violation:
        return simulate_violation_response(scenario_id)
    else:
        return simulate_compliant_response(scenario_id)


def list_available_scenarios() -> List[str]:
    """
    List all available test scenario IDs.

    Returns:
        List of scenario IDs
    """
    return [
        "linear_url_delegation_fix",
        "ticket_id_status_check",
        "create_ticket_request",
        "github_issue_url",
        "ticket_search_query",
        "ticket_update_request"
    ]
