#!/usr/bin/env bash
# Package and release standalone cross-platform Rollica CLI/daemon binaries to GitHub.
# Repository target: park0er/rollica-cli
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GITHUB_REPO="${ROLLICA_GITHUB_REPO:-park0er/rollica-cli}"

usage() {
  cat <<'EOF'
Usage:
  package-cli.sh <version> [--upload] [--repo <owner/repo>] [--repo-dir <path>]

Arguments:
  <version>       Release version (e.g. 0.0.7 or v0.0.7)
  --upload        Upload assets to GitHub Releases via gh CLI
  --repo          Target GitHub repo (default: park0er/rollica-cli)
  --repo-dir      Path to Rollica git repo checkout (default: current directory)

Examples:
  package-cli.sh v0.0.7
  package-cli.sh v0.0.7 --upload
EOF
  exit 1
}

if [ $# -lt 1 ]; then
  usage
fi

RAW_VERSION="$1"
shift
VERSION="${RAW_VERSION#v}"
TAG="v${VERSION}"
UPLOAD=false
REPO_DIR="$(pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    --upload)
      UPLOAD=true
      shift
      ;;
    --repo)
      GITHUB_REPO="$2"
      shift 2
      ;;
    --repo-dir)
      REPO_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      ;;
  esac
done

cd "$REPO_DIR"

if [ ! -f "Makefile" ] || [ ! -d "server/cmd/multica" ]; then
  echo "Error: $REPO_DIR does not look like a Rollica repository checkout" >&2
  exit 1
fi

echo "==> Building Rollica CLI binaries for version ${TAG}..."
DIST_DIR="$REPO_DIR/dist/personal-cli-${VERSION}"
ARCHIVE_DIR="$DIST_DIR/archives"
rm -rf "$DIST_DIR"
mkdir -p "$ARCHIVE_DIR"

PLATFORMS=("darwin/arm64" "darwin/amd64" "linux/arm64" "linux/amd64" "windows/amd64")
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

for plat in "${PLATFORMS[@]}"; do
  GOOS="${plat%/*}"
  GOARCH="${plat#*/}"
  EXT=""
  if [ "$GOOS" = "windows" ]; then
    EXT=".exe"
  fi
  BIN_NAME="multica${EXT}"
  OUT_BIN="$DIST_DIR/${GOOS}-${GOARCH}/${BIN_NAME}"
  mkdir -p "$(dirname "$OUT_BIN")"
  
  echo "  -> Compiling ${GOOS}/${GOARCH}..."
  CGO_ENABLED=0 GOOS="$GOOS" GOARCH="$GOARCH" go build -C server -trimpath \
    -ldflags "-s -w -X main.version=${TAG} -X main.commit=${COMMIT} -X main.date=${BUILD_DATE}" \
    -o "$OUT_BIN" ./cmd/multica

  # Create archive
  ARCHIVE_BASE="multica-cli-${VERSION}-${GOOS}-${GOARCH}"
  if [ "$GOOS" = "windows" ]; then
    ZIP_PATH="$ARCHIVE_DIR/${ARCHIVE_BASE}.zip"
    (cd "$(dirname "$OUT_BIN")" && zip -q "$ZIP_PATH" "$BIN_NAME")
    echo "     Packed ${ARCHIVE_BASE}.zip"
  else
    TAR_PATH="$ARCHIVE_DIR/${ARCHIVE_BASE}.tar.gz"
    tar -czf "$TAR_PATH" -C "$(dirname "$OUT_BIN")" "$BIN_NAME"
    echo "     Packed ${ARCHIVE_BASE}.tar.gz"
  fi
done

# Generate checksums.txt
echo "==> Generating checksums.txt..."
CHECKSUM_FILE="$ARCHIVE_DIR/checksums.txt"
rm -f "$CHECKSUM_FILE"
(
  cd "$ARCHIVE_DIR"
  for f in multica-cli-*; do
    if [ -f "$f" ]; then
      shasum -a 256 "$f" >> "checksums.txt"
    fi
  done
)
cat "$CHECKSUM_FILE"

# Generate install.sh with auto-detection and update-source identification marker
echo "==> Generating install.sh..."
INSTALLER_FILE="$ARCHIVE_DIR/install.sh"
cat <<'INSTALLER_EOF' > "$INSTALLER_FILE"
#!/usr/bin/env bash
# Rollica Standalone CLI / Daemon installer from personal GitHub releases.
# Destination: ~/.rollica-cli/bin (or $ROLLICA_INSTALL_DIR)
set -euo pipefail

REPO="park0er/rollica-cli"
DEST="${ROLLICA_INSTALL_DIR:-$HOME/.rollica-cli/bin}"
CONFIG_DIR="$HOME/.rollica-cli"
VERSION="${VERSION:-}"

os="$(uname -s | tr '[:upper:]' '[:lower:]')"
arch="$(uname -m)"

case "$os" in
  darwin|linux) ;;
  *)
    echo "Error: Windows installer is zip archive. Please download from https://github.com/${REPO}/releases" >&2
    exit 1
    ;;
esac

case "$arch" in
  x86_64|amd64) arch=amd64 ;;
  arm64|aarch64) arch=arm64 ;;
  *)
    echo "Error: unsupported CPU architecture: $arch" >&2
    exit 1
    ;;
esac

if [ -z "$VERSION" ]; then
  # Fetch latest tag from GitHub redirect
  LATEST_TAG="$(curl -fsSLI "https://github.com/${REPO}/releases/latest" | grep -i '^location:' | sed 's#.*/tag/##' | tr -d '\r\n')"
  VERSION="${LATEST_TAG#v}"
fi
VERSION="${VERSION#v}"

archive="multica-cli-${VERSION}-${os}-${arch}.tar.gz"
url="https://github.com/${REPO}/releases/download/v${VERSION}/${archive}"

mkdir -p "$DEST"
mkdir -p "$CONFIG_DIR"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "==> Downloading Rollica CLI v${VERSION} for ${os}/${arch}..."
echo "    $url"
curl -fsSL "$url" -o "$tmp/$archive"

tar -xzf "$tmp/$archive" -C "$tmp"
if [ ! -f "$tmp/multica" ]; then
  echo "Error: archive did not contain multica binary" >&2
  exit 1
fi

chmod 755 "$tmp/multica"
mv "$tmp/multica" "$DEST/multica"

# Write update-source marker for automatic update discovery
echo "${REPO}" > "$CONFIG_DIR/update-source"

echo "✓ Successfully installed multica to $DEST/multica"

# PATH checking and configuration advice
SHELL_NAME="$(basename "${SHELL:-bash}")"
RC_FILE=""
if [ "$SHELL_NAME" = "zsh" ]; then
  RC_FILE="$HOME/.zshrc"
elif [ "$SHELL_NAME" = "bash" ]; then
  if [ -f "$HOME/.bash_profile" ]; then
    RC_FILE="$HOME/.bash_profile"
  else
    RC_FILE="$HOME/.bashrc"
  fi
fi

if [[ ":$PATH:" != *":$DEST:"* ]]; then
  echo ""
  echo "👉 Notice: $DEST is not in your current PATH."
  if [ -n "$RC_FILE" ]; then
    echo "   To persist, add the following to $RC_FILE:"
    echo "     export PATH=\"$DEST:\$PATH\""
    echo "     export ROLLICA_UPDATE_REPO=\"${REPO}\""
  fi
  echo "   To use immediately in this shell:"
  echo "     export PATH=\"$DEST:\$PATH\""
  echo "     export ROLLICA_UPDATE_REPO=\"${REPO}\""
fi

echo ""
"$DEST/multica" --version || true
INSTALLER_EOF
chmod 755 "$INSTALLER_FILE"

# Also bundle install-desktop-tokyo.sh if it exists
if [ -f "$REPO_DIR/deploy/tokyo-private/install-desktop-tokyo.sh" ]; then
  cp "$REPO_DIR/deploy/tokyo-private/install-desktop-tokyo.sh" "$ARCHIVE_DIR/"
fi

echo ""
echo "=================================================================="
echo "Build and packaging complete!"
echo "Assets directory: $ARCHIVE_DIR"
ls -lh "$ARCHIVE_DIR"
echo "=================================================================="

if [ "$UPLOAD" = true ]; then
  echo "==> Publishing to GitHub ${GITHUB_REPO} @ ${TAG}..."
  if ! gh release view "$TAG" --repo "$GITHUB_REPO" >/dev/null 2>&1; then
    gh release create "$TAG" \
      --repo "$GITHUB_REPO" \
      --title "Rollica CLI ${TAG}" \
      --notes "Personal standalone cross-platform Rollica CLI/Daemon distribution built from commit ${COMMIT}." \
      --latest=true
  fi

  gh release upload "$TAG" \
    "$ARCHIVE_DIR"/* \
    --repo "$GITHUB_REPO" \
    --clobber
  echo "✓ Successfully uploaded to https://github.com/${GITHUB_REPO}/releases/tag/${TAG}"
else
  echo "Skipped upload. Pass --upload to push to GitHub Releases."
fi

echo ""
echo "=================================================================="
echo "🎯 即拷即用本地安装/更新命令 (One-liner command to install/update):"
echo "=================================================================="
echo "curl -fsSL https://github.com/${GITHUB_REPO}/releases/download/${TAG}/install.sh | bash"
echo "=================================================================="
