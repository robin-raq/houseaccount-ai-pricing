#!/usr/bin/env bash
# secret_guard.sh — fail if the deployed-app AI key (or anything shaped like a
# live key) is about to enter git or a deploy bundle. Run before every push and
# before building any bundle. Exit non-zero => do not push/deploy until scrubbed.
#
# Usage:
#   scripts/secret_guard.sh                 # scan git-tracked + staged files
#   scripts/secret_guard.sh path/to/bundle  # also scan a build/deploy output dir
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 2
BUNDLE="${1:-}"
HITS=0

note(){ printf "  [LEAK] %s\n" "$1"; HITS=1; }

# Files git would actually include: tracked + staged. (Untracked .env is fine.)
# (while-read instead of `mapfile` so this runs on macOS's default bash 3.2.)
FILES=()
while IFS= read -r f; do FILES+=("$f"); done < <( { git ls-files; git diff --cached --name-only; } 2>/dev/null | sort -u )
if [ -n "$BUNDLE" ] && [ -d "$BUNDLE" ]; then
  while IFS= read -r f; do FILES+=("$f"); done < <(find "$BUNDLE" -type f)
fi

# 1) The actual configured key value, if present in the environment, is the
#    highest-signal thing to look for — an exact match means a real leak.
KEYVAL="${OPENAI_API_KEY:-${APP_AI_KEY:-}}"

# 2) Generic provider-key shapes as a backstop (OpenAI sk-..., Anthropic, AWS).
PATTERNS=(
  'sk-[A-Za-z0-9_-]{20,}'
  'sk-proj-[A-Za-z0-9_-]{20,}'
  'sk-ant-[A-Za-z0-9_-]{20,}'
  'AKIA[0-9A-Z]{16}'
)

# Guard the count first: on bash 3.2, "${FILES[@]}" on an empty array trips
# `set -u` ("unbound variable"). No files => nothing git-bound to leak.
if [ "${#FILES[@]}" -gt 0 ]; then
for f in "${FILES[@]}"; do
  [ -f "$f" ] || continue
  case "$f" in *.png|*.jpg|*.jpeg|*.gif|*.mp4|*.mp3|*.zip|*.pdf|*.ico|*.woff*) continue;; esac
  if [ -n "$KEYVAL" ] && LC_ALL=C grep -qF -- "$KEYVAL" "$f" 2>/dev/null; then
    note "exact app key value found in: $f"
  fi
  for p in "${PATTERNS[@]}"; do
    if LC_ALL=C grep -Eq -- "$p" "$f" 2>/dev/null; then
      note "key-shaped string ($p) in: $f"
    fi
  done
done
fi

# .env must never be tracked.
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  note ".env is tracked by git — it must be gitignored and untracked"
fi

if [ "$HITS" -ne 0 ]; then
  echo "secret_guard: BLOCKED — scrub the above before pushing/deploying."
  echo "  - remove the value, move it to the untracked secrets file / PaaS secret store"
  echo "  - if it was committed, rewrite history (git rm --cached + amend/filter) and ROTATE the key"
  exit 1
fi
echo "secret_guard: clean — no key material in git-bound or bundle files."
exit 0
