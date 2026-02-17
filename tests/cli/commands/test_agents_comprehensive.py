"""
Comprehensive unit tests for the agents command module.

This module provides extensive test coverage for all agents command functionality
to serve as a safety net during refactoring.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.commands.agents import AgentsCommand, manage_agents
from claude_mpm.cli.shared import CommandResult
from claude_mpm.services.cli.agent_listing_service import AgentInfo, AgentTierInfo


# Module-level fixtures to share across all test classes
@pytest.fixture
def mock_deployment_service():
    """Create a mock deployment service with all required methods."""
    service = MagicMock()

    # Mock list_available_agents
    service.list_available_agents.return_value = [
        {
            "file": "engineer.json",
            "name": "Engineer",
            "description": "Software engineering specialist",
            "version": "1.0.0",
        },
        {
            "file": "qa.json",
            "name": "QA",
            "description": "Quality assurance specialist",
            "version": "1.0.0",
        },
    ]

    # Mock verify_deployment
    service.verify_deployment.return_value = {
        "agents_found": [
            {
                "file": "engineer.md",
                "name": "Engineer",
                "path": "/project/.claude/agents/engineer.md",
            },
            {
                "file": "qa.md",
                "name": "QA",
                "path": "/project/.claude/agents/qa.md",
            },
        ],
        "warnings": [],
    }

    # Mock list_agents_by_tier
    service.list_agents_by_tier.return_value = {
        "project": ["engineer", "qa"],
        "user": ["documentation"],
        "system": ["base", "pm"],
    }

    # Mock deploy_system_agents
    service.deploy_system_agents.return_value = {
        "deployed_count": 2,
        "deployed": [{"name": "engineer"}, {"name": "qa"}],
        "updated": [],
        "errors": [],
    }

    # Mock deploy_project_agents
    service.deploy_project_agents.return_value = {
        "deployed_count": 1,
        "deployed": [{"name": "custom"}],
        "updated": [],
        "errors": [],
    }

    # Mock clean_deployment
    service.clean_deployment.return_value = {
        "cleaned_count": 3,
        "removed": ["engineer.md", "qa.md", "custom.md"],
    }

    # Mock get_agent_details
    service.get_agent_details.return_value = {
        "name": "Engineer",
        "version": "1.0.0",
        "description": "Software engineering specialist",
        "path": "/project/.claude/agents/engineer.md",
    }

    # Mock fix_deployment
    service.fix_deployment.return_value = {
        "fixes_applied": [
            "Fixed frontmatter formatting",
            "Corrected version field",
        ],
    }

    # Mock dependency methods
    service.check_dependencies.return_value = {
        "missing_dependencies": ["numpy", "pandas"],
    }

    service.install_dependencies.return_value = {
        "installed_count": 2,
        "installed": ["numpy", "pandas"],
    }

    service.list_dependencies.return_value = {
        "dependencies": [
            {"name": "numpy", "installed": True},
            {"name": "pandas", "installed": True},
            {"name": "scipy", "installed": False},
        ],
    }

    service.fix_dependencies.return_value = {
        "fixes_applied": ["Installed numpy", "Installed pandas"],
    }

    return service


@pytest.fixture
def mock_listing_service():
    """Create a mock listing service."""
    service = MagicMock()

    # Mock list_system_agents - returns list of AgentInfo objects
    service.list_system_agents.return_value = [
        AgentInfo(
            name="Engineer",
            type="agent",
            tier="system",
            path="/path/to/engineer.json",
            description="Software engineering specialist",
            specializations=["coding", "architecture"],
            version="1.0.0",
        ),
        AgentInfo(
            name="QA",
            type="agent",
            tier="system",
            path="/path/to/qa.json",
            description="Quality assurance specialist",
            specializations=["testing", "quality"],
            version="1.0.0",
        ),
    ]

    # Mock list_deployed_agents - returns tuple of (list of AgentInfo, list of warnings)
    service.list_deployed_agents.return_value = (
        [
            AgentInfo(
                name="Engineer",
                type="agent",
                tier="project",
                path="/project/.claude/agents/engineer.md",
                description="Software engineering specialist",
                specializations=["coding"],
                version="1.0.0",
                deployed=True,
            ),
            AgentInfo(
                name="QA",
                type="agent",
                tier="project",
                path="/project/.claude/agents/qa.md",
                description="Quality assurance specialist",
                specializations=["testing"],
                version="1.0.0",
                deployed=True,
            ),
        ],
        [],  # warnings
    )

    # Mock list_agents_by_tier - returns AgentTierInfo object
    service.list_agents_by_tier.return_value = AgentTierInfo(
        project=[
            AgentInfo(
                name="Engineer",
                type="agent",
                tier="project",
                path="/project/.claude/agents/engineer.md",
                description="Project Engineer",
                specializations=["coding"],
                version="1.0.0",
            ),
        ],
        user=[
            AgentInfo(
                name="Documentation",
                type="agent",
                tier="user",
                path="/user/.claude/agents/documentation.md",
                description="User Documentation Agent",
                specializations=["docs"],
                version="1.0.0",
            ),
        ],
        system=[
            AgentInfo(
                name="Base",
                type="agent",
                tier="system",
                path="/system/agents/base.json",
                description="Base System Agent",
                specializations=["general"],
                version="1.0.0",
            ),
            AgentInfo(
                name="PM",
                type="agent",
                tier="system",
                path="/system/agents/pm.json",
                description="Project Manager Agent",
                specializations=["management"],
                version="1.0.0",
            ),
        ],
    )

    # Mock get_agent_details - returns agent detail dictionary
    service.get_agent_details.return_value = {
        "name": "engineer",
        "file": "engineer.md",
        "path": "/project/.claude/agents/engineer.md",
        "version": "1.0.0",
        "description": "Software engineering specialist",
        "tier": "project",
        "specializations": ["coding"],
    }

    # Mock find_agent - returns AgentInfo or None
    service.find_agent.return_value = AgentInfo(
        name="Engineer",
        type="agent",
        tier="project",
        path="/project/.claude/agents/engineer.md",
        description="Software engineering specialist",
        specializations=["coding"],
        version="1.0.0",
    )

    return service


@pytest.fixture
def mock_git_sync_service():
    """Create a mock GitSourceSyncService."""
    service = MagicMock()

    # Mock sync_repository (Phase 1: sync to cache)
    service.sync_repository.return_value = {
        "synced": True,
        "agent_count": 10,
        "cache_dir": "/home/user/.claude-mpm/cache/agents",
        "files_updated": 5,
        "files_cached": 5,
    }

    # Mock deploy_agents_to_project (Phase 2: deploy to project)
    service.deploy_agents_to_project.return_value = {
        "deployed": ["engineer.md", "qa.md"],
        "updated": ["research.md"],
        "skipped": ["base.md"],
        "failed": [],
        "deployment_dir": "/project/.claude/agents",
    }

    return service


@pytest.fixture
def mock_dependency_service():
    """Create a mock dependency service."""
    service = MagicMock()

    # Mock check_dependencies
    service.check_dependencies.return_value = {
        "success": True,
        "report": "Agent Dependencies Check:\nMissing dependencies:\n  - numpy",
        "python_dependencies": [{"name": "numpy", "installed": False}],
        "system_dependencies": [],
    }

    # Mock install_dependencies (default: nothing to install)
    service.install_dependencies.return_value = {
        "success": True,
        "missing_count": 0,
        "installed": [],
        "missing_dependencies": [],
        "fully_resolved": True,
    }

    # Mock list_dependencies
    service.list_dependencies.return_value = {
        "success": True,
        "python_dependencies": ["numpy", "pandas", "scipy"],
        "system_dependencies": [],
        "per_agent": {},
    }

    # Mock fix_dependencies
    service.fix_dependencies.return_value = {
        "success": True,
        "message": "Dependencies fixed",
        "missing_python": ["numpy"],
        "installed_python": ["numpy"],
        "final_status": {"resolved": True},
    }

    return service


@pytest.fixture
def mock_cleanup_service():
    """Create a mock cleanup service."""
    service = MagicMock()

    # Mock clean_deployed_agents (uses cleaned_count, not removed)
    service.clean_deployed_agents.return_value = {
        "cleaned_count": 3,
    }

    # Mock clean_orphaned_agents
    service.clean_orphaned_agents.return_value = {
        "orphaned": [],
        "removed": [],
        "errors": [],
    }

    return service


@pytest.fixture
def mock_validation_service():
    """Create a mock validation service."""
    service = MagicMock()

    # Mock fix_all_agents
    service.fix_all_agents.return_value = {
        "success": True,
        "dry_run": False,
        "total_agents": 2,
        "agents_checked": 2,
        "total_issues_found": 2,
        "total_corrections_made": 2,
        "total_corrections_available": 2,
        "agents_fixed": ["engineer.md", "qa.md"],
        "agents_with_errors": [],
        "results": [
            {
                "agent": "engineer",
                "path": "/path/to/engineer.md",
                "was_valid": False,
                "errors_found": 1,
                "warnings_found": 0,
                "corrections_made": 1,
                "corrections_available": 1,
            },
            {
                "agent": "qa",
                "path": "/path/to/qa.md",
                "was_valid": False,
                "errors_found": 1,
                "warnings_found": 0,
                "corrections_made": 1,
                "corrections_available": 1,
            },
        ],
    }

    # Mock fix_single_agent
    service.fix_single_agent.return_value = {
        "success": True,
        "agent": "engineer",
        "path": "/path/to/engineer.md",
        "was_valid": False,
        "errors_found": 1,
        "corrections_made": 1,
        "dry_run": False,
    }

    return service


@pytest.fixture
def command(
    mock_deployment_service,
    mock_listing_service,
    mock_dependency_service,
    mock_cleanup_service,
    mock_validation_service,
):
    """Create an AgentsCommand instance with mocked services."""
    cmd = AgentsCommand()
    cmd._deployment_service = mock_deployment_service
    cmd._listing_service = mock_listing_service
    cmd._dependency_service = mock_dependency_service
    cmd._cleanup_service = mock_cleanup_service
    cmd._validation_service = mock_validation_service
    return cmd


@pytest.fixture
def mock_args():
    """Create mock arguments object."""
    args = MagicMock()
    args.format = "text"
    args.agents_command = None
    args.verbose = False
    args.quiet = False
    args.preset = None  # Explicitly set to None to avoid MagicMock behavior
    args.agent = None  # Explicitly set to None for dependency commands
    args.dry_run = False  # Explicitly set to False for dependency commands
    args.all = False  # Explicitly set to False for fix commands
    args.agent_name = None  # Explicitly set to None for view/fix commands
    return args


class TestAgentsCommand:
    """Test suite for AgentsCommand class."""


class TestListingOperations(TestAgentsCommand):
    """Test listing operations for agents."""

    def test_list_system_agents_text_format(self, command, mock_args):
        """Test listing system agents in text format."""
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.deployed = False
        mock_args.by_tier = False

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert result.exit_code == 0
        assert "Listed 2 agent templates" in result.message
        # Check that the formatted output was printed (single call with full text)
        printed_output = str(mock_print.call_args_list[0][0][0])
        assert "Available Agents:" in printed_output
        assert "engineer.json" in printed_output
        assert "Name: Engineer" in printed_output

    def test_list_system_agents_json_format(self, command, mock_args):
        """Test listing system agents in JSON format."""
        mock_args.agents_command = "list"
        mock_args.format = "json"
        mock_args.system = True
        mock_args.deployed = False
        mock_args.by_tier = False

        result = command.run(mock_args)

        assert result.success
        assert result.data["count"] == 2
        assert len(result.data["agents"]) == 2
        assert result.data["agents"][0]["name"] == "Engineer"

    def test_list_deployed_agents_text_format(self, command, mock_args):
        """Test listing deployed agents in text format."""
        mock_args.agents_command = "list"
        mock_args.deployed = True
        mock_args.system = False
        mock_args.by_tier = False

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Listed 2 deployed agents" in result.message
        # Check that the formatted output contains expected content
        printed_output = str(mock_print.call_args_list[0][0][0])
        assert "Available Agents:" in printed_output
        assert "engineer.md" in printed_output

    def test_list_deployed_agents_with_warnings(
        self, command, mock_args, mock_listing_service
    ):
        """Test listing deployed agents with warnings."""
        # Mock listing service to return agents with warnings
        mock_listing_service.list_deployed_agents.return_value = (
            [
                AgentInfo(
                    name="Test",
                    type="agent",
                    tier="project",
                    path="/project/.claude/agents/test.md",
                    description="Test agent",
                    specializations=[],
                    version="1.0.0",
                    deployed=True,
                ),
            ],
            ["Missing version field", "Invalid frontmatter"],  # warnings
        )

        mock_args.agents_command = "list"
        mock_args.deployed = True
        mock_args.system = False
        mock_args.by_tier = False

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        # Check that warnings were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Warnings:" in str(call) for call in print_calls)
        assert any("Missing version field" in str(call) for call in print_calls)

    def test_list_agents_by_tier_text_format(self, command, mock_args):
        """Test listing agents grouped by tier in text format."""
        mock_args.agents_command = "list"
        mock_args.by_tier = True

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Agents listed by tier" in result.message
        # Check that the formatted output contains expected content
        printed_output = str(mock_print.call_args_list[0][0][0])
        assert "Agents by Tier/Precedence:" in printed_output
        assert "PROJECT:" in printed_output
        assert "Engineer" in printed_output

    def test_list_agents_by_tier_json_format(self, command, mock_args):
        """Test listing agents by tier in JSON format."""
        mock_args.agents_command = "list"
        mock_args.by_tier = True
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        # Data contains dicts with agent info, not just strings
        assert len(result.data["project"]) == 1
        assert result.data["project"][0]["name"] == "Engineer"
        assert len(result.data["user"]) == 1
        assert result.data["user"][0]["name"] == "Documentation"
        assert len(result.data["system"]) == 2
        assert result.data["system"][0]["name"] == "Base"
        assert result.data["system"][1]["name"] == "PM"

    def test_list_no_option_specified(self, command, mock_args):
        """Test list command with no specific option."""
        mock_args.agents_command = "list"
        mock_args.system = False
        mock_args.deployed = False
        mock_args.by_tier = False

        with patch("builtins.print"):
            result = command.run(mock_args)

        assert not result.success
        assert result.exit_code == 1
        assert "No list option specified" in result.message


class TestDeploymentOperations(TestAgentsCommand):
    """Test deployment operations for agents."""

    def test_deploy_agents_success(self, command, mock_args, mock_git_sync_service):
        """Test successful agent deployment using GitSourceSyncService."""
        mock_args.agents_command = "deploy"

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.GitSourceSyncService",
            return_value=mock_git_sync_service,
        ):
            with patch("builtins.print") as mock_print:
                result = command.run(mock_args)

        assert result.success
        # Default mock returns 2 deployed + 1 updated = 3 total
        assert "Deployed 3 agents from cache" in result.message
        assert result.data["total_deployed"] == 3

        # Verify GitSourceSyncService methods were called
        mock_git_sync_service.sync_repository.assert_called_once_with(force=False)
        mock_git_sync_service.deploy_agents_to_project.assert_called_once()

    def test_deploy_agents_force(self, command, mock_args, mock_git_sync_service):
        """Test force deployment of agents."""
        mock_args.agents_command = "force-deploy"

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.GitSourceSyncService",
            return_value=mock_git_sync_service,
        ):
            result = command.run(mock_args)

        assert result.success
        # Verify force=True was passed
        mock_git_sync_service.sync_repository.assert_called_once_with(force=True)
        call_args = mock_git_sync_service.deploy_agents_to_project.call_args
        assert call_args[1]["force"] is True

    def test_deploy_agents_no_changes(self, command, mock_args, mock_git_sync_service):
        """Test deployment when all agents are up to date."""
        # Configure mock to return no deployments
        mock_git_sync_service.deploy_agents_to_project.return_value = {
            "deployed": [],
            "updated": [],
            "skipped": ["engineer.md", "qa.md", "base.md"],
            "failed": [],
            "deployment_dir": "/project/.claude/agents",
        }

        mock_args.agents_command = "deploy"

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.GitSourceSyncService",
            return_value=mock_git_sync_service,
        ):
            with patch("builtins.print") as mock_print:
                result = command.run(mock_args)

        assert result.success
        assert "Deployed 0 agents from cache" in result.message

    def test_deploy_agents_json_format(self, command, mock_args, mock_git_sync_service):
        """Test deployment with JSON output format."""
        mock_args.agents_command = "deploy"
        mock_args.format = "json"

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.GitSourceSyncService",
            return_value=mock_git_sync_service,
        ):
            result = command.run(mock_args)

        assert result.success
        assert result.data["total_deployed"] == 3
        assert "sync_result" in result.data
        assert "deploy_result" in result.data

    def test_deploy_agents_with_errors(self, command, mock_args, mock_git_sync_service):
        """Test deployment with sync errors."""
        # Configure mock to return sync failure
        mock_git_sync_service.sync_repository.return_value = {
            "synced": False,
            "error": "Network error: connection timeout",
        }

        mock_args.agents_command = "deploy"

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.GitSourceSyncService",
            return_value=mock_git_sync_service,
        ):
            result = command.run(mock_args)

        assert not result.success
        assert "Sync failed" in result.message


class TestCleanupOperations(TestAgentsCommand):
    """Test cleanup operations for agents."""

    def test_clean_agents_success(self, command, mock_args):
        """Test successful agent cleanup."""
        mock_args.agents_command = "clean"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Cleaned 3 agents" in result.message
        # Check that the formatted output contains the expected message
        printed_output = mock_print.call_args[0][0]
        assert "✓ Cleaned 3 deployed agents" in printed_output

    def test_clean_agents_none_to_clean(self, command, mock_args, mock_cleanup_service):
        """Test cleanup when no agents are deployed."""
        mock_cleanup_service.clean_deployed_agents.return_value = {
            "cleaned_count": 0,
        }

        mock_args.agents_command = "clean"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        # Check that the formatted output contains the expected message
        printed_output = mock_print.call_args[0][0]
        assert "No deployed agents to clean" in printed_output

    def test_clean_agents_json_format(self, command, mock_args):
        """Test cleanup with JSON output."""
        mock_args.agents_command = "clean"
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        assert result.data["cleaned_count"] == 3

    def test_cleanup_orphaned_agents_dry_run(
        self, command, mock_args, mock_cleanup_service
    ):
        """Test cleanup orphaned agents in dry-run mode."""
        mock_args.agents_command = "cleanup-orphaned"
        mock_args.dry_run = True
        mock_args.force = False
        mock_args.quiet = False

        # Configure mock to return orphaned agents
        mock_cleanup_service.clean_orphaned_agents.return_value = {
            "orphaned": [
                {"name": "old-agent", "version": "0.1.0"},
                {"name": "unused-agent", "version": "0.2.0"},
            ],
            "removed": [],
            "errors": [],
        }

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        # Check that the formatted output contains the expected messages
        printed_output = mock_print.call_args[0][0]
        assert "Found 2 orphaned agent(s):" in printed_output
        assert "old-agent v0.1.0" in printed_output

        mock_cleanup_service.clean_orphaned_agents.assert_called_once()
        call_args = mock_cleanup_service.clean_orphaned_agents.call_args
        assert call_args.kwargs["dry_run"] is True

    def test_cleanup_orphaned_agents_force(
        self, command, mock_args, mock_cleanup_service
    ):
        """Test cleanup orphaned agents with force flag."""
        mock_args.agents_command = "cleanup-orphaned"
        mock_args.force = True
        mock_args.dry_run = False
        mock_args.quiet = False

        # Configure mock to return removed agents
        mock_cleanup_service.clean_orphaned_agents.return_value = {
            "orphaned": [{"name": "old-agent", "version": "0.1.0"}],
            "removed": [{"name": "old-agent", "version": "0.1.0"}],
            "errors": [],
        }

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        # Check that the formatted output contains the expected message
        printed_output = mock_print.call_args[0][0]
        assert "✅ Successfully removed 1 orphaned agent(s)" in printed_output

        call_args = mock_cleanup_service.clean_orphaned_agents.call_args
        assert call_args.kwargs["dry_run"] is False


class TestViewingOperations(TestAgentsCommand):
    """Test viewing operations for agents."""

    def test_view_agent_success(self, command, mock_args):
        """Test viewing agent details."""
        mock_args.agents_command = "view"
        mock_args.agent_name = "engineer"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Displayed details for engineer" in result.message
        # Check that the formatted output contains expected agent details
        printed_output = mock_print.call_args[0][0]
        assert "Agent: engineer" in printed_output
        assert "Software engineering specialist" in printed_output

    def test_view_agent_missing_name(self, command, mock_args):
        """Test view command without agent name."""
        mock_args.agents_command = "view"
        mock_args.agent_name = None

        result = command.run(mock_args)

        assert not result.success
        assert "Agent name is required" in result.message

    def test_view_agent_not_found(self, command, mock_args, mock_listing_service):
        """Test viewing non-existent agent."""
        # Mock get_agent_details to return None (agent not found)
        mock_listing_service.get_agent_details.return_value = None
        # Mock find_agent to return None (agent not found)
        mock_listing_service.find_agent.return_value = None

        mock_args.agents_command = "view"
        mock_args.agent_name = "nonexistent"

        result = command.run(mock_args)

        assert not result.success
        assert "Agent 'nonexistent' not found" in result.message

    def test_view_agent_json_format(self, command, mock_args, mock_listing_service):
        """Test viewing agent in JSON format."""
        # Ensure get_agent_details returns a proper dict for JSON serialization
        mock_listing_service.get_agent_details.return_value = {
            "name": "engineer",
            "file": "engineer.md",
            "path": "/project/.claude/agents/engineer.md",
            "version": "1.0.0",
            "description": "Software engineering specialist",
            "tier": "project",
            "specializations": ["coding"],
        }

        mock_args.agents_command = "view"
        mock_args.agent_name = "engineer"
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        assert result.data["name"] == "engineer"
        assert result.data["version"] == "1.0.0"


class TestFixOperations(TestAgentsCommand):
    """Test fix operations for agents."""

    def test_fix_agents_success(self, command, mock_args):
        """Test fixing agent deployment issues."""
        mock_args.agents_command = "fix"
        mock_args.all = True
        mock_args.dry_run = False

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Fixed 2 issues" in result.message
        # Check that the formatted output contains expected content
        # The output is printed via _print_all_agents_text_output which has detailed formatting
        assert mock_print.called

    def test_fix_agents_no_issues(self, command, mock_args, mock_validation_service):
        """Test fix when no issues exist."""
        # Configure mock to return no issues
        mock_validation_service.fix_all_agents.return_value = {
            "success": True,
            "dry_run": False,
            "total_agents": 2,
            "agents_checked": 2,
            "total_issues_found": 0,
            "total_corrections_made": 0,
            "total_corrections_available": 0,
            "agents_fixed": [],
            "agents_with_errors": [],
            "results": [],
        }

        mock_args.agents_command = "fix"
        mock_args.all = True
        mock_args.dry_run = False

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Fixed 0 issues" in result.message

    def test_fix_agents_json_format(self, command, mock_args):
        """Test fix command with JSON output."""
        mock_args.agents_command = "fix"
        mock_args.format = "json"
        mock_args.all = True
        mock_args.dry_run = False

        result = command.run(mock_args)

        assert result.success
        assert result.data["total_corrections_made"] == 2
        assert len(result.data["agents_fixed"]) == 2


class TestDependencyOperations(TestAgentsCommand):
    """Test dependency operations for agents."""

    def test_check_dependencies(self, command, mock_args, mock_dependency_service):
        """Test checking agent dependencies."""
        mock_args.agents_command = "deps-check"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Dependency check completed" in result.message
        # Check that the report was printed (single call with full report)
        mock_print.assert_called_once()
        printed_output = mock_print.call_args[0][0]
        assert "Agent Dependencies Check:" in printed_output
        assert "Missing dependencies:" in printed_output
        assert "numpy" in printed_output

    def test_check_dependencies_all_satisfied(
        self, command, mock_args, mock_dependency_service
    ):
        """Test checking dependencies when all are satisfied."""
        # Configure mock to return no missing dependencies
        mock_dependency_service.check_dependencies.return_value = {
            "success": True,
            "report": "✓ All dependencies satisfied",
            "python_dependencies": [],
            "system_dependencies": [],
        }

        mock_args.agents_command = "deps-check"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Dependency check completed" in result.message
        mock_print.assert_called_once_with("✓ All dependencies satisfied")

    def test_install_dependencies(self, command, mock_args, mock_dependency_service):
        """Test installing agent dependencies."""
        # Configure mock to simulate successful installation
        mock_dependency_service.install_dependencies.return_value = {
            "success": True,
            "missing_count": 2,
            "installed": ["numpy", "pandas"],
            "missing_dependencies": ["numpy", "pandas"],
            "fully_resolved": True,
        }

        mock_args.agents_command = "deps-install"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Dependency installation completed" in result.message
        # Check that success message was printed
        printed_output = str(mock_print.call_args_list)
        assert "Successfully installed 2 dependencies" in printed_output

    def test_install_dependencies_none_needed(
        self, command, mock_args, mock_dependency_service
    ):
        """Test installing when no dependencies are needed."""
        # Configure mock to return no installations (missing_count = 0)
        mock_dependency_service.install_dependencies.return_value = {
            "success": True,
            "missing_count": 0,
            "installed": [],
            "missing_dependencies": [],
        }

        mock_args.agents_command = "deps-install"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        mock_print.assert_called_once_with(
            "✅ All Python dependencies are already installed"
        )

    def test_list_dependencies(self, command, mock_args):
        """Test listing agent dependencies."""
        mock_args.agents_command = "deps-list"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Dependency listing completed" in result.message
        # The implementation prints a formatted table, check for key headers
        printed_output = str(mock_print.call_args_list)
        assert "DEPENDENCIES FROM DEPLOYED AGENTS" in printed_output

    def test_list_dependencies_json_format(
        self, command, mock_args, mock_dependency_service
    ):
        """Test listing dependencies in JSON format."""
        # Add 'data' key to mock return for JSON format
        mock_dependency_service.list_dependencies.return_value = {
            "success": True,
            "python_dependencies": ["numpy", "pandas", "scipy"],
            "system_dependencies": [],
            "per_agent": {},
            "data": {
                "python_dependencies": ["numpy", "pandas", "scipy"],
                "system_dependencies": [],
                "per_agent": {},
            },
        }

        mock_args.agents_command = "deps-list"
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        assert "Dependency listing completed" in result.message
        # Check result.data has the expected structure
        assert "python_dependencies" in result.data
        assert len(result.data["python_dependencies"]) == 3

    def test_fix_dependencies(self, command, mock_args, mock_dependency_service):
        """Test fixing dependency issues."""
        mock_args.agents_command = "deps-fix"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        # Check that the formatted header was printed
        printed_output = str(mock_print.call_args_list)
        assert "FIXING AGENT DEPENDENCIES WITH RETRY LOGIC" in printed_output


class TestErrorHandling(TestAgentsCommand):
    """Test error handling in agent operations."""

    def test_deployment_service_import_error(self, mock_args):
        """Test handling of deployment service import error."""
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.deployed = False
        mock_args.by_tier = False

        with patch(
            "claude_mpm.services.AgentDeploymentService", side_effect=ImportError
        ):
            cmd = AgentsCommand()
            result = cmd.run(mock_args)

        assert not result.success
        assert "Agent deployment service not available" in result.message

    def test_unknown_command(self, command, mock_args):
        """Test handling of unknown command."""
        mock_args.agents_command = "unknown-command"

        result = command.run(mock_args)

        assert not result.success
        assert "Unknown agent command: unknown-command" in result.message

    def test_general_exception_handling(self, command, mock_args, mock_listing_service):
        """Test general exception handling."""
        # The list command with system=True uses listing_service.list_system_agents
        mock_listing_service.list_system_agents.side_effect = Exception(
            "Unexpected error"
        )

        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.deployed = False
        mock_args.by_tier = False

        result = command.run(mock_args)

        assert not result.success
        assert "Error listing system agents" in result.message


class TestDefaultBehavior(TestAgentsCommand):
    """Test default behavior when no subcommand is specified."""

    def test_show_agent_versions_default(self, command, mock_args):
        """Test default behavior shows agent versions."""
        mock_args.agents_command = None

        with patch(
            "claude_mpm.cli.commands.agents.get_agent_versions_display"
        ) as mock_get_versions:
            mock_get_versions.return_value = "Engineer v1.0.0\nQA v1.0.0"

            with patch("builtins.print") as mock_print:
                result = command.run(mock_args)

            assert result.success
            mock_print.assert_any_call("Engineer v1.0.0\nQA v1.0.0")

    def test_show_agent_versions_no_agents(self, command, mock_args):
        """Test default behavior when no agents are deployed."""
        mock_args.agents_command = None

        with patch(
            "claude_mpm.cli.commands.agents.get_agent_versions_display"
        ) as mock_get_versions:
            mock_get_versions.return_value = None

            with patch("builtins.print") as mock_print:
                result = command.run(mock_args)

            assert result.success
            mock_print.assert_any_call("No deployed agents found")
            mock_print.assert_any_call(
                "\nTo deploy agents, run: claude-mpm --mpm:agents deploy"
            )

    def test_show_agent_versions_json_format(self, command, mock_args):
        """Test default behavior with JSON output."""
        mock_args.agents_command = None
        mock_args.format = "json"

        with patch(
            "claude_mpm.cli.commands.agents.get_agent_versions_display"
        ) as mock_get_versions:
            mock_get_versions.return_value = "Engineer v1.0.0"

            result = command.run(mock_args)

        assert result.success
        assert result.data["has_agents"] is True
        assert result.data["agent_versions"] == "Engineer v1.0.0"


class TestManageAgentsFunction:
    """Test the manage_agents entry point function."""

    def test_manage_agents_success(self):
        """Test successful execution of manage_agents."""
        mock_args = MagicMock()
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.format = "text"

        with patch.object(AgentsCommand, "execute") as mock_execute:
            mock_execute.return_value = CommandResult.success_result("Success")

            exit_code = manage_agents(mock_args)

        assert exit_code == 0
        mock_execute.assert_called_once_with(mock_args)

    def test_manage_agents_with_json_output(self):
        """Test manage_agents with JSON output format."""
        mock_args = MagicMock()
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.format = "json"

        with patch.object(AgentsCommand, "execute") as mock_execute:
            with patch.object(AgentsCommand, "print_result") as mock_print:
                mock_result = CommandResult.success_result(
                    "Success", data={"test": "data"}
                )
                mock_execute.return_value = mock_result

                exit_code = manage_agents(mock_args)

            assert exit_code == 0
            mock_print.assert_called_once_with(mock_result, mock_args)

    def test_manage_agents_failure(self):
        """Test manage_agents with failure."""
        mock_args = MagicMock()
        mock_args.agents_command = "deploy"
        mock_args.format = "text"

        with patch.object(AgentsCommand, "execute") as mock_execute:
            mock_execute.return_value = CommandResult.error_result(
                "Failed", exit_code=1
            )

            exit_code = manage_agents(mock_args)

        assert exit_code == 1


class TestLazyLoading:
    """Test lazy loading of deployment service."""

    def test_deployment_service_lazy_loading(self):
        """Test that deployment service is loaded lazily."""
        cmd = AgentsCommand()

        # Service should not be initialized yet
        assert cmd._deployment_service is None

        with patch("claude_mpm.services.AgentDeploymentService") as MockService:
            with patch(
                "claude_mpm.services.agents.deployment.deployment_wrapper.DeploymentServiceWrapper"
            ) as MockWrapper:
                # Access the property
                service = cmd.deployment_service

                # Service should now be initialized
                assert service is not None
                MockService.assert_called_once()
                MockWrapper.assert_called_once()

    def test_deployment_service_cached(self):
        """Test that deployment service is cached after first access."""
        cmd = AgentsCommand()

        with patch("claude_mpm.services.AgentDeploymentService") as MockService:
            with patch(
                "claude_mpm.services.agents.deployment.deployment_wrapper.DeploymentServiceWrapper"
            ) as MockWrapper:
                mock_wrapper = MagicMock()
                MockWrapper.return_value = mock_wrapper

                # First access
                service1 = cmd.deployment_service
                # Second access
                service2 = cmd.deployment_service

                # Should be the same instance
                assert service1 is service2
                # Should only be created once
                MockService.assert_called_once()
                MockWrapper.assert_called_once()


class TestOutputFormats:
    """Test different output formats for agent commands."""

    @pytest.fixture
    def command_with_service(
        self,
        mock_deployment_service,
        mock_listing_service,
        mock_cleanup_service,
    ):
        """Create command with mocked services."""
        cmd = AgentsCommand()
        cmd._deployment_service = mock_deployment_service
        cmd._listing_service = mock_listing_service
        cmd._cleanup_service = mock_cleanup_service
        return cmd

    @pytest.mark.parametrize("format_type", ["json", "yaml", "text"])
    def test_list_agents_formats(self, command_with_service, format_type):
        """Test list agents with different output formats."""
        mock_args = MagicMock()
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.format = format_type
        mock_args.deployed = False
        mock_args.by_tier = False

        result = command_with_service.run(mock_args)

        assert result.success
        if format_type in ["json", "yaml"]:
            assert result.data is not None
            assert "agents" in result.data
            assert "count" in result.data

    @pytest.mark.parametrize("format_type", ["json", "yaml", "text"])
    def test_deploy_agents_formats(
        self, command_with_service, format_type, mock_git_sync_service
    ):
        """Test deploy agents with different output formats."""
        mock_args = MagicMock()
        mock_args.agents_command = "deploy"
        mock_args.format = format_type
        mock_args.preset = None  # Explicitly set to None to avoid MagicMock behavior
        mock_args.force = False
        mock_args.verbose = False  # Explicitly set to False to avoid verbose mode

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.GitSourceSyncService",
            return_value=mock_git_sync_service,
        ):
            result = command_with_service.run(mock_args)

        assert result.success
        if format_type in ["json", "yaml"]:
            assert result.data is not None
            assert "total_deployed" in result.data


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def command_with_service(
        self,
        mock_deployment_service,
        mock_listing_service,
        mock_cleanup_service,
    ):
        """Create command with mocked services."""
        cmd = AgentsCommand()
        cmd._deployment_service = mock_deployment_service
        cmd._listing_service = mock_listing_service
        cmd._cleanup_service = mock_cleanup_service
        return cmd

    def test_empty_agent_list(self, command_with_service, mock_listing_service):
        """Test handling of empty agent list."""
        mock_listing_service.list_system_agents.return_value = []

        mock_args = MagicMock()
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.format = "text"
        mock_args.deployed = False
        mock_args.by_tier = False
        mock_args.verbose = False
        mock_args.quiet = False

        with patch("builtins.print") as mock_print:
            result = command_with_service.run(mock_args)

        assert result.success
        assert "Listed 0 agent templates" in result.message

    def test_cleanup_orphaned_no_directory(
        self, command_with_service, mock_cleanup_service
    ):
        """Test cleanup orphaned when agents directory doesn't exist."""
        mock_cleanup_service.clean_orphaned_agents.return_value = {
            "success": True,
            "message": "Agents directory not found: /Users/masa/.claude/agents",
            "orphaned": [],
            "removed": [],
            "errors": [],
        }

        mock_args = MagicMock()
        mock_args.agents_command = "cleanup-orphaned"
        mock_args.agents_dir = None
        mock_args.dry_run = True
        mock_args.force = False
        mock_args.format = "text"
        mock_args.quiet = False

        result = command_with_service.run(mock_args)

        assert result.success
        # The message is in result.data, not result.message
        assert (
            "Cleanup preview" in result.message
            or result.data.get("message") is not None
        )

    def test_cleanup_orphaned_with_errors(
        self, command_with_service, mock_cleanup_service
    ):
        """Test cleanup orphaned with errors during removal."""
        # Set initial default return to be overridden
        mock_cleanup_service.clean_orphaned_agents.return_value = {
            "orphaned": [{"name": "test", "version": "1.0"}],
            "removed": [],
            "errors": ["Permission denied", "File locked"],
        }

        mock_args = MagicMock()
        mock_args.agents_command = "cleanup-orphaned"
        mock_args.force = True
        mock_args.dry_run = False
        mock_args.quiet = False
        mock_args.format = "text"

        with patch("builtins.print") as mock_print:
            result = command_with_service.run(mock_args)

        # The implementation returns error result when there are errors and not dry_run
        assert not result.success
        assert "Cleanup completed with 2 errors" in result.message
        # Check that formatted output contains error message
        printed_output = mock_print.call_args[0][0]
        assert "Encountered 2 error(s)" in printed_output

    def test_view_agent_special_characters(
        self, command_with_service, mock_listing_service
    ):
        """Test viewing agent with special characters in name."""
        # Configure mock to return agent details for special character name
        mock_listing_service.get_agent_details.return_value = {
            "name": "test-agent_v2.0",
            "version": "2.0",
            "description": "Test agent",
        }

        mock_args = MagicMock()
        mock_args.agents_command = "view"
        mock_args.agent_name = "test-agent_v2.0"
        mock_args.format = "text"
        mock_args.verbose = False

        result = command_with_service.run(mock_args)

        assert result.success
        # View command uses listing_service, not deployment_service
        mock_listing_service.get_agent_details.assert_called_once_with(
            "test-agent_v2.0"
        )


class TestCompatibility:
    """Test backward compatibility with legacy functions.

    NOTE: These tests are skipped because the legacy functions have been
    removed during refactoring. The functionality is now provided by
    AgentsCommand class methods tested in other test classes.
    """

    @pytest.mark.skip(
        reason="Legacy function _list_agents_by_tier removed during refactoring. "
        "Functionality now in AgentsCommand._list_agents_by_tier_cmd"
    )
    def test_legacy_list_agents_by_tier(self):
        """Test legacy _list_agents_by_tier function (REMOVED)."""

    @pytest.mark.skip(
        reason="Legacy function _view_agent removed during refactoring. "
        "Functionality now in AgentsCommand._view_agent method"
    )
    def test_legacy_view_agent(self):
        """Test legacy _view_agent function (REMOVED)."""

    @pytest.mark.skip(
        reason="Legacy function _deploy_agents signature changed. "
        "Now uses GitSourceSyncService instead of deployment_service"
    )
    def test_legacy_deploy_agents(self):
        """Test legacy _deploy_agents function (CHANGED)."""

        mock_service.deploy_agents.assert_called_once()


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def full_command(self):
        """Create a fully configured command."""
        return AgentsCommand()
        # Don't mock the deployment service to test full integration

    def test_deploy_then_list_workflow(
        self, mock_deployment_service, mock_listing_service, mock_git_sync_service
    ):
        """Test deploy followed by list workflow."""
        cmd = AgentsCommand()
        cmd._deployment_service = mock_deployment_service
        cmd._listing_service = mock_listing_service

        # Deploy agents
        deploy_args = MagicMock()
        deploy_args.agents_command = "deploy"
        deploy_args.format = "text"
        deploy_args.preset = None
        deploy_args.force = False
        deploy_args.verbose = False

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.GitSourceSyncService",
            return_value=mock_git_sync_service,
        ):
            deploy_result = cmd.run(deploy_args)
        assert deploy_result.success

        # List deployed agents
        list_args = MagicMock()
        list_args.agents_command = "list"
        list_args.deployed = True
        list_args.system = False
        list_args.by_tier = False
        list_args.format = "text"
        list_args.verbose = False
        list_args.quiet = False

        list_result = cmd.run(list_args)
        assert list_result.success

        # Verify listing service was called
        mock_listing_service.list_deployed_agents.assert_called_once()

    def test_check_install_verify_dependencies_workflow(self, mock_dependency_service):
        """Test complete dependency management workflow."""
        cmd = AgentsCommand()
        cmd._dependency_service = mock_dependency_service

        # Configure mock to return missing dependencies initially
        mock_dependency_service.check_dependencies.return_value = {
            "success": True,
            "report": "Missing dependencies found",
            "python_dependencies": [{"name": "numpy", "installed": False}],
            "system_dependencies": [],
        }

        # Check dependencies
        check_args = MagicMock()
        check_args.agents_command = "deps-check"
        check_args.format = "text"
        check_args.agent = None
        check_args.verbose = False
        check_args.quiet = False

        check_result = cmd.run(check_args)
        assert check_result.success

        # Configure install to succeed
        mock_dependency_service.install_dependencies.return_value = {
            "success": True,
            "missing_count": 0,
            "installed": ["numpy"],
            "missing_dependencies": [],
            "fully_resolved": True,
        }

        # Install missing dependencies
        install_args = MagicMock()
        install_args.agents_command = "deps-install"
        install_args.format = "text"
        install_args.agent = None
        install_args.dry_run = False
        install_args.verbose = False
        install_args.quiet = False

        install_result = cmd.run(install_args)
        assert install_result.success

        # Verify dependencies again (now all resolved)
        mock_dependency_service.check_dependencies.return_value = {
            "success": True,
            "report": "All dependencies satisfied",
            "python_dependencies": [{"name": "numpy", "installed": True}],
            "system_dependencies": [],
        }

        verify_result = cmd.run(check_args)
        assert verify_result.success

        # Verify dependency service was called properly
        assert mock_dependency_service.check_dependencies.call_count == 2
        mock_dependency_service.install_dependencies.assert_called_once()
