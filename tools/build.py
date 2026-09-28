#!/usr/bin/env python3
"""Generate profiles/<theme>/ from themes/*.json.

Each theme produces:
  profiles/<name>/iterm.json     iTerm2 Dynamic Profile
  profiles/<name>/terminal.terminal  macOS Terminal.app profile
  profiles/<name>/starship.toml  Starship prompt config
  profiles/<name>/profile.conf   metadata read by install.sh

Usage:
  python3 tools/build.py          # regenerate everything
  python3 tools/build.py --check  # exit 1 if generated files are out of date (CI)
"""
import json
import plistlib
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEMES = ROOT / "themes"
PROFILES = ROOT / "profiles"
TEMPLATE = ROOT / "templates" / "starship.toml.tmpl"

FONT = "JetBrainsMonoNFM-Regular"
FONT_SIZE = 16
NAMESPACE = uuid.UUID("6f1d2c3b-9a8e-4d7c-b6a5-0e1f2d3c4b5a")  # stable GUIDs per theme
REQUIRED = ["name", "display", "description", "background", "foreground",
            "cursor", "selection", "muted", "ansi"]


def color(hex_str, alpha=1.0):
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return {"Red Component": round(r, 4), "Green Component": round(g, 4),
            "Blue Component": round(b, 4), "Alpha Component": alpha, "Color Space": "sRGB"}


def status_bar():
    adv = {"algorithm": 0, "remove empty components": True,
           "font": f"{FONT} 13", "auto-rainbow style": 3}

    def comp(cls, prio, extra=None):
        knobs = {"base: priority": prio, "base: compression resistance": 1}
        knobs.update(extra or {})
        return {"class": cls, "configuration": {
            "knobs": knobs, "layout advanced configuration dictionary value": adv}}

    return {"components": [
        comp("iTermStatusBarWorkingDirectoryComponent", 10),
        comp("iTermStatusBarGitComponent", 9),
        comp("iTermStatusBarHostnameComponent", 7),
        comp("iTermStatusBarCPUUtilizationComponent", 5),
        comp("iTermStatusBarMemoryUtilizationComponent", 5),
        comp("iTermStatusBarNetworkUtilizationComponent", 3),
        comp("iTermStatusBarClockComponent", 6, {"format": "HH:mm"}),
    ], "advanced configuration": adv}


def iterm_profile(t, guid):
    a = t["ansi"]
    p = {
        "Name": f"devterm · {t['display']}",
        "Guid": guid,
        "Tags": ["devterm"],
        # Font & text
        "Normal Font": f"{FONT} {FONT_SIZE}", "Non Ascii Font": f"{FONT} {FONT_SIZE}",
        "Use Non-ASCII Font": False, "ASCII Ligatures": True, "Non-ASCII Ligatures": True,
        "Use Bold Font": True, "Use Bright Bold": True, "Use Italic Font": True,
        "Horizontal Spacing": 1.0, "Vertical Spacing": 1.15, "Unicode Version": 9,
        "Side Margins": 16, "Top Bottom Margins": 12,
        # Window & session
        "Columns": 150, "Rows": 42, "Custom Directory": "Recycle",
        "Close Sessions On End": True, "Terminal Type": "xterm-256color",
        "Unlimited Scrollback": True, "Scrollback Lines": 0, "Mouse Reporting": True,
        "Load Shell Integration Automatically": True,
        # Cursor & bell
        "Cursor Type": 2, "Blinking Cursor": True, "Use Cursor Guide": True,
        "Silence Bell": True, "Visual Bell": True, "Flashing Bell": False,
        # Keys: left Option = Meta, right Option = special characters
        "Option Key Sends": 2, "Right Option Key Sends": 0,
        "Keyboard Map": {
            "0xf702-0x280000": {"Action": 10, "Text": "b"},     # ⌥←  word back
            "0xf703-0x280000": {"Action": 10, "Text": "f"},     # ⌥→  word forward
            "0xf702-0x300000": {"Action": 11, "Text": "0x01"},  # ⌘←  line start
            "0xf703-0x300000": {"Action": 11, "Text": "0x05"},  # ⌘→  line end
            "0x7f-0x80000": {"Action": 11, "Text": "0x17"},     # ⌥⌫  delete word
            "0x7f-0x100000": {"Action": 11, "Text": "0x15"},    # ⌘⌫  delete line
        },
        # ⌘-click paths → open in the best available editor
        "Semantic History": {"action": "best editor", "editor": "com.microsoft.VSCode", "text": ""},
        # Log-level highlighting
        "Triggers": [
            {"regex": r"\b(ERROR|FATAL|CRITICAL|PANIC|Error|Failed|FAILED)\b",
             "action": "HighlightTrigger", "parameter": f"{{{a[1]},}}", "partial": True},
            {"regex": r"\b(WARN|WARNING|Warning|CrashLoopBackOff|OOMKilled|Evicted|Pending)\b",
             "action": "HighlightTrigger", "parameter": f"{{{a[3]},}}", "partial": True},
            {"regex": r"\b(SUCCESS|PASSED|Running|Ready|Completed)\b",
             "action": "HighlightTrigger", "parameter": f"{{{a[2]},}}", "partial": True},
        ],
        "Show Status Bar": True,
        "Status Bar Layout": status_bar(),
        # Colors
        "Background Color": color(t["background"]), "Foreground Color": color(t["foreground"]),
        "Bold Color": color(t["foreground"]),
        "Cursor Color": color(t["cursor"]), "Cursor Text Color": color(t["background"]),
        "Selection Color": color(t["selection"]), "Selected Text Color": color(t["foreground"]),
        "Link Color": color(a[4]), "Cursor Guide Color": color(t["selection"], 0.35),
        "Transparency": t.get("transparency", 0.0), "Blur": t.get("blur", False),
        "Blur Radius": 18, "Minimum Contrast": 0.0,
    }
    for i, h in enumerate(a):
        p[f"Ansi {i} Color"] = color(h)
    return {"Profiles": [p]}


def _archive(obj, classes):
    """NSKeyedArchiver-encode a flat object dict, as Terminal.app stores colors and fonts."""
    objects = ["$null", None]
    root = {}
    for k, v in obj.items():
        if isinstance(v, str):  # strings are archived as separate objects, referenced by UID
            objects.append(v)
            v = plistlib.UID(len(objects) - 1)
        root[k] = v
    root["$class"] = plistlib.UID(len(objects))
    objects[1] = root
    objects.append({"$classname": classes[0], "$classes": classes})
    return plistlib.dumps({
        "$archiver": "NSKeyedArchiver", "$version": 100000,
        "$top": {"root": plistlib.UID(1)}, "$objects": objects,
    }, fmt=plistlib.FMT_BINARY)


def ns_color(hex_str):
    h = hex_str.lstrip("#")
    rgb = " ".join(f"{int(h[i:i + 2], 16) / 255:.6f}" for i in (0, 2, 4))
    # NSColorSpace 2 = device RGB, which Terminal renders as sRGB hex values
    return _archive({"NSColorSpace": 2, "NSRGB": rgb.encode() + b"\0"}, ["NSColor", "NSObject"])


def ns_font(name, size):
    return _archive({"NSName": name, "NSSize": float(size), "NSfFlags": 16}, ["NSFont", "NSObject"])


TERMINAL_ANSI = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]


def terminal_profile(t):
    """macOS Terminal.app profile (.terminal). Triggers/status bar are iTerm2-only."""
    a = t["ansi"]
    p = {
        "name": f"devterm · {t['display']}", "type": "Window Settings",
        "ProfileCurrentVersion": 2.07,
        "Font": ns_font(FONT, FONT_SIZE), "FontAntialias": True,
        "FontWidthSpacing": 1.0, "FontHeightSpacing": 1.15, "UseBrightBold": True,
        "columnCount": 150, "rowCount": 42,
        "CursorType": 0, "CursorBlink": True,        # 0 = block
        "useOptionAsMetaKey": True, "shellExitAction": 1,  # close if the shell exited cleanly
        "Bell": False, "VisualBell": True,
        "BackgroundColor": ns_color(t["background"]), "TextColor": ns_color(t["foreground"]),
        "TextBoldColor": ns_color(t["foreground"]), "CursorColor": ns_color(t["cursor"]),
        "SelectionColor": ns_color(t["selection"]),
    }
    for i, name in enumerate(TERMINAL_ANSI):
        p[f"ANSI{name}Color"] = ns_color(a[i])
        p[f"ANSIBright{name}Color"] = ns_color(a[i + 8])
    return plistlib.dumps(p).decode()


def starship(t, template):
    a = t["ansi"]
    subs = {"display": t["display"], "red": a[1], "green": a[2], "yellow": a[3],
            "blue": a[4], "purple": a[5], "cyan": a[6], "muted": t["muted"]}
    out = template
    for k, v in subs.items():
        out = out.replace(f"@@{k}@@", v)
    if "@@" in out:
        raise ValueError(f"unresolved placeholder in template for theme {t['name']}")
    return out


def render_all():
    template = TEMPLATE.read_text(encoding="utf-8")
    files = {}
    for path in sorted(THEMES.glob("*.json")):
        t = json.loads(path.read_text(encoding="utf-8"))
        missing = [k for k in REQUIRED if k not in t]
        if missing:
            raise ValueError(f"{path.name}: missing keys {missing}")
        if len(t["ansi"]) != 16:
            raise ValueError(f"{path.name}: 'ansi' must have 16 colors")
        name = t["name"]
        guid = str(uuid.uuid5(NAMESPACE, name)).upper()
        d = PROFILES / name
        files[d / "iterm.json"] = json.dumps(iterm_profile(t, guid), indent=2, ensure_ascii=False) + "\n"
        files[d / "terminal.terminal"] = terminal_profile(t)
        files[d / "starship.toml"] = starship(t, template)
        files[d / "profile.conf"] = (
            f"name={name}\ndisplay={t['display']}\n"
            f"description={t['description']}\nguid={guid}\n")
    return files


def main():
    check = "--check" in sys.argv
    files = render_all()
    stale = []
    for path, content in files.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            stale.append(path.relative_to(ROOT))
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    if check and stale:
        print("Generated files are out of date. Run: python3 tools/build.py")
        for s in stale:
            print(f"  {s}")
        sys.exit(1)
    print(f"{'Checked' if check else 'Built'} {len(files) // 4} profile(s)"
          + ("" if check else f", {len(stale)} file(s) updated"))


if __name__ == "__main__":
    main()
