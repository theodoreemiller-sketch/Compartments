#!/bin/bash
# Pre-commit hook: if index.html is part of this commit, its
# 📅 Creation Date / 📅 Last Updated field must match today's date.
# Installed by CLAUDE.md's git setup steps as .git/hooks/pre-commit
# (the hook itself lives in the ephemeral git-dir, so it must be
# reinstalled from this persistent copy each fresh session).

set -e

STAGED=$(git diff --cached --name-only)

if ! echo "$STAGED" | grep -q '^index\.html$'; then
  exit 0
fi

TODAY=$(date '+%-m/%-d/%Y')

STAGED_CONTENT=$(git show :index.html)

if echo "$STAGED_CONTENT" | grep -Eq "📅 (Creation Date|Last Updated) = ${TODAY//\//\\/}"; then
  exit 0
fi

echo "❌ Commit blocked: index.html is changing but its 📅 Creation Date / Last Updated field doesn't show today's date ($TODAY)."
echo "   Update the date line before committing (per CLAUDE.md's mandatory rule)."
FOUND_LINE=$(echo "$STAGED_CONTENT" | grep -E "📅 (Creation Date|Last Updated) =" | head -1)
if [ -n "$FOUND_LINE" ]; then
  echo "   Current line: $FOUND_LINE"
fi
exit 1
