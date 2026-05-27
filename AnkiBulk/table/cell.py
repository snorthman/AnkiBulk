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
SORT_FIELD_BG = QColor("#FFF9E6")
SELECTED_BG = QColor("#ECECEC")


class TableCellDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().initStyleOption(option, index)
        table = self.parent()
        item = table.item(index.row(), index.column())
        if item is None:
            return

        option.backgroundBrush.setStyle(Qt.BrushStyle.SolidPattern)
        if option.state & QStyle.StateFlag.State_Selected:
            option.backgroundBrush.setColor(SELECTED_BG)
            option.palette.setColor(option.palette.ColorRole.HighlightedText, QColor("#000000"))
        elif item.flags() & Qt.ItemFlag.ItemIsEditable:
            if index.column() == table.sort_col:
                option.backgroundBrush.setColor(SORT_FIELD_BG)
            else:
                option.backgroundBrush.setColor(EDITABLE_BG)
        else:
            option.backgroundBrush.setColor(READONLY_BG)
