#!/usr/bin/env bash
# Cut a mem-cli release from the latest version in CHANGELOG.md.
#
# - If the latest version has no git tag yet: syncs pyproject.toml, commits,
#   tags, and pushes (triggering the CI release workflow).
# - If the tag already exists: exits and asks the developer to bump the version
#   in CHANGELOG.md first.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHANGELOG="$ROOT/CHANGELOG.md"

# ── helpers ──────────────────────────────────────────────────────────────────

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n'  "$*"; }

# ── read latest released version from CHANGELOG.md ───────────────────────────

VERSION=$(grep -m1 -E '^\#\# \[[0-9]+\.[0-9]+\.[0-9]+\]' "$CHANGELOG" \
  | sed 's/.*\[\([^]]*\)\].*/\1/')

if [[ -z "$VERSION" ]]; then
  red "No released version found in CHANGELOG.md."
  echo "Add a version section like:  ## [0.2.0] — $(date +%Y-%m-%d)"
  exit 1
fi

TAG="v$VERSION"
bold "Latest version in CHANGELOG.md: $TAG"

# ── check if the tag already exists ──────────────────────────────────────────

if git tag --list "$TAG" | grep -q "^${TAG}$"; then
  red "Tag $TAG already exists."
  echo ""
  echo "To cut a new release, add a new version section to CHANGELOG.md:"
  echo ""
  echo "  ## [$(python3 -c "
v = '$VERSION'.split('.')
v[2] = str(int(v[2]) + 1)
print('.'.join(v))
")] — $(date +%Y-%m-%d)"
  echo ""
  echo "  ### Added"
  echo "  - ..."
  echo ""
  echo "Then re-run this script."
  exit 1
fi

# ── sync pyproject.toml ───────────────────────────────────────────────────────

echo "Syncing pyproject.toml to $VERSION..."
python3 "$ROOT/scripts/sync_version.py"

# ── commit, tag, push ────────────────────────────────────────────────────────

cd "$ROOT"

if ! git diff --quiet pyproject.toml; then
  echo "Committing version bump..."
  git add CHANGELOG.md pyproject.toml
  git commit -m "release: $TAG"
else
  echo "pyproject.toml already up to date, no commit needed."
fi

echo "Creating tag $TAG..."
git tag "$TAG"

echo "Pushing to origin..."
git push origin master --tags

green ""
green "Done. CI will now build the release binaries and publish $TAG."
green "Watch progress at: https://github.com/jleivas/mem-cli/actions"
