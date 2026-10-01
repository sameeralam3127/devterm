# Security Policy

devterm runs on your machine and edits your shell setup, so we take its safety
seriously. Thanks for helping keep it and its users safe.

## Supported versions

Only the latest commit on `main` is supported. Fixes are not backported.

## Reporting a vulnerability

**Please don't open a public issue for security problems.**

Report it privately through GitHub:
[**Report a vulnerability**](https://github.com/sameeralam3127/devterm/security/advisories/new)
(repo → _Security_ → _Report a vulnerability_).

Please include:

- what the problem is and what an attacker could do with it
- steps to reproduce (macOS version, terminal app, the exact command you ran)
- any suggested fix, if you have one

You can expect an acknowledgement within **3 business days** and a status
update within **7 days**. Once a fix is released, we'll credit you in the
advisory unless you'd rather stay anonymous.

## What's in scope

- `install.sh`, `uninstall.sh`, `doctor.sh`, `lib/common.sh` — anything that could run
  unintended commands, overwrite or delete files outside what the
  [README](README.md#what-it-changes) documents, or leak data
- the `curl … | bash` install path and how it downloads the repo
- generated profiles (`profiles/`) — for example, iTerm2 triggers or other
  settings that could run commands
- GitHub Actions workflows in `.github/workflows/`

Out of scope: vulnerabilities in Homebrew, iTerm2, Terminal.app, Starship or eza
themselves. Please report those to their maintainers.

## How devterm limits risk

- Every change to your files is listed in the README, and existing
  `~/.zshrc` and `starship.toml` files are backed up to `~/.devterm/backups/`
  before they're changed.
- `--dry-run` shows everything the installer would do without changing anything.
- The installer never uses `sudo`. Homebrew's own installer may ask for your
  password.
- The curl install downloads only from `github.com/sameeralam3127/devterm`
  over HTTPS. If you'd rather read the code first, clone the repo and run
  `./install.sh` instead.
