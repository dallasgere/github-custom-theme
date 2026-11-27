#!/usr/bin/env python3
"""Generate all 18 GitHub Zed themes (9 official variants + 9 unbordered) in themes/github.json.

Usage: python3 scripts/build.py [path/to/source]

Reads the official built VS Code themes from primer/github-vscode-theme in source/
and maps every workbench color and TextMate syntax scope 1:1 into Zed's theme schema,
plus an unbordered variant for each theme.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "source"
OUT = ROOT / "themes"
SCHEMA = "https://zed.dev/schema/themes/v0.2.0.json"
AUTHOR = "Dallas Gere"
TRANSPARENT = "#00000000"

# Ordered list: (source filename stem, display name, Zed appearance)
VARIANTS = [
    ("dark-default", "GitHub Dark Default", "dark"),
    ("dark-dimmed", "GitHub Dark Dimmed", "dark"),
    ("dark-high-contrast", "GitHub Dark High Contrast", "dark"),
    ("dark-colorblind", "GitHub Dark Colorblind", "dark"),
    ("dark", "GitHub Dark", "dark"),
    ("light-default", "GitHub Light Default", "light"),
    ("light-high-contrast", "GitHub Light High Contrast", "light"),
    ("light-colorblind", "GitHub Light Colorblind", "light"),
    ("light", "GitHub Light", "light"),
]

# Zed tree-sitter syntax capture -> representative TextMate scope stacks (outermost first).
SYNTAX_SCOPES = {
    "attribute": [["meta.tag", "entity.other.attribute-name"]],
    "boolean": [["constant.language.boolean.true"], ["constant.language"]],
    "comment": [["comment.line.double-slash"], ["comment"]],
    "comment.doc": [["comment.block.documentation"], ["comment"]],
    "constant": [["variable.other.constant"], ["constant"]],
    "constant.builtin": [["constant.language.null"], ["constant.language"]],
    "constructor": [["entity.name.type.class"], ["entity.name.class"], ["support.class"]],
    "diff.minus": [["markup.deleted"]],
    "diff.plus": [["markup.inserted"]],
    "embedded": [["meta.embedded"]],
    "emphasis": [["markup.italic"]],
    "emphasis.strong": [["markup.bold"]],
    "enum": [["entity.name.type.enum"], ["entity.name.type"]],
    "function": [["entity.name.function"]],
    "function.builtin": [["support.function"], ["entity.name.function"]],
    "function.call": [["meta.function-call", "entity.name.function"], ["entity.name.function"]],
    "function.definition": [["entity.name.function"]],
    "function.method": [["entity.name.function.member"], ["entity.name.function"]],
    "function.method.call": [["meta.function-call", "entity.name.function"], ["entity.name.function"]],
    "function.special": [["support.function.macro"], ["entity.name.function"]],
    "keyword": [["keyword"]],
    "keyword.conditional": [["keyword.control.conditional"], ["keyword.control"], ["keyword"]],
    "keyword.control": [["keyword.control"], ["keyword"]],
    "keyword.coroutine": [["keyword.control.flow"], ["storage.modifier.async"], ["keyword"]],
    "keyword.directive": [["meta.preprocessor"], ["keyword.control.directive"], ["keyword"]],
    "keyword.exception": [["keyword.control.trycatch"], ["keyword.control"], ["keyword"]],
    "keyword.export": [["keyword.control.export"], ["keyword.control"], ["keyword"]],
    "keyword.function": [["storage.type.function"], ["storage.type"], ["keyword"]],
    "keyword.import": [["keyword.control.import"], ["keyword.control"], ["keyword"]],
    "keyword.modifier": [["storage.modifier"], ["keyword"]],
    "keyword.operator": [["keyword.operator"], ["keyword"]],
    "keyword.repeat": [["keyword.control.loop"], ["keyword.control"], ["keyword"]],
    "keyword.return": [["keyword.control.flow"], ["keyword.control"], ["keyword"]],
    "keyword.storage": [["storage.type"], ["storage"]],
    "keyword.type": [["storage.type"], ["keyword"]],
    "label": [["entity.name.label"], ["variable"]],
    "link_text": [["markup.underline.link"], ["string.other.link"]],
    "link_uri": [["markup.underline.link"], ["constant.other.reference.link"]],
    "namespace": [["entity.name.namespace"], ["entity.name.type"]],
    "number": [["constant.numeric"]],
    "operator": [["keyword.operator"]],
    "preproc": [["meta.preprocessor"], ["keyword"]],
    "primary": [["source"]],
    "property": [["variable.other.property"], ["support.type.property-name"], ["variable.other.object.property"]],
    "property.json_key": [["support.type.property-name.json"], ["entity.name.tag"]],
    "punctuation": [["punctuation"]],
    "punctuation.bracket": [["meta.brace.round"], ["punctuation.section"], ["punctuation"]],
    "punctuation.delimiter": [["punctuation.separator"], ["punctuation"]],
    "punctuation.list_marker": [["punctuation.definition.list.begin.markdown"], ["markup.list"]],
    "punctuation.markup": [["punctuation.definition.heading.markdown"], ["punctuation"]],
    "punctuation.special": [["punctuation.definition.template-expression.begin"], ["punctuation"]],
    "selector": [["entity.name.tag.css"], ["entity.other.attribute-name.class.css"]],
    "selector.pseudo": [["entity.other.attribute-name.pseudo-class.css"], ["entity.name.tag"]],
    "string": [["string.quoted.double"], ["string"]],
    "string.doc": [["string.quoted.docstring"], ["string"]],
    "string.escape": [["constant.character.escape"], ["string"]],
    "string.regex": [["string.regexp"], ["source.regexp"]],
    "string.special": [["string.template"], ["string"]],
    "string.special.symbol": [["constant.other.symbol"], ["constant"]],
    "tag": [["entity.name.tag"]],
    "tag.doctype": [["meta.tag.sgml.doctype"], ["entity.name.tag"]],
    "text.literal": [["markup.inline.raw"], ["string"]],
    "title": [["markup.heading"], ["entity.name.section"]],
    "type": [["entity.name.type"], ["support.type"]],
    "type.builtin": [["support.type.primitive"], ["support.type"], ["storage.type"]],
    "type.interface": [["entity.name.type.interface"], ["entity.name.type"]],
    "type.parameter": [["entity.name.type.parameter"], ["entity.name.type"]],
    "variable": [["variable.other.readwrite"], ["variable"]],
    "variable.member": [["variable.other.property"], ["variable.other.object.property"], ["variable"]],
    "variable.parameter": [["variable.parameter"], ["variable"]],
    "variable.special": [["variable.language.this"], ["variable.language"]],
    "variant": [["variable.other.enummember"], ["constant"]],
}


def norm_color(val):
    if not val or not isinstance(val, str) or not val.startswith("#"):
        return None
    h = val[1:].lower()
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8) or not re.fullmatch(r"[0-9a-f]+", h):
        return None
    return "#" + h


def with_alpha(val, alpha):
    c = norm_color(val)
    return (c[:7] + alpha) if c else None


def parse_rules(theme):
    rules = []
    for idx, rule in enumerate(theme.get("tokenColors", [])):
        settings = rule.get("settings", {})
        fg = norm_color(settings.get("foreground"))
        fs = settings.get("fontStyle")
        if not fg and not fs:
            continue
        scopes = rule.get("scope", [])
        if isinstance(scopes, str):
            scopes = [s.strip() for s in scopes.split(",") if s.strip()]
        for sel in scopes:
            parts = [p for p in sel.split() if p]
            if parts:
                rules.append((parts, idx, fg, fs))
    return rules


def scope_matches(prefix, scope):
    return scope == prefix or scope.startswith(prefix + ".")


def match_selector(parts, stack):
    """Match a TextMate selector `parts` against a `stack` of scopes (outermost first)."""
    if not parts or not stack:
        return None
    if not scope_matches(parts[-1], stack[-1]):
        return None
    # Match remaining ancestor parts right-to-left.
    si = len(stack) - 2
    for pi in range(len(parts) - 2, -1, -1):
        while si >= 0 and not scope_matches(parts[pi], stack[si]):
            si -= 1
        if si < 0:
            return None
        si -= 1
    # Specificity tuple: (leaf depth, selector length, total parts length)
    return (len(parts[-1].split(".")), len(parts), sum(len(p) for p in parts))


def resolve_token(rules, stacks, fallback_fg):
    best_fg = None
    best_fg_key = None
    best_fs = None
    best_fs_key = None
    for stack in stacks:
        for parts, idx, fg, fs in rules:
            spec = match_selector(parts, stack)
            if spec is None:
                continue
            key = (spec, idx)
            if fg and (best_fg_key is None or key > best_fg_key):
                best_fg, best_fg_key = fg, key
            if fs is not None and (best_fs_key is None or key > best_fs_key):
                best_fs, best_fs_key = fs, key
        if best_fg is not None:
            break
    font_style = "italic" if (best_fs and "italic" in best_fs) else "normal"
    font_weight = 700 if (best_fs and "bold" in best_fs) else 400
    return {
        "color": best_fg or fallback_fg,
        "font_style": font_style,
        "font_weight": font_weight,
    }


def build_syntax(theme, c):
    rules = parse_rules(theme)
    fallback = norm_color(c.get("editor.foreground")) or norm_color(c.get("foreground"))
    syntax = {}
    for name, stacks in SYNTAX_SCOPES.items():
        syntax[name] = resolve_token(rules, stacks, fallback)
    hint_col = norm_color(c.get("editorInlayHint.foreground")) or norm_color(c.get("editorLineNumber.foreground"))
    pred_col = norm_color(c.get("editorGhostText.foreground")) or norm_color(c.get("editorLineNumber.foreground"))
    if hint_col:
        syntax["hint"] = {"color": hint_col, "font_style": "normal", "font_weight": 400}
    if pred_col:
        syntax["predictive"] = {"color": pred_col, "font_style": "normal", "font_weight": 400}
    return dict(sorted(syntax.items()))


def blend(fg, alpha, bg):
    """Straight sRGB mix: alpha of fg over bg."""
    a = [int(fg[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * alpha + y * (1 - alpha)):02x}" for x, y in zip(a, b))




def subheader_bg(editor_bg, fg):
    """Clearly distinct multibuffer / git diff file header background."""
    def _mix(a, t, b):
        ca = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
        cb = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{round(x * t + y * (1 - t)):02x}" for x, y in zip(ca, cb))
    is_light = int(editor_bg[1:3], 16) > 128
    # Lift cleanly on dark themes (14% toward fg), darken slightly on light themes (10% toward fg).
    return _mix(fg[:7], 0.10 if is_light else 0.14, editor_bg[:7])


def visible_invisible(fg, selection, editor_bg):
    """Compute editor.invisible so whitespace dots stay clearly legible over selected text."""
    def _mix(a, t, b):
        ca = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
        cb = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{round(x * t + y * (1 - t)):02x}" for x, y in zip(ca, cb))
    sel = selection or editor_bg
    if len(sel) == 9:
        sel = _mix(sel[:7], int(sel[7:9], 16) / 255, editor_bg[:7])
    target = editor_bg[:7] if abs(int(sel[1:3], 16) - int(fg[1:3], 16)) < 60 else fg[:7]
    return _mix(target, 0.46, sel[:7])


def build_style(theme, appearance, unbordered=False):
    c = {k: norm_color(v) for k, v in theme.get("colors", {}).items()}
    g = lambda *keys: next((c[k] for k in keys if c.get(k)), None)

    editor_bg = g("editor.background")
    shell_bg = editor_bg if unbordered else g("sideBar.background", "titleBar.activeBackground", "editor.background")
    elevated_bg = g("editorWidget.background", "menu.background", "dropdown.background", "sideBar.background", "editor.background")
    # If unbordered and elevated equals editor_bg (e.g. light-default where widget is #ffffff), use sideBar bg for subtle elevation.
    if unbordered and elevated_bg == editor_bg:
        elevated_bg = g("sideBar.background", "tab.inactiveBackground", "editor.background")

    border = TRANSPARENT if unbordered else (g("sideBar.border", "editorGroup.border", "panel.border", "contrastBorder") or TRANSPARENT)
    border_variant = TRANSPARENT if unbordered else (g("panel.border", "editorGroup.border", "sideBar.border") or border)
    accent = g("focusBorder", "button.background", "textLink.foreground")
    fg = g("editor.foreground", "foreground")
    ui_text = g("foreground", "sideBar.foreground", "editor.foreground")
    muted_text = g("descriptionForeground", "tab.inactiveForeground", "editorLineNumber.foreground")
    disabled_text = g("disabledForeground", "editorLineNumber.foreground")
    # Subtle, well-contrasted list hover & selection (VS Code's 40%-alpha gray #6e768166 reads too bright in Zed).
    hover = blend(fg[:7], 0.06 if appearance == "dark" else 0.05, shell_bg[:7])
    selected = blend(fg[:7], 0.11 if appearance == "dark" else 0.09, shell_bg[:7])
    cursor = g("editorCursor.foreground") or fg
    selection = g("editor.selectionBackground") or with_alpha(accent, "3d")

    style = {
        "background.appearance": "opaque",
        "background": shell_bg,
        "border": border,
        "border.variant": border_variant,
        "border.focused": TRANSPARENT,
        "border.selected": TRANSPARENT,
        "border.transparent": TRANSPARENT,
        "border.disabled": border,
        "elevated_surface.background": elevated_bg,
        "surface.background": shell_bg,
        "element.background": g("input.background") or elevated_bg,
        "element.hover": hover,
        "element.active": selected,
        "element.selected": selected,
        "element.disabled": g("input.background") or elevated_bg,
        "drop_target.background": with_alpha(accent, "2b"),
        "ghost_element.background": TRANSPARENT,
        "ghost_element.hover": hover,
        "ghost_element.active": selected,
        "ghost_element.selected": selected,
        "ghost_element.disabled": TRANSPARENT,
        "text": ui_text,
        "text.muted": muted_text,
        "text.placeholder": g("input.placeholderForeground") or muted_text,
        "text.disabled": disabled_text,
        "text.accent": g("textLink.foreground") or accent,
        "icon": g("icon.foreground") or ui_text,
        "icon.muted": g("activityBar.inactiveForeground") or muted_text,
        "icon.disabled": disabled_text,
        "icon.placeholder": muted_text,
        "icon.accent": g("textLink.foreground") or accent,
        "status_bar.background": editor_bg if unbordered else g("statusBar.background", "sideBar.background", "editor.background"),
        "title_bar.background": editor_bg if unbordered else g("titleBar.activeBackground", "sideBar.background", "editor.background"),
        "title_bar.inactive_background": editor_bg if unbordered else g("titleBar.inactiveBackground", "titleBar.activeBackground", "sideBar.background"),
        "toolbar.background": editor_bg,
        "tab_bar.background": editor_bg if unbordered else g("editorGroupHeader.tabsBackground", "sideBar.background", "editor.background"),
        "tab.inactive_background": editor_bg if unbordered else g("tab.inactiveBackground", "editorGroupHeader.tabsBackground", "sideBar.background"),
        "tab.active_background": elevated_bg if unbordered else g("tab.activeBackground", "editor.background"),
        "search.match_background": g("editor.findMatchHighlightBackground"),
        "search.active_match_background": g("editor.findMatchBackground"),
        "panel.background": shell_bg,
        "panel.focused_border": TRANSPARENT,
        "panel.indent_guide": g("tree.indentGuidesStroke", "editorIndentGuide.background"),
        "panel.indent_guide_active": g("editorIndentGuide.activeBackground", "tree.indentGuidesStroke"),
        "panel.indent_guide_hover": g("editorIndentGuide.activeBackground", "tree.indentGuidesStroke"),
        "pane.focused_border": TRANSPARENT,
        "pane_group.border": border,
        "scrollbar.thumb.background": g("scrollbarSlider.background"),
        "scrollbar.thumb.hover_background": g("scrollbarSlider.hoverBackground"),
        "scrollbar.thumb.active_background": g("scrollbarSlider.activeBackground"),
        "scrollbar.thumb.border": TRANSPARENT,
        "scrollbar.track.background": TRANSPARENT,
        "scrollbar.track.border": TRANSPARENT,
        "minimap.thumb.background": g("scrollbarSlider.background"),
        "minimap.thumb.hover_background": g("scrollbarSlider.hoverBackground"),
        "minimap.thumb.active_background": g("scrollbarSlider.activeBackground"),
        "minimap.thumb.border": TRANSPARENT,
        "editor.foreground": fg,
        "editor.background": editor_bg,
        "editor.gutter.background": editor_bg,
        "editor.subheader.background": elevated_bg,
        "editor.active_line.background": g("editor.lineHighlightBackground"),
        "editor.highlighted_line.background": g("editor.lineHighlightBackground"),
        "editor.line_number": g("editorLineNumber.foreground"),
        "editor.active_line_number": g("editorLineNumber.activeForeground") or fg,
        "editor.hover_line_number": g("editorLineNumber.activeForeground") or fg,
        "editor.invisible": g("editorWhitespace.foreground"),
        "editor.wrap_guide": g("editorIndentGuide.background"),
        "editor.active_wrap_guide": g("editorIndentGuide.activeBackground"),
        "editor.indent_guide": g("editorIndentGuide.background"),
        "editor.indent_guide_active": g("editorIndentGuide.activeBackground"),
        "editor.document_highlight.read_background": g("editor.wordHighlightBackground"),
        "editor.document_highlight.write_background": g("editor.wordHighlightStrongBackground"),
        "editor.document_highlight.bracket_background": g("editorBracketMatch.background"),
        "link_text.hover": g("textLink.activeForeground", "textLink.foreground"),
        "terminal.background": g("terminal.background") or editor_bg,
        "terminal.foreground": g("terminal.foreground") or fg,
        "terminal.ansi.background": g("terminal.background") or editor_bg,
        "terminal.bright_foreground": g("terminal.ansiBrightWhite") or fg,
        "terminal.dim_foreground": muted_text,
    }

    for name in ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"):
        t = name.capitalize()
        style[f"terminal.ansi.{name}"] = g(f"terminal.ansi{t}")
        style[f"terminal.ansi.bright_{name}"] = g(f"terminal.ansiBright{t}")

    statuses = {
        "error": g("editorError.foreground", "errorForeground", "gitDecoration.deletedResourceForeground"),
        "warning": g("editorWarning.foreground", "gitDecoration.modifiedResourceForeground"),
        "info": g("textLink.foreground", "focusBorder"),
        "hint": g("editorInlayHint.foreground", "descriptionForeground"),
        "success": g("gitDecoration.addedResourceForeground", "terminal.ansiGreen"),
        "created": g("gitDecoration.untrackedResourceForeground", "gitDecoration.addedResourceForeground"),
        "modified": g("gitDecoration.modifiedResourceForeground"),
        "deleted": g("gitDecoration.deletedResourceForeground"),
        "renamed": g("gitDecoration.addedResourceForeground"),
        "conflict": g("gitDecoration.conflictingResourceForeground", "gitDecoration.modifiedResourceForeground"),
        "ignored": g("gitDecoration.ignoredResourceForeground", "disabledForeground"),
        "hidden": disabled_text,
        "unreachable": muted_text,
        "predictive": g("editorGhostText.foreground", "editorLineNumber.foreground"),
    }
    for name, val in statuses.items():
        if not val:
            continue
        style[name] = val
        style[f"{name}.background"] = with_alpha(val, "2e" if name in ("created", "deleted", "modified") else "1f")
        style[f"{name}.border"] = with_alpha(val, "66")
    style["hint.background"] = g("editorInlayHint.background") or elevated_bg

    # Use full opaque gitDecoration colors (not 40%-alpha editorGutter.*) so +N -M counts and diffs stay crisp.
    vc_add = (g("gitDecoration.addedResourceForeground", "editorGutter.addedBackground") or "")[:7] or None
    vc_mod = (g("gitDecoration.modifiedResourceForeground", "editorGutter.modifiedBackground") or "")[:7] or None
    vc_del = (g("gitDecoration.deletedResourceForeground", "editorGutter.deletedBackground") or "")[:7] or None
    style["version_control.added"] = vc_add
    style["version_control.modified"] = vc_mod
    style["version_control.deleted"] = vc_del
    style["version_control.renamed"] = vc_mod
    style["version_control.conflict"] = statuses["conflict"]
    style["version_control.ignored"] = statuses["ignored"]
    if vc_add:
        style["version_control.word_added"] = with_alpha(vc_add, "5c")
    if vc_del:
        style["version_control.word_deleted"] = with_alpha(vc_del, "5c")

    player_colors = [accent] + [
        g(f"terminal.ansi{n}") for n in ("Blue", "Magenta", "Yellow", "Green", "Cyan", "Red")
    ]
    style["players"] = [
        {
            "cursor": cursor if i == 0 else p,
            "background": p,
            "selection": selection if i == 0 else with_alpha(p, "3d"),
        }
        for i, p in enumerate(player_colors)
        if p
    ]
    style["accents"] = [
        c[f"editorBracketHighlight.foreground{i}"]
        for i in range(1, 7)
        if c.get(f"editorBracketHighlight.foreground{i}")
    ] or [p for p in player_colors[:6] if p]

    style["editor.invisible"] = visible_invisible(fg, selection, editor_bg)
    style["editor.subheader.background"] = subheader_bg(editor_bg, fg)
    style["syntax"] = build_syntax(theme, c)
    return {k: v for k, v in style.items() if v is not None}


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    OUT.mkdir(exist_ok=True)
    themes = []
    for stem, label, appearance in VARIANTS:
        path = source / f"{stem}.json"
        raw = json.loads(path.read_text())
        for unbordered in (False, True):
            name = f"{label} Unbordered" if unbordered else label
            themes.append({
                "name": name,
                "appearance": appearance,
                "style": build_style(raw, appearance, unbordered=unbordered),
            })

    family = {
        "$schema": SCHEMA,
        "name": "GitHub Custom",
        "author": AUTHOR,
        "themes": themes,
    }
    target = OUT / "github.json"
    target.write_text(json.dumps(family, indent=2, ensure_ascii=False) + "\n")
    for t in themes:
        print(f"themes/github.json: {t['name']} ({t['appearance']})")


if __name__ == "__main__":
    main()
