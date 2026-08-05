# CLAUDE.md

## Project overview

AnkiBulk is an Anki desktop addon (Python, PyQt6) for bulk-adding notes. It lives in `AnkiBulk/` and is loaded by Anki's addon system via `AnkiBulk/__init__.py`. The addon hooks into the browser menu and opens a non-modal dialog for adding notes in bulk.

## Architecture

```
AnkiBulk/
  __init__.py          # Entry point: adds internal/ to sys.path, calls main()
  main.py              # Hooks into browser menu, creates "Bulk Add" and "Help" actions
  dialog.py            # Main dialog: chooser, toggle, stacked groups, shortcuts, Help/Bulk Add/Cancel buttons
  group.py             # Base class for TableGroup/TextGroup (shared toggle, icon toolbar, separators)
  chooser.py           # Notetype + Deck chooser row (enabled/disabled based on browser selection)
  toggle.py            # ToggleSwitch widget (animated sliding toggle, Table/Text)
  config.py            # ConfigField descriptor (factory defaults), Preset dataclass (per-notetype settings)
  icon.py              # SVG icon loader with dark mode support, cached per (name, dark_mode)
  i18n.py              # YAML-based i18n: lazy locale rebuild, module-level tr() binding
  help.py              # Help dialog — builds HTML from tr() calls, no template file
  style.css            # Light mode stylesheet
  style-dark.css       # Dark mode stylesheet
  config.json          # Anki addon config defaults (empty)
  svg/                 # SVG icon files (stroke="currentColor", resolved at load time)
  i18n/
    en-US/
      ankibulk.yaml    # English translations (YAML format)
    de/, fr/, ...      # 12 additional locale files
  table/
    __init__.py
    group.py           # TableGroup: icon toolbar + Table widget, update from selection
    table.py           # Table(QTableWidget): columns, rows, undo/redo, YAML I/O, key handling
    context.py         # Context menu + copy/paste/clear actions (shared by toolbar and right-click)
    cell.py            # TableCellDelegate(QStyledItemDelegate): theme-aware cell colors
    menu.py            # TableMenu(QMenu): column visibility checkboxes, toggle on mouse-down
    undo.py            # Generic UndoStack[T] with dirty tracking
    yaml.py            # Table ↔ YAML conversion helpers
  text/
    __init__.py
    group.py           # TextGroup: buttons + two QPlainTextEdits (examples + editables), linter, copy to clipboard
    linter.py          # Debounced YAML validation, error highlighting, field name checks, flow-style rejection
    options.py         # Per-notetype preset dialog (copy format, include examples, mark tag, additional text)
  internal/            # Vendored dependencies (yaml) — do not modify
```

## Key patterns

- **Tab base class `Group`** — owns a shared `ToggleSwitch` widget and a `_top_row` QHBoxLayout. A stretch separates the toggle (left) from subclass buttons (right). The toggle is reparented via `showEvent` when the stacked widget switches pages. Buttons are added via `_add_icon_button(svg_name, tooltip, callback)` and grouped with `_add_separator()`.
- **Cell backgrounds** — controlled by `TableCellDelegate(QStyledItemDelegate)` in `table/cell.py`, not CSS. Qt stylesheets on parent widgets override `setBackground()`, so the delegate handles readonly/editable/selected/sort-field colors in `initStyleOption()`. Colors are theme-aware (light/dark checked via `theme_manager.night_mode`).
- **All columns editable** — in editable rows, every column is editable. The sort field column is visually distinguished with a warm background color.
- **Tags column** — synthetic column appended after notetype fields. `table.tags_col_name` property resolves collisions if a field is named "Tags" (prepends underscores).
- **Column visibility menu** — `TableMenu(QMenu)` with `QWidgetAction`-wrapped checkboxes. Toggles on mouse-down (not release). Mouse release is swallowed to keep the menu open.
- **Context menu** — `table/context.py` provides copy/paste/clear actions used by both the toolbar buttons and the right-click context menu. The context menu also mirrors undo/redo, insert/delete row, and update from selection when passed the `TableGroup`.
- **Dark mode** — detected via `aqt.theme.theme_manager.night_mode`. Four layers: (1) `style.css` / `style-dark.css` loaded dynamically in `dialog.py`, (2) theme-aware cell delegate colors in `table/cell.py`, (3) SVG `currentColor` resolved to light/dark color in `icon.py`, (4) hardcoded colors in `help.py` and `text/linter.py`.
- **Stylesheet** — `style.css` (light) and `style-dark.css` (dark) loaded at dialog construction based on theme. No `::item` CSS rules (they would break the cell delegate). Widget targeting uses `setObjectName()`.
- **Icons** — SVG files in `svg/` use `stroke="currentColor"`. `icon.py` resolves the color at load time based on dark mode, writes to a temp file (preserving SVG scalability), and caches by `(name, dark_mode)`.
- **Config** — `ConfigField` descriptor reads/writes via `mw.addonManager.getConfig/writeConfig`. Uses factory callables (e.g. `dict`) for mutable defaults. `Preset` is a dataclass with `to_dict()/from_dict()` for persistence.
- **Undo** — `UndoStack[T]` generic class in `table/undo.py`, used by Table for row snapshots. Text editor uses QPlainTextEdit's built-in undo (cleared on tab switch via `clearUndoRedoStacks()`).
- **i18n** — All user-facing strings use `tr("key-id")` from `i18n.py`. Translations live in `i18n/<locale>/ankibulk.yaml` (YAML format). Variables: `tr("key", name=val)` → `{name}` in YAML. Plurals use `one`/`other` dict keys selected by `n`.
- **Shortcuts** — all dialog-level `QShortcut`s, guarded by active page and editing state:
  - `Ctrl+R` — update from selection (Table view)
  - `Ctrl+V` — paste clipboard (Table view, not editing)
  - `Ctrl+Z` / `Ctrl+Y` — undo/redo (Table view, not editing)
  - `Ctrl+Shift+C` — copy to clipboard (Text view)
- **Selection mode** — `ContiguousSelection` (shift-click extends, Ctrl+click is swallowed/ignored).
- **Non-modal dialog** — opened via `show()` not `exec()`, so the user can interact with the browser. A module-level `_dialog` reference in `main.py` prevents garbage collection.
- **First-time-use hints** — yellow labels: one in TableGroup (dismissed when switching to Text view, `first_time_use` config), one in TextGroup (dismissed when switching back to Table view, `first_time_text` config).
- **Notetype change guard** — `_notetype_changing` boolean in the dialog prevents reentrancy when setting `chooser.notetype_id` fires `on_notetype_changed`.

## Conventions

- Python 3.10+ (`match/case`, `X | Y` union types)
- `from __future__ import annotations` in all modules
- Variable naming: use `note_id` not `mid`, `notetype` not `model`
- Unused imports are fine — the developer handles cleanup
- No emoji in code or files unless explicitly asked
- `internal/` is vendored — never modify files there
- All user-facing strings go through `tr()` from `i18n.py` — add new keys to `i18n/en-US/ankibulk.yaml`

## Testing

```
pytest
```

Tests are in `tests/`. The project uses a `.venv` with pytest installed.

## Common tasks

- **Adding a button** — use `self._add_icon_button(svg_name, tooltip, callback)` in the group's `__init__`. SVG file goes in `svg/`. Group buttons with `_add_separator()`.
- **Styling** — edit `AnkiBulk/style.css` and `AnkiBulk/style-dark.css`. Target widgets by `#objectName`. Never add `::item` rules on the table (breaks cell delegate).
- **New config field** — add a `ConfigField` to `_AnkiBulkConfig` in `config.py`. Use factory callables (`dict`, `list`) for mutable defaults.
- **Notetype field access** — `table.current_notetype["flds"]` for field list, `table.column_names` includes the synthetic Tags column
- **Adding a translation** — add a `key-id: "Text"` line to `i18n/en-US/ankibulk.yaml`, use `tr("key-id")` in Python. Variables: `tr("key", name=val)` → `{name}` in YAML. Add the key to all 13 locale files.
- **Packaging** — run `bash package.sh` to create `AnkiBulk.ankiaddon` (zip of `AnkiBulk/` contents, no `__pycache__`).
