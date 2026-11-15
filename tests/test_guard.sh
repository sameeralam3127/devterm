#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEVTERM="$ROOT/bin/devterm"
passed=0

pass() { passed=$((passed + 1)); printf 'ok %d - %s\n' "$passed" "$1"; }
fail() { printf 'not ok - %s\n' "$1" >&2; exit 1; }

output="$(DEVTERM_KUBE_CONTEXT_OVERRIDE=production-us "$DEVTERM" context)"
case "$output" in
  *"Safety:     PRODUCTION (production-us)"*) pass "detects a production Kubernetes context" ;;
  *) fail "production Kubernetes context was not detected" ;;
esac

if DEVTERM_PROD_PATTERN='critical' "$DEVTERM" is-production production >/dev/null 2>&1; then
  fail "custom production pattern was ignored"
else
  pass "honors a custom production pattern"
fi

if command -v zsh >/dev/null 2>&1; then
  if PATH="$ROOT/bin:$PATH" zsh -f -c \
    'source "$1"; _devterm_is_risky kubectl delete pod api' _ "$ROOT/shell/devterm.zsh"; then
    pass "classifies kubectl delete as risky"
  else
    fail "kubectl delete was not classified as risky"
  fi
  if PATH="$ROOT/bin:$PATH" zsh -f -c \
    'source "$1"; ! _devterm_is_risky kubectl get pod api' _ "$ROOT/shell/devterm.zsh"; then
    pass "allows read-only kubectl commands"
  else
    fail "kubectl get was classified as risky"
  fi
else
  printf 'ok - zsh guard classification (skipped: zsh unavailable)\n'
fi

test_home="$(mktemp -d)"
trap 'rm -rf "${test_home:?}"' EXIT
mkdir -p "$test_home/config"
printf '%s\n' '# original starship config' > "$test_home/config/starship.toml"
printf '%s\n' '# original zsh config' > "$test_home/.zshrc"
HOME="$test_home" ZDOTDIR="$test_home" STARSHIP_CONFIG="$test_home/config/starship.toml" \
  DEVTERM_SKIP_OS_CHECK=1 "$ROOT/install.sh" --profile midnight --app iterm --skip-brew --yes >/dev/null
# Force a later install to create a backup directory that does not contain Starship.
printf '%s\n' '# user changed zsh config' > "$test_home/.zshrc"
HOME="$test_home" ZDOTDIR="$test_home" STARSHIP_CONFIG="$test_home/config/starship.toml" \
  DEVTERM_SKIP_OS_CHECK=1 "$ROOT/install.sh" --profile midnight --app iterm --skip-brew --yes >/dev/null
HOME="$test_home" ZDOTDIR="$test_home" STARSHIP_CONFIG="$test_home/config/starship.toml" \
  "$ROOT/uninstall.sh" --yes >/dev/null
if [ "$(cat "$test_home/config/starship.toml")" = '# original starship config' ]; then
  pass "restores the original Starship config after reinstall"
else
  fail "original Starship config was not restored"
fi
if [ -e "$test_home/.devterm/original_starship_backup" ]; then
  fail "completed uninstall retained stale original-backup state"
else
  pass "resets original-backup state after uninstall"
fi

printf '1..%d\n' "$passed"
