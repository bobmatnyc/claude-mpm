"""Regression tests for leaf-name collision in bundled skill discovery (issue #829).

WHAT: Verify ``SkillsService.discover_bundled_skills()`` retains ALL skills even
when two or more skills share the same immediate parent directory name (leaf name),
e.g. ``a/b/core/SKILL.md`` and ``a/c/core/SKILL.md`` both having ``name == "core"``.
WHY: After PR #813 switched discovery to ``rglob``, each skill's ``name`` was set to
its leaf directory.  Deeply-nested skills under different categories can share a leaf
name (the six ``toolchains/<lang>/core`` skills all resolve to ``name="core"``).
Any dict keyed by ``name`` alone silently drops all but one.  The fix introduces a
``canonical_id`` field (POSIX-formatted relative path, e.g. ``"toolchains/rust/core"``)
that is unique across the entire bundled tree and safe to use as a dict key.

References
----------
SPEC-SKILLS-02~1 : docs/specs/skills.md#SPEC-SKILLS-02~1
"""

from pathlib import Path

from claude_mpm.skills.skills_service import SkillsService

_SKILL_MD = """---
name: {name}
description: Test skill {name}
---

# {name}
"""


def _write_skill(skill_dir: Path, name: str) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(_SKILL_MD.format(name=name), encoding="utf-8")


def _discover(bundled: Path) -> list[dict]:
    """Run discover_bundled_skills() against a custom bundled root."""
    service = SkillsService()
    service.bundled_skills_path = bundled
    skills = service.discover_bundled_skills()
    # Filter to skills under our temp tree only (avoids Superpowers cache noise).
    return [s for s in skills if Path(s["path"]).is_relative_to(bundled)]


# ---------------------------------------------------------------------------
# Core regression: two skills at different paths sharing the same leaf name
# ---------------------------------------------------------------------------


def test_leaf_name_collision_both_skills_discovered(tmp_path: Path) -> None:
    """Skills sharing a leaf name must ALL be returned, not silently deduped.

    Scenario: a/b/core/SKILL.md and a/c/core/SKILL.md both produce name="core".
    Before the fix a dict keyed by ``name`` would keep only one of them.
    """
    bundled = tmp_path / "bundled"
    _write_skill(bundled / "a" / "b" / "core", "core")
    _write_skill(bundled / "a" / "c" / "core", "core")

    skills = _discover(bundled)
    assert len(skills) == 2, (
        f"Expected 2 skills but got {len(skills)}: "
        f"{[s['canonical_id'] for s in skills]}"
    )


def test_leaf_name_collision_canonical_ids_are_distinct(tmp_path: Path) -> None:
    """canonical_id must differ even when leaf names collide."""
    bundled = tmp_path / "bundled"
    _write_skill(bundled / "a" / "b" / "core", "core")
    _write_skill(bundled / "a" / "c" / "core", "core")

    skills = _discover(bundled)
    canonical_ids = {s["canonical_id"] for s in skills}
    assert canonical_ids == {"a/b/core", "a/c/core"}


def test_leaf_name_collision_both_skill_names_present(tmp_path: Path) -> None:
    """Both skills must report name='core' (leaf name preserved unchanged)."""
    bundled = tmp_path / "bundled"
    _write_skill(bundled / "a" / "b" / "core", "core")
    _write_skill(bundled / "a" / "c" / "core", "core")

    skills = _discover(bundled)
    names = [s["name"] for s in skills]
    assert names.count("core") == 2, f"Expected 2 skills named 'core', got: {names}"


# ---------------------------------------------------------------------------
# canonical_id format correctness
# ---------------------------------------------------------------------------


def test_canonical_id_is_posix_relative_path(tmp_path: Path) -> None:
    """canonical_id must be a POSIX-format relative path from the bundled root."""
    bundled = tmp_path / "bundled"
    _write_skill(bundled / "toolchains" / "rust" / "core", "core")

    skills = _discover(bundled)
    assert len(skills) == 1
    assert skills[0]["canonical_id"] == "toolchains/rust/core"


def test_flat_skill_canonical_id_equals_leaf_name(tmp_path: Path) -> None:
    """A skill at depth-1 (direct child of bundled root) has canonical_id == name."""
    bundled = tmp_path / "bundled"
    _write_skill(bundled / "my-skill", "my-skill")

    skills = _discover(bundled)
    assert len(skills) == 1
    assert skills[0]["canonical_id"] == "my-skill"
    assert skills[0]["name"] == "my-skill"
    assert skills[0]["canonical_id"] == skills[0]["name"]


def test_deeper_skill_canonical_id_differs_from_leaf_name(tmp_path: Path) -> None:
    """A skill at depth > 1 has canonical_id != name."""
    bundled = tmp_path / "bundled"
    _write_skill(bundled / "toolchains" / "python" / "core", "core")

    skills = _discover(bundled)
    assert len(skills) == 1
    assert skills[0]["name"] == "core"
    assert skills[0]["canonical_id"] == "toolchains/python/core"
    assert skills[0]["canonical_id"] != skills[0]["name"]


# ---------------------------------------------------------------------------
# Realistic six-toolchain scenario mirroring the actual bundled layout
# ---------------------------------------------------------------------------


def test_six_toolchain_cores_all_discovered(tmp_path: Path) -> None:
    """All six toolchain/core skills must be discovered (not just one)."""
    bundled = tmp_path / "bundled"
    languages = ["rust", "python", "golang", "typescript", "java", "javascript"]
    for lang in languages:
        _write_skill(bundled / "toolchains" / lang / "core", "core")

    skills = _discover(bundled)
    assert len(skills) == 6, (
        f"Expected 6 skills, got {len(skills)}: {[s['canonical_id'] for s in skills]}"
    )


def test_six_toolchain_cores_canonical_ids_all_distinct(tmp_path: Path) -> None:
    """All six toolchain/core canonical_ids must be unique."""
    bundled = tmp_path / "bundled"
    languages = ["rust", "python", "golang", "typescript", "java", "javascript"]
    for lang in languages:
        _write_skill(bundled / "toolchains" / lang / "core", "core")

    skills = _discover(bundled)
    canonical_ids = {s["canonical_id"] for s in skills}
    expected = {f"toolchains/{lang}/core" for lang in languages}
    assert canonical_ids == expected


# ---------------------------------------------------------------------------
# Existing behaviour is not broken
# ---------------------------------------------------------------------------


def test_non_colliding_skills_still_discovered(tmp_path: Path) -> None:
    """Skills with unique leaf names must still be discovered correctly."""
    bundled = tmp_path / "bundled"
    _write_skill(bundled / "category-a" / "skill-flat", "skill-flat")
    _write_skill(bundled / "toolchains" / "rust" / "core", "core")

    skills = _discover(bundled)
    assert len(skills) == 2
    by_id = {s["canonical_id"]: s for s in skills}
    assert "category-a/skill-flat" in by_id
    assert "toolchains/rust/core" in by_id


def test_hidden_dirs_still_excluded_with_canonical_id(tmp_path: Path) -> None:
    """Hidden-directory skills must still be excluded when canonical_id is present."""
    bundled = tmp_path / "bundled"
    _write_skill(bundled / "category-a" / "skill-visible", "skill-visible")
    _write_skill(bundled / ".hidden" / "skill-hidden", "skill-hidden")

    skills = _discover(bundled)
    canonical_ids = {s["canonical_id"] for s in skills}
    assert "category-a/skill-visible" in canonical_ids
    assert ".hidden/skill-hidden" not in canonical_ids


# ---------------------------------------------------------------------------
# update_skills: leaf-name collision warning
# ---------------------------------------------------------------------------


def test_update_skills_warns_on_leaf_name_collision(
    tmp_path: Path, caplog: object
) -> None:
    """update_skills must emit a WARNING when two bundled skills share a leaf name.

    Why: Callers pass plain leaf names to update_skills; if two bundled skills
    share the same leaf name the correct one to update is ambiguous.  The
    collision warning makes this visible so callers can pass canonical_id instead.

    What: Set up two bundled skills with the same leaf name ("core") under
    different category paths, then call update_skills with that name; assert
    the warning text appears in the log.

    Test: The captured log must contain "ambiguous leaf names" and the
    colliding name.
    """
    import logging

    bundled = tmp_path / "bundled"
    _write_skill(bundled / "cat-a" / "core", "core")
    _write_skill(bundled / "cat-b" / "core", "core")

    service = SkillsService()
    service.bundled_skills_path = bundled
    service.deployed_skills_path = tmp_path / "deployed"

    with caplog.at_level(logging.WARNING, logger="claude_mpm.skills.skills_service"):
        # Pass "core" explicitly so the method does not bail out early on an
        # empty skill_names list; the collision warning fires before the
        # individual skill lookup.
        service.update_skills(["core"])

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    collision_warnings = [
        r for r in warning_records if "ambiguous leaf names" in r.message
    ]
    assert collision_warnings, (
        f"Expected a collision warning but got records: "
        f"{[r.message for r in warning_records]}"
    )
    assert "core" in collision_warnings[0].message
