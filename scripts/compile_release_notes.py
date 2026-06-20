#!/usr/bin/env python3
"""Compile structured per-minor-version release notes from CHANGELOG.md.

Called automatically by `make compile-release-notes` after `cz bump`.

Behaviour:
- Minor release (X.Y.0): creates docs/releases/vX.Y.md
- Patch release (X.Y.Z, Z>0): appends ### vX.Y.Z section to docs/releases/vX.Y.md
- Always writes docs/releases/release-notes-latest.md for gh release create --notes-file
  (written to docs/releases/ not dist/ so it survives the dist/ + build/ clean in
  release-build and is available when release-publish runs gh release create)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Section heading normalisation map
# ---------------------------------------------------------------------------
_HEADING_MAP: dict[str, str] = {
    "Feat": "Features",
    "Fix": "Bug Fixes",
    "Perf": "Performance",
    "Refactor": "Refactoring",
    # Already-normalised spellings are passed through unchanged
    "Features": "Features",
    "Bug Fixes": "Bug Fixes",
    "Fixed": "Bug Fixes",
    "Performance": "Performance",
    "Refactoring": "Refactoring",
    "Changed": "Changed",
}


def _normalise_section(raw: str) -> str:
    """Normalise heading names and strip blank-only sub-sections."""
    lines = raw.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(#+)\s+(.+)$", line)
        if m:
            depth = m.group(1)
            heading = m.group(2).strip()
            normalised = _HEADING_MAP.get(heading, heading)
            line = f"{depth} {normalised}"
        out.append(line)
        i += 1

    # Remove sub-sections whose bodies are entirely blank
    result: list[str] = []
    j = 0
    while j < len(out):
        line = out[j]
        if re.match(r"^#{2,}\s+", line):
            # Collect the body of this sub-section
            body_start = j + 1
            body_end = body_start
            while body_end < len(out) and not re.match(r"^#{2,}\s+", out[body_end]):
                body_end += 1
            body = out[body_start:body_end]
            if any(bl.strip() for bl in body):
                result.append(line)
                result.extend(body)
            j = body_end
        else:
            result.append(line)
            j += 1

    # Trim trailing blank lines
    while result and not result[-1].strip():
        result.pop()

    return "\n".join(result)


def _find_changelog_section(changelog_text: str, version: str) -> tuple[str, str]:
    """Return (date_str, section_body) for *version* from changelog text.

    Returns ("unknown", "") when the version heading is not found.
    """
    # Three supported header formats, matched in preference order:
    #   ## v6.5.26 (2026-06-10)
    #   ## [6.5.26] (2026-06-10)
    #   ## [6.5.26] - 2026-06-10
    patterns = [
        re.compile(
            rf"^## v{re.escape(version)}\s+\((\d{{4}}-\d{{2}}-\d{{2}})\)",
            re.MULTILINE,
        ),
        re.compile(
            rf"^## \[{re.escape(version)}\]\s+\((\d{{4}}-\d{{2}}-\d{{2}})\)",
            re.MULTILINE,
        ),
        re.compile(
            rf"^## \[{re.escape(version)}\]\s*-\s*(\d{{4}}-\d{{2}}-\d{{2}})",
            re.MULTILINE,
        ),
    ]

    start_match = None
    date_str = "unknown"
    for pat in patterns:
        m = pat.search(changelog_text)
        if m:
            start_match = m
            date_str = m.group(1)
            break

    if start_match is None:
        return "unknown", ""

    # Find the start of the next top-level `## ` heading
    remainder = changelog_text[start_match.end() :]
    next_header = re.search(r"^## ", remainder, re.MULTILINE)
    if next_header:
        body = remainder[: next_header.start()]
    else:
        body = remainder

    return date_str, body.strip()


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).parent.parent

    # 1. Read current version
    version_file = repo_root / "VERSION"
    if not version_file.exists():
        print("ERROR: VERSION file not found", file=sys.stderr)
        return 1
    version = version_file.read_text(encoding="utf-8").strip()

    # Parse X, Y, Z
    ver_match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not ver_match:
        print(f"ERROR: VERSION '{version}' is not in X.Y.Z format", file=sys.stderr)
        return 1
    major, minor, patch = ver_match.group(1), ver_match.group(2), ver_match.group(3)
    is_minor_release = patch == "0"

    # 2. Parse CHANGELOG.md
    changelog_path = repo_root / "CHANGELOG.md"
    if not changelog_path.exists():
        print("ERROR: CHANGELOG.md not found", file=sys.stderr)
        return 1
    changelog_text = _read_file(changelog_path)

    date_str, raw_body = _find_changelog_section(changelog_text, version)

    if not raw_body:
        print(
            f"WARNING: No CHANGELOG section found for v{version}; "
            "writing minimal notes.",
            file=sys.stderr,
        )
        normalised_body = "_No changelog entries recorded for this release._"
        date_str = date_str if date_str != "unknown" else "date unknown"
    else:
        normalised_body = _normalise_section(raw_body)

    # 3. Determine paths
    minor_doc = repo_root / "docs" / "releases" / f"v{major}.{minor}.md"
    # Write release-notes-latest.md alongside the versioned minor doc rather than
    # in dist/ or build/ — docs/releases/ is never wiped by the release-build clean
    # (`rm -rf dist/ build/`), so this file is available when release-publish calls
    # `gh release create --notes-file`.
    notes_file = repo_root / "docs" / "releases" / "release-notes-latest.md"

    # 4. Build the section text that will appear in the minor doc
    section_text = f"## v{version} ({date_str})\n\n{normalised_body}"

    # 5. Write or append to docs/releases/vX.Y.md
    if is_minor_release:
        # Create new minor release file
        file_content = f"# v{major}.{minor} Release Notes\n\n{section_text}\n"
        _write_file(minor_doc, file_content)
        print(f"Wrote {minor_doc.relative_to(repo_root)}")
    else:
        # Prepend patch section after the title line (newest-first ordering)
        new_block = f"\n---\n\n{section_text}\n"
        if minor_doc.exists():
            existing = _read_file(minor_doc)
            # Skip if this version is already present (idempotent re-runs)
            if re.search(rf"^## v{re.escape(version)}\s", existing, re.MULTILINE):
                print(
                    f"NOTE: v{version} already present in {minor_doc.relative_to(repo_root)}; skipping prepend.",
                    file=sys.stderr,
                )
                # Still fall through to write docs/releases/release-notes-latest.md below
            else:
                # Insert after the first `# ` heading line so newest patches appear at top
                title_match = re.match(r"(# [^\n]+\n)", existing)
                if title_match:
                    title_line = title_match.group(1)
                    rest = existing[title_match.end() :]
                    _write_file(minor_doc, title_line + new_block + rest)
                else:
                    # No title line found — prepend at top
                    _write_file(minor_doc, new_block + existing)
        else:
            # Bootstrap a file if it doesn't exist yet
            bootstrap = (
                f"# v{major}.{minor} Release Notes\n"
                f"{new_block}"
                f"\n_Patch series starting at v{major}.{minor}.{patch}._\n"
            )
            _write_file(minor_doc, bootstrap)
            print(
                f"NOTE: {minor_doc.relative_to(repo_root)} did not exist; created it.",
                file=sys.stderr,
            )
        print(f"Updated {minor_doc.relative_to(repo_root)} (newest-first)")

    # 6. Always write docs/releases/release-notes-latest.md
    # docs/releases/ is never cleaned by the release-build `rm -rf dist/ build/`,
    # so this file survives the uv-build step and is available for `gh release create`.
    # It is intentionally NOT committed — it is a transient build artefact.
    _write_file(notes_file, section_text + "\n")
    print(f"Wrote {notes_file.relative_to(repo_root)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
