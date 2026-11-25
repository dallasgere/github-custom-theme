# GitHub Custom Theme

All nine official themes from [primer/github-vscode-theme](https://github.com/primer/github-vscode-theme) ported to [Zed](https://zed.dev) with exact 1:1 color matching, plus an **Unbordered** variant for each — all packaged in a single `themes/github.json` file.

## Variants (18 total)

- **GitHub Dark Default** / **GitHub Dark Default Unbordered**
- **GitHub Dark Dimmed** / **GitHub Dark Dimmed Unbordered**
- **GitHub Dark High Contrast** / **GitHub Dark High Contrast Unbordered**
- **GitHub Dark Colorblind** / **GitHub Dark Colorblind Unbordered**
- **GitHub Dark** *(classic)* / **GitHub Dark Unbordered**
- **GitHub Light Default** / **GitHub Light Default Unbordered**
- **GitHub Light High Contrast** / **GitHub Light High Contrast Unbordered**
- **GitHub Light Colorblind** / **GitHub Light Colorblind Unbordered**
- **GitHub Light** *(classic)* / **GitHub Light Unbordered**

## Install locally

1. In Zed, open the command palette and run `zed: install dev extension`.
2. Select this folder.
3. Run `theme selector: toggle` and pick any `GitHub …` theme.

Or copy `themes/github.json` into `~/.config/zed/themes/`.

## Regenerating

```bash
python3 scripts/build.py
```
