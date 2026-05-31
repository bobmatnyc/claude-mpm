"""Tests for the ADR scaffold created by mpm-init.

Covers:
- docs/adr/README.md and docs/adr/0000-template.md are created in a fresh
  project directory.
- Idempotency: re-running scaffold_adr_directory() does not clobber files
  that already exist (an edited README must survive).
- The mpm-adr SKILL.md files parse correctly (valid frontmatter with
  required fields).

WHY: Issue #562 — ADRs as a first-class opt-in convention in claude-mpm.
"""

import sys
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SRC_ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_ROOT))


def _load_skill_frontmatter(skill_path: Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md file.

    Returns an empty dict if the file has no frontmatter.

    Raises:
        ValueError: If frontmatter delimiters are found but content is invalid.
    """
    content = skill_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}

    # Split on the closing --- delimiter
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter in {skill_path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Scaffold tests
# ---------------------------------------------------------------------------


class TestADRScaffold:
    """Verify that scaffold_adr_directory() creates expected files."""

    def test_creates_readme_in_new_project(self, tmp_path: Path) -> None:
        """README.md is created inside docs/adr/ for a fresh project."""
        from claude_mpm.cli.commands.mpm_init.adr_scaffold import scaffold_adr_directory

        scaffold_adr_directory(tmp_path)

        readme = tmp_path / "docs" / "adr" / "README.md"
        assert readme.exists(), "docs/adr/README.md was not created"
        content = readme.read_text(encoding="utf-8")
        assert len(content) > 0, "README.md is empty"

    def test_creates_template_in_new_project(self, tmp_path: Path) -> None:
        """0000-template.md is created inside docs/adr/ for a fresh project."""
        from claude_mpm.cli.commands.mpm_init.adr_scaffold import scaffold_adr_directory

        scaffold_adr_directory(tmp_path)

        template = tmp_path / "docs" / "adr" / "0000-template.md"
        assert template.exists(), "docs/adr/0000-template.md was not created"
        content = template.read_text(encoding="utf-8")
        assert "## Status" in content, "Template is missing the ## Status section"
        assert "## Context" in content, "Template is missing the ## Context section"
        assert "## Decision" in content, "Template is missing the ## Decision section"
        assert "## Consequences" in content, (
            "Template is missing the ## Consequences section"
        )

    def test_returns_created_true_for_new_files(self, tmp_path: Path) -> None:
        """scaffold_adr_directory() returns True for each newly created file."""
        from claude_mpm.cli.commands.mpm_init.adr_scaffold import scaffold_adr_directory

        result = scaffold_adr_directory(tmp_path)

        assert result["docs/adr/README.md"] is True
        assert result["docs/adr/0000-template.md"] is True

    def test_idempotent_does_not_overwrite_existing_readme(
        self, tmp_path: Path
    ) -> None:
        """Re-running scaffold does not clobber an already-existing README.md."""
        from claude_mpm.cli.commands.mpm_init.adr_scaffold import scaffold_adr_directory

        # First run — creates files
        scaffold_adr_directory(tmp_path)

        # Simulate user editing the README
        readme = tmp_path / "docs" / "adr" / "README.md"
        custom_content = "# My Custom ADR README\n\nThis is my edited version.\n"
        readme.write_text(custom_content, encoding="utf-8")

        # Second run — must not overwrite the edited README
        result = scaffold_adr_directory(tmp_path)

        assert result["docs/adr/README.md"] is False, (
            "scaffold_adr_directory() overwrote an existing README.md"
        )
        assert readme.read_text(encoding="utf-8") == custom_content, (
            "README.md content was changed despite already existing"
        )

    def test_idempotent_does_not_overwrite_existing_template(
        self, tmp_path: Path
    ) -> None:
        """Re-running scaffold does not clobber an already-existing 0000-template.md."""
        from claude_mpm.cli.commands.mpm_init.adr_scaffold import scaffold_adr_directory

        # First run
        scaffold_adr_directory(tmp_path)

        template = tmp_path / "docs" / "adr" / "0000-template.md"
        custom_content = "# My edited template\n"
        template.write_text(custom_content, encoding="utf-8")

        # Second run
        result = scaffold_adr_directory(tmp_path)

        assert result["docs/adr/0000-template.md"] is False, (
            "scaffold_adr_directory() overwrote an existing 0000-template.md"
        )
        assert template.read_text(encoding="utf-8") == custom_content

    def test_idempotent_second_run_returns_false_for_both(self, tmp_path: Path) -> None:
        """Both entries are False on the second run when nothing changed."""
        from claude_mpm.cli.commands.mpm_init.adr_scaffold import scaffold_adr_directory

        scaffold_adr_directory(tmp_path)
        result = scaffold_adr_directory(tmp_path)

        assert result["docs/adr/README.md"] is False
        assert result["docs/adr/0000-template.md"] is False

    def test_creates_docs_adr_directory_when_missing(self, tmp_path: Path) -> None:
        """docs/adr/ directory is created if it does not exist."""
        from claude_mpm.cli.commands.mpm_init.adr_scaffold import scaffold_adr_directory

        adr_dir = tmp_path / "docs" / "adr"
        assert not adr_dir.exists()

        scaffold_adr_directory(tmp_path)

        assert adr_dir.is_dir()

    def test_readme_mentions_when_to_write(self, tmp_path: Path) -> None:
        """README.md must explain the 'when to write an ADR' heuristic."""
        from claude_mpm.cli.commands.mpm_init.adr_scaffold import scaffold_adr_directory

        scaffold_adr_directory(tmp_path)

        readme = tmp_path / "docs" / "adr" / "README.md"
        content = readme.read_text(encoding="utf-8")
        # Must contain guidance on when (and when not) to write an ADR
        assert "when" in content.lower(), (
            "README.md should mention 'when' to write an ADR"
        )

    def test_readme_mentions_trusty_tools_prior_art(self, tmp_path: Path) -> None:
        """README.md references bobmatnyc/trusty-tools as prior art."""
        from claude_mpm.cli.commands.mpm_init.adr_scaffold import scaffold_adr_directory

        scaffold_adr_directory(tmp_path)

        readme = tmp_path / "docs" / "adr" / "README.md"
        content = readme.read_text(encoding="utf-8")
        assert "trusty-tools" in content, (
            "README.md should reference bobmatnyc/trusty-tools as prior art"
        )


# ---------------------------------------------------------------------------
# SKILL.md validation tests
# ---------------------------------------------------------------------------


class TestADRSkillFiles:
    """Verify that the mpm-adr SKILL.md files have valid, required frontmatter."""

    PLUGIN_SKILL = (
        Path(__file__).parent.parent / "plugin" / "skills" / "mpm-adr" / "SKILL.md"
    )
    BUNDLED_SKILL = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "skills"
        / "bundled"
        / "pm"
        / "mpm-adr"
        / "SKILL.md"
    )

    @pytest.fixture(params=["plugin", "bundled"])
    def skill_path(self, request: pytest.FixtureRequest) -> Path:
        """Parametrize over both skill file locations."""
        return self.PLUGIN_SKILL if request.param == "plugin" else self.BUNDLED_SKILL

    def test_skill_file_exists(self, skill_path: Path) -> None:
        """The SKILL.md file must exist at the expected path."""
        assert skill_path.exists(), f"SKILL.md not found at {skill_path}"

    def test_skill_has_valid_frontmatter(self, skill_path: Path) -> None:
        """SKILL.md must have parseable YAML frontmatter."""
        frontmatter = _load_skill_frontmatter(skill_path)
        assert frontmatter, f"No frontmatter found in {skill_path}"

    def test_skill_has_required_name_field(self, skill_path: Path) -> None:
        """Frontmatter must contain a 'name' field."""
        frontmatter = _load_skill_frontmatter(skill_path)
        assert "name" in frontmatter, f"'name' field missing in {skill_path}"
        assert frontmatter["name"] == "mpm-adr"

    def test_skill_has_required_description_field(self, skill_path: Path) -> None:
        """Frontmatter must contain a non-empty 'description' field."""
        frontmatter = _load_skill_frontmatter(skill_path)
        assert "description" in frontmatter, (
            f"'description' field missing in {skill_path}"
        )
        assert frontmatter["description"], f"'description' is empty in {skill_path}"

    def test_skill_description_within_spec_length(self, skill_path: Path) -> None:
        """Description must be <= 1024 characters (agentskills.io spec)."""
        frontmatter = _load_skill_frontmatter(skill_path)
        desc = frontmatter.get("description", "")
        assert len(desc) <= 1024, (
            f"Description too long ({len(desc)} chars > 1024) in {skill_path}"
        )

    def test_skill_name_format(self, skill_path: Path) -> None:
        """Name must match pattern: lowercase alphanumeric + hyphens."""
        import re

        frontmatter = _load_skill_frontmatter(skill_path)
        name = frontmatter.get("name", "")
        assert re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name), (
            f"Name '{name}' in {skill_path} does not match the required pattern"
        )

    def test_plugin_and_bundled_skills_have_matching_name(self) -> None:
        """Both SKILL.md copies must have the same 'name' value."""
        plugin_fm = _load_skill_frontmatter(self.PLUGIN_SKILL)
        bundled_fm = _load_skill_frontmatter(self.BUNDLED_SKILL)
        assert plugin_fm.get("name") == bundled_fm.get("name"), (
            "plugin and bundled SKILL.md have different 'name' values"
        )

    def test_skill_body_contains_nygard_sections(self, skill_path: Path) -> None:
        """SKILL.md body must describe the Nygard template sections."""
        content = skill_path.read_text(encoding="utf-8")
        for section in ("## Status", "## Context", "## Decision", "## Consequences"):
            assert section in content, (
                f"SKILL.md at {skill_path} is missing section '{section}'"
            )

    def test_skill_body_mentions_opt_in(self, skill_path: Path) -> None:
        """SKILL.md must communicate that ADRs are opt-in."""
        content = skill_path.read_text(encoding="utf-8")
        assert "opt-in" in content.lower(), (
            f"SKILL.md at {skill_path} does not mention that ADRs are opt-in"
        )
