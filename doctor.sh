#!/usr/bin/env bash
# devterm doctor — check the devterm setup and explain how to fix problems.
# Read-only: changes nothing, and never launches iTerm2 or Terminal.app.
# Exit status: 0 = no problems (warnings are OK), 1 = problems found.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$REPO_DIR/lib/common.sh"

case "${1:-}" in
  -h|--help)
    echo "Usage: $(pretty_path "$REPO_DIR")/doctor.sh"
    echo "Checks fonts, tools, ~/.zshrc, the Starship config and the iTerm2 /"
    echo "Terminal.app profiles, and prints how to fix each problem. Changes nothing."
    exit 0 ;;
  "") ;;
  *) die "unknown option: $1 (see --help)" ;;
esac

PROBLEMS=0
WARNINGS=0
ITERM_PREFS="$HOME/Library/Preferences/com.googlecode.iterm2.plist"
TERMINAL_PREFS="$HOME/Library/Preferences/com.apple.Terminal.plist"
INSTALL="$(pretty_path "$REPO_DIR")/install.sh"

# problem MSG [FIX...] / caution MSG [FIX...] — report, with how to fix it
problem() {
  printf '    %s✗%s %s\n' "$C_RED" "$C_RESET" "$1"; shift
  for line in "$@"; do printf '      %s→%s %s\n' "$C_DIM" "$C_RESET" "$line"; done
  PROBLEMS=$((PROBLEMS + 1))
}
caution() {
  printf '    %s!%s %s\n' "$C_YELLOW" "$C_RESET" "$1"; shift
  for line in "$@"; do printf '      %s→%s %s\n' "$C_DIM" "$C_RESET" "$line"; done
  WARNINGS=$((WARNINGS + 1))
}

# plist_get FILE KEYPATH — print a value, or nothing if it's missing
plist_get() { plutil -extract "$2" raw -o - "$1" 2>/dev/null || true; }

is_nerd_font() { case "$1" in *NerdFont*|*NFM-*|*NF-*|*NFP-*) return 0 ;; *) return 1 ;; esac; }

# The theme the Starship prompt was generated for, e.g. "Midnight"
prompt_theme() {
  [ -f "$STARSHIP_CFG" ] || return 0
  sed -n '1s/^# devterm starship config — theme: //p' "$STARSHIP_CFG"
}

# theme_mismatch APP PROFILE_NAME — warn when the prompt and the profile disagree
theme_mismatch() {
  local app="$1" theme="${2#devterm · }" prompt
  prompt="$(prompt_theme)"
  if [ -n "$prompt" ] && [ "$prompt" != "$theme" ]; then
    caution "$app uses the $theme colors, but the prompt was set up for $prompt" \
      "run: $INSTALL -p $(echo "$theme" | tr '[:upper:]' '[:lower:]')  (or pick devterm · $prompt in $app)"
  fi
}

check_system() {
  step "System"
  local ver shell
  ver="$(sw_vers -productVersion 2>/dev/null || echo unknown)"
  ok "macOS $ver"
  shell="$(dscl . -read "$HOME" UserShell 2>/dev/null | awk '{print $2}' || true)"
  shell="${shell:-${SHELL:-unknown}}"
  case "$shell" in
    */zsh) ok "login shell is zsh" ;;
    *) problem "your login shell is $shell, but devterm sets up zsh" "run: chsh -s /bin/zsh" ;;
  esac
}

check_tools() {
  step "Tools"
  if command -v starship >/dev/null 2>&1; then
    ok "$(starship --version 2>/dev/null | head -n 1)"
  else
    problem "Starship isn't installed — there's no prompt" "run: brew install starship"
  fi

  if compgen -G "$HOME/Library/Fonts/JetBrainsMonoNerdFont*" >/dev/null \
     || compgen -G "/Library/Fonts/JetBrainsMonoNerdFont*" >/dev/null; then
    ok "JetBrains Mono Nerd Font"
  else
    problem "JetBrains Mono Nerd Font isn't installed — prompt icons show as ? or boxes" \
      "run: brew install --cask font-jetbrains-mono-nerd-font"
  fi

  if [ -f "$ZSHRC" ] && grep -q "alias ls='eza" "$ZSHRC"; then
    if command -v eza >/dev/null 2>&1; then
      ok "eza"
    else
      caution "the ls aliases need eza, which isn't installed (ls still works)" "run: brew install eza"
    fi
  fi
}

check_shell() {
  step "Shell ($(pretty_path "$ZSHRC"))"
  if [ ! -f "$ZSHRC" ]; then
    problem "$(pretty_path "$ZSHRC") doesn't exist, so the prompt isn't set up" "run: $INSTALL"
    return 0
  fi

  local has_start=0 has_end=0 extra
  grep -qF "$MARK_START" "$ZSHRC" && has_start=1
  grep -qF "$MARK_END" "$ZSHRC" && has_end=1
  if [ "$has_start" -eq 1 ] && [ "$has_end" -eq 1 ]; then
    ok "devterm block present"
  elif [ "$has_start" -eq 1 ]; then
    problem "the devterm block has no '$MARK_END' line — the installer won't touch the file" \
      "add '$MARK_END' after the block, or remove the block, then rerun: $INSTALL"
  else
    problem "no devterm block, so Starship isn't started by devterm" "run: $INSTALL"
  fi

  # `starship init` outside the devterm block starts the prompt twice
  extra="$(awk -v s="$MARK_START" -v e="$MARK_END" '
    $0 == s { inblock = 1; next }
    $0 == e { inblock = 0; next }
    !inblock && /^[^#]*starship init/ { printf "%s%d", (n++ ? ", " : ""), NR }
  ' "$ZSHRC")"
  if [ -n "$extra" ] && [ "$has_start" -eq 1 ]; then
    caution "Starship is also started outside the devterm block (line $extra), so it runs twice" \
      "delete line $extra of $(pretty_path "$ZSHRC")"
  fi

  if grep -Eq '^[[:space:]]*ZSH_THEME="[^"]+"' "$ZSHRC"; then
    caution "an Oh My Zsh theme is set and may replace the Starship prompt" \
      "set ZSH_THEME=\"\" in $(pretty_path "$ZSHRC")"
  fi
}

check_starship() {
  step "Starship prompt ($(pretty_path "$STARSHIP_CFG"))"
  local theme err
  if [ ! -f "$STARSHIP_CFG" ]; then
    problem "no Starship config — the prompt uses Starship's defaults" "run: $INSTALL"
    return 0
  fi
  theme="$(prompt_theme)"
  if [ -n "$theme" ]; then
    ok "devterm theme: $theme"
  else
    caution "this config isn't from devterm (your own, or edited) — fine if that's intended" \
      "to use devterm's, run: $INSTALL (your config is backed up first)"
  fi
  if command -v starship >/dev/null 2>&1; then
    # starship logs config errors to stderr as "[ERROR] - (starship::config): …", colored
    err="$(STARSHIP_CONFIG="$STARSHIP_CFG" STARSHIP_SHELL=zsh starship prompt 2>&1 >/dev/null \
      | tr -d '\033' | sed 's/\[[0-9;]*m//g' | grep -E '^\[(ERROR|WARN)\]' | head -n 1 || true)"
    if [ -n "$err" ]; then
      problem "Starship can't use the config: ${err#*): }" \
        "fix the config, or rerun $INSTALL to replace it"
    else
      ok "config loads without errors"
    fi
  fi
}

# iterm_profile_name GUID — look the GUID up in dynamic and regular profiles
iterm_profile_name() {
  local guid="$1" f i count
  for f in "$DYN_DIR"/*.json; do
    [ -e "$f" ] || continue
    if [ "$(plist_get "$f" Profiles.0.Guid)" = "$guid" ]; then
      plist_get "$f" Profiles.0.Name; return 0
    fi
  done
  count="$(plist_get "$ITERM_PREFS" "New Bookmarks")"
  i=0
  while [ "$i" -lt "${count:-0}" ]; do
    if [ "$(plist_get "$ITERM_PREFS" "New Bookmarks.$i.Guid")" = "$guid" ]; then
      plist_get "$ITERM_PREFS" "New Bookmarks.$i.Name"; return 0
    fi
    i=$((i + 1))
  done
}

check_iterm() {
  step "iTerm2"
  if [ ! -d /Applications/iTerm.app ] && [ ! -d "$HOME/Applications/iTerm.app" ]; then
    info "not installed — skipped"
    return 0
  fi
  local f names="" guid name
  for f in "$DYN_DIR"/devterm-*.json; do
    [ -e "$f" ] || continue
    if ! plutil -convert xml1 -o /dev/null "$f" >/dev/null 2>&1; then  # -lint rejects JSON
      problem "$(basename "$f") is not valid JSON, so iTerm2 ignores it" "rerun: $INSTALL"
      continue
    fi
    names="${names:+$names, }$(plist_get "$f" Profiles.0.Name)"
    guid="$(plist_get "$f" Profiles.0.Guid)"
    if iterm_imported_copy "$guid"; then
      problem "an imported copy of $(basename "$f") has the same GUID, so iTerm2 reports a Dynamic Profiles error" \
        "delete the non-dynamic copy in iTerm2 → Settings → Profiles"
    fi
  done
  if [ -z "$names" ]; then
    caution "no devterm profile installed in iTerm2" "run: $INSTALL --app iterm"
    return 0
  fi
  ok "profiles: $names"

  guid="$(plist_get "$ITERM_PREFS" "Default Bookmark Guid")"
  name=""
  if [ -n "$guid" ]; then name="$(iterm_profile_name "$guid")"; fi
  case "$name" in
    "devterm · "*)
      ok "new windows use \"$name\""
      theme_mismatch "iTerm2" "$name" ;;
    *)
      caution "new iTerm2 windows use \"${name:-Default}\", not a devterm profile" \
        "iTerm2 → Settings → Profiles → devterm · … → Other Actions → Set as Default" ;;
  esac
}

check_terminal() {
  step "Terminal.app"
  local d names="" display default font_name colors_off
  for d in "$REPO_DIR"/profiles/*/; do
    [ -f "$d/profile.conf" ] || continue
    display="$(conf_get "$d/profile.conf" display)"
    if [ -n "$(plist_get "$TERMINAL_PREFS" "Window Settings.devterm · $display.name")" ]; then
      names="${names:+$names, }devterm · $display"
    fi
  done
  if [ -z "$names" ] && [ "${TERM_PROGRAM:-}" != "Apple_Terminal" ]; then
    info "no devterm profile installed — skipped (install with: $INSTALL --app terminal)"
    return 0
  fi
  if [ -n "$names" ]; then
    ok "profiles: $names"
  else
    caution "no devterm profile installed in Terminal.app" "run: $INSTALL --app terminal"
  fi

  default="$(defaults read com.apple.Terminal "Default Window Settings" 2>/dev/null || echo Basic)"
  case "$default" in
    "devterm · "*)
      ok "new windows use \"$default\""
      theme_mismatch "Terminal.app" "$default" ;;
    *)
      caution "new Terminal.app windows use \"$default\", not a devterm profile" \
        "Terminal → Settings → Profiles → devterm · … → Default, or run: $INSTALL --app terminal --set-default" ;;
  esac

  # Built-in profiles like Ocean have no Nerd Font, and some turn ANSI colors off (#7)
  colors_off="$(plist_get "$TERMINAL_PREFS" "Window Settings.$default.DisableANSIColor")"
  if [ "$colors_off" = "true" ]; then
    problem "\"$default\" has Display ANSI colors turned off, so the prompt has no colors" \
      "use a devterm profile, or tick Terminal → Settings → Profiles → $default → Text → Display ANSI colors"
  fi
  font_name="$(plist_get "$TERMINAL_PREFS" "Window Settings.$default.Font" | base64 -D 2>/dev/null \
    | plutil -p - 2>/dev/null | sed -n 's/^ *[0-9][0-9]* => "\(.*\)"$/\1/p' \
    | grep -vE "^([\$]null|NSFont|NSObject)\$" | head -n 1 || true)"
  if [ -n "$font_name" ] && ! is_nerd_font "$font_name"; then
    problem "\"$default\" uses $font_name, which has no Nerd Font icons, so they show as ?" \
      "use a devterm profile, or set the font to JetBrainsMono Nerd Font Mono"
  fi
}

check_this_terminal() {
  [ -t 1 ] || return 0
  step "This window (${TERM_PROGRAM:-unknown terminal})"
  case "${COLORTERM:-}" in
    truecolor|24bit) ok "24-bit color supported" ;;
    *)
      if [ "${TERM_PROGRAM:-}" = "Apple_Terminal" ]; then
        caution "this Terminal.app doesn't report 24-bit color, so prompt colors may be off" \
          "update to macOS 26 or later, or use iTerm2"
      else
        caution "this terminal doesn't report 24-bit color (COLORTERM=${COLORTERM:-unset}); prompt colors may be off"
      fi ;;
  esac
  info "Icon test:   󰌢 󰍛  󱃾 "
  info "${C_DIM}If any of those show as ? or empty boxes, this window isn't using a Nerd Font.${C_RESET}"
}

main() {
  printf '%sdevterm doctor%s — checking your setup (nothing will be changed)\n' "$C_BOLD" "$C_RESET"
  check_system
  check_tools
  check_shell
  check_starship
  check_iterm
  check_terminal
  check_this_terminal

  step "Summary"
  if [ "$PROBLEMS" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
    ok "everything looks good"
  else
    info "$PROBLEMS problem(s), $WARNINGS warning(s) — see the → lines above for fixes"
  fi
  [ "$PROBLEMS" -eq 0 ]
}

main
