#!/usr/bin/env bash
# devterm — opinionated iTerm2 / Terminal.app + Starship developer terminal setup for macOS.
set -euo pipefail

# Run straight from GitHub (no clone needed):
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/sameeralam3127/devterm/main/install.sh)"
#   curl -fsSL https://raw.githubusercontent.com/sameeralam3127/devterm/main/install.sh | bash -s -- -p midnight
# The script then downloads the repo to ~/.devterm/src and runs the copy there.
# DEVTERM_REPO (owner/name) and DEVTERM_REF (branch, tag or commit) pick what to download.
bootstrap() {
  local repo="${DEVTERM_REPO:-sameeralam3127/devterm}" ref="${DEVTERM_REF:-main}"
  local src="$HOME/.devterm/src" tmp
  if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
    echo "error: curl and tar are required" >&2; exit 1
  fi
  echo "==> Downloading devterm ($repo@$ref) to ~/.devterm/src"
  tmp="$(mktemp -d)"
  curl -fsSL "https://github.com/$repo/archive/$ref.tar.gz" | tar -xz -C "$tmp" --strip-components 1 \
    || { echo "error: download failed: https://github.com/$repo/archive/$ref.tar.gz" >&2; exit 1; }
  if [ ! -f "$tmp/install.sh" ] || [ ! -f "$tmp/lib/common.sh" ]; then
    echo "error: downloaded archive doesn't look like devterm" >&2; exit 1
  fi
  mkdir -p "$HOME/.devterm"
  rm -rf "$HOME/.devterm/src"
  mv "$tmp" "$src"
  # `curl | bash` leaves stdin on the pipe; reattach the terminal so prompts work
  if [ ! -t 0 ] && (exec </dev/tty) 2>/dev/null; then
    exec bash "$src/install.sh" "$@" </dev/tty
  fi
  exec bash "$src/install.sh" "$@"
}
if [ ! -f "${BASH_SOURCE[0]:-}" ]; then
  bootstrap "$@"
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$REPO_DIR/lib/common.sh"

PROFILES_DIR="$REPO_DIR/profiles"
PROFILE=""
FONT_SIZE=""
APP="all"
SKIP_BREW=0
WITH_EZA=1
SET_DEFAULT=0

usage() {
  cat <<USAGE
Usage: ./install.sh [options]

Options:
  -p, --profile NAME     Theme to install (see --list). Prompts if omitted.
  -f, --font-size N      Terminal font size, 10–32 (default: 16)
  -a, --app APP          Where to install: iterm, terminal (macOS Terminal.app)
                         or all (default: all)
  -l, --list             List available profiles and exit
      --set-default      Make the profile the default (for iTerm2, quit it first)
      --no-eza           Don't install eza or add the ls aliases
      --skip-brew        Don't install anything with Homebrew
  -n, --dry-run          Show what would change without changing anything
  -y, --yes              Don't ask for confirmation
  -h, --help             Show this help

Examples:
  ./install.sh
  ./install.sh --profile midnight --font-size 17 --set-default
  ./install.sh -p daylight --dry-run
  ./install.sh -p ember --app terminal
USAGE
}

list_profiles() {
  local d name desc
  for d in "$PROFILES_DIR"/*/; do
    [ -f "$d/profile.conf" ] || continue
    name="$(conf_get "$d/profile.conf" name)"
    desc="$(conf_get "$d/profile.conf" description)"
    printf '  %s%-10s%s %s\n' "$C_BOLD" "$name" "$C_RESET" "$desc"
  done
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      -p|--profile)   [ $# -ge 2 ] || die "$1 needs a value"; PROFILE="$2"; shift ;;
      -f|--font-size) [ $# -ge 2 ] || die "$1 needs a value"; FONT_SIZE="$2"; shift ;;
      -a|--app)       [ $# -ge 2 ] || die "$1 needs a value"; APP="$2"; shift ;;
      -l|--list)      echo "Available profiles:"; list_profiles; exit 0 ;;
      --set-default)  SET_DEFAULT=1 ;;
      --no-eza)       WITH_EZA=0 ;;
      --skip-brew)    SKIP_BREW=1 ;;
      -n|--dry-run)   DRY_RUN=1 ;;
      -y|--yes)       ASSUME_YES=1 ;;
      -h|--help)      usage; exit 0 ;;
      *)              usage; die "unknown option: $1" ;;
    esac
    shift
  done
}

preflight() {
  if [ "$(uname -s)" != "Darwin" ] && [ "${DEVTERM_SKIP_OS_CHECK:-0}" != "1" ]; then
    die "devterm supports macOS only"
  fi
  [ -d "$PROFILES_DIR" ] || die "profiles/ not found — run from a full clone of the repo"
  case "$APP" in iterm|terminal|all) ;; *) die "--app must be iterm, terminal or all" ;; esac
}

want() { [ "$APP" = all ] || [ "$APP" = "$1" ]; }

choose_profile() {
  local names=() d i choice
  for d in "$PROFILES_DIR"/*/; do
    [ -f "$d/profile.conf" ] && names+=("$(basename "$d")")
  done
  [ ${#names[@]} -gt 0 ] || die "no profiles found in $PROFILES_DIR"

  if [ -z "$PROFILE" ]; then
    if [ ! -t 0 ] || [ "$ASSUME_YES" -eq 1 ]; then
      PROFILE="${names[0]}"
    else
      step "Choose a profile"
      i=1
      for d in "${names[@]}"; do
        printf '  %s%d)%s %s%-10s%s %s\n' "$C_BLUE" "$i" "$C_RESET" "$C_BOLD" "$d" "$C_RESET" \
          "$(conf_get "$PROFILES_DIR/$d/profile.conf" description)"
        i=$((i + 1))
      done
      while :; do
        read -r -p "    Select [1-${#names[@]}] (default 1): " choice
        choice="${choice:-1}"
        case "$choice" in
          *[!0-9]*) ;;
          *) if [ "$choice" -ge 1 ] && [ "$choice" -le ${#names[@]} ]; then
               PROFILE="${names[$((choice - 1))]}"; break
             fi ;;
        esac
        warn "enter a number between 1 and ${#names[@]}"
      done
    fi
  fi
  [ -f "$PROFILES_DIR/$PROFILE/profile.conf" ] || {
    echo "Available profiles:"; list_profiles; die "unknown profile: $PROFILE"; }
}

choose_font_size() {
  if [ -z "$FONT_SIZE" ]; then
    if [ -t 0 ] && [ "$ASSUME_YES" -eq 0 ]; then
      read -r -p "    Font size (default 16): " FONT_SIZE
    fi
    FONT_SIZE="${FONT_SIZE:-16}"
  fi
  case "$FONT_SIZE" in *[!0-9]*|"") die "font size must be a number" ;; esac
  if [ "$FONT_SIZE" -lt 10 ] || [ "$FONT_SIZE" -gt 32 ]; then die "font size must be 10–32"; fi
}

brew_has() { command -v brew >/dev/null 2>&1 && brew list "$@" >/dev/null 2>&1; }

# prereqs — one "label|kind|brew package" line per thing devterm needs
prereqs() {
  if want iterm; then echo "iTerm2|cask|iterm2"; fi
  echo "JetBrains Mono Nerd Font|cask|font-jetbrains-mono-nerd-font"
  echo "Starship prompt|formula|starship"
  if [ "$WITH_EZA" -eq 1 ]; then echo "eza (ls with icons)|formula|eza"; fi
}

# prereq_present KIND PKG — also detects things installed without Homebrew
prereq_present() {
  case "$2" in
    iterm2) [ -d /Applications/iTerm.app ] || [ -d "$HOME/Applications/iTerm.app" ] ;;
    font-jetbrains-mono-nerd-font)
      brew_has --cask "$2" \
        || compgen -G "$HOME/Library/Fonts/JetBrainsMonoNerdFont*" >/dev/null \
        || compgen -G "/Library/Fonts/JetBrainsMonoNerdFont*" >/dev/null ;;
    *) command -v "$2" >/dev/null 2>&1 || brew_has "--$1" "$2" ;;
  esac
}

pending() { printf '    %s○%s %s\n' "$C_YELLOW" "$C_RESET" "$*"; }

install_brew() {
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [ -x /opt/homebrew/bin/brew ]; then eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then eval "$(/usr/local/bin/brew shellenv)"; fi
  command -v brew >/dev/null 2>&1 || die "Homebrew install failed — see https://brew.sh"
}

install_deps() {
  step "Prerequisites"
  local label kind pkg need_brew=0 missing=() cmds=()
  while IFS='|' read -r label kind pkg; do
    if prereq_present "$kind" "$pkg"; then
      ok "$label"
    else
      pending "$label ${C_DIM}— not installed${C_RESET}"
      missing+=("$label")
      if [ "$kind" = cask ]; then cmds+=("brew install --cask $pkg"); else cmds+=("brew install $pkg"); fi
    fi
  done <<EOF_PREREQS
$(prereqs)
EOF_PREREQS

  if [ ${#missing[@]} -eq 0 ]; then
    info "everything is already installed"
    return 0
  fi
  if ! command -v brew >/dev/null 2>&1; then
    need_brew=1
    pending "Homebrew ${C_DIM}— not installed (needed to install the above)${C_RESET}"
  fi

  echo
  info "To install:"
  [ "$need_brew" -eq 0 ] || info "  Homebrew  (https://brew.sh)"
  for pkg in "${cmds[@]}"; do info "  $pkg"; done

  if [ "$SKIP_BREW" -eq 1 ]; then
    warn "--skip-brew: install the above yourself, then open a new tab"
    return 0
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    return 0
  fi
  confirm "Install ${#missing[@]} missing item(s) now?" \
    || die "prerequisites are required (or rerun with --skip-brew to install them yourself)"

  [ "$need_brew" -eq 0 ] || install_brew
  for pkg in "${cmds[@]}"; do
    # word-splitting is intended: "brew install --cask name"
    # shellcheck disable=SC2086
    run $pkg
  done
  ok "prerequisites installed"
}

check_guid_conflict() {
  local guid="$1"
  command -v defaults >/dev/null 2>&1 || return 0
  # capture first: with pipefail, `defaults | grep -q` can fail on SIGPIPE after a match
  local bookmarks
  bookmarks="$(defaults read com.googlecode.iterm2 "New Bookmarks" 2>/dev/null || true)"
  if printf '%s' "$bookmarks" | grep -qi "$guid"; then
    warn "iTerm2 has a regular (imported) profile with the same GUID as this one."
    warn "Delete it in iTerm2 → Settings → Profiles, or iTerm will report a Dynamic Profiles error."
  fi
}

install_iterm_profile() {
  step "iTerm2 profile"
  local src="$PROFILES_DIR/$PROFILE/iterm.json"
  local dest="$DYN_DIR/devterm-$PROFILE.json"
  check_guid_conflict "$GUID"
  run mkdir -p "$DYN_DIR"
  if [ "$DRY_RUN" -eq 1 ]; then
    run "write $(pretty_path "$dest") (font size $FONT_SIZE)"
  else
    sed -E "s/(\"(Normal|Non Ascii) Font\": \"[^ \"]+) [0-9]+\"/\1 $FONT_SIZE\"/" "$src" > "$dest.tmp"
    mv "$dest.tmp" "$dest"
  fi
  ok "installed \"devterm · $DISPLAY_NAME\" (font size $FONT_SIZE)"
}

install_terminal_profile() {
  step "Terminal.app profile"
  local name="devterm · $DISPLAY_NAME" tmp i major found=0
  major="$(sw_vers -productVersion 2>/dev/null | cut -d. -f1)"
  if [ -n "$major" ] && [ "$major" -lt 26 ]; then
    warn "Terminal.app before macOS 26 has no 24-bit color, so prompt colors will be off."
    warn "iTerm2 is recommended on this macOS version."
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    run "import \"$name\" into Terminal.app (font size $FONT_SIZE)"
    return 0
  fi
  # Terminal names an imported profile after its file, and re-importing adds a
  # "<name> 1" duplicate instead of replacing it — so remove the old one first.
  if [ "$(defaults read com.apple.Terminal "Default Window Settings" 2>/dev/null || true)" = "$name" ]; then
    SET_TERMINAL_DEFAULT=1
  fi
  terminal_remove_profiles "$name" >/dev/null \
    || { warn "couldn't control Terminal.app — allow it in System Settings → Privacy & Security → Automation"; return 0; }
  tmp="$(mktemp -d)"
  cp "$PROFILES_DIR/$PROFILE/terminal.terminal" "$tmp/$name.terminal"
  open -a Terminal "$tmp/$name.terminal"   # imports it, and opens a window using it
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    osascript -e "tell application \"Terminal\" to exists settings set \"$name\"" 2>/dev/null \
      | grep -q true && { found=1; break; }
    sleep 0.5
  done
  if [ "$found" -eq 0 ]; then
    warn "Terminal.app didn't pick up the profile; open $tmp/$name.terminal by hand"
    return 0
  fi
  rm -f "$tmp/$name.terminal"; rmdir "$tmp"
  osascript -e "tell application \"Terminal\" to set font size of settings set \"$name\" to $FONT_SIZE"
  ok "installed \"$name\" (font size $FONT_SIZE)"
}

install_starship_config() {
  step "Starship prompt"
  local src="$PROFILES_DIR/$PROFILE/starship.toml"
  if [ -f "$STARSHIP_CFG" ] && ! head -n 1 "$STARSHIP_CFG" | grep -q '^# devterm'; then
    backup_file "$STARSHIP_CFG" "$BACKUP_DIR"
  fi
  run mkdir -p "$(dirname "$STARSHIP_CFG")"
  run cp "$src" "$STARSHIP_CFG"
  ok "wrote $(pretty_path "$STARSHIP_CFG")"
}

install_zsh_block() {
  step "Shell ($(pretty_path "$ZSHRC"))"
  [ -f "$ZSHRC" ] || run touch "$ZSHRC"
  if [ -f "$ZSHRC" ] && ! grep -qF "$MARK_START" "$ZSHRC"; then
    backup_file "$ZSHRC" "$BACKUP_DIR"
  fi
  remove_zsh_block "$ZSHRC"

  if [ -f "$ZSHRC" ]; then
    if grep -Eq '^[^#]*starship init' "$ZSHRC"; then
      warn "found another 'starship init' in your .zshrc — remove it to avoid double init"
    fi
    if grep -Eq '^[[:space:]]*ZSH_THEME="[^"]+"' "$ZSHRC"; then
      warn "Oh My Zsh theme detected — set ZSH_THEME=\"\" so Starship controls the prompt"
    fi
  fi

  local block
  block="$MARK_START
# Managed by devterm — changes inside this block are overwritten on reinstall.
if command -v starship >/dev/null 2>&1; then
  eval \"\$(starship init zsh)\"
fi"
  if [ "$WITH_EZA" -eq 1 ]; then
    block="$block
if command -v eza >/dev/null 2>&1; then
  alias ls='eza --icons --group-directories-first'
  alias ll='eza -l --icons --git --group-directories-first'
  alias la='eza -la --icons --git --group-directories-first'
  alias lt='eza --tree --level=2 --icons'
fi"
  fi
  block="$block
$MARK_END"

  if [ "$DRY_RUN" -eq 1 ]; then
    run "append devterm block to $(pretty_path "$ZSHRC")"
  else
    printf '\n%s\n' "$block" >> "$ZSHRC"
  fi
  ok "added Starship init$( [ "$WITH_EZA" -eq 1 ] && echo " and eza aliases")"
}

set_default_profile() {
  [ "$SET_DEFAULT" -eq 1 ] || [ "$SET_TERMINAL_DEFAULT" -eq 1 ] || return 0
  step "Default profile"
  if want terminal; then
    run osascript -e "tell application \"Terminal\"" \
      -e "set default settings to settings set \"devterm · $DISPLAY_NAME\"" \
      -e "set startup settings to settings set \"devterm · $DISPLAY_NAME\"" -e "end tell"
    ok "set \"devterm · $DISPLAY_NAME\" as Terminal.app's default profile"
  fi
  if [ "$SET_DEFAULT" -eq 0 ] || ! want iterm; then
    return 0
  elif iterm_running; then
    warn "iTerm2 is running and would overwrite this change on quit."
    warn "Quit iTerm2, run this from Terminal.app with --set-default, or use"
    warn "Settings → Profiles → Other Actions → Set as Default."
    return 0
  fi
  run defaults write com.googlecode.iterm2 "Default Bookmark Guid" -string "$GUID"
  ok "set \"devterm · $DISPLAY_NAME\" as iTerm2's default profile"
}

save_state() {
  run mkdir -p "$STATE_DIR"
  if [ "$DRY_RUN" -eq 0 ]; then
    echo "$PROFILE" > "$STATE_DIR/current"
    [ -d "$BACKUP_DIR" ] && echo "$BACKUP_DIR" > "$STATE_DIR/last_backup"
  fi
  return 0
}

main() {
  parse_args "$@"
  preflight
  printf '%sdevterm%s — developer terminal setup for macOS\n' "$C_BOLD" "$C_RESET"
  [ "$DRY_RUN" -eq 1 ] && printf '%s(dry run: nothing will be changed)%s\n' "$C_YELLOW" "$C_RESET"

  choose_profile
  choose_font_size
  GUID="$(conf_get "$PROFILES_DIR/$PROFILE/profile.conf" guid)"
  DISPLAY_NAME="$(conf_get "$PROFILES_DIR/$PROFILE/profile.conf" display)"
  BACKUP_DIR="$STATE_DIR/backups/$(date +%Y%m%d-%H%M%S)"

  SET_TERMINAL_DEFAULT=0

  install_deps
  if want iterm; then install_iterm_profile; fi
  if want terminal; then install_terminal_profile; fi
  install_starship_config
  install_zsh_block
  set_default_profile
  save_state

  step "Done"
  info "Profile: ${C_BOLD}devterm · $DISPLAY_NAME${C_RESET}  (font size $FONT_SIZE)"
  info "Next:"
  if want iterm; then
    info "  iTerm2:   Settings → Profiles → select \"devterm · $DISPLAY_NAME\""
    [ "$SET_DEFAULT" -eq 1 ] || info "            → Other Actions → Set as Default"
    info "            Optional: Settings → Appearance → General → Theme: Minimal"
  fi
  if want terminal && [ "$SET_DEFAULT" -eq 0 ]; then
    info "  Terminal: Settings → Profiles → select \"devterm · $DISPLAY_NAME\" → Default"
  fi
  info "  Then open a new tab (or run: exec zsh)"
}

main "$@"
