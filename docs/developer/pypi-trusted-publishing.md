# PyPI Trusted Publishing (OIDC) — Release Setup

`claude-mpm` publishes per-platform wheels and the sdist to PyPI from CI using
**PyPI Trusted Publishing (OIDC)** — no long-lived `PYPI_API_TOKEN` secret.

- **Workflow:** `.github/workflows/release-wheels.yml`
- **Publish job environment name:** `pypi` (must match the PyPI config exactly)
- **Publish action:** `pypa/gh-action-pypi-publish@release/v1` with
  `permissions: id-token: write` and `skip-existing: true`

## Why this changed

The old publish job used `twine upload` with
`TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}`. That secret was empty/unset, so
**every release got a 403 Forbidden** (v6.5.0 / 6.5.1 / 6.5.2 all failed). OIDC
removes the token entirely: GitHub mints a short-lived, audience-scoped token at
publish time and PyPI validates it against a trusted-publisher entry you create.

## One-time owner setup (REQUIRED before the next release)

Do this once on PyPI as a maintainer of the `claude-mpm` project:

1. Go to <https://pypi.org/manage/project/claude-mpm/settings/publishing/>
   (PyPI → your account → **claude-mpm** → **Publishing**).
2. Under **Add a new trusted publisher → GitHub**, enter **exactly**:
   - **Owner:** `bobmatnyc`
   - **Repository name:** `claude-mpm`
   - **Workflow filename:** `release-wheels.yml`
   - **Environment name:** `pypi`
3. Click **Add**.

That's it. The next time a `v*` tag is pushed (via `make release-publish`), the
`publish` job authenticates via OIDC and uploads all platform wheels + the sdist.

### If the project did not yet exist on PyPI ("pending publisher")

If `claude-mpm` already exists on PyPI (it does), use the steps above. If you
were bootstrapping a brand-new project name, you would instead use
<https://pypi.org/manage/account/publishing/> → **Add a pending publisher** with
the same four fields plus the **PyPI project name** (`claude-mpm`). The pending
entry is consumed on the first successful publish and becomes a normal trusted
publisher.

## Who publishes what (local vs CI)

| Channel                          | Owner | Trigger                          |
|----------------------------------|-------|----------------------------------|
| PyPI per-platform wheels + sdist | CI    | push of `v*` tag (OIDC publish)  |
| Homebrew tap                     | local | `make release-publish` (waits for the CI-published sdist on PyPI, then computes sha256) |
| npm (`@bobmatnyc/claude-mpm`)    | local | `make release-publish`           |
| GitHub release (sdist asset)     | local | `make release-publish`           |

`make release-publish` no longer runs `twine upload`. It pushes the bump commit
and the `v*` tag (which triggers the CI publish), then runs the Homebrew / npm /
GitHub-release steps. `scripts/publish_to_pypi.sh` is a **local fallback that
uploads the sdist only** (via `uv publish --check-url`, the skip-existing
equivalent) and never the binary-bundled `py3-none-any` wheel.

## Verifying a release

- Watch the workflow:
  <https://github.com/bobmatnyc/claude-mpm/actions/workflows/release-wheels.yml>
- Confirm platform wheels on PyPI (each carries a platform tag, e.g.
  `claude_mpm-X.Y.Z-py3-none-macosx_11_0_arm64.whl`), not a single
  `py3-none-any` wheel.
