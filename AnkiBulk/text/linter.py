from __future__ import annotations

from aqt.qt import (
    QColor,
    QLabel,
    QPlainTextEdit,
    QTextCharFormat,
    QTextEdit,
    QTimer,
    qconnect,
)

from AnkiBulk.i18n import tr
from AnkiBulk.table.table import Table


class Linter:
    """Debounced YAML linter for the Raw tab's editable text editor."""

    def __init__(self, raw_new: QPlainTextEdit, raw_status: QLabel, table: Table) -> None:
        self._raw_new = raw_new
        self._raw_status = raw_status
        self._table = table

        self._lint_timer = QTimer(raw_new)
        self._lint_timer.setSingleShot(True)
        self._lint_timer.setInterval(300)
        qconnect(self._lint_timer.timeout, self.validate_yaml)

    def schedule(self) -> None:
        """Restart the debounce timer (connect to textChanged)."""
        self._lint_timer.start()

    def validate_yaml(self) -> bool:
        """Parse the YAML in raw_new, highlight errors and validate structure.
        Returns True if the YAML is valid (or empty), False otherwise."""
        import re
        import yaml

        text = self._raw_new.toPlainText()
        if not text.strip():
            self._set_status("", ok=True)
            self._clear_highlights()
            return True

        errors: list[str] = []
        error_lines: list[int] = []  # 0-based line numbers to highlight

        # --- Pass 0: Reject flow-style YAML ---
        stripped = text.strip()
        if stripped.startswith(('[', '{')):
            errors.append(tr("lint-flow-style"))
            self._set_status("\n".join(errors), ok=False)
            self._highlight_lines([0])
            return False

        # --- Pass 1: Syntax ---
        try:
            doc = yaml.safe_load(text)
        except yaml.MarkedYAMLError as e:
            msg = parse_yaml_error(e)
            errors.append(tr("lint-syntax-error", msg=msg))
            if e.problem_mark is not None:
                error_lines.append(e.problem_mark.line)
            self._set_status("\n".join(errors), ok=False)
            self._highlight_lines(error_lines)
            return False
        except yaml.YAMLError:
            errors.append(tr("lint-parse-error"))
            self._set_status("\n".join(errors), ok=False)
            self._clear_highlights()
            return False

        # --- Pass 2: Structure & field names ---
        if not isinstance(doc, list):
            errors.append(tr("lint-not-list"))
            self._set_status("\n".join(errors), ok=False)
            self._clear_highlights()
            return False

        visible_names = {name for _, name in self._table.visible_columns}
        nt_name = self._table.current_notetype["name"]

        # Map each entry back to its starting line in the text.
        # Only match '- ' that is not inside a comment or blank line.
        lines = text.split("\n")
        entry_start_lines: list[int] = []
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith("#") or not stripped:
                continue
            if re.match(r"^- ", line):
                entry_start_lines.append(i)

        all_unknown: set[str] = set()
        for idx, entry in enumerate(doc):
            start_line = entry_start_lines[idx] if idx < len(entry_start_lines) else 0
            # End of this entry's lines: next entry start, or end of text
            end_line = (
                entry_start_lines[idx + 1]
                if idx + 1 < len(entry_start_lines)
                else len(lines)
            )

            if not isinstance(entry, dict):
                errors.append(tr("lint-not-dict"))
                error_lines.append(start_line)
                continue

            unknown = set(entry.keys()) - visible_names
            if unknown:
                all_unknown |= unknown
                for field_name in unknown:
                    for li in range(start_line, end_line):
                        if re.match(rf"^[\s-]*['\"]?{re.escape(field_name)}['\"]?\s*:", lines[li]):
                            error_lines.append(li)
                            break
                    else:
                        error_lines.append(start_line)

            for key, val in entry.items():
                if val is not None and not isinstance(val, str):
                    errors.append(tr("lint-value-not-text", key=key, val=str(val)))
                    for li in range(start_line, end_line):
                        if re.match(rf"^[\s-]*['\"]?{re.escape(key)}['\"]?\s*:", lines[li]):
                            error_lines.append(li)
                            break
                    else:
                        error_lines.append(start_line)

        if all_unknown:
            kwargs = dict(n=len(all_unknown), notetype=nt_name, fields=", ".join(sorted(all_unknown)))
            errors.insert(0, tr("lint-unknown-fields", **kwargs))

        if errors:
            self._set_status("\n".join(errors), ok=False)
            self._highlight_lines(error_lines)
            return False

        self._set_status("", ok=True)
        self._clear_highlights()
        return True

    def _set_status(self, text: str, ok: bool) -> None:
        """Update the status label below the raw editor. Hide if no errors."""
        if ok:
            self._raw_status.hide()
        else:
            self._raw_status.setStyleSheet("color: #c62828; padding: 2px 4px;")
            self._raw_status.setText(text)
            self._raw_status.show()

    def _highlight_lines(self, lines: list[int]) -> None:
        """Highlight multiple lines in the raw_new editor with a red background."""
        self._clear_highlights()
        if not lines:
            return
        selections = []
        seen: set[int] = set()
        for line in lines:
            if line in seen:
                continue
            seen.add(line)
            block = self._raw_new.document().findBlockByLineNumber(line)
            if not block.isValid():
                continue

            selection = QTextEdit.ExtraSelection()
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#ffcdd2"))
            fmt.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            selection.format = fmt

            cursor = self._raw_new.textCursor()
            cursor.setPosition(block.position())
            cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
            selection.cursor = cursor
            selections.append(selection)
        self._raw_new.setExtraSelections(selections)

    def _clear_highlights(self) -> None:
        """Remove all error highlights from the raw_new editor."""
        self._raw_new.setExtraSelections([])


def parse_yaml_error(e) -> str:
    """Convert a yaml.YAMLError into a user-friendly message."""
    problem = getattr(e, "problem", "") or ""
    if "found character" in problem and "that cannot start" in problem:
        return tr("lint-err-special-char")
    if "expected <block end>" in problem:
        return tr("lint-err-block-end")
    if "mapping values are not allowed" in problem:
        return tr("lint-err-no-colon-allowed")
    if "could not find expected ':'" in problem:
        return tr("lint-err-missing-colon")
    if "expected ',' or ']'" in problem or "expected ',' or '}'" in problem:
        return tr("lint-err-mismatched-brackets")
    if "found unexpected ':'" in problem:
        return tr("lint-err-unexpected-colon")
    if "did not find expected" in problem:
        return tr("lint-err-unclosed-quotes")
    if problem:
        return tr("lint-err-formatting")
    return tr("lint-err-generic")
