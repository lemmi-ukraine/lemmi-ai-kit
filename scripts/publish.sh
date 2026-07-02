#!/usr/bin/env bash
# Cut a stable release.
#
# The version in pyproject.toml is always the version currently under development;
# pushes to main produce vX.Y.Z-preview.N prereleases of it (see release.yaml).
# This script promotes that version to a stable vX.Y.Z release, then starts the
# next development cycle.
#
# Usage:
#   scripts/publish.sh            # release the current pyproject version as-is
#   scripts/publish.sh minor      # bump to the next minor first, then release
#   scripts/publish.sh major      # bump to the next major first, then release
set -euo pipefail

cd "$(dirname "$0")/.."

BUMP="${1:-none}"
case "$BUMP" in
  none | minor | major) ;;
  *)
    echo "usage: scripts/publish.sh [minor|major]" >&2
    exit 2
    ;;
esac

die() {
  echo "error: $1" >&2
  exit 1
}

branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$branch" = "main" ] || die "releases are cut from main (currently on: $branch)"
git diff-index --quiet HEAD -- || die "working tree is dirty — commit or stash first"
git fetch origin main
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "local main is not in sync with origin/main"

echo "==> Running checks"
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv run pytest

if [ "$BUMP" != "none" ]; then
  echo "==> Bumping $BUMP version"
  uv version --bump "$BUMP"
  uv lock
  git add pyproject.toml uv.lock
  git commit -m "chore(release): v$(uv version --short)"
fi

VERSION="$(uv version --short)"
case "$VERSION" in
  *.dev* | *rc* | *a* | *b*) die "refusing to tag a non-final version: $VERSION" ;;
esac

echo "==> Tagging v${VERSION}"
git tag -a "v${VERSION}" -m "Release v${VERSION}"
git push origin main "v${VERSION}"

echo "==> Starting next development cycle"
uv version --bump patch
uv lock
git add pyproject.toml uv.lock
git commit -m "chore: begin v$(uv version --short) development"
git push origin main

echo "==> Done. GitHub Actions will build and publish the v${VERSION} release."
