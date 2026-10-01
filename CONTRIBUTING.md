# Contributing to devterm

Thanks for helping out! Bug fixes, new themes and docs improvements are all welcome.

## Before you start

- **Bugs:** open an issue with your macOS version, terminal app (iTerm2 or
  Terminal.app) and the output of `./install.sh --dry-run`.
- **New features:** open an issue first so we can agree on the approach before
  you spend time on it.
- **Security problems:** don't open an issue — see [SECURITY.md](SECURITY.md).

## Development setup

```bash
git clone https://github.com/sameeralam3127/devterm.git
cd devterm
brew install shellcheck        # for `make lint`
```

Everything else uses tools that ship with macOS (`bash` 3.2, `python3`, `osascript`).

| Command        | What it does                                             |
| -------------- | -------------------------------------------------------- |
| `make lint`    | ShellCheck all scripts                                   |
| `make build`   | Regenerate `profiles/` from `themes/`                    |
| `make check`   | Fail if `profiles/` is out of date (CI runs this)        |
| `make doctor`  | Check your own setup (read-only)                         |
| `make demo`    | Re-record `docs/demo-*.gif` (needs `brew install vhs ffmpeg`) |

### Testing without touching your own setup

Point `HOME` at a scratch folder and skip Homebrew:

```bash
mkdir -p /tmp/devterm-home
HOME=/tmp/devterm-home ./install.sh -p midnight --app iterm --skip-brew --yes
HOME=/tmp/devterm-home ./uninstall.sh --yes
```

Terminal.app profiles are **not** stored under `HOME`, so a scratch `HOME` doesn't
isolate them: `--app terminal` imports into your real Terminal.app, and
`uninstall.sh` removes every real `devterm · …` Terminal.app profile. Use
`--app iterm` for sandboxed tests, or `--dry-run`.

## Making changes

1. Fork the repo and create a branch from `main`: `git checkout -b fix/short-description`
2. Make your change. Keep the scripts **bash 3.2 compatible**, because that's what
   macOS ships: no associative arrays, `mapfile`, `${var,,}` or `|&`.
3. If you changed `themes/`, `templates/` or `tools/build.py`, run `make build`
   and commit the regenerated `profiles/`.
4. Run `make lint check` and try `./install.sh --dry-run`.
5. Update the README if you changed behavior, options or what files are touched.

### Adding a theme

See [Adding a theme](README.md#adding-a-theme). Please include the generated
profiles and a recorded GIF (`make demo`) in the PR.

## Pull requests

- Fill in the PR template, including how you tested.
- Keep PRs focused: one fix or feature per PR.
- CI must pass: ShellCheck, a check that generated files are up to date, and
  macOS dry runs of install and uninstall.
- A maintainer must approve the PR before it can be merged into `main`.
- **First-time contributors:** GitHub Actions won't run on your PR until a
  maintainer approves the workflow run. This protects the repo's CI from
  untrusted code, so please be patient.

### Commit messages

Use the imperative mood and keep the first line under ~70 characters:

```
Add Terminal.app profile export
Fix zshrc block removal when end marker is missing
```

## Code of conduct

Be kind and constructive. Harassment or personal attacks aren't tolerated.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
