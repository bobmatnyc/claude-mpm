---
description: "Release a new version of claude-mpm (patch/minor/major)"
argument-hint: "[patch|minor|major]"
---

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

**CRITICAL**: Never manually edit version files or call `./scripts/publish_to_pypi.sh` directly. Always use the Makefile targets.
