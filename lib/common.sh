#!/usr/bin/env bash
# Shared helpers for install.sh / uninstall.sh. Bash 3.2 compatible (macOS default).
# shellcheck disable=SC2034  # variables are used by the scripts that source this file

DYN_DIR="$HOME/Library/Application Support/iTerm2/DynamicProfiles"
STARSHIP_CFG="${STARSHIP_CONFIG:-$HOME/.config/starship.toml}"
ZSHRC="${ZDOTDIR:-$HOME}/.zshrc"
STATE_DIR="$HOME/.devterm"
MARK_START="# >>> devterm >>>"
MARK_END="# <<< devterm <<<"

DRY_RUN="${DRY_RUN:-0}"
ASSUME_YES="${ASSUME_YES:-0}"

if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
  C_BLUE=$'\033[34m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""; C_BLUE=""; C_GREEN=""; C_YELLOW=""; C_RED=""
fi

step() { printf '\n%s==>%s %s%s%s\n' "$C_BLUE" "$C_RESET" "$C_BOLD" "$*" "$C_RESET"; }
info() { printf '    %s\n' "$*"; }
ok()   { printf '    %s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '    %s!%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
die()  { printf '%serror:%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }

# run CMD...  — execute, or just print in dry-run mode
run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '    %s[dry-run]%s %s\n' "$C_DIM" "$C_RESET" "$*"
  else
    "$@"
  fi
}

# confirm "Question" — default yes; auto-yes with --yes or non-interactive stdin
confirm() {
  if [ "$ASSUME_YES" -eq 1 ] || [ ! -t 0 ]; then return 0; fi
  local reply
  read -r -p "    $1 [Y/n] " reply
  case "$reply" in [nN]*) return 1 ;; *) return 0 ;; esac
}

# backup_file PATH BACKUP_DIR — copy PATH into BACKUP_DIR if it exists
backup_file() {
  local src="$1" dest_dir="$2"
  [ -e "$src" ] || return 0
  run mkdir -p "$dest_dir"
  run cp -p "$src" "$dest_dir/"
  info "backed up $(basename "$src") → $(pretty_path "$dest_dir")"
}

# remove_zsh_block FILE — strip the managed devterm block from FILE
remove_zsh_block() {
  local file="$1" tmp
  [ -f "$file" ] || return 0
  grep -qF "$MARK_START" "$file" || return 0
  if [ "$DRY_RUN" -eq 1 ]; then
    run "remove devterm block from $file"
    return 0
  fi
  grep -qF "$MARK_END" "$file" \
    || die "$(pretty_path "$file") has '$MARK_START' but no '$MARK_END' — fix it by hand first"
  tmp="$(mktemp)"
  # drop the block, then trim trailing blank lines so reinstalls don't pile them up
  awk -v s="$MARK_START" -v e="$MARK_END" '
    $0 == s { skip = 1; next }
    $0 == e { skip = 0; next }
    skip    { next }
    { lines[++n] = $0; if ($0 !~ /^[[:space:]]*$/) last = n }
    END     { for (i = 1; i <= last; i++) print lines[i] }
  ' "$file" > "$tmp"
  cat "$tmp" > "$file"   # preserve original file permissions / symlinks
  rm -f "$tmp"
}

# pretty_path PATH — show $HOME as ~
pretty_path() {
  case "$1" in
    "$HOME"/*) printf '~%s' "${1#"$HOME"}" ;;
    *)         printf '%s' "$1" ;;
  esac
}

# conf_get FILE KEY — read key=value from a profile.conf
conf_get() { sed -n "s/^$2=//p" "$1" | head -n 1; }

# terminal_remove_profiles PREFIX — delete Terminal.app profiles whose name starts with
# PREFIX (moving default/startup to "Basic" first); prints the removed names
terminal_remove_profiles() {
  osascript - "$1" <<'OSA'
on run argv
  set prefix to item 1 of argv
  set removed to {}
  tell application "Terminal"
    repeat with n in (get name of every settings set)
      set n to n as text
      if n starts with prefix then
        if name of default settings is n then set default settings to settings set "Basic"
        if name of startup settings is n then set startup settings to settings set "Basic"
        delete settings set n
        set end of removed to n
      end if
    end repeat
  end tell
  set AppleScript's text item delimiters to linefeed
  return removed as text
end run
OSA
}

# terminal_has_devterm_profiles — check Terminal.app prefs without launching it
terminal_has_devterm_profiles() {
  local prefs
  prefs="$(defaults read com.apple.Terminal "Window Settings" 2>/dev/null || true)"
  case "$prefs" in *'"devterm '*) return 0 ;; *) return 1 ;; esac
}

# iterm_imported_copy GUID — true if iTerm2 has a regular (imported, non-dynamic)
# profile with this GUID. iTerm2 also lists dynamic profiles in its prefs, but
# marks them with "Dynamic Profile Filename", so those don't count.
iterm_imported_copy() {
  local prefs="$HOME/Library/Preferences/com.googlecode.iterm2.plist" count i
  count="$(plutil -extract "New Bookmarks" raw -o - "$prefs" 2>/dev/null || echo 0)"
  i=0
  while [ "$i" -lt "$count" ]; do
    if [ "$(plutil -extract "New Bookmarks.$i.Guid" raw -o - "$prefs" 2>/dev/null)" = "$1" ] \
       && ! plutil -extract "New Bookmarks.$i.Dynamic Profile Filename" raw -o - "$prefs" >/dev/null 2>&1; then
      return 0
    fi
    i=$((i + 1))
  done
  return 1
}

iterm_running() { command -v pgrep >/dev/null 2>&1 && pgrep -x iTerm2 >/dev/null 2>&1; }
