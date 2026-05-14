# CLAUDE.md

## Project overview

AnkiBulk is an Anki desktop addon (Python, PyQt6) for bulk-adding notes. It lives in `AnkiBulk/` and is loaded by Anki's addon system via `AnkiBulk/__init__.py`. The addon hooks into the browser menu and opens a non-modal dialog for adding notes in bulk.

## Architecture

```
AnkiBulk/
  __init__.py          # Entry point: adds internal/ to sys.path, calls main()
  main.py              # Hooks into browser menu, creates "Bulk Add" and "Help" actions
  dialog.py            # Main dialog: chooser, toggle, stacked groups, shortcuts, Help/Bulk Add/Cancel buttons
  group.py             # Base class for TableGroup/TextGroup (shared toggle widget, top row layout with stretch)
  chooser.py           # Notetype + Deck chooser row (enabled/disabled based on browser selection)
  toggle.py            # ToggleSwitch widget (animated sliding toggle, Table/Text)
  config.py            # ConfigField descriptor (factory defaults), Preset dataclass (per-notetype settings)
  undo.py              # Generic UndoStack[T] with dirty tracking
  i18n.py              # Fluent-based i18n: i18n class with lazy locale rebuild, module-level tr() binding
  help.py              # Help dialog — builds HTML from tr() calls, no template file
  style.css            # Global stylesheet (loaded once in dialog.py)
  config.json          # Anki addon config defaults (empty)
  i18n/
    en-US/
      ankibulk.ftl     # English translations (Fluent format)
  table/
    __init__.py
    group.py           # TableGroup: buttons + Table widget, clipboard insert, update from selection
    table.py           # Table(QTableWidget): columns, rows, undo/redo, YAML I/O, key handling
    cell.py            # TableCellDelegate(QStyledItemDelegate): readonly/editable/selected cell colors
    menu.py            # TableMenu(QMenu): column visibility checkboxes, toggle on mouse-down
  text/
    __init__.py
    group.py           # TextGroup: buttons + two QPlainTextEdits (examples + editables), linter, copy to clipboard
    linter.py          # Debounced YAML validation, error highlighting, field name checks, flow-style rejection
    options.py         # Per-notetype preset dialog (copy format, include examples, mark tag, additional text)
  internal/            # Vendored dependencies (yaml, fluent) — do not modify
```

## Key patterns

- **Tab base class `Group`** — owns a shared `ToggleSwitch` widget and a `_top_row` QHBoxLayout. A stretch separates the toggle (left) from subclass buttons (right). The toggle is reparented via `showEvent` when the stacked widget switches pages.
- **Cell backgrounds** — controlled by `TableCellDelegate(QStyledItemDelegate)` in `table/cell.py`, not CSS. Qt stylesheets on parent widgets override `setBackground()`, so the delegate handles readonly/editable/selected colors in `initStyleOption()`.
- **Sort-field-only editing** — in editable rows, only the sort field column is editable. Double-clicking any other cell redirects to the sort field. All other fields are filled via YAML in the Text view.
- **Tags column** — synthetic column appended after notetype fields. `table.tags_col_name` property resolves collisions if a field is named "Tags" (prepends underscores).
- **Column visibility menu** — `TableMenu(QMenu)` with `QWidgetAction`-wrapped checkboxes. Toggles on mouse-down (not release). Mouse release is swallowed to keep the menu open.
- **Stylesheet** — single `style.css` loaded once on the dialog. No `::item` CSS rules (they would break the cell delegate). Widget targeting uses `setObjectName()`.
- **Config** — `ConfigField` descriptor reads/writes via `mw.addonManager.getConfig/writeConfig`. Uses factory callables (e.g. `dict`) for mutable defaults. `Preset` is a dataclass with `to_dict()/from_dict()` for persistence.
- **Undo** — `UndoStack[T]` generic class used by Table for row snapshots. Text editor uses QPlainTextEdit's built-in undo (cleared on tab switch via `clearUndoRedoStacks()`).
- **i18n** — All user-facing strings use `tr("key-id")` from `i18n.py`. The `i18n` class lazily rebuilds `FluentLocalization` when the locale changes; `tr = i18n().tr` is the module-level binding. Translations live in `i18n/<locale>/ankibulk.ftl` (Fluent format).
- **Shortcuts** — all dialog-level `QShortcut`s, guarded by active page and editing state:
  - `Ctrl+R` — update from selection (Table view)
  - `Ctrl+V` — insert clipboard as rows (Table view, not editing)
  - `Ctrl+Z` / `Ctrl+Y` — undo/redo (Table view, not editing)
  - `Ctrl+Shift+C` — copy to clipboard (Text view)
- **Non-modal dialog** — opened via `show()` not `exec()`, so the user can interact with the browser. A module-level `_dialog` reference in `main.py` prevents garbage collection.
- **First-time-use hint** — yellow label shown inside the TableGroup on first launch, dismissed permanently when the user switches to Text view (persisted via `first_time_use` config).
- **Notetype change guard** — `_notetype_changing` boolean in the dialog prevents reentrancy when setting `chooser.notetype_id` fires `on_notetype_changed`.

## Conventions

- Python 3.10+ (`match/case`, `X | Y` union types)
- `from __future__ import annotations` in all modules
- Variable naming: use `note_id` not `mid`, `notetype` not `model`
- Unused imports are fine — the developer handles cleanup
- No emoji in code or files unless explicitly asked
- `internal/` is vendored — never modify files there
- All user-facing strings go through `tr()` from `i18n.py` — add new keys to `i18n/en-US/ankibulk.ftl`

## Testing

```
pytest
```

Tests are in `tests/`. The project uses a `.venv` with pytest installed.

## Common tasks

- **Adding a button** — add to `_top_row` in the relevant group's `__init__`, set tooltip via `setToolTip()`, post-action feedback via `aqt.utils.tooltip()`
- **Styling** — edit `AnkiBulk/style.css`. Target widgets by `#objectName`. Never add `::item` rules on the table (breaks cell delegate).
- **New config field** — add a `ConfigField` to `_AnkiBulkConfig` in `config.py`. Use factory callables (`dict`, `list`) for mutable defaults.
- **Notetype field access** — `table.current_notetype["flds"]` for field list, `table.column_names` includes the synthetic Tags column
- **Adding a translation** — add a `key-id = Text` line to `i18n/en-US/ankibulk.ftl`, use `tr("key-id")` in Python. Variables: `tr("key", name=val)` → `{ $name }` in FTL.
- **Packaging** — run `bash package.sh` to create `AnkiBulk.ankiaddon` (zip of `AnkiBulk/` contents, no `__pycache__`).
