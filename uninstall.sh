#!/usr/bin/env bash
# Remove everything devterm installed. Homebrew packages are left in place.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$REPO_DIR/lib/common.sh"

PURGE=0
while [ $# -gt 0 ]; do
  case "$1" in
    -n|--dry-run) DRY_RUN=1 ;;
    -y|--yes)     ASSUME_YES=1 ;;
    --purge)      PURGE=1 ;;
    -h|--help)
      echo "Usage: ./uninstall.sh [--dry-run] [--yes] [--purge]"
      echo "  --purge  also delete ~/.devterm (including backups)"
      exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

printf '%sdevterm uninstall%s\n' "$C_BOLD" "$C_RESET"
confirm "Remove devterm iTerm2 / Terminal.app profiles, prompt config and shell block?" || exit 0

step "iTerm2 profiles"
found=0
for f in "$DYN_DIR"/devterm-*.json; do
  [ -e "$f" ] || continue
  run rm -f "$f"; ok "removed $(basename "$f")"; found=1
done
[ "$found" -eq 1 ] || info "none installed"

step "Terminal.app profiles"
if ! terminal_has_devterm_profiles; then
  info "none installed"
elif [ "$DRY_RUN" -eq 1 ]; then
  run "remove devterm profiles from Terminal.app"
elif removed="$(terminal_remove_profiles "devterm · ")"; then
  while IFS= read -r name; do [ -z "$name" ] || ok "removed \"$name\""; done <<EOF
$removed
EOF
else
  warn "couldn't control Terminal.app — delete devterm profiles in Terminal → Settings → Profiles"
fi

step "Shell"
if [ -f "$ZSHRC" ] && grep -qF "$MARK_START" "$ZSHRC"; then
  remove_zsh_block "$ZSHRC"; ok "removed devterm block from $(pretty_path "$ZSHRC")"
else
  info "no devterm block found"
fi

step "Starship config"
backup=""
original_backup=""
[ -f "$STATE_DIR/original_starship_backup" ] && original_backup="$(cat "$STATE_DIR/original_starship_backup")"
if [ -z "$original_backup" ] && [ -f "$STATE_DIR/last_backup" ]; then
  backup="$(cat "$STATE_DIR/last_backup")"
  original_backup="$backup/$(basename "$STARSHIP_CFG")"
fi
if [ -n "$original_backup" ] && [ -f "$original_backup" ]; then
  run cp -p "$original_backup" "$STARSHIP_CFG"
  ok "restored your previous starship.toml"
elif [ -f "$STARSHIP_CFG" ] && head -n 1 "$STARSHIP_CFG" | grep -q '^# devterm'; then
  run rm -f "$STARSHIP_CFG"; ok "removed $(pretty_path "$STARSHIP_CFG")"
else
  info "left $(pretty_path "$STARSHIP_CFG") untouched (not managed by devterm)"
fi
if [ -f "$STATE_DIR/original_starship_backup" ]; then
  run rm -f "$STATE_DIR/original_starship_backup"
fi

step "DevTerm tools"
for f in "$STATE_DIR/bin/devterm" "$STATE_DIR/shell/devterm.zsh"; do
  if [ -f "$f" ]; then run rm -f "$f"; ok "removed $(pretty_path "$f")"; fi
done

if [ "$PURGE" -eq 1 ]; then
  step "State"
  run rm -rf "${STATE_DIR:?}"; ok "removed ~/.devterm"
fi

step "Done"
info "Homebrew packages were kept. To remove them:"
info "  brew uninstall starship eza && brew uninstall --cask font-jetbrains-mono-nerd-font"
