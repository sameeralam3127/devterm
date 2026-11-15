# devterm Guard — context badges and confirmations for destructive commands.
# This file is sourced from the managed block in ~/.zshrc.

typeset -g DEVTERM_GUARD="${DEVTERM_GUARD:-1}"
typeset -g DEVTERM_GUARD_UNLOCK_UNTIL="${DEVTERM_GUARD_UNLOCK_UNTIL:-0}"
typeset -g _DEVTERM_CONTEXT_SIGNATURE=""
typeset -g _DEVTERM_CONTEXT_VALID=0
typeset -g _DEVTERM_PRODUCTION_CONTEXT=""
typeset -g _DEVTERM_LAST_BADGE=""

_devterm_context_refresh() {
  local signature line
  signature="$PWD|${AWS_PROFILE:-}|${AWS_DEFAULT_PROFILE:-}|${KUBECONFIG:-}|${TF_WORKSPACE:-}"
  if [[ "$signature" == "$_DEVTERM_CONTEXT_SIGNATURE" && "$_DEVTERM_CONTEXT_VALID" == "1" ]]; then
    return 0
  fi
  _DEVTERM_CONTEXT_SIGNATURE="$signature"
  line="$(command devterm context --tsv 2>/dev/null)" || line=""
  local -a fields
  fields=("${(@s:	:)line}")
  _DEVTERM_PRODUCTION_CONTEXT="${fields[7]:-}"
  _DEVTERM_CONTEXT_VALID=1
}

_devterm_badge() {
  _devterm_context_refresh
  local badge=""
  if [[ -n "$_DEVTERM_PRODUCTION_CONTEXT" ]]; then
    badge="PRODUCTION · $_DEVTERM_PRODUCTION_CONTEXT"
  fi
  [[ "$badge" == "$_DEVTERM_LAST_BADGE" ]] && return 0
  local previous="$_DEVTERM_LAST_BADGE"
  _DEVTERM_LAST_BADGE="$badge"

  if [[ "${TERM_PROGRAM:-}" == "iTerm.app" ]]; then
    local encoded
    encoded="$(printf '%s' "$badge" | base64 | tr -d '\n')"
    printf '\e]1337;SetBadgeFormat=%s\a' "$encoded"
  fi
  if [[ -n "$badge" ]]; then
    printf '\e]0;%s\a' "$badge"
  elif [[ -n "$previous" ]]; then
    printf '\e]0;%s\a' "${PWD##*/}"
  fi
}

_devterm_is_production() {
  local value
  for value in "$@"; do
    [[ -n "$value" ]] && command devterm is-production "$value" >/dev/null 2>&1 && return 0
  done
  return 1
}

_devterm_arg_value() {
  local wanted="$1"
  shift
  local previous="" arg
  for arg in "$@"; do
    if [[ "$previous" == "$wanted" ]]; then
      printf '%s' "$arg"
      return 0
    fi
    case "$arg" in
      "$wanted"=*) printf '%s' "${arg#*=}"; return 0 ;;
    esac
    previous="$arg"
  done
}

_devterm_target_context() {
  local tool="$1"
  shift
  local override=""
  case "$tool" in
    kubectl) override="$(_devterm_arg_value --context "$@")" ;;
    aws) override="$(_devterm_arg_value --profile "$@")" ;;
  esac
  if [[ -n "$override" ]]; then
    printf '%s' "$override"
    return 0
  fi
  _DEVTERM_CONTEXT_SIGNATURE=""
  _DEVTERM_CONTEXT_VALID=0
  _devterm_context_refresh
  printf '%s' "$_DEVTERM_PRODUCTION_CONTEXT"
}

_devterm_is_risky() {
  local tool="$1" joined=" $* "
  case "$tool" in
    kubectl)
      [[ "$joined" == *" delete "* || "$joined" == *" drain "* || \
         ( "$joined" == *" replace "* && \
           ( "$joined" == *" --force "* || "$joined" == *" --force="* ) ) ]]
      ;;
    terraform)
      [[ "$joined" == *" destroy "* || "$joined" == *" state rm "* || \
         "$joined" == *" force-unlock "* ]]
      ;;
    aws)
      [[ "$joined" == *" terminate-instances "* || "$joined" == *" delete-cluster "* || \
         "$joined" == *" delete-db-instance "* || "$joined" == *" delete-stack "* ]]
      ;;
    git)
      [[ "$joined" == *" push "* && ( "$joined" == *" --force "* || "$joined" == *" -f "* || \
         "$joined" == *" --force="* || "$joined" == *" --force-with-lease "* || \
         "$joined" == *" --force-with-lease="* ) ]]
      ;;
    *) return 1 ;;
  esac
}

_devterm_guard_confirm() {
  local tool="$1"
  shift
  [[ "$DEVTERM_GUARD" == "1" ]] || return 0
  _devterm_is_risky "$tool" "$@" || return 0

  local now context expected reply
  now="$(date +%s)"
  (( DEVTERM_GUARD_UNLOCK_UNTIL > now )) && return 0
  context="$(_devterm_target_context "$tool" "$@")"

  # Force-push protection applies everywhere. Infrastructure protection is
  # intentionally limited to production-like contexts to avoid confirmation fatigue.
  if [[ "$tool" == "git" ]]; then
    expected="force"
  elif _devterm_is_production "$context"; then
    expected="$context"
  else
    return 0
  fi

  print -u2 -- ""
  print -u2 -- "devterm Guard: blocked a destructive $tool command"
  print -u2 -- "Target: ${context:-Git remote}"
  # Read from the terminal so a pipeline such as `cat objects.yaml | kubectl
  # delete -f -` keeps its standard input intact.
  read -r "reply?Type '$expected' to continue: " < /dev/tty
  if [[ "$reply" != "$expected" ]]; then
    print -u2 -- "Cancelled."
    return 1
  fi
}

devterm-unlock() {
  local minutes="${1:-5}"
  case "$minutes" in
    *[!0-9]*|"") print -u2 -- "usage: devterm-unlock [minutes]"; return 2 ;;
  esac
  DEVTERM_GUARD_UNLOCK_UNTIL=$(( $(date +%s) + minutes * 60 ))
  print -- "devterm Guard unlocked for $minutes minute(s) in this shell."
}

devterm-lock() {
  DEVTERM_GUARD_UNLOCK_UNTIL=0
  print -- "devterm Guard locked."
}

kubectl() {
  _devterm_guard_confirm kubectl "$@" || return $?
  command kubectl "$@"
  local status=$?
  _DEVTERM_CONTEXT_SIGNATURE=""
  _DEVTERM_CONTEXT_VALID=0
  return $status
}

terraform() {
  _devterm_guard_confirm terraform "$@" || return $?
  command terraform "$@"
}

aws() {
  _devterm_guard_confirm aws "$@" || return $?
  command aws "$@"
}

git() {
  _devterm_guard_confirm git "$@" || return $?
  command git "$@"
}

autoload -Uz add-zsh-hook
add-zsh-hook precmd _devterm_badge
