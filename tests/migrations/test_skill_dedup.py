"""Tests for the framework-skill dedup sweep logic.

All tests use tmp_path fixtures.  Real ~/.claude/skills/ and ~/Projects/ are
NEVER touched.

Covered scenarios:
    1. Idempotent no-op when project is already clean.
    2. Removes only USER_LEVEL_SKILLS names that also exist at user level.
    3. Never removes project-unique or toolchain skills.
    4. dry-run (default) deletes nothing.
    5. sweep_projects() scans multiple projects and aggregates results.
    6. Skill kept when user-level copy is missing.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_FAKE_USER_SKILLS: frozenset[str] = frozenset(
    {
        "mpm",
        "mpm-help",
        "mpm-status",
        "universal-testing-test-driven-development",
    }
)
"""A small, stable subset of USER_LEVEL_SKILLS used in all tests.
Patched in via _get_user_level_skills so tests are independent of the live set."""


def _make_user_skill(user_skills_base: Path, name: str) -> Path:
    """Create <user_skills_base>/<name>/SKILL.md and return the skill dir.

    Mirrors the layout that PMSkillsDeployerService creates at ~/.claude/skills/.
    """
    skill_dir = user_skills_base / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"# {name}")
    return skill_dir


def _make_project_skill(project_dot_claude: Path, name: str) -> Path:
    """Create <project_dot_claude>/skills/<name>/SKILL.md and return the skill dir.

    Mirrors the layout in <project>/.claude/skills/.
    """
    skill_dir = project_dot_claude / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"# {name}")
    return skill_dir


def _make_project(root: Path, name: str, skills: list[str]) -> Path:
    """Create a project directory with the given skills in .claude/skills/."""
    project = root / name
    for skill in skills:
        _make_project_skill(project / ".claude", skill)
    return project


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_user_level_skills():
    """Always patch _get_user_level_skills to return a deterministic small set."""
    target = "claude_mpm.services.skills.skill_dedup._get_user_level_skills"
    with patch(target, return_value=_FAKE_USER_SKILLS):
        yield


# ---------------------------------------------------------------------------
# dedup_project_skills tests
# ---------------------------------------------------------------------------


class TestDedupProjectSkills:
    """Unit tests for the single-project dedup helper."""

    def test_noop_when_no_skills_dir(self, tmp_path: Path):
        """Returns empty result when project has no .claude/skills/."""
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        user_skills.mkdir()

        result = dedup_project_skills(
            project_dir=tmp_path / "project",
            user_skills_base=user_skills,
            dry_run=True,
        )

        assert result.removed == []
        assert result.kept == []
        assert result.project_unique == []
        assert result.errors == []

    def test_noop_when_no_framework_skills_present(self, tmp_path: Path):
        """Project with only toolchain skills: nothing removed."""
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        user_skills.mkdir()

        project = tmp_path / "my-project"
        _make_project_skill(project / ".claude", "toolchains-python-core")
        _make_project_skill(project / ".claude", "cargo-publish")

        result = dedup_project_skills(
            project_dir=project,
            user_skills_base=user_skills,
            dry_run=True,
        )

        assert result.removed == []
        assert sorted(result.project_unique) == sorted(
            ["toolchains-python-core", "cargo-publish"]
        )

    def test_removes_only_user_level_skills_with_user_copy_dry_run(
        self, tmp_path: Path
    ):
        """In dry-run mode: reports what would be removed, files stay intact."""
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        # Provide user-level copy for mpm-help only.
        _make_user_skill(user_skills, "mpm-help")

        project = tmp_path / "my-project"
        _make_project_skill(
            project / ".claude", "mpm-help"
        )  # USER_LEVEL → should be removed
        _make_project_skill(
            project / ".claude", "mpm-status"
        )  # USER_LEVEL, no user copy → kept
        _make_project_skill(
            project / ".claude", "toolchains-python-core"
        )  # project-unique → kept

        result = dedup_project_skills(
            project_dir=project,
            user_skills_base=user_skills,
            dry_run=True,
        )

        assert result.removed == ["mpm-help"]
        assert result.kept == ["mpm-status"]
        assert result.project_unique == ["toolchains-python-core"]
        assert result.errors == []

        # Dry-run: file must still exist.
        assert (project / ".claude" / "skills" / "mpm-help").exists()

    def test_removes_only_user_level_skills_with_user_copy_apply(self, tmp_path: Path):
        """In apply mode: actually deletes framework skill dirs, leaves others."""
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        _make_user_skill(user_skills, "mpm-help")
        _make_user_skill(user_skills, "mpm")

        project = tmp_path / "my-project"
        _make_project_skill(project / ".claude", "mpm-help")
        _make_project_skill(project / ".claude", "mpm")
        # toolchain skill — must NOT be deleted
        _make_project_skill(project / ".claude", "toolchains-python-core")
        # project-unique skill — must NOT be deleted
        _make_project_skill(project / ".claude", "my-custom-skill")

        result = dedup_project_skills(
            project_dir=project,
            user_skills_base=user_skills,
            dry_run=False,
        )

        assert sorted(result.removed) == ["mpm", "mpm-help"]
        assert result.errors == []

        # Framework skills are gone.
        assert not (project / ".claude" / "skills" / "mpm-help").exists()
        assert not (project / ".claude" / "skills" / "mpm").exists()

        # Non-framework skills survive.
        assert (project / ".claude" / "skills" / "toolchains-python-core").exists()
        assert (project / ".claude" / "skills" / "my-custom-skill").exists()

    def test_never_removes_toolchain_skills(self, tmp_path: Path):
        """Toolchain-prefixed skills are never in USER_LEVEL_SKILLS → untouched."""
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        # Even if a toolchain skill had a user-level copy, we never touch it
        # because it's not in _FAKE_USER_SKILLS.
        _make_user_skill(user_skills, "toolchains-python-core")

        project = tmp_path / "proj"
        _make_project_skill(project / ".claude", "toolchains-python-core")

        result = dedup_project_skills(
            project_dir=project,
            user_skills_base=user_skills,
            dry_run=False,
        )

        assert result.removed == []
        assert result.project_unique == ["toolchains-python-core"]
        assert (project / ".claude" / "skills" / "toolchains-python-core").exists()

    def test_keeps_framework_skill_when_no_user_copy(self, tmp_path: Path):
        """Framework skill at project level is NOT removed if user-level copy is missing."""
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        user_skills.mkdir()
        # No user-level copy for mpm-help.

        project = tmp_path / "proj"
        _make_project_skill(project / ".claude", "mpm-help")

        result = dedup_project_skills(
            project_dir=project,
            user_skills_base=user_skills,
            dry_run=False,  # apply — but no user copy means it stays
        )

        assert result.removed == []
        assert result.kept == ["mpm-help"]
        # File untouched.
        assert (project / ".claude" / "skills" / "mpm-help").exists()

    def test_idempotent_second_run(self, tmp_path: Path):
        """Running dedup twice returns empty removed list on second run."""
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        _make_user_skill(user_skills, "mpm-help")

        project = tmp_path / "proj"
        _make_project_skill(project / ".claude", "mpm-help")

        # First run removes.
        r1 = dedup_project_skills(project, user_skills, dry_run=False)
        assert r1.removed == ["mpm-help"]

        # Second run is a no-op.
        r2 = dedup_project_skills(project, user_skills, dry_run=False)
        assert r2.removed == []
        assert r2.errors == []

    def test_dry_run_never_deletes_anything(self, tmp_path: Path):
        """dry_run=True must not remove any file, even when user copy is present."""
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        for skill in _FAKE_USER_SKILLS:
            _make_user_skill(user_skills, skill)

        project = tmp_path / "proj"
        for skill in _FAKE_USER_SKILLS:
            _make_project_skill(project / ".claude", skill)

        result = dedup_project_skills(project, user_skills, dry_run=True)

        assert result.removed_count == len(_FAKE_USER_SKILLS)
        # All files still there.
        for skill in _FAKE_USER_SKILLS:
            assert (project / ".claude" / "skills" / skill).exists(), skill


# ---------------------------------------------------------------------------
# sweep_projects tests
# ---------------------------------------------------------------------------


class TestSweepProjects:
    """Integration tests for the multi-project sweep."""

    def test_empty_root(self, tmp_path: Path):
        """Sweep of an empty directory produces zero results."""
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        root = tmp_path / "Projects"
        root.mkdir()
        user_skills = tmp_path / "user_skills"
        user_skills.mkdir()

        summary = sweep_projects(root=root, user_skills_base=user_skills, dry_run=True)

        assert summary.projects_scanned == 0
        assert summary.results == []
        assert summary.total_removed == 0

    def test_missing_root_returns_empty(self, tmp_path: Path):
        """If root does not exist, sweep returns empty summary without error."""
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        root = tmp_path / "nonexistent"
        user_skills = tmp_path / "user_skills"
        user_skills.mkdir()

        summary = sweep_projects(root=root, user_skills_base=user_skills, dry_run=True)

        assert summary.total_removed == 0
        assert summary.results == []

    def test_projects_without_skills_dir_counted_not_reported(self, tmp_path: Path):
        """Projects with no .claude/skills/ dir are counted but produce no result entry."""
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        root = tmp_path / "Projects"
        (root / "bare-project").mkdir(parents=True)  # no skills dir
        (root / "another").mkdir()

        user_skills = tmp_path / "user_skills"
        user_skills.mkdir()

        summary = sweep_projects(root=root, user_skills_base=user_skills, dry_run=True)

        assert summary.projects_scanned == 2
        assert summary.results == []

    def test_sweep_reports_duplicates_in_dry_run(self, tmp_path: Path):
        """Dry-run sweep reports duplicates across multiple projects."""
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        user_skills = tmp_path / "user_skills"
        _make_user_skill(user_skills, "mpm-help")
        _make_user_skill(user_skills, "mpm-status")

        root = tmp_path / "Projects"
        _make_project(root, "proj-a", ["mpm-help", "toolchains-python-core"])
        _make_project(root, "proj-b", ["mpm-status", "cargo-publish"])
        _make_project(root, "proj-c", ["cargo-publish"])  # no framework skills

        summary = sweep_projects(root=root, user_skills_base=user_skills, dry_run=True)

        assert summary.projects_scanned == 3
        assert summary.total_removed == 2  # mpm-help + mpm-status
        assert summary.projects_with_dupes == 2

        # Files untouched (dry-run).
        assert (root / "proj-a" / ".claude" / "skills" / "mpm-help").exists()
        assert (root / "proj-b" / ".claude" / "skills" / "mpm-status").exists()

    def test_sweep_apply_removes_duplicates(self, tmp_path: Path):
        """Apply mode deletes framework skill dirs across all projects."""
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        user_skills = tmp_path / "user_skills"
        _make_user_skill(user_skills, "mpm-help")

        root = tmp_path / "Projects"
        _make_project(root, "proj-a", ["mpm-help", "toolchains-rust"])
        _make_project(root, "proj-b", ["mpm-help", "my-local-skill"])

        summary = sweep_projects(root=root, user_skills_base=user_skills, dry_run=False)

        assert summary.total_removed == 2

        # Framework skills deleted.
        assert not (root / "proj-a" / ".claude" / "skills" / "mpm-help").exists()
        assert not (root / "proj-b" / ".claude" / "skills" / "mpm-help").exists()

        # Non-framework skills survive.
        assert (root / "proj-a" / ".claude" / "skills" / "toolchains-rust").exists()
        assert (root / "proj-b" / ".claude" / "skills" / "my-local-skill").exists()

    def test_sweep_dry_run_does_not_delete_when_apply_not_set(self, tmp_path: Path):
        """Default dry_run=True must never touch the filesystem."""
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        user_skills = tmp_path / "user_skills"
        for skill in _FAKE_USER_SKILLS:
            _make_user_skill(user_skills, skill)

        root = tmp_path / "Projects"
        for proj_name in ["p1", "p2", "p3"]:
            _make_project(root, proj_name, list(_FAKE_USER_SKILLS))

        summary = sweep_projects(root=root, user_skills_base=user_skills, dry_run=True)

        assert summary.total_removed == len(_FAKE_USER_SKILLS) * 3

        # Every file still present.
        for proj_name in ["p1", "p2", "p3"]:
            for skill in _FAKE_USER_SKILLS:
                path = root / proj_name / ".claude" / "skills" / skill
                assert path.exists(), f"dry-run deleted {path}"

    def test_project_unique_skills_preserved_in_apply(self, tmp_path: Path):
        """Project-unique and toolchain skills survive --apply sweep."""
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        user_skills = tmp_path / "user_skills"
        _make_user_skill(user_skills, "mpm")

        root = tmp_path / "Projects"
        project = _make_project(
            root,
            "proj",
            [
                "mpm",  # USER_LEVEL → removed
                "toolchains-typescript-core",  # project-unique → kept
                "cargo-publish",  # project-unique → kept
                "buffer",  # not in USER_LEVEL_SKILLS → kept
                "example-skill",  # not in USER_LEVEL_SKILLS → kept
            ],
        )

        sweep_projects(root=root, user_skills_base=user_skills, dry_run=False)

        assert not (project / ".claude" / "skills" / "mpm").exists()
        assert (project / ".claude" / "skills" / "toolchains-typescript-core").exists()
        assert (project / ".claude" / "skills" / "cargo-publish").exists()
        assert (project / ".claude" / "skills" / "buffer").exists()
        assert (project / ".claude" / "skills" / "example-skill").exists()


# ---------------------------------------------------------------------------
# Mutation-hardening tests (target specific surviving mutants)
# ---------------------------------------------------------------------------


class TestDefaultsAndGuards:
    """Pin default-argument and field-default behaviour that prior tests
    overwrote before observing.  These target mutants on the dry_run defaults,
    the SweepSummary.projects_scanned field default, the None-guard on
    user_skills_base, and the sweep loop's continue/break semantics."""

    def test_dedup_default_is_dry_run(self, tmp_path: Path):
        """dedup_project_skills() with NO dry_run arg must NOT delete files.

        Targets the `dry_run: bool = True` default on dedup_project_skills
        (line 92). Earlier tests always passed dry_run explicitly, so flipping
        the default to False went unnoticed. Here we rely on the default and
        assert the on-disk skill dir survives — i.e. the safe default is
        dry-run, not apply.
        """
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        _make_user_skill(user_skills, "mpm-help")

        project = tmp_path / "proj"
        _make_project_skill(project / ".claude", "mpm-help")

        # Call WITHOUT dry_run — the default must protect the file.
        result = dedup_project_skills(
            project_dir=project,
            user_skills_base=user_skills,
        )

        assert result.removed == ["mpm-help"]  # reported as "would remove"
        assert (project / ".claude" / "skills" / "mpm-help").exists(), (
            "default must be dry-run: file must still exist on disk"
        )

    def test_sweep_default_is_dry_run(self, tmp_path: Path):
        """sweep_projects() with NO dry_run arg must NOT delete files.

        Targets the `dry_run: bool = True` default on sweep_projects (line 185).
        """
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        user_skills = tmp_path / "user_skills"
        _make_user_skill(user_skills, "mpm-help")

        root = tmp_path / "Projects"
        _make_project(root, "proj-a", ["mpm-help"])

        # Call WITHOUT dry_run — default must be dry-run.
        summary = sweep_projects(root=root, user_skills_base=user_skills)

        assert summary.total_removed == 1
        assert summary.dry_run is True
        assert (root / "proj-a" / ".claude" / "skills" / "mpm-help").exists(), (
            "default sweep must be dry-run: file must still exist on disk"
        )

    def test_projects_scanned_defaults_to_zero_on_missing_root(self, tmp_path: Path):
        """A missing root returns a SweepSummary with projects_scanned == 0.

        Targets the `projects_scanned: int = 0` field default (line 74). On the
        `not root.exists()` early-return path the field is never assigned, so the
        default is the only thing observable. The empty-root test does not catch
        this because there len(top_level) overwrites the default with 0 anyway.
        """
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        root = tmp_path / "does-not-exist"
        user_skills = tmp_path / "user_skills"
        user_skills.mkdir()

        summary = sweep_projects(root=root, user_skills_base=user_skills)

        assert summary.projects_scanned == 0
        assert summary.results == []

    def test_sweep_skips_skill_less_projects_and_continues(self, tmp_path: Path):
        """A skill-less project earlier in sort order must NOT stop the sweep.

        Targets the `continue` -> `break` mutant in the sweep loop (line 230).
        'aaa-bare' (no .claude/skills/) sorts before 'zzz-real' (a removable
        framework skill). With `continue` the sweep skips the bare project and
        still processes the later one; with `break` it would stop at the bare
        project and miss the real duplicate.
        """
        from claude_mpm.services.skills.skill_dedup import sweep_projects

        user_skills = tmp_path / "user_skills"
        _make_user_skill(user_skills, "mpm-help")

        root = tmp_path / "Projects"
        (root / "aaa-bare").mkdir(parents=True)  # sorts first, no skills dir
        _make_project(root, "zzz-real", ["mpm-help"])  # sorts last, has duplicate

        summary = sweep_projects(root=root, user_skills_base=user_skills, dry_run=True)

        assert summary.projects_scanned == 2
        assert summary.total_removed == 1, (
            "sweep must continue past the skill-less project to reach the duplicate"
        )

    def test_sweep_user_skills_base_defaults_to_home(self, tmp_path: Path, monkeypatch):
        """Omitting user_skills_base falls back to ~/.claude/skills (not None).

        Targets the `if user_skills_base is None:` guard (line 210). The mutant
        flips it to `is not None`, which leaves user_skills_base as None and makes
        the downstream `None / skill_name` raise TypeError. We monkeypatch
        Path.home() to a tmp dir so the real home is never touched, place the
        user-level copy there, and assert the sweep resolves the duplicate via
        the home fallback.
        """
        from claude_mpm.services.skills import skill_dedup

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        # User-level copy lives under the (patched) home dir.
        _make_user_skill(fake_home / ".claude" / "skills", "mpm-help")
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: fake_home))

        root = tmp_path / "Projects"
        _make_project(root, "proj", ["mpm-help"])

        # No user_skills_base -> must default to fake_home/.claude/skills.
        summary = skill_dedup.sweep_projects(root=root, dry_run=True)

        assert summary.total_removed == 1, (
            "default user_skills_base must resolve to ~/.claude/skills (home fallback)"
        )


class TestUserCopyDetectionLogic:
    """Pin the exact predicate that decides a user-level copy exists:
    `is_dir() and (SKILL.md exists OR any *.md)`.  Targets the or/and and
    is_dir-and/or mutants on lines 147-148."""

    def test_non_skill_md_file_still_counts_as_user_copy(self, tmp_path: Path):
        """A user dir with only a non-SKILL.md *.md file still counts as a copy.

        Targets two mutants on line 147:
          - glob pattern `*.md` -> `XX*.mdXX` (id 37): under the mutant the glob
            finds nothing, so detection falls back to the (missing) SKILL.md and
            the skill is wrongly kept.
          - `or` -> `and` (id 38): under the mutant BOTH SKILL.md and a *.md match
            would be required; with only index.md present, detection fails and the
            skill is wrongly kept.
        Real behaviour: the `or` + `*.md` glob means index.md alone is enough to
        confirm the copy, so the project duplicate IS removed.
        """
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        user_skill_dir = user_skills / "mpm-help"
        user_skill_dir.mkdir(parents=True)
        # Deliberately NO SKILL.md — only a differently named markdown file.
        (user_skill_dir / "index.md").write_text("# mpm-help")

        project = tmp_path / "proj"
        _make_project_skill(project / ".claude", "mpm-help")

        result = dedup_project_skills(
            project_dir=project,
            user_skills_base=user_skills,
            dry_run=False,
        )

        assert result.removed == ["mpm-help"], (
            "a non-SKILL.md *.md file must still confirm the user-level copy"
        )
        assert result.kept == []
        assert not (project / ".claude" / "skills" / "mpm-help").exists()

    def test_empty_user_dir_is_not_a_copy(self, tmp_path: Path):
        """An empty user-level dir (no *.md at all) does NOT count as a copy.

        Targets the `is_dir() and (...)` -> `is_dir() or (...)` mutant (id 39,
        lines 147-148). The user dir EXISTS (is_dir() True) but contains no md
        files, so the right operand is False. Real `and`: True and False = False
        -> skill kept. Mutant `or`: True -> skill wrongly removed. Asserting the
        skill is KEPT (and the file survives) distinguishes the two.
        """
        from claude_mpm.services.skills.skill_dedup import dedup_project_skills

        user_skills = tmp_path / "user_skills"
        empty_user_dir = user_skills / "mpm-help"
        empty_user_dir.mkdir(parents=True)  # exists, but no *.md inside

        project = tmp_path / "proj"
        _make_project_skill(project / ".claude", "mpm-help")

        result = dedup_project_skills(
            project_dir=project,
            user_skills_base=user_skills,
            dry_run=False,
        )

        assert result.removed == []
        assert result.kept == ["mpm-help"], (
            "an empty user dir must NOT be treated as a confirmed copy"
        )
        assert (project / ".claude" / "skills" / "mpm-help").exists()
