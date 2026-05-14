from __future__ import annotations

from typing import Callable

from aqt.qt import (
    QCheckBox,
    QMenu,
    QMouseEvent,
    QTableWidget,
    QWidgetAction,
)


class TableMenu(QMenu):
    def __init__(self, table: QTableWidget, column_names: list[str], sort_col: int, toggle_column: Callable):
        super().__init__()
        self._checkboxes = []
        for col, name in enumerate(column_names):
            cb = QCheckBox(self)
            cb.setChecked(not table.isColumnHidden(col))
            if col == sort_col:
                cb.setText(f"{name} (sort field)")
                cb.setEnabled(False)
            else:
                cb.setText(name)
                cb.toggled.connect(lambda checked, c=col: toggle_column(c, checked))
            self._checkboxes.append(cb)

            wa = QWidgetAction(self)
            wa.setDefaultWidget(cb)
            self.addAction(wa)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        action = self.activeAction()
        if isinstance(action, QWidgetAction):
            return
        super().mouseReleaseEvent(event)
