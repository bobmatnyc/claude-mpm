"""
Pytest configuration for agent evaluation tests.

Provides fixtures and configuration for BASE_AGENT and specialized agent testing.
Extends the main tests/eval/conftest.py with agent-specific fixtures.
"""

import pytest

# Import shared fixtures from agents/shared
from .shared.agent_fixtures import (
    base_agent_template,
    engineer_agent_template,
    mock_base_agent_response,
    mock_deployment_env,
    mock_docker_env,
    mock_engineer_agent_response,
    mock_filesystem,
    mock_git_repo,
    mock_qa_agent_response,
    mock_research_agent_response,
    qa_agent_template,
    research_agent_template,
    sample_javascript_files,
    sample_python_files,
    temp_project_dir,
)

# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Register custom markers for agent tests."""
    config.addinivalue_line("markers", "base_agent: BASE_AGENT tests")
    config.addinivalue_line("markers", "research: Research agent tests")
    config.addinivalue_line("markers", "engineer: Engineer agent tests")
    config.addinivalue_line("markers", "qa: QA agent tests")
    config.addinivalue_line("markers", "ops: Ops agent tests")
    config.addinivalue_line("markers", "documentation: Documentation agent tests")
    config.addinivalue_line("markers", "prompt_engineer: Prompt Engineer agent tests")
    config.addinivalue_line("markers", "agent_integration: Agent integration tests")


# ============================================================================
# MOCK AGENT FIXTURES
# ============================================================================


@pytest.fixture
async def mock_agent():
    """
    Mock agent that simulates agent behavior for testing.

    Returns mock responses based on agent_type configuration.

    Example:
        async def test_agent(mock_agent):
            mock_agent.set_agent_type(AgentType.RESEARCH)
            response = await mock_agent.process_request("Analyze code")
    """

    class MockAgent:
        """Mock agent for testing with configurable behavior."""

        def __init__(self):
            self.agent_type = "base"
            self.responses = {
                "base": mock_base_agent_response,
                "research": mock_research_agent_response,
                "engineer": mock_engineer_agent_response,
                "qa": mock_qa_agent_response,
            }

        def set_agent_type(self, agent_type: str):
            """Set agent type for response generation."""
            self.agent_type = agent_type

        async def process_request(self, input_text: str, context=None):
            """Process request and return mock response."""
            # Return appropriate mock response based on agent type
            response_fixture = self.responses.get(
                self.agent_type, self.responses["base"]
            )

            # If using fixture, get the text
            if callable(response_fixture):
                response_data = response_fixture()
                response_text = response_data["text"]
            else:
                response_text = response_fixture.get("text", "Mock response")

            return {
                "content": response_text,
                "agent_type": self.agent_type,
                "input": input_text,
                "context": context,
            }

        def process_request_sync(self, input_text: str, context=None):
            """Synchronous version for non-async tests."""
            import asyncio

            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.process_request(input_text, context))

    return MockAgent()


# ============================================================================
# AGENT TYPE FIXTURES
# ============================================================================


@pytest.fixture
def base_agent_type():
    """Return BASE agent type string."""
    return "base"


@pytest.fixture
def research_agent_type():
    """Return Research agent type string."""
    return "research"


@pytest.fixture
def engineer_agent_type():
    """Return Engineer agent type string."""
    return "engineer"


@pytest.fixture
def qa_agent_type():
    """Return QA agent type string."""
    return "qa"


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def large_file_scenario():
    """Scenario for testing large file handling (Research agent)."""
    return {
        "scenario_id": "RES-001",
        "input": "Analyze authentication implementation in auth_service.py (50KB file)",
        "file_size": 50000,
        "expected_behavior": {
            "should_check_file_size": True,
            "should_use_document_summarizer": True,
            "should_not_read_directly": True,
        },
    }


@pytest.fixture
def code_minimization_scenario():
    """Scenario for testing code minimization (Engineer agent)."""
    return {
        "scenario_id": "ENG-001",
        "input": "Implement JWT token validation",
        "expected_behavior": {
            "should_search_first": True,
            "should_report_loc_delta": True,
            "should_consolidate_duplicates": True,
        },
    }


@pytest.fixture
def test_execution_scenario():
    """Scenario for testing safe test execution (QA agent)."""
    return {
        "scenario_id": "QA-001",
        "input": "Run tests for authentication module",
        "expected_behavior": {
            "should_check_package_json": True,
            "should_use_ci_mode": True,
            "should_not_use_watch_mode": True,
            "should_verify_process_cleanup": True,
        },
    }
