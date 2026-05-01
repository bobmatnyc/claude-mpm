#!/usr/bin/env bash
# Download bundled ztk binaries from the bobmatnyc/ztk GitHub release.
#
# Used by claude-mpm release process to populate src/claude_mpm/bin/ztk with
# the binary matching the current build platform. The platform-specific wheel
# build CI (.github/workflows/release-wheels.yml) downloads all 4 binaries
# in parallel; this script targets local/single-platform builds.
#
# Usage:
#   scripts/download_ztk_binaries.sh <ztk-tag>
#
# Example:
#   scripts/download_ztk_binaries.sh v0.2.1

set -euo pipefail

ZTK_REPO="bobmatnyc/ztk"
TAG="${1:-}"

if [ -z "$TAG" ]; then
  echo "Usage: $0 <ztk-tag>  (e.g. v0.2.1)" >&2
  exit 1
fi

# Resolve repo root (script lives in scripts/)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd)"
BIN_DIR="$REPO_ROOT/src/claude_mpm/bin"
mkdir -p "$BIN_DIR"

# Detect current platform → ztk asset name
detect_platform() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"
  case "$os" in
    Darwin)
      case "$arch" in
        arm64|aarch64) echo "macosx_11_0_arm64" ;;
        x86_64)        echo "macosx_10_9_x86_64" ;;
        *) echo "Unsupported macOS arch: $arch" >&2; return 1 ;;
      esac
      ;;
    Linux)
      case "$arch" in
        x86_64|amd64)  echo "linux_x86_64" ;;
        aarch64|arm64) echo "linux_aarch64" ;;
        *) echo "Unsupported Linux arch: $arch" >&2; return 1 ;;
      esac
      ;;
    *) echo "Unsupported OS: $os" >&2; return 1 ;;
  esac
}

PLATFORM="$(detect_platform)"
BASE_URL="https://github.com/${ZTK_REPO}/releases/download/${TAG}"

echo "==> Downloading ztk ${TAG} for platform: ${PLATFORM}"
echo "    Source: ${BASE_URL}"
echo "    Target: ${BIN_DIR}"

# Download platform-specific binary → bin/ztk
ASSET="ztk-${PLATFORM}"
TARGET="${BIN_DIR}/ztk"
echo "--> ${ASSET} -> ${TARGET}"
curl -fSL --retry 3 -o "${TARGET}" "${BASE_URL}/${ASSET}"
chmod +x "${TARGET}"

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
ls -la "${BIN_DIR}/ztk" "${LICENSE_TARGET}"
file "${BIN_DIR}/ztk" 2>/dev/null || true
echo "==> Done."
