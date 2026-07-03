"""Regression tests for auto-configure CORE-agent skip accounting (#919).

WHY: ``deploy_agent`` is tri-state — ``False`` is a real failure, ``None`` means a
CORE agent was intentionally skipped for a project target, and a truthy value is a
genuine deploy. A prior ``if success is False: ... else: deployed`` branch wrongly
counted a skip (``None``) as a successful deployment. This test locks in that a skip
is excluded from BOTH ``deployed_agents`` and ``failed_agents`` and is instead
surfaced in ``skipped_agents``.

WHAT: Drives ``_run_auto_configure`` end-to-end with mocked services and a fake
Socket.IO handler, then inspects the ``autoconfig_completed`` event payload.

TEST: Run ``uv run pytest tests/services/config_api/test_autoconfig_skip_accounting.py``.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class _FakeHandler:
    """Records emit_config_event calls so tests can assert on the completion payload.

    WHY: The real handler pushes Socket.IO events; tests only need to capture the
    emitted operation/data pairs to verify skip accounting.
    WHAT: Async ``emit_config_event`` appends every (operation, data) pair to ``events``.
    TEST: Assert the recorded "autoconfig_completed" event contains the expected lists.
    """

    def __init__(self):
        self.events = []

    async def emit_config_event(
        self, *, operation, entity_type, entity_id, status, data
    ):
        self.events.append((operation, data))

    def completed_payload(self):
        for operation, data in self.events:
            if operation == "autoconfig_completed":
                return data
        raise AssertionError("no autoconfig_completed event was emitted")


def _run_with_deploy_results(tmp_path, deploy_results):
    """Drive _run_auto_configure with a stubbed tri-state deploy_agent.

    WHY: Centralizes the heavy mock wiring so individual tests only supply the
    {agent_id: deploy_agent return value} mapping they care about.
    WHAT: Patches the toolchain analyzer, auto-config manager (preview.would_deploy),
    backup manager, AgentDeploymentService, skills deployer, and DeploymentVerifier,
    then runs the coroutine and returns the completion payload.
    TEST: Pass {"a": True, "b": None, "c": False}; assert returned dict partitions them.
    """
    import claude_mpm.services.config_api.autoconfig_handler as mod

    would_deploy = list(deploy_results.keys())
    handler = _FakeHandler()

    def _deploy_agent(name, agents_dir, force_rebuild=False):
        return deploy_results[name]

    deploy_svc = MagicMock()
    deploy_svc.deploy_agent.side_effect = _deploy_agent

    verifier = MagicMock()
    verifier.verify_agent_deployed.return_value = SimpleNamespace(passed=True)

    skills_deployer = MagicMock()
    skills_deployer.deploy_skills.return_value = {"deployed_skills": [], "errors": []}

    preview = SimpleNamespace(would_deploy=would_deploy, recommendations=[])

    with (
        patch.object(mod, "_get_toolchain_analyzer", return_value=MagicMock()),
        patch.object(
            mod,
            "_get_auto_config_manager",
            return_value=MagicMock(
                preview_configuration=MagicMock(return_value=preview)
            ),
        ),
        patch.object(
            mod,
            "_get_backup_manager",
            return_value=MagicMock(
                create_backup=MagicMock(
                    return_value=SimpleNamespace(backup_id="backup-1")
                )
            ),
        ),
        patch.object(mod, "_get_skills_deployer", return_value=skills_deployer),
        patch(
            "claude_mpm.services.agents.deployment.agent_deployment.AgentDeploymentService",
            return_value=deploy_svc,
        ),
        patch(
            "claude_mpm.services.config_api.deployment_verifier.DeploymentVerifier",
            return_value=verifier,
        ),
    ):
        asyncio.run(
            mod._run_auto_configure(
                job_id="job-1",
                project_path=tmp_path,
                dry_run=False,
                min_confidence=0.5,
                handler=handler,
            )
        )

    return handler.completed_payload()


def test_skipped_core_agent_excluded_from_deployed_and_failed(tmp_path):
    """A None (skipped CORE agent) result must not count as deployed or failed."""
    payload = _run_with_deploy_results(
        tmp_path,
        {"deploy_ok": True, "skip_core": None, "fail_one": False},
    )

    assert "skip_core" not in payload["deployed_agents"]
    assert "skip_core" not in payload["failed_agents"]
    assert payload["skipped_agents"] == ["skip_core"]
    assert payload["deployed_agents"] == ["deploy_ok"]
    assert payload["failed_agents"] == ["fail_one"]


def test_only_real_deploys_trigger_restart(tmp_path):
    """A run that only skips (no real deploy) must not report needs_restart."""
    payload = _run_with_deploy_results(tmp_path, {"skip_core": None})

    assert payload["skipped_agents"] == ["skip_core"]
    assert payload["deployed_agents"] == []
    assert payload["failed_agents"] == []
    assert payload["needs_restart"] is False
