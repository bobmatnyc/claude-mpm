# Squash-Merge Trailer Normalization

> Issue: [#863](https://github.com/bobmatnyc/claude-mpm/issues/863)

## The Problem

The `commit_cost_tracker` post-commit hook
(`src/claude_mpm/hooks/commit_cost_tracker.py`) amends **every** commit with a
git trailer block:

```
Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>
X-AI-Tokens-In: 1234
X-AI-Tokens-Out: 567
X-AI-Model: claude-opus-4-8
X-MPM-Version: 6.5.45
```

A git trailer block is only recognized by `git interpret-trailers --parse` when
it is the **last paragraph** of the commit message.

When GitHub performs a **squash-merge**, it concatenates the bodies of *all*
branch commits into one squash commit message. Every interior commit's trailer
block becomes mid-body prose, and only the **last** commit's trailer block
remains the trailing paragraph. As a result:

- `git interpret-trailers --parse` on the merged-to-`main` commit recovers only
  the last commit's `Co-Authored-By` (and maybe its token line).
- All `X-AI-Tokens-In/Out`, `X-AI-Model(s)`, and `X-MPM-Version` provenance from
  the other branch commits is **lost**.

## The Solution: Merge-Time Normalization

`scripts/squash_merge_trailers.py` composes a squash-commit body whose **last
paragraph is a single aggregated trailer block** that survives the squash:

- **Sum** `X-AI-Tokens-In` and `X-AI-Tokens-Out` across all branch commits.
- **Union** every `X-AI-Model` / `X-AI-Models` value (deduplicated, stable
  order) into one `X-AI-Models` line.
- **Take the latest** `X-MPM-Version` (chronologically last commit on the
  branch).
- Always include the canonical
  `Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>` exactly
  once.

Empty families are omitted: a branch with no token data emits no
`X-AI-Tokens-*` lines but still stamps `X-MPM-Version` and `Co-Authored-By`.

The trailer key names are imported from
`claude_mpm.hooks.commit_cost_tracker` (the same source the hook emits from), so
the merge-time parser can never drift from the hook-time emitter.

The script is **side-effect free** — it never performs the merge. It only prints
(or writes) the normalized body, which you then feed to `gh pr merge`.

## Usage

```bash
# 1. Compose the normalized squash body for a PR into a file.
python scripts/squash_merge_trailers.py --pr 870 --body-file /tmp/squash-body.txt

# 2. Squash-merge with that body (and delete the branch, per the PR workflow).
gh pr merge 870 --squash \
  --subject "feat: your clean squash subject (#870)" \
  --body-file /tmp/squash-body.txt \
  --delete-branch
```

Other modes:

```bash
# Print the full composed body to stdout.
python scripts/squash_merge_trailers.py --pr 870

# Print ONLY the aggregated trailer block (handy for inspection / testing).
python scripts/squash_merge_trailers.py --pr 870 --print-trailers-only

# Operate on a local commit range instead of a PR (smoke testing / no network).
python scripts/squash_merge_trailers.py --local --base main --head HEAD
```

## Verify It Worked

After merging, confirm the squash commit on `main` is parseable:

```bash
git log -1 --format=%B main | git interpret-trailers --parse
```

You should see the aggregated `X-AI-Tokens-In/Out`, `X-AI-Models`,
`X-MPM-Version`, and `Co-Authored-By` lines.

## Tests

`tests/test_squash_merge_trailers.py` covers the aggregation logic and runs the
**real** `git interpret-trailers --parse` to:

- document the burial bug (interior trailers are not recovered from a naive
  GitHub-style squash body), and
- prove the normalized body's last paragraph is fully parseable.

```bash
uv run pytest -p no:xdist tests/test_squash_merge_trailers.py -v
```
