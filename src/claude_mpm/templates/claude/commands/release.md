---
description: "Release a new version of claude-mpm (MPM-provided — may be shadowed by a user /release command)"
argument-hint: "[patch|minor|major]"
---

> **Note (MPM-provided command)**: This `/release` command is shipped by claude-mpm.
> If you have a project or user-level command also named `/release`, it will shadow
> this one.  User commands take precedence by design.

Release a new version of claude-mpm using the Makefile workflow.

The release type is: $ARGUMENTS

Steps to follow:

1. First, verify the correct GitHub account is active:
   ```
   claude-mpm gh switch
   ```
   This must be `bobmatnyc`, not `bob-duetto`.

2. Run the appropriate release target:
   ```
   make release-$ARGUMENTS
   ```
   This bumps the version, updates changelogs, and builds the package.

3. Publish to all platforms (PyPI, Homebrew, npm, GitHub Releases):
   ```
   make release-publish
   ```

If $ARGUMENTS is empty or not one of patch/minor/major, ask the user which type they want before proceeding.

**Recovery if release fails mid-build**: If `make release-$ARGUMENTS` fails *after*
the version bump (i.e. during the build or publish step), do **NOT** re-run
`make release-$ARGUMENTS` — it would bump the version a second time (double-bump).
Instead, finish the in-progress release without bumping again:

```
make release-build-current && make release-publish
```

`release-check` now aborts if HEAD is already a `bump:` commit, which catches this
case automatically.

**CRITICAL**: Never manually edit version files or call `./scripts/publish_to_pypi.sh` directly. Always use the Makefile targets.
