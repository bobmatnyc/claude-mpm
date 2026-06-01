#!/usr/bin/env bash
# Download the bundled ztk binary from the codejunkie99/ztk GitHub release.
#
# Used by claude-mpm release process to populate src/claude_mpm/bin/ztk with
# the binary matching the current build platform. The platform-specific wheel
# build CI (.github/workflows/release-wheels.yml) downloads all 4 binaries
# in parallel; this script targets local/single-platform builds.
#
# Upstream assets are .tar.gz TARBALLS (e.g. ztk-aarch64-macos.tar.gz), each
# containing a `ztk` binary. This script downloads the tarball, extracts the
# binary, and installs it to src/claude_mpm/bin/ztk.
#
# The <ztk-tag> is PINNED for reproducible/deterministic builds — the canonical
# source of truth is src/claude_mpm/bin/ztk_version.txt (the Makefile's
# `download-ztk` target reads it; `claude-mpm ztk update` passes it here). When
# no tag is supplied, the script falls back to that manifest; never fetch
# "latest by accident".
#
# Usage:
#   scripts/download_ztk_binaries.sh [<ztk-tag>]
#
# Example:
#   scripts/download_ztk_binaries.sh v0.3.1

set -euo pipefail

ZTK_REPO="codejunkie99/ztk"

# Resolve repo root (script lives in scripts/)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd)"
BIN_DIR="$REPO_ROOT/src/claude_mpm/bin"
VERSION_FILE="$BIN_DIR/ztk_version.txt"
mkdir -p "$BIN_DIR"

# Tag: explicit CLI arg, else the pinned version manifest (single source of truth).
TAG="${1:-}"
if [ -z "$TAG" ] && [ -f "$VERSION_FILE" ]; then
  TAG="$(tr -d '[:space:]' < "$VERSION_FILE")"
fi
if [ -z "$TAG" ]; then
  echo "Usage: $0 [<ztk-tag>]  (e.g. v0.3.1; defaults to ${VERSION_FILE})" >&2
  exit 1
fi

# Detect current platform → codejunkie99/ztk release asset (a .tar.gz tarball).
# Real v0.3.1 assets:
#   ztk-aarch64-macos.tar.gz       ztk-x86_64-macos.tar.gz
#   ztk-aarch64-linux-musl.tar.gz  ztk-x86_64-linux-musl.tar.gz
#   ztk-x86_64-windows.zip
detect_asset() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"
  case "$os" in
    Darwin)
      case "$arch" in
        arm64|aarch64) echo "ztk-aarch64-macos.tar.gz" ;;
        x86_64)        echo "ztk-x86_64-macos.tar.gz" ;;
        *) echo "Unsupported macOS arch: $arch" >&2; return 1 ;;
      esac
      ;;
    Linux)
      case "$arch" in
        x86_64|amd64)  echo "ztk-x86_64-linux-musl.tar.gz" ;;
        aarch64|arm64) echo "ztk-aarch64-linux-musl.tar.gz" ;;
        *) echo "Unsupported Linux arch: $arch" >&2; return 1 ;;
      esac
      ;;
    *) echo "Unsupported OS: $os" >&2; return 1 ;;
  esac
}

ASSET="$(detect_asset)"
BASE_URL="https://github.com/${ZTK_REPO}/releases/download/${TAG}"
TARGET="${BIN_DIR}/ztk"

echo "==> Downloading ztk ${TAG} (asset: ${ASSET})"
echo "    Source: ${BASE_URL}/${ASSET}"
echo "    Target: ${TARGET}"

# Download the tarball to a temp dir, extract the ztk binary, install it.
# Non-fatal: if the asset is missing/unreachable, warn and skip so the wheel
# can still build without a bundled binary (ztk compression degrades
# gracefully). Preserves the original retry/best-effort behavior.
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
TARBALL="${TMP_DIR}/${ASSET}"

if curl -fSL --retry 3 -o "${TARBALL}" "${BASE_URL}/${ASSET}" 2>/dev/null; then
  if tar -xzf "${TARBALL}" -C "${TMP_DIR}"; then
    # Locate the extracted `ztk` binary (may sit in a subdir); prefer executable.
    EXTRACTED="$(find "${TMP_DIR}" -type f -name ztk -perm -u+x 2>/dev/null | head -n1)"
    if [ -z "${EXTRACTED}" ]; then
      EXTRACTED="$(find "${TMP_DIR}" -type f -name ztk 2>/dev/null | head -n1)"
    fi
    if [ -n "${EXTRACTED}" ]; then
      mv -f "${EXTRACTED}" "${TARGET}"
      chmod +x "${TARGET}"
      echo "--> Extracted ztk binary -> ${TARGET}"
    else
      echo "    WARNING: no 'ztk' binary found inside ${ASSET}; skipping." >&2
    fi
  else
    echo "    WARNING: failed to extract ${ASSET}; skipping." >&2
  fi
else
  echo "    WARNING: ztk asset not available at ${BASE_URL}/${ASSET} — skipping bundled binary." >&2
fi

# Download LICENSE (optional — fall back gracefully if not in release)
LICENSE_TARGET="${BIN_DIR}/ztk_LICENSE"
echo "--> LICENSE -> ${LICENSE_TARGET}"
if ! curl -fSL --retry 3 -o "${LICENSE_TARGET}" "${BASE_URL}/LICENSE" 2>/dev/null; then
  echo "    (LICENSE not in release; fetching from raw repo)"
  if ! curl -fSL --retry 3 -o "${LICENSE_TARGET}" \
       "https://raw.githubusercontent.com/${ZTK_REPO}/master/LICENSE" 2>/dev/null; then
    echo "    WARNING: no LICENSE file available; writing placeholder"
    cat > "${LICENSE_TARGET}" <<EOF
ztk binary distributed with claude-mpm.
Source: https://github.com/${ZTK_REPO} (tag: ${TAG})
See upstream repository for license terms.
EOF
  fi
fi

# Summary
echo ""
echo "==> Summary"
ls -la "${TARGET}" "${LICENSE_TARGET}" 2>/dev/null || true
file "${TARGET}" 2>/dev/null || true
echo "==> Done."
