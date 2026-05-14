from __future__ import annotations

from aqt.qt import (
    QColor,
    QModelIndex,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    Qt,
)

READONLY_BG = QColor("#F5F5F5")
EDITABLE_BG = QColor("#FFFFFF")
SELECTED_BG = QColor("#ECECEC")


class TableCellDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().initStyleOption(option, index)
        item = self.parent().item(index.row(), index.column())
        if item is None:
            return

        option.backgroundBrush.setStyle(Qt.BrushStyle.SolidPattern)
        if option.state & QStyle.StateFlag.State_Selected:
            option.backgroundBrush.setColor(SELECTED_BG)
            option.palette.setColor(option.palette.ColorRole.HighlightedText, QColor("#000000"))
        elif item.flags() & Qt.ItemFlag.ItemIsEditable:
            option.backgroundBrush.setColor(EDITABLE_BG)
        else:
            option.backgroundBrush.setColor(READONLY_BG)