#!/usr/bin/env bash
# Record docs/demo-<theme>.gif — the real Starship prompt for each theme, in a
# throwaway sandbox (fake HOME, git repo, kube context) so nothing personal leaks.
# Needs: vhs, ffmpeg, starship, git, python3, JetBrains Mono Nerd Font.
#
# VHS only captures frames here; ffmpeg composes the GIF (window chrome +
# optimized palette), which also avoids VHS's encoder breaking on newer ffmpeg.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO_DIR/docs"
for cmd in vhs ffmpeg starship git python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "error: $cmd is required" >&2; exit 1; }
done

SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
H="$SANDBOX/home"
mkdir -p "$H/projects/api-service" "$H/projects/platform-deploy/.terraform" "$H/.kube" "$SANDBOX/zdot"

cat > "$H/.kube/config" <<'YAML'
apiVersion: v1
kind: Config
current-context: prod-eu-1
contexts:
  - name: prod-eu-1
    context: {cluster: prod-eu-1, user: sre, namespace: payments}
clusters:
  - name: prod-eu-1
    cluster: {server: "https://127.0.0.1:6443"}
users:
  - name: sre
    user: {}
YAML

# starship hides the AWS segment without credentials; these are AWS's documented example keys
mkdir -p "$H/.aws"
printf '[profile staging]\nregion = eu-west-1\n' > "$H/.aws/config"
printf '[staging]\naws_access_key_id = AKIAIOSFODNN7EXAMPLE\naws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n' \
  > "$H/.aws/credentials"

git_quiet() { git -c user.name=devterm -c user.email=demo@devterm.invalid -c init.defaultBranch=main "$@" >/dev/null 2>&1; }
(
  cd "$H/projects/api-service"
  printf '[project]\nname = "api-service"\n' > pyproject.toml
  printf 'print("hello")\n' > app.py
  git_quiet init && git_quiet add . && git_quiet commit -m init
  git_quiet checkout -b feat/auth
  printf 'print("hello, auth")\n' > app.py
)
(
  cd "$H/projects/platform-deploy"
  printf 'apiVersion: v2\nname: platform\nversion: 0.1.0\n' > Chart.yaml
  printf 'terraform {}\n' > main.tf
  printf 'staging' > .terraform/environment
  git_quiet init && git_quiet add . && git_quiet commit -m init
)
cat > "$SANDBOX/zdot/.zshrc" <<'ZSH'
setopt interactive_comments
PROMPT_EOL_MARK=""
eval "$(starship init zsh)"
ZSH

mkdir -p "$OUT"
for theme in "$REPO_DIR"/themes/*.json; do
  name="$(basename "$theme" .json)"
  python3 - "$theme" > "$SANDBOX/vhs-theme.json" <<'PY'
import json, sys
t = json.load(open(sys.argv[1]))
keys = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
out = {"name": t["display"], "background": t["background"], "foreground": t["foreground"],
       "cursor": t["cursor"], "selection": t["selection"]}
for i, k in enumerate(keys):
    out[k] = t["ansi"][i]
    out["bright" + k.capitalize()] = t["ansi"][i + 8]
print(json.dumps(out))
PY
  cat > "$SANDBOX/demo.tape" <<TAPE
Output "$SANDBOX/frames-$name/"
Set Shell zsh
Set FontFamily "JetBrainsMono Nerd Font Mono"
Set FontSize 18
Set Width 1100
Set Height 460
Set TypingSpeed 50ms
Set Theme $(cat "$SANDBOX/vhs-theme.json")
Env HOME "$H"
Env STARSHIP_CONFIG "$REPO_DIR/profiles/$name/starship.toml"
Env KUBECONFIG "$H/.kube/config"
Env TZ "UTC"

Hide
Type "source $SANDBOX/zdot/.zshrc && cd ~/projects/api-service && clear"
Enter
Sleep 1.5s
Show

Sleep 2.5s
Type "cd ../platform-deploy"
Sleep 300ms
Enter
Sleep 2.5s
Type "export AWS_PROFILE=staging"
Sleep 300ms
Enter
Sleep 2.5s
Type "sleep 3"
Enter
Sleep 5s
Type "false"
Enter
Sleep 3s
TAPE
  echo "recording ${name}..."
  vhs "$SANDBOX/demo.tape" >/dev/null 2>&1
  bg="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["background"])' "$theme")"
  dot="format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-6.5,Y-6.5),6.5),255,0)'"
  ffmpeg -loglevel error -y \
    -framerate 50 -i "$SANDBOX/frames-$name/frame-text-%05d.png" \
    -framerate 50 -i "$SANDBOX/frames-$name/frame-cursor-%05d.png" \
    -f lavfi -i "color=c=#ff5f56:s=14x14:r=50" \
    -f lavfi -i "color=c=#ffbd2e:s=14x14:r=50" \
    -f lavfi -i "color=c=#27c93f:s=14x14:r=50" \
    -filter_complex "
      [2]${dot}[r]; [3]${dot}[y]; [4]${dot}[g];
      [0][1]overlay,pad=w=iw+48:h=ih+84:x=24:y=60:color=${bg}[win];
      [win][r]overlay=x=24:y=22:shortest=1[w1];
      [w1][y]overlay=x=46:y=22:shortest=1[w2];
      [w2][g]overlay=x=68:y=22:shortest=1,fps=20,
        split[a][b]; [a]palettegen=stats_mode=diff[p];
        [b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
    "$OUT/demo-$name.gif"
done
ls -lh "$OUT"/demo-*.gif
