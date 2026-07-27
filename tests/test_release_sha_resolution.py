#!/usr/bin/env python3
"""
Tests for the release-tag -> commit-SHA resolution used by the
`update-homebrew-tap` Makefile target.

Background (security/correctness followup to #946 / PR #951):
`git rev-parse "$TAG"` on an *annotated* tag (created via `git tag -a` or
`git tag -s` — the norm for release workflows) returns the tag OBJECT's
SHA, not the SHA of the commit it points to. The GitHub Actions API filters
workflow runs by `head_sha` (a commit SHA), so passing the tag-object SHA
to scripts/lib/find_release_ci_run.sh would never match any run, and every
annotated-tag release would poll until it timed out.

The fix dereferences the tag with `TAG^{}` first (which peels an annotated
tag down to its commit and is a harmless no-op for lightweight tags, whose
`rev-parse` output already equals `rev-parse TAG^{}`), and only falls back
to a bare `git rev-parse "$TAG"` if that somehow fails — never silently
substituting HEAD, which could refer to an unrelated commit.

These tests exercise the same resolution logic against real temporary git
repositories (asserting the underlying git behaviour that the fix depends
on) and statically check that the Makefile still contains the corrected
pattern, so a future edit can't silently reintroduce the bug.
"""

import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MAKEFILE_PATH = REPO_ROOT / "Makefile"


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


class TestAnnotatedTagShaResolution(unittest.TestCase):
    """Verify the git behaviour the update-homebrew-tap fix relies on."""

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "test@example.com")
        _git(self.repo, "config", "user.name", "Test")
        (self.repo / "a.txt").write_text("a\n")
        _git(self.repo, "add", "a.txt")
        _git(self.repo, "commit", "-q", "-m", "initial")
        self.commit_sha = _git(self.repo, "rev-parse", "HEAD")

    def tearDown(self):
        self._tmp.cleanup()

    def test_annotated_tag_rev_parse_differs_from_commit_sha(self):
        """`git rev-parse TAG` on an annotated tag returns the tag OBJECT
        SHA, not the commit SHA — this is the root cause of the bug.
        """
        _git(self.repo, "tag", "-a", "release-tag", "-m", "release")
        tag_object_sha = _git(self.repo, "rev-parse", "release-tag")

        self.assertNotEqual(
            tag_object_sha,
            self.commit_sha,
            "annotated tag's rev-parse unexpectedly matched the commit SHA "
            "directly — test fixture no longer exercises the bug",
        )

    def test_dereferenced_annotated_tag_matches_commit_sha(self):
        """`git rev-parse TAG^{}` peels the annotated tag to the commit it
        points to — this is what the Makefile fix now does first.
        """
        _git(self.repo, "tag", "-a", "release-tag", "-m", "release")
        dereferenced_sha = _git(self.repo, "rev-parse", "release-tag^{}")

        self.assertEqual(dereferenced_sha, self.commit_sha)

    def test_dereferenced_lightweight_tag_matches_commit_sha(self):
        """`TAG^{}` is a safe no-op for lightweight tags: it resolves
        identically to a bare `rev-parse TAG`.
        """
        _git(self.repo, "tag", "lightweight-tag")

        bare_sha = _git(self.repo, "rev-parse", "lightweight-tag")
        dereferenced_sha = _git(self.repo, "rev-parse", "lightweight-tag^{}")

        self.assertEqual(bare_sha, self.commit_sha)
        self.assertEqual(dereferenced_sha, self.commit_sha)

    def test_makefile_shell_snippet_resolves_annotated_tag_correctly(self):
        """Run the actual shell resolution line used by update-homebrew-tap
        (TAG^{} first, then bare TAG, no silent HEAD fallback) against a
        repo with an annotated tag, and confirm it yields the commit SHA.
        """
        _git(self.repo, "tag", "-a", "release-tag", "-m", "release")

        snippet = (
            'TAG="release-tag"; '
            'SHA=$(git rev-parse "$TAG^{}" 2>/dev/null '
            '|| git rev-parse "$TAG" 2>/dev/null) || exit 1; '
            'echo "$SHA"'
        )
        result = subprocess.run(
            ["bash", "-c", snippet],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), self.commit_sha)

    def test_makefile_shell_snippet_fails_loudly_when_tag_is_missing(self):
        """If the tag cannot be resolved at all, the snippet must exit
        non-zero instead of silently substituting HEAD.
        """
        snippet = (
            'TAG="nonexistent-tag"; '
            'SHA=$(git rev-parse "$TAG^{}" 2>/dev/null '
            '|| git rev-parse "$TAG" 2>/dev/null) || exit 1; '
            'echo "$SHA"'
        )
        result = subprocess.run(
            ["bash", "-c", snippet],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


class TestMakefileUsesCorrectedShaResolutionPattern(unittest.TestCase):
    """Guard against silently regressing the fix in the Makefile itself."""

    def setUp(self):
        self.makefile_text = MAKEFILE_PATH.read_text()

    def test_update_homebrew_tap_dereferences_tag_before_rev_parse(self):
        match = re.search(
            r"update-homebrew-tap:.*?(?=\n[a-zA-Z0-9_.-]+:\s*(?:##|\n|$))",
            self.makefile_text,
            re.DOTALL,
        )
        self.assertIsNotNone(
            match, "could not locate update-homebrew-tap target in Makefile"
        )
        target_body = match.group(0)

        self.assertIn(
            'git rev-parse "$$TAG^{}"',
            target_body,
            "update-homebrew-tap must dereference annotated tags with "
            "TAG^{} before resolving the commit SHA (see #946 / PR #951)",
        )

    def test_update_homebrew_tap_does_not_silently_fall_back_to_head(self):
        match = re.search(
            r"update-homebrew-tap:.*?(?=\n[a-zA-Z0-9_.-]+:\s*(?:##|\n|$))",
            self.makefile_text,
            re.DOTALL,
        )
        self.assertIsNotNone(
            match, "could not locate update-homebrew-tap target in Makefile"
        )
        target_body = match.group(0)

        self.assertNotIn(
            'git rev-parse "$$TAG" 2>/dev/null || git rev-parse HEAD',
            target_body,
            "SHA resolution must not silently fall back to HEAD when the "
            "tag cannot be resolved — it should fail loudly instead",
        )


if __name__ == "__main__":
    unittest.main()
