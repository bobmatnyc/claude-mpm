#!/usr/bin/env python3
"""
Tests for the release-tag -> commit-SHA resolution used by the
`update-homebrew-tap` Makefile target.

Background (security/correctness followups to #946 / PR #951):

1. `git rev-parse "$TAG"` on an *annotated* tag (created via `git tag -a` or
   `git tag -s` — the norm for release workflows) returns the tag OBJECT's
   SHA, not the SHA of the commit it points to. The GitHub Actions API
   filters workflow runs by `head_sha` (a commit SHA), so passing the
   tag-object SHA to scripts/lib/find_release_ci_run.sh would never match
   any run, and every annotated-tag release would poll until it timed out.
   Fixed by dereferencing with `TAG^{}` before falling back to a bare
   `git rev-parse "$TAG"`.

2. A later adversarial review of PR #951 flagged that `SHA=$(...) || { ...
   exit 1; }` relies on the exit status of a bare shell assignment
   propagating the command substitution's failure — a pattern considered
   fragile/non-obvious across shells, so the target was changed to resolve
   SHA first and then explicitly check `if [ -z "$SHA" ]; then ... exit 1;
   fi`.

3. Investigating (2) surfaced a THIRD, more consequential bug that a naive
   application of fix (2) would have introduced: `git rev-parse` (without
   `--verify`) does not just fail on an unresolvable ref — it also echoes
   the literal ref text back on STDOUT as part of its "ambiguous argument:
   could be a revision or a path" disambiguation hint, even though it
   exits non-zero. That means `SHA=$(git rev-parse "$TAG^{}" 2>/dev/null
   || git rev-parse "$TAG" 2>/dev/null)` for a missing tag does NOT
   produce an empty string — it produces garbage like `"my-tag^{}\nmy-tag"`.
   An `if [ -z "$SHA" ]` check alone would never trigger, and the target
   would silently proceed to poll find_release_ci_run.sh with a bogus
   `--sha` value for the full 180s timeout instead of failing fast with a
   clear message — i.e. fix (2), applied literally without also switching
   to `git rev-parse --verify`, would have been WORSE than the
   exit-status check it replaced (which, empirically, already propagated
   the failure correctly in bash). `git rev-parse --verify` suppresses
   that stdout disambiguation dance (it only ever prints the resolved SHA
   on success), so the Makefile now uses `--verify` on both the
   dereferencing attempt and the fallback, which makes the explicit `-z`
   check actually correct.

These tests exercise the *actual* SHA-resolution recipe text extracted
verbatim from the Makefile (not a hand-retyped analog) against real
temporary git repositories, so a future edit that silently drops
`--verify` or the `-z` check is caught by running the real snippet, not by
a static string match that could drift from what the Makefile actually
does.
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


def _extract_sha_resolution_snippet():
    r"""Pull the real `SHA=... ; if [ -z "$SHA" ]; then ... fi` block out of
    the `update-homebrew-tap` target, verbatim, and convert it from
    Makefile syntax (`$$`, trailing `\` line continuations, `$(RED)` etc.
    Make variable references) into a plain, directly-runnable bash
    snippet.

    Returns the snippet text; callers are expected to prepend a `TAG=...`
    assignment and run the whole thing with `bash -c`.
    """
    lines = MAKEFILE_PATH.read_text().splitlines()

    start = None
    end = None
    for i, line in enumerate(lines):
        if start is None and "SHA=$$(git rev-parse" in line:
            start = i
            continue
        if start is not None and line.strip() == "fi; \\":
            end = i
            break

    assert start is not None and end is not None, (
        'could not locate the SHA=...; if [ -z "$$SHA" ]; then ... fi '
        "block in update-homebrew-tap — the Makefile recipe shape changed; "
        "update this extractor to match"
    )

    block_lines = lines[start : end + 1]
    processed = []
    for line in block_lines:
        text = line.strip()
        if text.endswith("\\"):
            text = text[:-1].rstrip()
        text = text.replace("$$", "$")
        # Make variable references like $(RED)/$(NC) are substituted by
        # `make` itself before the shell ever sees this line; outside of
        # `make` they'd be parsed as (nonexistent) command substitutions,
        # so strip them for standalone execution. The behavior under test
        # (exit status / whether SHA resolves) does not depend on color
        # codes.
        text = re.sub(r"\$\([A-Z_]+\)", "", text)
        processed.append(text)

    return "\n".join(processed)


def _run_sha_resolution(repo, tag):
    """Run the real, verbatim-extracted SHA-resolution snippet from the
    Makefile against `repo` with the given TAG, returning the completed
    process (stdout carries `SHA_RESULT=<value>` on the success path).
    """
    snippet = _extract_sha_resolution_snippet()
    script = f'TAG="{tag}"\n{snippet}\necho "SHA_RESULT=$SHA"\n'
    return subprocess.run(
        ["bash", "-c", script],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


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
        SHA, not the commit SHA — this is the root cause of bug #1.
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
        points to — this is what the Makefile fix does first.
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

    def test_missing_ref_rev_parse_leaks_ref_text_onto_stdout(self):
        """Document the git quirk that motivates `--verify`: a bare
        `git rev-parse` on an unresolvable ref does not just fail with a
        non-zero exit — it also prints the literal ref argument back on
        STDOUT (its "ambiguous argument: could be a revision or a path"
        disambiguation hint), even with stderr redirected away. Any code
        that captures this into a variable and only checks `[ -z "$VAR" ]`
        will treat that leaked text as a resolved value.
        """
        result = subprocess.run(
            ["git", "rev-parse", "totally-bogus-ref^{}"],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("totally-bogus-ref", result.stdout)

    def test_missing_ref_rev_parse_verify_produces_empty_stdout(self):
        """`git rev-parse --verify` on the same unresolvable ref exits
        non-zero WITHOUT leaking anything onto stdout — this is why the
        Makefile fix uses `--verify` rather than bare `rev-parse`.
        """
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "totally-bogus-ref^{}"],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_makefile_snippet_resolves_annotated_tag_correctly(self):
        """Run the real, verbatim-extracted Makefile SHA-resolution block
        against a repo with an annotated tag and confirm it yields the
        commit SHA and reaches the success path (no abort).
        """
        _git(self.repo, "tag", "-a", "release-tag", "-m", "release")

        result = _run_sha_resolution(self.repo, "release-tag")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(f"SHA_RESULT={self.commit_sha}", result.stdout)

    def test_makefile_snippet_resolves_lightweight_tag_correctly(self):
        """Same as above, for a lightweight tag (no dereferencing needed,
        but `TAG^{}` must remain a harmless no-op).
        """
        _git(self.repo, "tag", "lightweight-tag")

        result = _run_sha_resolution(self.repo, "lightweight-tag")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(f"SHA_RESULT={self.commit_sha}", result.stdout)

    def test_makefile_snippet_fails_loudly_when_tag_is_missing(self):
        """If the tag cannot be resolved at all, the real Makefile
        SHA-resolution block must abort (non-zero exit) before ever
        reaching the success-path echo — never silently proceed with a
        bogus SHA value.
        """
        result = _run_sha_resolution(self.repo, "nonexistent-tag")

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("SHA_RESULT=", result.stdout)

    def test_bare_rev_parse_without_verify_would_defeat_the_z_check(self):
        """Regression guard for the bug this fix surfaced: if a future
        edit "simplifies" the Makefile by dropping `--verify` (keeping
        only the `if [ -z "$SHA" ]` check), the target would silently
        proceed with a garbage SHA instead of aborting. This runs that
        exact (deliberately broken) variant to prove it is broken, so the
        Makefile must keep `--verify` — see
        test_makefile_snippet_fails_loudly_when_tag_is_missing above for
        the correct, currently-shipped behaviour.
        """
        broken_snippet = (
            'SHA=$(git rev-parse "$TAG^{}" 2>/dev/null '
            '|| git rev-parse "$TAG" 2>/dev/null)\n'
            'if [ -z "$SHA" ]; then\n'
            "    exit 1\n"
            "fi\n"
            'echo "SHA_RESULT=$SHA"\n'
        )
        script = f'TAG="nonexistent-tag"\n{broken_snippet}'

        result = subprocess.run(
            ["bash", "-c", script],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )

        # This documents the broken behaviour: it does NOT abort, and it
        # DOES reach the success-path echo with a garbage, non-SHA value.
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("SHA_RESULT=", result.stdout)
        self.assertNotIn(f"SHA_RESULT={self.commit_sha}", result.stdout)


class TestMakefileUsesCorrectedShaResolutionPattern(unittest.TestCase):
    """Guard against silently regressing either fix in the Makefile itself."""

    def setUp(self):
        self.makefile_text = MAKEFILE_PATH.read_text()

    def _target_body(self):
        match = re.search(
            r"update-homebrew-tap:.*?(?=\n[a-zA-Z0-9_.-]+:\s*(?:##|\n|$))",
            self.makefile_text,
            re.DOTALL,
        )
        self.assertIsNotNone(
            match, "could not locate update-homebrew-tap target in Makefile"
        )
        return match.group(0)

    def test_update_homebrew_tap_dereferences_tag_before_rev_parse(self):
        target_body = self._target_body()

        self.assertIn(
            'git rev-parse --verify "$$TAG^{}"',
            target_body,
            "update-homebrew-tap must dereference annotated tags with "
            "TAG^{} before resolving the commit SHA (see #946 / PR #951)",
        )

    def test_update_homebrew_tap_uses_verify_on_both_resolution_attempts(self):
        target_body = self._target_body()

        self.assertEqual(
            target_body.count("git rev-parse --verify"),
            2,
            "both the dereferencing attempt and the bare-tag fallback must "
            "use `git rev-parse --verify` — without it, an unresolvable "
            "ref leaks its literal text onto stdout instead of producing "
            'an empty string, which defeats the `-z "$$SHA"` check '
            "below (see test_bare_rev_parse_without_verify_would_defeat_"
            "the_z_check)",
        )

    def test_update_homebrew_tap_checks_sha_emptiness_explicitly(self):
        target_body = self._target_body()

        self.assertIn(
            'if [ -z "$$SHA" ]; then',
            target_body,
            "SHA resolution must explicitly check for an empty result "
            "after the assignment rather than relying solely on the "
            "assignment statement's own exit status",
        )

    def test_update_homebrew_tap_does_not_silently_fall_back_to_head(self):
        target_body = self._target_body()

        self.assertNotIn(
            'git rev-parse "$$TAG" 2>/dev/null || git rev-parse HEAD',
            target_body,
            "SHA resolution must not silently fall back to HEAD when the "
            "tag cannot be resolved — it should fail loudly instead",
        )


if __name__ == "__main__":
    unittest.main()
