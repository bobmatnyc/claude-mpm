"""Version-aware deployment tests for PMSkillsDeployerService (Bug #735).

Guarantees:
- A deployed skill whose version is >= bundled is NEVER overwritten on
  redeploy / auto-repair (no silent revert of user-hardened skills).
- A strictly-newer bundled version DOES upgrade the deployed skill.
- Genuinely missing/empty skills are still auto-repaired, without clobbering
  unrelated user-modified skills.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from claude_mpm.services import pm_skills_deployer as mod
from claude_mpm.services.pm_skills_deployer import (
    PMSkillsDeployerService,
    _parse_version_tuple,
    _read_skill_version,
)

if TYPE_CHECKING:
    from pathlib import Path


def _skill_md(version: str, body: str = "content") -> str:
    return f'---\nname: test\nversion: "{version}"\n---\n\n# Test\n\n{body}\n'


@pytest.fixture
def deployer(tmp_path, monkeypatch):
    """A deployer whose bundled source and ~/.claude/skills both live in tmp."""
    # Bundled source dir.
    bundled = tmp_path / "bundled" / "pm"
    bundled.mkdir(parents=True)

    # Deployment dir (stand-in for ~/.claude/skills/).
    deploy_root = tmp_path / "home" / ".claude" / "skills"
    deploy_root.mkdir(parents=True)

    svc = PMSkillsDeployerService()
    svc.bundled_pm_skills_path = bundled

    # Force deployment + safe-path checks to use our temp deploy root.
    monkeypatch.setattr(svc, "_get_deployment_dir", lambda project_dir: deploy_root)
    monkeypatch.setattr(svc, "_validate_safe_path", lambda base, target: True)

    svc._bundled = bundled  # convenience handle for tests
    svc._deploy_root = deploy_root
    return svc


def _write_bundled(deployer, name: str, version: str, body: str = "bundled") -> Path:
    d = deployer._bundled / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(_skill_md(version, body))
    return p


def _write_deployed(deployer, name: str, version: str, body: str = "deployed") -> Path:
    d = deployer._deploy_root / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(_skill_md(version, body))
    return p


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_parse_version_tuple_numeric_ordering():
    assert _parse_version_tuple("10.0.0") > _parse_version_tuple("9.9.9")
    assert _parse_version_tuple("1.2.0") == (1, 2, 0)
    assert _parse_version_tuple("2.0") < _parse_version_tuple("2.0.1")


def test_parse_version_tuple_handles_junk():
    # Never raises; junk segments degrade to 0.
    assert _parse_version_tuple("not-a-version") == (0,)
    assert _parse_version_tuple("1.x.3") == (1, 0, 3)


def test_read_skill_version_reads_frontmatter(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text(_skill_md("3.4.5"))
    assert _read_skill_version(f) == "3.4.5"


def test_read_skill_version_defaults_when_missing(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: x\n---\n# no version\n")
    assert _read_skill_version(f) == mod.DEFAULT_SKILL_VERSION


# ---------------------------------------------------------------------------
# Deploy: version-aware overwrite policy
# ---------------------------------------------------------------------------


def test_deploy_refuses_to_overwrite_newer_deployed_skill(deployer, tmp_path):
    """Bundled 1.0.0 must NOT clobber a deployed 2.0.0 user-hardened skill."""
    name = "mpm-session-resume"
    _write_bundled(deployer, name, "1.0.0", body="bundled-original")
    deployed = _write_deployed(deployer, name, "2.0.0", body="USER-HARDENED")

    # Seed registry so the skill is "known deployed" with a stale checksum
    # (simulating that the user edited it after deployment).
    project = tmp_path / "proj"
    project.mkdir()
    deployer._save_registry(
        project,
        {
            "version": deployer.REGISTRY_VERSION,
            "skills": [
                {
                    "name": name,
                    "version": "2.0.0",
                    "deployed_at": "2020-01-01T00:00:00+00:00",
                    "checksum": "stale-checksum-does-not-match",
                }
            ],
        },
    )

    result = deployer.deploy_pm_skills(project, tier="minimal")

    # The deployed file is untouched — user content preserved.
    assert "USER-HARDENED" in deployed.read_text()
    assert name in result.skipped
    assert name not in result.deployed


def test_deploy_refuses_when_versions_equal(deployer, tmp_path):
    """Equal versions with differing content => keep deployed (do not clobber)."""
    name = "mpm-session-resume"
    _write_bundled(deployer, name, "1.5.0", body="bundled")
    deployed = _write_deployed(deployer, name, "1.5.0", body="USER-EDIT")

    project = tmp_path / "proj"
    project.mkdir()
    deployer._save_registry(
        project,
        {
            "version": deployer.REGISTRY_VERSION,
            "skills": [
                {
                    "name": name,
                    "version": "1.5.0",
                    "deployed_at": "2020-01-01T00:00:00+00:00",
                    "checksum": "stale",
                }
            ],
        },
    )

    result = deployer.deploy_pm_skills(project, tier="minimal")
    assert "USER-EDIT" in deployed.read_text()
    assert name in result.skipped


def test_deploy_upgrades_when_bundled_strictly_newer(deployer, tmp_path):
    """Bundled 2.0.0 DOES overwrite deployed 1.0.0."""
    name = "mpm-session-resume"
    _write_bundled(deployer, name, "2.0.0", body="NEW-BUNDLED")
    deployed = _write_deployed(deployer, name, "1.0.0", body="old-deployed")

    project = tmp_path / "proj"
    project.mkdir()
    deployer._save_registry(
        project,
        {
            "version": deployer.REGISTRY_VERSION,
            "skills": [
                {
                    "name": name,
                    "version": "1.0.0",
                    "deployed_at": "2020-01-01T00:00:00+00:00",
                    "checksum": "stale",
                }
            ],
        },
    )

    result = deployer.deploy_pm_skills(project, tier="minimal")
    assert "NEW-BUNDLED" in deployed.read_text()
    assert name in result.deployed


def test_force_still_overwrites(deployer, tmp_path):
    """force=True bypasses version gating (explicit operator intent)."""
    name = "mpm-session-resume"
    _write_bundled(deployer, name, "1.0.0", body="FORCED-BUNDLED")
    deployed = _write_deployed(deployer, name, "9.9.9", body="user")

    project = tmp_path / "proj"
    project.mkdir()
    deployer._save_registry(
        project,
        {
            "version": deployer.REGISTRY_VERSION,
            "skills": [
                {
                    "name": name,
                    "version": "9.9.9",
                    "deployed_at": "2020-01-01T00:00:00+00:00",
                    "checksum": "stale",
                }
            ],
        },
    )

    result = deployer.deploy_pm_skills(project, tier="minimal", force=True)
    assert "FORCED-BUNDLED" in deployed.read_text()
    assert name in result.deployed


# ---------------------------------------------------------------------------
# Auto-repair: surgical, version-aware
# ---------------------------------------------------------------------------


def test_targeted_repair_fixes_only_named_skills(deployer, tmp_path):
    """_repair_specific_skills repairs the named skill, leaves others alone."""
    project = tmp_path / "proj"
    project.mkdir()

    # 'broken' has a bundled source; 'pristine' is a user-modified skill we must
    # not touch.
    _write_bundled(deployer, "mpm-status", "1.0.0", body="REPAIRED")
    pristine = _write_deployed(deployer, "mpm-help", "5.0.0", body="USER-PRISTINE")

    repaired = deployer._repair_specific_skills(project, ["mpm-status"])

    assert repaired == ["mpm-status"]
    # The repaired skill now exists with bundled content.
    fixed = deployer._deploy_root / "mpm-status" / "SKILL.md"
    assert "REPAIRED" in fixed.read_text()
    # The unrelated user skill is untouched.
    assert "USER-PRISTINE" in pristine.read_text()


def test_verify_modified_skill_not_classified_corrupted(deployer, tmp_path):
    """A non-empty user-modified file is a warning, not corruption.

    Therefore auto-repair must NOT redeploy it, and its content survives.
    """
    name = "mpm-session-resume"
    _write_bundled(deployer, name, "1.0.0", body="bundled")
    deployed = _write_deployed(deployer, name, "1.0.0", body="USER-HARDENED")

    project = tmp_path / "proj"
    project.mkdir()
    deployer._save_registry(
        project,
        {
            "version": deployer.REGISTRY_VERSION,
            "skills": [
                {
                    "name": name,
                    "version": "1.0.0",
                    "deployed_at": "2020-01-01T00:00:00+00:00",
                    "checksum": "stale-so-it-looks-changed",
                }
            ],
        },
    )

    result = deployer.verify_pm_skills(project, auto_repair=True)

    # User content preserved — never reverted by auto-repair.
    assert "USER-HARDENED" in deployed.read_text()
    assert name not in result.corrupted_skills
    # A "modified since deployment" warning is present.
    assert any("modified since deployment" in w for w in result.warnings)
