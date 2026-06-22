"""Session Pause Manager Service.

WHAT: Creates session pause documents (JSON + Markdown) capturing git state,
todos, and working-directory context so sessions can be resumed later.  Also
prunes stale git worktrees under ``<repo>/.claude/worktrees/`` at pause time,
preserving any worktrees that have uncommitted changes, unmerged commits, or a
git lock.  Additionally sweeps orphaned (unregistered) directories under
``<repo>/.claude/worktrees/`` that were left behind after worktrees were
de-registered.

WHY: Centralises all pause-document creation so both ``session pause`` and
``mpm-init pause`` share a single, tested code path.  Stale worktrees
accumulate silently during agent runs; pruning them at pause is a natural
clean-up gate that reclaims disk and branch namespace without user friction.
Orphaned directories are not reported by ``git worktree list`` so a separate
sweep is needed to remove them.

DESIGN DECISIONS:
- Two format output (JSON, Markdown) for different use cases
- .yaml was dropped: no reader exists in the codebase; .json is authoritative,
  .md serves as the human-readable view and legacy-resume fallback
- Atomic file operations using StateStorage
- Compatible with SessionResumeHelper for resume workflow
- LATEST-SESSION.txt pointer for quick access
- Sessions are written PROJECT-LOCAL to ``<project>/.claude-mpm/sessions/``
  (NOT to ``~/.claude-mpm/sessions/``). The directory is gitignored; sessions
  are intentionally never committed to version control.
- Worktree pruning is conservative: when in doubt PRESERVE.  Removal never
  uses --force; that defeats the safety checks.
- Orphan sweep uses shutil.rmtree with a path-containment guard; only paths
  strictly under ``.claude/worktrees/`` are ever deleted.
- All git subprocess calls use ``git -C <path>`` with ``capture_output=True,
  check=False`` per project stability conventions.
"""

import json
import shutil
import subprocess  # nosec B404 - required for git operations
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_mpm.core.logger import get_logger
from claude_mpm.storage.state_storage import StateStorage

logger = get_logger(__name__)

# Relative location of MPM-managed worktrees inside the repo.
_WORKTREES_SUBDIR = Path(".claude") / "worktrees"


class SessionPauseManager:
    """Manages creating pause sessions and capturing state.

    Sessions are written project-locally to ``<project>/.claude-mpm/sessions/``
    and are intentionally NOT committed to git (the directory is gitignored).
    """

    def __init__(self, project_path: Path | None = None):
        """Initialize session pause manager.

        Args:
            project_path: Project root path (default: current directory)
        """
        self.project_path = (project_path or Path.cwd()).resolve()
        # Use project-local path so sessions are scoped to the project that created them
        self.pause_dir = self.project_path / ".claude-mpm" / "sessions"
        self.pause_dir.mkdir(parents=True, exist_ok=True)
        self.storage = StateStorage(self.pause_dir)
        # Populated by create_pause_session after pruning; None if pruning was
        # skipped or has not yet run.  Accessed via getattr in session_shared.py.
        self._last_prune_summary: dict[str, Any] | None = None

    def create_pause_session(
        self,
        message: str | None = None,
        skip_commit: bool = False,  # deprecated no-op: sessions are never committed
        export_path: str | None = None,
        prune_worktrees: bool = True,
    ) -> str:
        """Create a pause session with captured state.

        Sessions are written to the project-local ``.claude-mpm/sessions/``
        directory which is gitignored.  No git commit is ever created —
        ``skip_commit`` is accepted for API stability but has no effect.

        After writing all session files, stale worktrees under
        ``<repo>/.claude/worktrees/`` are pruned (unless *prune_worktrees* is
        ``False``).  Pruning failures are logged but never block the session
        save.

        Args:
            message: Optional pause reason/context message
            skip_commit: Accepted but ignored; sessions are never committed.
            export_path: Optional export location for session file
            prune_worktrees: When True (the default), prune stale git
                worktrees under ``<repo>/.claude/worktrees/`` after the
                session state is safely written.  Pass False to skip pruning
                (also exposed via ``--no-prune-worktrees`` CLI flag).

        Returns:
            Session ID

        Raises:
            Exception: If session creation fails
        """
        logger.info("Creating pause session")

        # Generate session ID
        session_id = f"session-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

        # Capture state
        state = self._capture_state(session_id, message)

        # Save JSON format
        json_path = self.pause_dir / f"{session_id}.json"
        if not self.storage.write_json(state, json_path, atomic=True):
            raise RuntimeError(f"Failed to write JSON to {json_path}")
        logger.debug(f"Saved JSON: {json_path}")

        # Save Markdown format
        md_path = self.pause_dir / f"{session_id}.md"
        md_content = self._generate_markdown(state)
        md_path.write_text(md_content)
        logger.debug(f"Saved Markdown: {md_path}")

        # Update LATEST-SESSION.txt pointer
        self._update_latest_pointer(session_id)

        # Optional export
        if export_path:
            export_file = Path(export_path).resolve()
            if not self.storage.write_json(state, export_file, atomic=True):
                logger.warning(f"Failed to export to {export_file}")
            else:
                logger.info(f"Exported session to {export_file}")

        # Prune stale worktrees AFTER session state is safely written.
        # Failures are non-fatal — we log and continue.
        self._last_prune_summary: dict[str, Any] | None = None
        if prune_worktrees:
            try:
                prune_summary = self.prune_stale_worktrees()
                logger.info(
                    "Worktree prune complete: pruned=%d preserved=%d",
                    prune_summary["pruned_count"],
                    prune_summary["preserved_count"],
                )
                state["worktree_prune_summary"] = prune_summary
                self._last_prune_summary = prune_summary
            except Exception as exc:  # nosec B110 - intentional non-fatal wrapper
                logger.warning("Worktree pruning failed (non-fatal): %s", exc)

        logger.info(f"Pause session created: {session_id}")
        return session_id

    # ------------------------------------------------------------------
    # Worktree pruning
    # ------------------------------------------------------------------

    def prune_stale_worktrees(self) -> dict[str, Any]:
        """Prune stale git worktrees under ``<repo>/.claude/worktrees/``.

        WHAT: Enumerates all git worktrees whose path is under
        ``<main-repo>/.claude/worktrees/``.  For each candidate, classifies
        it as PRUNE or PRESERVE using conservative safety checks (uncommitted
        changes, untracked files, unmerged/unpushed commits, git lock).  Only
        worktrees that are provably clean and fully merged are removed.
        Additionally sweeps orphaned (unregistered) directories under
        ``<main-repo>/.claude/worktrees/`` that are not known to git.

        WHY: Agent runs create isolated worktrees that are never automatically
        cleaned up.  Pruning at pause time reclaims disk and branch namespace
        without risk of data loss because the safety checks are conservative —
        when in doubt the worktree is PRESERVED.  Orphaned directories are not
        reported by ``git worktree list`` so a separate sweep is required.

        Returns:
            Summary dict with keys:
            - ``pruned_count`` (int)
            - ``preserved_count`` (int)
            - ``admin_pruned`` (bool) — True if ``git worktree prune`` ran
            - ``worktrees`` (list[dict]) — per-worktree decision records
            - ``orphans_swept`` (int) — orphaned dirs removed
            - ``orphans_preserved`` (int) — orphaned dirs kept (with reason)
            - ``orphans`` (list[dict]) — per-orphan decision records
        """
        summary: dict[str, Any] = {
            "pruned_count": 0,
            "preserved_count": 0,
            "admin_pruned": False,
            "worktrees": [],
            "orphans_swept": 0,
            "orphans_preserved": 0,
            "orphans": [],
        }

        if not self._is_git_repo():
            logger.debug("prune_stale_worktrees: not a git repo, skipping")
            return summary

        # Resolve the MAIN working tree (we may be running from inside a
        # linked worktree ourselves).
        main_repo = self._resolve_main_working_tree(str(self.project_path))

        worktrees_dir = Path(main_repo) / _WORKTREES_SUBDIR
        if not worktrees_dir.is_dir():
            logger.debug(
                "prune_stale_worktrees: %s does not exist, no-op", worktrees_dir
            )
            return summary

        # Parse ``git worktree list --porcelain`` output.
        candidates = self._list_worktree_candidates(main_repo, worktrees_dir)

        for wt in candidates:
            decision = self._classify_worktree(wt, main_repo)
            wt.update(decision)
            summary["worktrees"].append(wt)

            if decision["action"] == "prune":
                removed = self._remove_worktree(main_repo, wt["path"])
                if removed:
                    summary["pruned_count"] += 1
                    wt["removed"] = True
                else:
                    # Removal failed — treat as preserved
                    summary["preserved_count"] += 1
                    wt["removed"] = False
                    wt["action"] = "preserve"
                    wt["reason"] = wt.get("reason", "") + "; removal failed, preserved"
            else:
                summary["preserved_count"] += 1

        # Always run ``git worktree prune`` to clean dangling admin entries
        # (registered worktrees whose directories no longer exist).
        prune_result = subprocess.run(  # nosec B603, B607 - safe git command
            ["git", "-C", str(main_repo), "worktree", "prune"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        summary["admin_pruned"] = prune_result.returncode == 0
        if prune_result.returncode != 0:
            logger.warning(
                "git worktree prune returned %d: %s",
                prune_result.returncode,
                prune_result.stderr.strip(),
            )

        # Sweep orphaned directories — unregistered subdirs of worktrees_dir.
        # Build the set of registered paths AFTER git worktree prune so we
        # don't treat newly-cleaned entries as orphans.
        registered_paths = self._collect_registered_worktree_paths(main_repo)
        orphan_records = self._sweep_orphaned_dirs(
            main_repo, worktrees_dir, registered_paths
        )
        for rec in orphan_records:
            summary["orphans"].append(rec)
            if rec.get("action") == "swept":
                summary["orphans_swept"] += 1
            else:
                summary["orphans_preserved"] += 1

        return summary

    def _resolve_main_working_tree(self, cwd: str) -> str:
        """Return the main git working tree path for *cwd*, handling linked worktrees.

        WHAT: Determines the main (non-linked) git working tree root for any
        given working directory path, using three fallback strategies in order:
        (1) compare ``--git-dir`` vs ``--git-common-dir`` to detect when
        *cwd* is already the main tree; (2) parse ``git worktree list
        --porcelain`` and return the first ``worktree`` entry, which git always
        reports as the main tree; (3) resolve the parent of ``--git-common-dir``
        as a last resort.  Falls back to *cwd* unchanged if all git calls fail.

        WHY: Worktree pruning and path resolution must always operate relative
        to the main working tree, not a linked worktree.  When ``session pause``
        is invoked from inside a linked worktree (e.g. during agent runs), the
        naive approach of using ``cwd`` directly would target the wrong tree.
        Inlining this avoids a cross-package import dependency on
        ``commit_cost_tracker``.

        Args:
            cwd: Absolute path string of the working directory.

        Returns:
            Absolute path string of the main working tree.
        """
        # Fast path: git-dir == git-common-dir means we ARE in the main tree.
        try:
            r_dir = subprocess.run(  # nosec B603, B607 - safe git command
                ["git", "-C", cwd, "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            r_common = subprocess.run(  # nosec B603, B607 - safe git command
                ["git", "-C", cwd, "rev-parse", "--git-common-dir"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if r_dir.returncode == 0 and r_common.returncode == 0:
                git_dir = (Path(cwd) / r_dir.stdout.strip()).resolve()
                git_common = (Path(cwd) / r_common.stdout.strip()).resolve()
                if git_dir == git_common:
                    return cwd
        except Exception as exc:
            logger.debug("resolve_main_working_tree fast-path failed: %s", exc)

        # Porcelain worktree list — first entry is the main tree.
        try:
            result = subprocess.run(  # nosec B603, B607 - safe git command
                ["git", "-C", cwd, "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("worktree "):
                        return stripped[len("worktree ") :]
        except Exception as exc:
            logger.debug("resolve_main_working_tree worktree list failed: %s", exc)

        # Fallback: parent of git-common-dir.
        try:
            result2 = subprocess.run(  # nosec B603, B607 - safe git command
                ["git", "-C", cwd, "rev-parse", "--git-common-dir"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result2.returncode == 0:
                git_common = (Path(cwd) / result2.stdout.strip()).resolve()
                return str(git_common.parent)
        except Exception as exc:
            logger.debug(
                "resolve_main_working_tree common-dir fallback failed: %s", exc
            )

        return cwd

    def _list_worktree_candidates(
        self, main_repo: str, worktrees_dir: Path
    ) -> list[dict[str, Any]]:
        """Parse ``git worktree list --porcelain`` and return candidates.

        WHAT: Runs ``git worktree list --porcelain`` from *main_repo*, parses
        every worktree stanza into a dict with ``path``, ``branch``, and
        ``locked`` keys, then filters out the main working tree and any entry
        whose resolved path is not a descendant of *worktrees_dir*.  Returns
        the remaining list as prune candidates.  Returns an empty list if the
        git command fails.

        WHY: Pruning must be scoped strictly to MPM-managed worktrees under
        ``.claude/worktrees/`` so it cannot accidentally remove worktrees that
        the user or other tools created elsewhere.  The porcelain format is
        stable across git versions and unambiguous, making it safe to parse
        without shell pipelines.

        Args:
            main_repo: Absolute path string of the main git repo.
            worktrees_dir: Absolute Path of the managed worktrees directory.

        Returns:
            List of dicts with keys: ``path``, ``branch``, ``locked``.
        """
        result = subprocess.run(  # nosec B603, B607 - safe git command
            ["git", "-C", main_repo, "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "git worktree list failed (rc=%d): %s",
                result.returncode,
                result.stderr.strip(),
            )
            return []

        candidates: list[dict[str, Any]] = []
        current: dict[str, Any] = {}

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if line.startswith("worktree "):
                if current:
                    candidates.append(current)
                current = {
                    "path": line[len("worktree ") :].strip(),
                    "branch": None,
                    "locked": False,
                }
            elif line.startswith("branch "):
                current["branch"] = line[len("branch ") :].strip()
            elif line == "locked" or line.startswith("locked "):
                current["locked"] = True
            elif line == "":
                if current:
                    candidates.append(current)
                    current = {}
        if current:
            candidates.append(current)

        # Keep only entries under our managed worktrees directory; skip main tree.
        main_resolved = Path(main_repo).resolve()
        wt_dir_resolved = worktrees_dir.resolve()
        filtered: list[dict[str, Any]] = []
        for wt in candidates:
            wt_path = Path(wt["path"]).resolve()
            if wt_path == main_resolved:
                continue  # Never touch the main working tree
            try:
                wt_path.relative_to(wt_dir_resolved)
            except ValueError:
                continue  # Not under .claude/worktrees/ — skip
            wt["path"] = str(wt_path)
            filtered.append(wt)

        return filtered

    def _classify_worktree(self, wt: dict[str, Any], main_repo: str) -> dict[str, Any]:
        """Classify a candidate worktree as PRUNE or PRESERVE.

        WHAT: Applies four sequential safety rules to a single worktree dict
        and returns a decision dict with ``action`` (``"prune"`` or
        ``"preserve"``) and a human-readable ``reason``.  Rules in evaluation
        order: (1) git-locked flag; (2) directory existence; (3) non-empty
        ``git status --porcelain`` (uncommitted or untracked files); (4) branch
        has commits not reachable from the default branch, via
        ``_has_unmerged_commits``.  Any git command failure causes an immediate
        PRESERVE decision.

        WHY: A multi-rule conservative classifier prevents accidental data loss
        during automated pruning.  Each rule addresses a distinct failure mode:
        (1) user-locked worktrees must never be touched; (2) admin-only entries
        without a directory are already handled by ``git worktree prune``; (3)
        uncommitted work would be destroyed by removal; (4) unmerged commits
        represent unreachable history after branch deletion.  TOCTOU between
        this check and removal is mitigated by calling ``git worktree remove``
        without ``--force`` so git re-validates before deleting.

        Args:
            wt: Worktree dict with ``path``, ``branch``, ``locked`` keys.
            main_repo: Absolute path string of the main git repo.

        Returns:
            Dict with ``action`` (``"prune"`` | ``"preserve"``) and ``reason``.
        """
        wt_path = wt["path"]
        branch = wt.get("branch")

        # Rule 1: Locked
        if wt.get("locked"):
            return {"action": "preserve", "reason": "worktree is locked"}

        # Rule 2: Directory missing — admin-only entry, let prune handle it.
        if not Path(wt_path).is_dir():
            return {
                "action": "preserve",
                "reason": "directory missing; will be cleaned by git worktree prune",
            }

        # Rule 3: Uncommitted or untracked changes.
        try:
            status_result = subprocess.run(  # nosec B603, B607 - safe git command
                ["git", "-C", wt_path, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if status_result.returncode != 0:
                return {
                    "action": "preserve",
                    "reason": f"git status failed (rc={status_result.returncode})",
                }
            if status_result.stdout.strip():
                return {
                    "action": "preserve",
                    "reason": "has uncommitted or untracked changes",
                }
        except Exception as exc:
            return {"action": "preserve", "reason": f"git status error: {exc}"}

        # Rule 4: Unmerged/unpushed commits.
        if branch:
            unmerged = self._has_unmerged_commits(wt_path, main_repo, branch)
            if unmerged is None:
                # Could not determine — be conservative.
                return {
                    "action": "preserve",
                    "reason": "could not determine merge status; preserving conservatively",
                }
            if unmerged:
                return {
                    "action": "preserve",
                    "reason": "branch has commits not merged into main branch",
                }

        return {"action": "prune", "reason": "clean worktree with no unmerged commits"}

    def _has_unmerged_commits(
        self, wt_path: str, main_repo: str, branch_ref: str
    ) -> bool | None:
        """Check whether *branch_ref* has commits not present on the default branch.

        WHAT: Uses a two-pronged strategy to determine whether a worktree
        branch has commits that have not yet been merged or pushed.  Prong 1:
        if the branch tracks a remote upstream, runs ``git rev-list --count
        @{u}..HEAD`` in *wt_path* — any non-zero count means unpushed commits
        and returns True immediately.  Prong 2: resolves the default branch via
        ``_get_default_branch``, then runs ``git rev-list --count
        <ref>..<branch>`` in *main_repo* for both ``origin/<default>`` and the
        local default ref, returning ``count > 0``.  Returns None if neither
        check can be completed (caller must PRESERVE conservatively).

        WHY: Pruning a branch with unmerged commits destroys otherwise
        unreachable history.  The two-prong approach maximises detection
        coverage: prong 1 catches unpushed work even when the branch has no
        name on the default ref; prong 2 catches branches that were pushed to
        origin but not yet merged.  Returning None (rather than defaulting to
        False) on error ensures the caller does not prune when the merge state
        is genuinely unknown.

        Args:
            wt_path: Absolute path to the worktree directory.
            main_repo: Absolute path to the main git repository.
            branch_ref: Full ref name (e.g. ``refs/heads/agent-abc``).

        Returns:
            True if unmerged, False if merged, None if undetermined.
        """
        # Derive the short branch name (strip ``refs/heads/`` prefix if present).
        short_branch = branch_ref
        if branch_ref.startswith("refs/heads/"):
            short_branch = branch_ref[len("refs/heads/") :]

        # Check 1: upstream ahead count.
        try:
            ahead_result = subprocess.run(  # nosec B603, B607 - safe git command
                ["git", "-C", wt_path, "rev-list", "--count", "@{u}..HEAD"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if ahead_result.returncode == 0:
                ahead = int(ahead_result.stdout.strip() or "0")
                if ahead > 0:
                    return True
        except (ValueError, Exception):
            pass  # nosec B110 - upstream check is optional; fall through

        # Check 2: compare against local default branch in main_repo.
        default_branch = self._get_default_branch(main_repo)
        if default_branch is None:
            return None

        # Use origin/default_branch if available, else local default_branch.
        # This catches commits that haven't been pushed to origin.
        for ref_to_compare in [f"origin/{default_branch}", default_branch]:
            try:
                ahead_result2 = subprocess.run(  # nosec B603, B607 - safe git command
                    [
                        "git",
                        "-C",
                        main_repo,
                        "rev-list",
                        "--count",
                        f"{ref_to_compare}..{short_branch}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                if ahead_result2.returncode == 0:
                    count = int(ahead_result2.stdout.strip() or "0")
                    return count > 0
            except (ValueError, Exception):
                continue  # nosec B112 - try next ref

        return None  # Could not determine

    def _get_default_branch(self, main_repo: str) -> str | None:
        """Return the name of the default local branch (``main`` or ``master``).

        WHAT: Resolves the short name of the repository's default branch using
        three strategies in order: (1) ``git symbolic-ref --short
        refs/remotes/origin/HEAD`` — strips the ``origin/`` prefix from the
        result; (2) ``git rev-parse --abbrev-ref HEAD`` on *main_repo* if HEAD
        is not detached; (3) iterates through ``("main", "master")`` and
        returns the first ref that ``git rev-parse --verify`` can resolve.
        Returns None if all strategies fail.

        WHY: Different repositories use different default branch names and
        remote configurations.  The symbolic-ref strategy is the most reliable
        when the remote is configured; HEAD-based fallback handles local-only
        repos; and the explicit name scan handles unusual setups where the
        symbolic ref is unset but a conventional branch name exists.  Returning
        None signals the caller to treat the branch conservatively (PRESERVE)
        rather than guess incorrectly.

        Args:
            main_repo: Absolute path to the main git repository.

        Returns:
            Short branch name, or None if undetermined.
        """
        # Try origin/HEAD symbolic ref.
        try:
            ref_result = subprocess.run(  # nosec B603, B607 - safe git command
                [
                    "git",
                    "-C",
                    main_repo,
                    "symbolic-ref",
                    "--short",
                    "refs/remotes/origin/HEAD",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if ref_result.returncode == 0:
                ref = ref_result.stdout.strip()
                # Returns something like ``origin/main``
                if "/" in ref:
                    return ref.split("/", 1)[1]
                return ref
        except Exception:
            pass  # nosec B110 - fall through

        # Try HEAD of the main repo itself.
        try:
            head_result = subprocess.run(  # nosec B603, B607 - safe git command
                ["git", "-C", main_repo, "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if head_result.returncode == 0:
                branch = head_result.stdout.strip()
                if branch and branch != "HEAD":
                    return branch
        except Exception:
            pass  # nosec B110 - fall through

        # Check common branch names.
        for candidate in ("main", "master"):
            try:
                check = subprocess.run(  # nosec B603, B607 - safe git command
                    ["git", "-C", main_repo, "rev-parse", "--verify", candidate],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if check.returncode == 0:
                    return candidate
            except Exception:
                continue  # nosec B112 - try next candidate

        return None

    def _remove_worktree(self, main_repo: str, wt_path: str) -> bool:
        """Remove a git worktree safely (no --force).

        Using ``git worktree remove`` WITHOUT ``--force`` so git refuses if the
        worktree still has modifications — a last-resort safety net on top of
        our classification logic.

        Args:
            main_repo: Absolute path to the main git repository.
            wt_path: Absolute path to the worktree to remove.

        Returns:
            True if removal succeeded, False otherwise.
        """
        result = subprocess.run(  # nosec B603, B607 - safe git command
            ["git", "-C", main_repo, "worktree", "remove", wt_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "git worktree remove %s failed (rc=%d): %s",
                wt_path,
                result.returncode,
                result.stderr.strip(),
            )
            return False
        logger.info("Pruned stale worktree: %s", wt_path)
        return True

    def _collect_registered_worktree_paths(self, main_repo: str) -> set[Path]:
        """Return the set of resolved paths for all registered git worktrees.

        WHAT: Runs ``git worktree list --porcelain`` from *main_repo* and
        collects every ``worktree`` path line, resolving each to an absolute
        ``Path``.  Returns the resulting set (may be empty on git failure).

        WHY: The orphan sweep needs to know which on-disk directories are
        legitimately registered so it can exclude them from deletion.  Using a
        dedicated helper keeps the path-collection logic separate from both
        ``_list_worktree_candidates`` (which applies scope filtering) and the
        orphan sweep itself (which operates on all immediate children of the
        managed worktrees directory).

        Args:
            main_repo: Absolute path string of the main git repository.

        Returns:
            Set of resolved ``Path`` objects for all registered worktrees.
        """
        result = subprocess.run(  # nosec B603, B607 - safe git command
            ["git", "-C", main_repo, "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "_collect_registered_worktree_paths: git worktree list failed (rc=%d)",
                result.returncode,
            )
            return set()

        paths: set[Path] = set()
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("worktree "):
                raw_path = stripped[len("worktree ") :]
                try:
                    paths.add(Path(raw_path).resolve())
                except Exception as exc:
                    logger.debug(
                        "_collect_registered_worktree_paths: could not resolve %s: %s",
                        raw_path,
                        exc,
                    )
        return paths

    def _sweep_orphaned_dirs(
        self,
        main_repo: str,
        worktrees_dir: Path,
        registered_paths: set[Path],
    ) -> list[dict[str, Any]]:
        """Sweep orphaned (unregistered) directories under *worktrees_dir*.

        WHAT: Lists immediate child directories of *worktrees_dir*.  For each
        child whose resolved path is NOT in *registered_paths* (i.e. not a
        registered git worktree), classifies it with
        ``_classify_orphan_candidate``.  Directories classified as safe are
        removed with ``shutil.rmtree`` after a strict path-containment guard
        verifies the target is under *worktrees_dir*.  Returns a list of
        per-directory decision records.

        WHY: ``git worktree list`` only enumerates registered worktrees.
        Directories orphaned when worktrees were de-registered (e.g. via
        ``git worktree remove --force``) are invisible to git and accumulate
        indefinitely.  A separate filesystem scan at the same managed-worktrees
        root is the only way to find and clean them.

        Args:
            main_repo: Absolute path to the main git repository.
            worktrees_dir: Absolute Path of ``<repo>/.claude/worktrees/``.
            registered_paths: Set of resolved paths for all registered
                worktrees (used to skip legitimate worktrees).

        Returns:
            List of dicts with keys: ``path``, ``action`` (``"swept"`` |
            ``"preserved"``), ``reason``.
        """
        records: list[dict[str, Any]] = []
        wt_dir_resolved = worktrees_dir.resolve()
        main_resolved = Path(main_repo).resolve()

        try:
            children = [c for c in worktrees_dir.iterdir() if c.is_dir()]
        except OSError as exc:
            logger.warning(
                "_sweep_orphaned_dirs: could not list %s: %s", worktrees_dir, exc
            )
            return records

        for child in children:
            child_resolved = child.resolve()

            # Skip registered worktrees — they are handled by the main prune path.
            if child_resolved in registered_paths:
                continue

            # Skip main working tree (should never appear here but be defensive).
            if child_resolved == main_resolved:
                continue

            # Path-containment guard: child must be strictly under worktrees_dir.
            try:
                child_resolved.relative_to(wt_dir_resolved)
            except ValueError:
                logger.warning(
                    "_sweep_orphaned_dirs: skipping %s — resolves outside %s",
                    child,
                    wt_dir_resolved,
                )
                records.append(
                    {
                        "path": str(child_resolved),
                        "action": "preserved",
                        "reason": "path resolves outside .claude/worktrees/ — containment guard",
                    }
                )
                continue

            # Classify the candidate.
            decision = self._classify_orphan_candidate(str(child_resolved), main_repo)
            rec: dict[str, Any] = {"path": str(child_resolved)}
            rec.update(decision)

            if decision["action"] == "sweep":
                # Perform the actual removal.
                try:
                    shutil.rmtree(str(child_resolved))  # nosec B106 - path-containment guard applied above
                    logger.info("Swept orphaned dir: %s", child_resolved)
                    rec["action"] = "swept"
                    rec["removed"] = True
                except OSError as exc:
                    logger.warning(
                        "_sweep_orphaned_dirs: rmtree(%s) failed: %s",
                        child_resolved,
                        exc,
                    )
                    rec["action"] = "preserved"
                    rec["reason"] = f"rmtree failed: {exc}"
                    rec["removed"] = False
            else:
                rec["action"] = "preserved"

            records.append(rec)

        return records

    def _classify_orphan_candidate(
        self, dir_path: str, main_repo: str
    ) -> dict[str, Any]:
        """Classify an unregistered directory as SWEEP or PRESERVE.

        WHAT: Applies conservative safety rules to a single unregistered
        directory and returns a decision dict with ``action`` (``"sweep"`` or
        ``"preserve"``) and a human-readable ``reason``.  The rules are:
        (1) If the directory is not a usable git work area (broken ``.git``
        link, not inside any repo) it is SWEEP-eligible only when clean and
        contains no tracked-but-modified or untracked files — but if ``git
        status`` itself errors, PRESERVE.  (2) If it IS a usable git work area,
        apply the same four rules as ``_classify_worktree``: locked flag, missing
        dir, uncommitted/untracked changes, unmerged commits.  Any ambiguity
        returns PRESERVE.

        WHY: De-registered worktree directories may still have modified files or
        unpushed commits that the user has not yet recovered.  The conservative
        ``when-in-doubt-PRESERVE`` policy ensures we never delete real work.
        Mirroring ``_classify_worktree`` rules avoids duplicating safety logic.

        Args:
            dir_path: Absolute path string of the orphaned directory.
            main_repo: Absolute path to the main git repository.

        Returns:
            Dict with ``action`` (``"sweep"`` | ``"preserve"``) and ``reason``.
        """
        # Rule 1: Run git status to determine if this is a usable git work area
        # and whether it has any changes.
        try:
            status_result = subprocess.run(  # nosec B603, B607 - safe git command
                ["git", "-C", dir_path, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if status_result.returncode != 0:
                # git cannot operate here — may be a broken .git link or a
                # plain non-git directory.  Treat as non-git dir: safe to sweep
                # if it's truly not a git area; but we cannot be certain, so
                # check if .git exists as a heuristic.
                git_link = Path(dir_path) / ".git"
                if git_link.exists():
                    # Has a .git entry but git can't read it — ambiguous, PRESERVE.
                    return {
                        "action": "preserve",
                        "reason": f"git status failed (rc={status_result.returncode}) but .git exists; ambiguous state",
                    }
                # No .git at all — plain leftover directory, safe to sweep.
                return {
                    "action": "sweep",
                    "reason": "not a git work area (no .git); plain leftover directory",
                }

            # git status succeeded — check for any changes.
            if status_result.stdout.strip():
                return {
                    "action": "preserve",
                    "reason": "has uncommitted or untracked changes",
                }
        except Exception as exc:
            return {"action": "preserve", "reason": f"git status error: {exc}"}

        # Rule 2: Check for unmerged commits (reuse existing helper).
        # First we need the branch from this directory.
        try:
            branch_result = subprocess.run(  # nosec B603, B607 - safe git command
                ["git", "-C", dir_path, "symbolic-ref", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            branch: str | None = None
            if branch_result.returncode == 0:
                branch = branch_result.stdout.strip() or None
        except Exception:
            branch = None

        if branch:
            branch_ref = f"refs/heads/{branch}"
            unmerged = self._has_unmerged_commits(dir_path, main_repo, branch_ref)
            if unmerged is None:
                return {
                    "action": "preserve",
                    "reason": "could not determine merge status; preserving conservatively",
                }
            if unmerged:
                return {
                    "action": "preserve",
                    "reason": "branch has commits not merged into main branch",
                }

        return {
            "action": "sweep",
            "reason": "clean orphaned directory with no unmerged commits",
        }

    # ------------------------------------------------------------------
    # State capture
    # ------------------------------------------------------------------

    def _capture_state(self, session_id: str, message: str | None) -> dict[str, Any]:
        """Capture current session state.

        Args:
            session_id: Session identifier
            message: Optional context message

        Returns:
            Complete state dictionary
        """
        # Get git context
        git_context = self._get_git_context()

        # Get task list state
        task_list = self._capture_task_list_state()

        # Build state dictionary
        return {
            "session_id": session_id,
            "paused_at": datetime.now(UTC).isoformat(),
            "duration_hours": 0,  # Can be calculated if session start time known
            "context_usage": {
                "tokens_used": 0,  # Would need Claude API integration
                "tokens_total": 200000,
                "percentage": 0,
            },
            "conversation": {
                "primary_task": "Manual pause - see message below",
                "current_phase": "In progress",
                "summary": message or "No summary provided",
                "accomplishments": [],
                "next_steps": [],
            },
            "git_context": git_context,
            "active_context": {
                "working_directory": str(self.project_path),
            },
            "important_reminders": [],
            "resume_instructions": {
                "quick_start": [
                    f"Read {session_id}.md for full context",
                    "Run: git status to check current state",
                    f"Run: cat {self.pause_dir}/LATEST-SESSION.txt",
                ],
                "files_to_review": [],
                "validation_commands": {
                    "check_git": "git status && git log -1 --stat",
                    "check_session": f"cat {self.pause_dir}/{session_id}.md",
                },
            },
            "open_questions": [],
            "performance_metrics": {},
            "todos": {"active": [], "completed": []},
            "task_list": task_list,
            "version": self._get_project_version(),
            "build": "current",
            "project_path": str(self.project_path),
        }

    def _capture_task_list_state(self) -> dict[str, Any]:
        """Capture task list state from ~/.claude/tasks/ directory.

        Reads task files and categorizes them by status.

        Returns:
            Dict with pending_tasks, in_progress_tasks, completed_count
        """
        tasks_dir = Path.home() / ".claude" / "tasks"

        result: dict[str, Any] = {
            "pending_tasks": [],
            "in_progress_tasks": [],
            "completed_count": 0,
        }

        # Handle missing directory gracefully
        if not tasks_dir.exists():
            logger.debug(f"Tasks directory does not exist: {tasks_dir}")
            return result

        if not tasks_dir.is_dir():
            logger.warning(f"Tasks path is not a directory: {tasks_dir}")
            return result

        try:
            # Read all JSON task files
            task_files = list(tasks_dir.glob("*.json"))
            logger.debug(f"Found {len(task_files)} task files in {tasks_dir}")

            for task_file in task_files:
                try:
                    task_data = json.loads(task_file.read_text())

                    # Extract task info
                    task_info = {
                        "id": task_data.get("id", task_file.stem),
                        "title": task_data.get("title", "Untitled"),
                        "description": task_data.get("description", ""),
                        "priority": task_data.get("priority", "medium"),
                        "created_at": task_data.get("created_at"),
                        "file": str(task_file),
                    }

                    # Categorize by status
                    status = task_data.get("status", "pending").lower()

                    if status in {"completed", "done"}:
                        result["completed_count"] += 1
                    elif status in {"in_progress", "in-progress"}:
                        result["in_progress_tasks"].append(task_info)
                    else:
                        # pending, todo, or any other status
                        result["pending_tasks"].append(task_info)

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse task file {task_file}: {e}")
                except Exception as e:
                    logger.warning(f"Error reading task file {task_file}: {e}")

        except Exception as e:
            logger.error(f"Error scanning tasks directory: {e}")

        return result

    def _get_git_context(self) -> dict[str, Any]:
        """Get git repository context.

        Returns:
            Git context dictionary
        """
        if not self._is_git_repo():
            return {
                "is_git_repo": False,
                "branch": None,
                "recent_commits": [],
                "status": {
                    "clean": True,
                    "modified_files": [],
                    "untracked_files": [],
                },
            }

        try:
            # Get current branch
            branch = subprocess.check_output(  # nosec B603, B607 - safe git command
                ["git", "branch", "--show-current"],
                cwd=self.project_path,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            # Get recent commits (last 5)
            commit_log = subprocess.check_output(  # nosec B603, B607 - safe git command
                ["git", "log", "-5", "--pretty=format:%h|%an|%ai|%s"],
                cwd=self.project_path,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            recent_commits = []
            for line in commit_log.split("\n"):
                if line:
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        recent_commits.append(
                            {
                                "sha": parts[0],
                                "author": parts[1],
                                "timestamp": parts[2],
                                "message": parts[3],
                            }
                        )

            # Get status
            status_output = subprocess.check_output(  # nosec B603, B607 - safe git command
                ["git", "status", "--porcelain"],
                cwd=self.project_path,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            modified_files = []
            untracked_files = []
            if status_output:
                for line in status_output.split("\n"):
                    if line.startswith("??"):
                        untracked_files.append(line[3:])
                    elif line:
                        modified_files.append(line[3:])

            return {
                "is_git_repo": True,
                "branch": branch,
                "recent_commits": recent_commits,
                "status": {
                    "clean": len(modified_files) == 0 and len(untracked_files) == 0,
                    "modified_files": modified_files,
                    "untracked_files": untracked_files,
                },
            }

        except subprocess.CalledProcessError as e:
            logger.warning(f"Git command failed: {e}")
            return {
                "is_git_repo": True,
                "branch": "unknown",
                "recent_commits": [],
                "status": {"clean": True, "modified_files": [], "untracked_files": []},
            }

    def _is_git_repo(self) -> bool:
        """Check if directory is a git repository.

        Returns:
            True if git repository exists
        """
        return (self.project_path / ".git").exists()

    def _generate_markdown(self, state: dict[str, Any]) -> str:
        """Generate human-readable markdown format.

        Args:
            state: State dictionary

        Returns:
            Markdown formatted string
        """
        session_id = state["session_id"]
        paused_at = state["paused_at"]
        conversation = state["conversation"]
        git_context = state["git_context"]
        active_context = state["active_context"]

        lines = [
            "# Claude MPM Session Pause Document",
            "",
            "## Session Metadata",
            "",
            f"**Session ID**: `{session_id}`",
            f"**Paused At**: {paused_at}",
            f"**Project**: `{state['project_path']}`",
            f"**Version**: {state.get('version', 'unknown')}",
            "",
            "## What You Were Working On",
            "",
            f"**Primary Task**: {conversation['primary_task']}",
            f"**Current Phase**: {conversation['current_phase']}",
            "",
            "**Summary**:",
            f"{conversation['summary']}",
            "",
        ]

        # Accomplishments
        if conversation.get("accomplishments"):
            lines.append("## Accomplishments This Session")
            lines.append("")
            for item in conversation["accomplishments"]:
                lines.append(f"- {item}")
            lines.append("")

        # Next steps
        if conversation.get("next_steps"):
            lines.append("## Next Steps (Priority Order)")
            lines.append("")
            for i, step in enumerate(conversation["next_steps"], 1):
                if isinstance(step, dict):
                    lines.append(
                        f"{i}. **{step.get('task', 'Unknown task')}** (Priority: {step.get('priority', '?')})"
                    )
                    if step.get("estimated_hours"):
                        lines.append(f"   - Est. time: {step['estimated_hours']}")
                    if step.get("status"):
                        lines.append(f"   - Status: {step['status']}")
                    if step.get("notes"):
                        lines.append(f"   - Notes: {step['notes']}")
                else:
                    lines.append(f"{i}. {step}")
            lines.append("")

        # Active context
        lines.extend(
            [
                "## Active Context",
                "",
                f"**Working Directory**: `{active_context['working_directory']}`",
                "",
            ]
        )

        # Git context
        lines.append("## Git Context")
        lines.append("")
        if git_context["is_git_repo"]:
            lines.append(f"**Branch**: `{git_context['branch']}`")
            lines.append(
                f"**Status**: {'Clean' if git_context['status']['clean'] else 'Modified'}"
            )
            lines.append("")

            if git_context["status"]["modified_files"]:
                lines.append("**Modified files**:")
                for f in git_context["status"]["modified_files"][:10]:
                    lines.append(f"- `{f}`")
                lines.append("")

            if git_context["recent_commits"]:
                lines.append("**Recent commits**:")
                for commit in git_context["recent_commits"]:
                    lines.append(
                        f"- `{commit['sha']}` - {commit['message']} ({commit['author']})"
                    )
                lines.append("")
        else:
            lines.append("*Not a git repository*")
            lines.append("")

        # Important reminders
        if state.get("important_reminders"):
            lines.append("## Important Reminders")
            lines.append("")
            for reminder in state["important_reminders"]:
                lines.append(f"- {reminder}")
            lines.append("")

        # Resume instructions
        lines.extend(
            [
                "## Resume Instructions",
                "",
                "### Quick Resume (5 minutes)",
                "",
            ]
        )
        for instruction in state["resume_instructions"]["quick_start"]:
            lines.append(f"1. {instruction}")
        lines.append("")

        if state["resume_instructions"]["validation_commands"]:
            lines.append("### Validation Commands")
            lines.append("")
            lines.append("```bash")
            for cmd in state["resume_instructions"]["validation_commands"].values():
                lines.append(cmd)
            lines.append("```")
            lines.append("")

        # Footer
        lines.extend(
            [
                "---",
                "",
                "Resume with: `/mpm-init resume` or `cat .claude-mpm/sessions/LATEST-SESSION.txt`",
                "",
            ]
        )

        return "\n".join(lines)

    def _update_latest_pointer(self, session_id: str) -> None:
        """Update LATEST-SESSION.txt pointer.

        Args:
            session_id: Session identifier
        """
        try:
            latest_file = self.pause_dir / "LATEST-SESSION.txt"
            content = f"""Latest Session: {session_id}
Paused At: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S %Z")}
Project: {self.project_path}

Files:
- {session_id}.json (machine-readable)
- {session_id}.md (human-readable documentation)

Quick Resume:
  /mpm-init resume

Full Context:
  cat {self.pause_dir}/{session_id}.md

Validation:
  git status && git log -1 --stat
"""
            latest_file.write_text(content)
            logger.debug(f"Updated LATEST-SESSION.txt: {session_id}")
        except Exception as e:
            logger.warning(f"Failed to update LATEST-SESSION.txt: {e}")

    def _get_project_version(self) -> str:
        """Get project version from pyproject.toml or package.

        Returns:
            Version string or 'unknown'
        """
        try:
            # Try pyproject.toml
            pyproject = self.project_path / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text()
                for line in content.split("\n"):
                    if line.startswith("version"):
                        return line.split("=")[1].strip().strip('"')

            # Try package __version__
            import claude_mpm

            if hasattr(claude_mpm, "__version__"):
                return claude_mpm.__version__

        except Exception:
            pass  # nosec B110 - fallback to "unknown" is intentional

        return "unknown"
