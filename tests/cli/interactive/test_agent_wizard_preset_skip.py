"""Regression tests for preset batch-deploy skip accounting (issue #919).

Why: The interactive preset deploy loop counted every truthy ``deploy_agent``
result as a deployment. Because a skipped CORE agent used to return ``True``,
the printed "Deployed: N" summary over-counted and the loop wrongly announced
"deployed successfully!" even when nothing was actually deployed.

What: Drives ``AgentWizard._deploy_preset_interactive`` with a mocked deployer
whose ``deploy_agent`` returns ``None`` (a skip) and asserts the summary reports
the agent as skipped, not deployed, and does not claim success.

Test: Run the two cases below; assert on captured stdout and the count buckets.
"""

import logging
from unittest.mock import Mock, patch

from claude_mpm.cli.interactive.agent_wizard import AgentWizard


def _make_wizard() -> AgentWizard:
    """Build an AgentWizard without running its heavy __init__.

    Why: The constructor wires up GitSourceManager/LocalAgentTemplateManager,
    which are irrelevant here and slow; we only need a few attributes.
    """
    wizard = AgentWizard.__new__(AgentWizard)
    wizard.logger = logging.getLogger("test.agent_wizard")
    wizard.source_manager = Mock()
    wizard.discovery_enabled = True
    return wizard


def _preset_service_with(agents):
    """Return a mock AgentPresetService exposing one preset resolving to *agents*."""
    service = Mock()
    service.list_presets.return_value = [
        {
            "name": "core",
            "description": "Core agents",
            "agents": [a["agent_id"] for a in agents],
        }
    ]
    service.resolve_agents.return_value = {"missing_agents": [], "agents": agents}
    return service


def _run_preset_deploy(wizard, deploy_return, agents):
    """Drive _deploy_preset_interactive once, returning the mocked deployer.

    Patches the preset service, the deployment service classes, base-agent
    resolution and ``input`` (select preset -> confirm -> press-enter).
    """
    service = _preset_service_with(agents)
    deployer_instance = Mock()
    deployer_instance.deploy_agent.return_value = deploy_return

    with (
        patch(
            "claude_mpm.services.agents.agent_preset_service.AgentPresetService",
            return_value=service,
        ),
        patch(
            "claude_mpm.services.agents.deployment.single_agent_deployer.SingleAgentDeployer",
            return_value=deployer_instance,
        ),
        patch(
            "claude_mpm.services.agents.deployment.agent_template_builder.AgentTemplateBuilder"
        ),
        patch(
            "claude_mpm.services.agents.deployment.agent_version_manager.AgentVersionManager"
        ),
        patch(
            "claude_mpm.services.agents.deployment.deployment_results_manager.DeploymentResultsManager"
        ),
        patch.object(
            AgentWizard, "_resolve_base_agent_path", return_value="/tmp/BASE_AGENT.md"
        ),
        patch("builtins.input", side_effect=["1", "y", ""]),
    ):
        wizard._deploy_preset_interactive()

    return deployer_instance


CORE_AGENT = {
    "agent_id": "engineer",
    "metadata": {"metadata": {"name": "Engineer"}, "path": "/fake/engineer.md"},
    "source": "system",
}


def test_skipped_core_agent_not_counted_as_deployed(capsys):
    """A skipped CORE agent (deploy_agent -> None) is reported as skipped."""
    wizard = _make_wizard()
    deployer = _run_preset_deploy(wizard, deploy_return=None, agents=[CORE_AGENT])

    deployer.deploy_agent.assert_called_once()
    out = capsys.readouterr().out

    assert "Deployed: 0" in out, "A skip must not increment the deployed count"
    assert "Skipped: 1" in out, "The skipped CORE agent must be reported as skipped"
    assert "deployed successfully" not in out, (
        "Must not claim success when nothing was actually deployed (#919)"
    )


def test_real_deployment_still_reported_as_success(capsys):
    """A genuine deployment (deploy_agent -> True) is still counted + celebrated."""
    wizard = _make_wizard()
    project_agent = {
        "agent_id": "my-custom-agent",
        "metadata": {"metadata": {"name": "Custom"}, "path": "/fake/custom.md"},
        "source": "project",
    }
    deployer = _run_preset_deploy(wizard, deploy_return=True, agents=[project_agent])

    deployer.deploy_agent.assert_called_once()
    out = capsys.readouterr().out

    assert "Deployed: 1" in out
    assert "deployed successfully" in out
