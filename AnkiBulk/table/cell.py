from __future__ import annotations

from aqt.qt import (
    QColor,
    QModelIndex,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    Qt,
)

# Light mode
_L_READONLY = QColor("#F5F5F5")
_L_EDITABLE = QColor("#FFFFFF")
_L_SORT = QColor("#FFF9E6")
_L_SELECTED = QColor("#ECECEC")
_L_SEL_TEXT = QColor("#000000")

# Dark mode
_D_READONLY = QColor("#2D2D2D")
_D_EDITABLE = QColor("#1E1E1E")
_D_SORT = QColor("#2D2A1E")
_D_SELECTED = QColor("#3A3A3A")
_D_SEL_TEXT = QColor("#E0E0E0")


def _dark() -> bool:
    from aqt.theme import theme_manager
    return theme_manager.night_mode


class TableCellDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().initStyleOption(option, index)
        table = self.parent()
        item = table.item(index.row(), index.column())
        if item is None:
            return

        dark = _dark()
        option.backgroundBrush.setStyle(Qt.BrushStyle.SolidPattern)
        if option.state & QStyle.StateFlag.State_Selected:
            option.backgroundBrush.setColor(_D_SELECTED if dark else _L_SELECTED)
            option.palette.setColor(option.palette.ColorRole.HighlightedText, _D_SEL_TEXT if dark else _L_SEL_TEXT)
        elif item.flags() & Qt.ItemFlag.ItemIsEditable:
            if index.column() == table.sort_col:
                option.backgroundBrush.setColor(_D_SORT if dark else _L_SORT)
            else:
                option.backgroundBrush.setColor(_D_EDITABLE if dark else _L_EDITABLE)
        else:
            option.backgroundBrush.setColor(_D_READONLY if dark else _L_READONLY)
