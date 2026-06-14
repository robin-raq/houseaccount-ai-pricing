#!/usr/bin/env bash
# verify.sh — the project's own advertised quality gates, both stacks. A passing
# dev boot is NOT enough; this runs the real linters/type-checkers/tests and fails
# loudly if any is red. Run after each increment and as a hard gate before every
# push, every deploy, and before declaring the run Done.
#
#   Rails  (api/)           : rubocop · zeitwerk:check · rspec
#   Python (model_service/) : ruff · mypy · pytest
#
# Exit 0 = all green. Non-zero = STOP and fix before proceeding.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
[ -d "$HOME/.rbenv/shims" ] && export PATH="$HOME/.rbenv/shims:$PATH"

gate() { # gate <dir> <label> <cmd...>
  local dir="$1" label="$2"; shift 2
  echo "  [$label] \$ $*"
  if ( cd "$ROOT/$dir" && "$@" >/tmp/verify_gate.$$ 2>&1 ); then
    echo "    [PASS]"
  else
    echo "    [FAIL] $*"; sed 's/^/      /' /tmp/verify_gate.$$ | tail -25; FAILED=1
  fi
  rm -f /tmp/verify_gate.$$
}

echo "== verify: Rails API gates =="
if [ -f "$ROOT/api/Gemfile" ]; then
  gate api rubocop  bundle exec rubocop --format simple
  gate api zeitwerk bin/rails zeitwerk:check
  gate api rspec    bundle exec rspec
else
  echo "  (api/ not scaffolded yet — skipped)"
fi

echo "== verify: Python model service gates =="
if [ -f "$ROOT/model_service/pyproject.toml" ]; then
  gate model_service ruff   uv run ruff check .
  gate model_service mypy   uv run mypy pricing service
  gate model_service pytest uv run pytest
else
  echo "  (model_service/ not scaffolded yet — skipped)"
fi

echo "== verify summary =="
if [ "$FAILED" -ne 0 ]; then
  echo "RESULT: BLOCKED — an advertised gate is RED. Do NOT push, deploy, or declare Done."
  exit 1
fi
echo "RESULT: ALL GREEN — every advertised quality gate passed."
exit 0
