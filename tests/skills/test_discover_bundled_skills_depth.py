"""Regression tests for deeply-nested bundled skill discovery (issue #808).

WHAT: Verify ``SkillsService.discover_bundled_skills()`` finds SKILL.md files at
any depth under the bundled root, not just two levels deep.
WHY: The previous nested ``iterdir()`` implementation only reached level-2
``SKILL.md`` files, silently dropping skills laid out as
``toolchains/<lang>/<tier>/SKILL.md`` and ``universal/<skill>/SKILL.md``.

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


def _build_bundled_tree(root: Path) -> None:
    """Create a fake bundled/ tree spanning levels 2 and 3 plus a hidden dir."""
    # Level 2 — already worked before the fix.
    _write_skill(root / "category-a" / "skill-flat", "skill-flat")
    # Level 3 — was broken before the fix.
    _write_skill(root / "toolchains" / "rust" / "core", "core")
    _write_skill(root / "universal" / "collab" / "brainstorm", "brainstorm")
    # Hidden dir — must be ignored.
    _write_skill(root / ".hidden" / "skill", "hidden-skill")


def _discover(tmp_path: Path) -> dict[str, dict]:
    bundled = tmp_path / "bundled"
    _build_bundled_tree(bundled)

    service = SkillsService()
    service.bundled_skills_path = bundled
    skills = service.discover_bundled_skills()

    # Restrict to skills under our temp tree; the Superpowers cache scan may add
    # unrelated real skills from the developer's home directory.
    return {s["name"]: s for s in skills if Path(s["path"]).is_relative_to(bundled)}


def test_discovers_skills_at_all_depths(tmp_path: Path) -> None:
    found = _discover(tmp_path)
    assert set(found) == {"skill-flat", "core", "brainstorm"}


def test_flat_skill_category_and_name(tmp_path: Path) -> None:
    found = _discover(tmp_path)
    assert found["skill-flat"]["category"] == "category-a"
    assert found["skill-flat"]["name"] == "skill-flat"


def test_level3_toolchain_skill_category_and_name(tmp_path: Path) -> None:
    found = _discover(tmp_path)
    assert found["core"]["category"] == "toolchains"
    assert found["core"]["name"] == "core"


def test_level3_universal_skill_category_and_name(tmp_path: Path) -> None:
    found = _discover(tmp_path)
    assert found["brainstorm"]["category"] == "universal"
    assert found["brainstorm"]["name"] == "brainstorm"


def test_hidden_dirs_are_not_discovered(tmp_path: Path) -> None:
    found = _discover(tmp_path)
    assert "hidden-skill" not in found
