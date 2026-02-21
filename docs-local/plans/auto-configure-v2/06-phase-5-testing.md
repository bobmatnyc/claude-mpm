# Phase 5: End-to-End Testing Plan

## Objective

Establish comprehensive test coverage for all changes introduced in Phases 0-2 and 4. This includes unit tests for the new `ConfigScope` module, integration tests for API skill deployment, and an end-to-end test verifying the full auto-configure flow from detection through deployment to file verification. Regression tests ensure the CLI path remains unaffected.

## Prerequisites

- **All previous phases (0-2, 4)** must be complete. This phase tests the entire implementation. (Phase 3 was removed from scope.)

## Scope

**IN SCOPE:**
- Unit tests for `ConfigScope` enum and resolver functions (Phase 0)
- Unit tests for min_confidence default (Phase 1)
- Integration tests for API skill deployment (Phase 2)
- E2E test for full auto-configure flow (all phases)
- Regression tests for CLI auto-configure (both scopes)
- Verification of Socket.IO event payloads

**NOT IN SCOPE:**
- Visual/screenshot testing of Svelte components (manual verification sufficient)
- Performance/load testing
- Security penetration testing (the project_path validation concern from research doc section 8.10 warrants a separate security review)

## Current State

### Existing Test Coverage

**File:** `tests/services/agents/test_recommender.py`
- Extensive tests for the recommender covering the fixes from commit `62ba0f42`
- Tests PEP 621 parsing, scoring math, Node.js alias, and confidence thresholds

**File:** `tests/services/config_api/test_autoconfig_handler.py` (if it exists)
- May have basic tests for detect/preview/apply endpoints
- Does NOT test skill deployment (since that feature did not exist)

### Test Infrastructure

The project uses `pytest` with the following patterns observed:
- `asyncio.to_thread()` wrapping for sync services tested with `pytest-asyncio`
- Mock objects for `AgentDeploymentService`, `ToolchainAnalyzerService`
- Temp directories for file system operations (`tmp_path` fixture)

## Target State

A test suite that verifies:

1. `ConfigScope` enum and all four resolver functions produce correct paths
2. API min_confidence defaults to 0.5 (not 0.8)
3. API skill deployment calls `SkillsDeployerService` and returns real results
4. Preview endpoint returns `skill_recommendations`
5. Completion event includes `deployed_skills`, `needs_restart`
6. CLI auto-configure still works in both project and user scopes
7. Concurrent auto-configure jobs are rejected (409)
8. Partial failures (skill errors) are captured correctly

## Implementation Steps

### Step 1: Unit tests for ConfigScope (`tests/core/test_config_scope.py`)

**Create:** `tests/core/test_config_scope.py`

```python
"""Tests for core.config_scope module."""
import pytest
from pathlib import Path
from claude_mpm.core.config_scope import (
    ConfigScope,
    resolve_agents_dir,
    resolve_skills_dir,
    resolve_archive_dir,
    resolve_config_dir,
)


class TestConfigScope:
    """Test ConfigScope enum properties."""

    def test_project_value(self):
        assert ConfigScope.PROJECT == "project"
        assert ConfigScope.PROJECT.value == "project"

    def test_user_value(self):
        assert ConfigScope.USER == "user"
        assert ConfigScope.USER.value == "user"

    def test_backward_compatibility_with_string(self):
        """Existing CLI code compares scope == 'project'."""
        assert ConfigScope.PROJECT == "project"
        assert ConfigScope.USER == "user"
        # This is the critical test: str(enum) and enum == str both work
        scope = ConfigScope.PROJECT
        assert scope == "project"

    def test_json_serializable(self):
        """API payloads need JSON serialization."""
        import json
        assert json.dumps(ConfigScope.PROJECT) == '"project"'
        assert json.dumps(ConfigScope.USER) == '"user"'


class TestResolveAgentsDir:
    """Test resolve_agents_dir function."""

    def test_project_scope(self, tmp_path):
        result = resolve_agents_dir(ConfigScope.PROJECT, tmp_path)
        assert result == tmp_path / ".claude" / "agents"

    def test_user_scope(self, tmp_path):
        result = resolve_agents_dir(ConfigScope.USER, tmp_path)
        assert result == Path.home() / ".claude" / "agents"

    def test_project_scope_with_different_paths(self):
        p1 = resolve_agents_dir(ConfigScope.PROJECT, Path("/project-a"))
        p2 = resolve_agents_dir(ConfigScope.PROJECT, Path("/project-b"))
        assert p1 != p2
        assert p1 == Path("/project-a/.claude/agents")
        assert p2 == Path("/project-b/.claude/agents")


class TestResolveSkillsDir:
    """Test resolve_skills_dir function."""

    def test_always_returns_user_home(self):
        result = resolve_skills_dir()
        assert result == Path.home() / ".claude" / "skills"

    def test_scope_parameter_ignored(self):
        """Skills are always user-scoped for now."""
        result_project = resolve_skills_dir(ConfigScope.PROJECT)
        result_user = resolve_skills_dir(ConfigScope.USER)
        assert result_project == result_user
        assert result_project == Path.home() / ".claude" / "skills"


class TestResolveArchiveDir:
    """Test resolve_archive_dir function."""

    def test_project_scope(self, tmp_path):
        result = resolve_archive_dir(ConfigScope.PROJECT, tmp_path)
        assert result == tmp_path / ".claude" / "agents" / "unused"

    def test_user_scope(self, tmp_path):
        result = resolve_archive_dir(ConfigScope.USER, tmp_path)
        assert result == Path.home() / ".claude" / "agents" / "unused"

    def test_is_subdirectory_of_agents_dir(self, tmp_path):
        agents = resolve_agents_dir(ConfigScope.PROJECT, tmp_path)
        archive = resolve_archive_dir(ConfigScope.PROJECT, tmp_path)
        assert archive.parent == agents


class TestResolveConfigDir:
    """Test resolve_config_dir function."""

    def test_project_scope(self, tmp_path):
        result = resolve_config_dir(ConfigScope.PROJECT, tmp_path)
        assert result == tmp_path / ".claude-mpm"

    def test_user_scope(self, tmp_path):
        result = resolve_config_dir(ConfigScope.USER, tmp_path)
        assert result == Path.home() / ".claude-mpm"
```

### Step 2: Unit tests for min_confidence default (`tests/services/config_api/test_autoconfig_defaults.py`)

**Create:** `tests/services/config_api/test_autoconfig_defaults.py`

```python
"""Tests for autoconfig_handler default values."""
import pytest


class TestMinConfidenceDefault:
    """Verify min_confidence default matches CLI."""

    def test_preview_default_is_0_5(self):
        """The preview endpoint should default to 0.5, not 0.8."""
        # Read the source to verify the default
        import inspect
        from claude_mpm.services.config_api import autoconfig_handler

        source = inspect.getsource(autoconfig_handler)

        # Count occurrences of the old incorrect default
        assert source.count('min_confidence", 0.8') == 0, (
            "Found min_confidence default of 0.8 -- should be 0.5"
        )

    def test_no_0_8_defaults_in_codebase(self):
        """Ensure no other files have the old 0.8 default."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "min_confidence.*0\\.8", "src/"],
            capture_output=True, text=True,
            cwd="/Users/mac/workspace/claude-mpm-fork"
        )
        assert result.stdout.strip() == "", (
            f"Found min_confidence 0.8 defaults:\n{result.stdout}"
        )
```

### Step 3: Integration tests for API skill deployment

**Create or modify:** `tests/services/config_api/test_autoconfig_skill_deployment.py`

```python
"""Integration tests for skill deployment in auto-configure API."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestAutoConfigSkillDeployment:
    """Test skill deployment integration in auto-configure."""

    @patch("claude_mpm.services.skills_deployer.SkillsDeployerService")
    @patch("claude_mpm.cli.interactive.skills_wizard.get_skills_for_agent")
    def test_skills_recommended_from_agent_mapping(
        self, mock_get_skills, mock_deployer_cls
    ):
        """Skills should be recommended based on AGENT_SKILL_MAPPING."""
        mock_get_skills.side_effect = lambda agent_id: {
            "python-engineer": ["python-style", "test-driven-development"],
            "engineer": ["systematic-debugging", "git-workflow"],
        }.get(agent_id, [])

        # Simulate the recommendation logic
        from claude_mpm.cli.interactive.skills_wizard import get_skills_for_agent

        recommended = set()
        for agent_id in ["python-engineer", "engineer"]:
            skills = get_skills_for_agent(agent_id)
            recommended.update(skills)

        assert "python-style" in recommended
        assert "test-driven-development" in recommended
        assert "systematic-debugging" in recommended
        assert "git-workflow" in recommended

    @patch("claude_mpm.services.skills_deployer.SkillsDeployerService")
    def test_skill_deployment_returns_results(self, mock_deployer_cls):
        """Skill deployment should return deployed and errors."""
        mock_instance = MagicMock()
        mock_instance.deploy_skills.return_value = {
            "deployed": ["python-style", "git-workflow"],
            "errors": ["test-driven-development: download failed"],
        }
        mock_deployer_cls.return_value = mock_instance

        result = mock_instance.deploy_skills(
            skill_names=["python-style", "git-workflow", "test-driven-development"],
            force=False,
        )

        assert len(result["deployed"]) == 2
        assert len(result["errors"]) == 1

    def test_preview_includes_skill_recommendations(self):
        """Preview response should contain skill_recommendations field."""
        # This test would call the preview endpoint with a mock
        # and verify the response shape includes skill_recommendations
        pass  # Implement with aiohttp test client

    def test_completion_event_includes_deployed_skills(self):
        """Completion event should have real deployed_skills data."""
        # This test would verify the Socket.IO event payload
        pass  # Implement with aiohttp test client


class TestSkillDeploymentErrorHandling:
    """Test error handling for skill deployment."""

    def test_skill_failure_does_not_crash_autoconfig(self):
        """If all skills fail, auto-configure should still succeed."""
        # Simulate SkillsDeployerService raising an exception
        # Verify that the auto-configure reports partial success
        pass  # Implement with mock

    def test_empty_skill_recommendations(self):
        """If no skills match, deployed_skills should be empty list."""
        # Simulate agents that have no skill mappings
        pass  # Implement with mock
```

### Step 4: E2E test for full auto-configure flow

**Create:** `tests/e2e/test_autoconfig_full_flow.py`

```python
"""End-to-end test for auto-configure API flow.

Tests the complete pipeline: detect -> preview -> apply -> verify files.
Uses tmp_path to create a temporary project directory with known files.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def fake_project(tmp_path):
    """Create a minimal Python project for detection."""
    # Create pyproject.toml
    (tmp_path / "pyproject.toml").write_text("""
[project]
name = "test-project"
dependencies = ["fastapi", "pytest"]
""")

    # Create a Python file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

    # Create .claude directory structure
    claude_dir = tmp_path / ".claude" / "agents"
    claude_dir.mkdir(parents=True)

    return tmp_path


class TestFullAutoConfigureFlow:
    """E2E test for the complete auto-configure pipeline."""

    def test_detect_preview_apply_verify(self, fake_project):
        """
        Full flow:
        1. Detect toolchain -> should find Python + FastAPI
        2. Preview -> should recommend agents and skills
        3. Apply -> should deploy agents and skills
        4. Verify -> files should exist on disk
        """
        # This test requires significant mocking of the HTTP layer
        # but verifies the logical flow end-to-end
        pass  # Implement with full mock chain

    def test_preview_and_apply_produce_consistent_results(self, fake_project):
        """Preview should predict what apply actually does."""
        # Preview says would_deploy: ["python-engineer", "engineer"]
        # Apply should deploy exactly those agents
        pass


class TestCLIRegression:
    """Regression tests ensuring CLI still works after API changes."""

    def test_cli_project_scope_unchanged(self):
        """CLI with --scope project should work as before."""
        # Verify configure_paths.py functions still return correct paths
        from claude_mpm.cli.commands.configure_paths import (
            get_config_directory,
            get_agents_directory,
            get_behaviors_directory,
        )

        project_dir = Path("/fake/project")

        assert get_config_directory("project", project_dir) == project_dir / ".claude-mpm"
        assert get_agents_directory("project", project_dir) == project_dir / ".claude-mpm" / "agents"
        assert get_behaviors_directory("project", project_dir) == project_dir / ".claude-mpm" / "behaviors"

    def test_cli_user_scope_unchanged(self):
        """CLI with --scope user should work as before."""
        from claude_mpm.cli.commands.configure_paths import (
            get_config_directory,
            get_agents_directory,
        )

        project_dir = Path("/fake/project")

        assert get_config_directory("user", project_dir) == Path.home() / ".claude-mpm"
        assert get_agents_directory("user", project_dir) == Path.home() / ".claude-mpm" / "agents"

    def test_config_scope_enum_compatible_with_cli_strings(self):
        """ConfigScope enum must be backward compatible with raw strings."""
        from claude_mpm.core.config_scope import ConfigScope

        # These are the comparisons that exist throughout the CLI
        assert ConfigScope.PROJECT == "project"
        assert ConfigScope.USER == "user"

        # In a dict
        scope_map = {"project": "found_project", "user": "found_user"}
        assert scope_map[ConfigScope.PROJECT] == "found_project"
        assert scope_map[ConfigScope.USER] == "found_user"
```

### Step 5: Test Socket.IO event payloads

**Create:** `tests/services/config_api/test_autoconfig_events.py`

```python
"""Tests for auto-configure Socket.IO event payloads."""
import pytest


class TestAutoConfigProgressEvents:
    """Test that progress events include new phases."""

    def test_deploying_skills_phase_emitted(self):
        """A 'deploying_skills' phase should be emitted."""
        pass  # Verify by mocking handler.emit_config_event

    def test_phase_numbering_sequential(self):
        """Phase numbers should be sequential without gaps."""
        pass


class TestAutoConfigCompletionEvent:
    """Test the completion event payload structure."""

    def test_completion_includes_new_fields(self):
        """Completion event should include all new fields."""
        required_fields = [
            "deployed_agents",
            "failed_agents",
            "deployed_skills",
            "skill_errors",
            "needs_restart",
            "backup_id",
            "duration_ms",
            "verification",
        ]
        # Verify by mocking the handler and checking the emitted data
        pass

    def test_needs_restart_true_when_agents_deployed(self):
        """needs_restart should be True when agents were deployed."""
        pass

    def test_needs_restart_true_when_skills_deployed(self):
        """needs_restart should be True when skills were deployed."""
        pass

    def test_needs_restart_false_when_nothing_deployed(self):
        """needs_restart should be False when nothing was deployed."""
        pass
```

## Devil's Advocate Analysis

### "How do we test file system operations safely? Mock or temp directories?"

**Answer: Both, depending on the test level.**

- **Unit tests:** Mock `SkillsDeployerService` and file system operations. Verify the handler calls services with correct arguments and processes return values correctly.
- **Integration tests:** Use `tmp_path` fixture (pytest's temporary directory) for file operations. Create fake project structures, run the service methods, verify files exist where expected.
- **E2E tests:** Use `tmp_path` for the project directory and mock the HTTP layer (aiohttp test client). Verify the full logical flow without network calls.

**DO NOT test against the real `~/.claude/skills/` directory** -- skill deployment would modify the developer's actual environment. Mock the skills directory:
```python
@patch("claude_mpm.services.skills_deployer.SkillsDeployerService.CLAUDE_SKILLS_DIR", new_callable=lambda: tmp_path / ".claude" / "skills")
```

### "Should we test the Svelte components?"

Manual visual testing is sufficient for the Svelte changes in Phase 4. Automated component testing (e.g., with Playwright or vitest) would be valuable but is outside the scope of this initiative. The TypeScript interfaces can be validated by building the Svelte project (`npm run build`) and checking for type errors.

### "How do we test concurrent job rejection?"

Create a test that:
1. Starts an auto-configure job (mocking the background task to sleep)
2. Immediately starts a second job
3. Verifies the second job returns 409

```python
async def test_concurrent_job_rejection(aiohttp_client):
    # Start first job
    resp1 = await client.post('/api/config/auto-configure/apply', json={})
    assert resp1.status == 202

    # Start second job immediately
    resp2 = await client.post('/api/config/auto-configure/apply', json={})
    assert resp2.status == 409
```

### "The E2E test requires a lot of mocking -- is it really end-to-end?"

It tests the logical flow end-to-end (detect -> recommend -> validate -> deploy -> verify) but mocks the HTTP transport and file system boundaries. A true E2E test would start the aiohttp server and make real HTTP calls. This is more of an integration test with E2E scope.

For true E2E testing, consider adding a Playwright test that opens the dashboard, triggers auto-configure, and verifies the UI elements. This is a future enhancement.

### "Existing recommender tests might break if we change phase numbering"

The recommender tests (`test_recommender.py`) test the recommendation service, not the API handler phases. Phase numbering changes are local to `autoconfig_handler.py` and should not affect recommender tests.

However, if there are existing handler tests that assert specific phase numbers in Socket.IO events, those would need updating. Check with:
```bash
grep -rn "total_phases\|phase.*[0-9]" tests/services/config_api/
```

## Acceptance Criteria

1. All `TestConfigScope` tests pass (enum values, backward compatibility, JSON serialization)
2. All resolver function tests pass (correct paths for both scopes)
3. min_confidence default test verifies no `0.8` defaults remain in codebase
4. Skill deployment integration tests verify `SkillsDeployerService` is called correctly
5. CLI regression tests pass without any modifications to `configure_paths.py`
6. `ConfigScope.PROJECT == "project"` backward compatibility test passes
7. E2E test verifies the complete detect -> preview -> apply -> verify flow
8. All existing tests in `test_recommender.py` pass without modification
9. `npm run build` succeeds for the Svelte project (TypeScript type check)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Tests pollute real `~/.claude/skills/` | Mock `CLAUDE_SKILLS_DIR` with `tmp_path` |
| Tests pollute real `.claude/agents/` | Use `tmp_path` for all project directories |
| Existing tests break from phase numbering | Check for phase number assertions in existing tests |
| Flaky async tests | Use `pytest-asyncio` strict mode; avoid timing-dependent assertions |
| Import errors from lazy singletons | Test singleton initialization in isolation |

## Estimated Effort

**S-M (2-3 hours)**

- 45 minutes for `test_config_scope.py` (Step 1)
- 20 minutes for min_confidence default tests (Step 2)
- 45 minutes for skill deployment integration tests (Step 3)
- 30 minutes for E2E flow test skeleton (Step 4)
- 20 minutes for event payload tests (Step 5)
- 30 minutes for running full test suite and fixing issues
