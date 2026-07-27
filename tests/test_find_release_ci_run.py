#!/usr/bin/env python3
"""
Tests for scripts/lib/find_release_ci_run.sh.

The script correlates a GitHub Actions workflow run with the exact commit
that should have triggered it, instead of blindly taking `gh run list
--limit=1` (which returns the most recently *created* run, not the one for
a specific push — see GitHub issue #946: v6.5.82's Homebrew update watched
the stale, already-green v6.5.81 run instead).

These tests exercise the real script against a fake `gh` binary placed
first on PATH. The fake `gh` implements just enough of `gh api
repos/<repo>/actions/workflows/<workflow>/runs?head_sha=<sha>` to be a
faithful stand-in: it honors the `head_sha` query parameter server-side
(returning only runs for that SHA, exactly like the real endpoint) and can
simulate GitHub Actions not having created the run yet via
FAKE_GH_READY_AFTER.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).parent.parent / "scripts" / "lib" / "find_release_ci_run.sh"
)

# Fake `gh` CLI. Reads its canned dataset from FAKE_GH_DATA_FILE (a JSON
# object mapping head_sha -> list of run objects), filters by the head_sha
# query parameter (mimicking the real API's server-side filter), and can
# withhold matches for the first FAKE_GH_READY_AFTER calls to simulate
# GitHub Actions not having materialised the run yet.
FAKE_GH_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" != "api" ]; then
    echo "fake gh: unsupported subcommand '${1:-}'" >&2
    exit 1
fi
URL="${2:-}"
SHA="$(printf '%s' "$URL" | sed -n 's/.*head_sha=\\([^&]*\\).*/\\1/p')"

COUNT=0
if [ -f "$FAKE_GH_CALL_COUNTER" ]; then
    COUNT="$(cat "$FAKE_GH_CALL_COUNTER")"
fi
echo $((COUNT + 1)) > "$FAKE_GH_CALL_COUNTER"

FAIL_UNTIL="${FAKE_GH_FAIL_UNTIL:-0}"
if [ "$COUNT" -lt "$FAIL_UNTIL" ]; then
    echo "fake gh: simulated auth failure (HTTP 401)" >&2
    exit 1
fi

READY_AFTER="${FAKE_GH_READY_AFTER:-0}"
if [ "$COUNT" -lt "$READY_AFTER" ]; then
    echo '{"workflow_runs": []}'
    exit 0
fi

python3 - "$FAKE_GH_DATA_FILE" "$SHA" <<'PYEOF'
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)
runs = data.get(sys.argv[2], [])
print(json.dumps({"workflow_runs": runs}))
PYEOF
"""


class TestFindReleaseCIRun(unittest.TestCase):
    """Exercise find_release_ci_run.sh against a fake `gh` on PATH."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

        self.bin_dir = self.tmp_path / "bin"
        self.bin_dir.mkdir()
        fake_gh = self.bin_dir / "gh"
        fake_gh.write_text(FAKE_GH_SCRIPT)
        fake_gh.chmod(0o755)

        self.data_file = self.tmp_path / "gh_data.json"
        self.counter_file = self.tmp_path / "gh_call_count"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, sha, data, timeout=5, interval=1, ready_after=0):
        """Run the real script against the fake gh with the given dataset."""
        self.data_file.write_text(json.dumps(data))
        if self.counter_file.exists():
            self.counter_file.unlink()

        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}"
        env["FAKE_GH_DATA_FILE"] = str(self.data_file)
        env["FAKE_GH_CALL_COUNTER"] = str(self.counter_file)
        env["FAKE_GH_READY_AFTER"] = str(ready_after)

        return subprocess.run(
            [
                "bash",
                str(SCRIPT_PATH),
                "--repo",
                "bobmatnyc/claude-mpm",
                "--workflow",
                "release-wheels.yml",
                "--sha",
                sha,
                "--timeout",
                str(timeout),
                "--interval",
                str(interval),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
        )

    def _call_count(self):
        return int(self.counter_file.read_text().strip())

    def test_selects_run_matching_head_sha_ignoring_unrelated_newer_run(self):
        """A run for the requested SHA is chosen even though a newer,
        unrelated run (a different commit's CI run) also exists.
        """
        data = {
            "matching-sha": [
                {
                    "id": 111,
                    "head_sha": "matching-sha",
                    "created_at": "2026-07-26T10:00:00Z",
                }
            ],
            "unrelated-sha": [
                {
                    "id": 999,
                    "head_sha": "unrelated-sha",
                    "created_at": "2026-07-26T12:00:00Z",
                }
            ],
        }

        result = self._run("matching-sha", data)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "111")

    def test_picks_most_recently_created_when_multiple_runs_match_same_sha(self):
        """When more than one run matches the SHA (e.g. a manual re-run),
        the most recently created one is selected, per the script's
        defensive sort_by(.created_at) | reverse | .[0].
        """
        data = {
            "matching-sha": [
                {
                    "id": 100,
                    "head_sha": "matching-sha",
                    "created_at": "2026-07-26T09:00:00Z",
                },
                {
                    "id": 200,
                    "head_sha": "matching-sha",
                    "created_at": "2026-07-26T11:00:00Z",
                },
            ]
        }

        result = self._run("matching-sha", data)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "200")

    def test_polls_until_run_appears(self):
        """GitHub Actions may not have created the run yet right after the
        push; the script must keep polling (not give up on the first empty
        response) until a matching run shows up.
        """
        data = {
            "matching-sha": [
                {
                    "id": 42,
                    "head_sha": "matching-sha",
                    "created_at": "2026-07-26T10:00:00Z",
                }
            ]
        }

        result = self._run("matching-sha", data, timeout=5, interval=1, ready_after=2)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "42")
        # Confirm it actually retried rather than matching by luck on the
        # first call.
        self.assertGreaterEqual(self._call_count(), 3)

    def test_fails_loudly_when_no_matching_run_within_timeout(self):
        """If no run ever matches the requested SHA before the timeout, the
        script must abort with a non-zero exit and an explanatory stderr
        message — never silently report success for the wrong run.
        """
        data = {
            "other-sha": [
                {
                    "id": 1,
                    "head_sha": "other-sha",
                    "created_at": "2026-07-26T10:00:00Z",
                }
            ]
        }

        result = self._run("never-appears-sha", data, timeout=2, interval=1)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        self.assertIn("no run of workflow", result.stderr)
        self.assertIn("release-wheels.yml", result.stderr)
        self.assertIn("never-appears-sha", result.stderr)

    def test_missing_required_argument_exits_with_usage(self):
        """Missing --sha (or any required arg) should fail fast with usage,
        not attempt to poll the GitHub API at all.
        """
        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}"

        result = subprocess.run(
            [
                "bash",
                str(SCRIPT_PATH),
                "--repo",
                "bobmatnyc/claude-mpm",
                "--workflow",
                "release-wheels.yml",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
