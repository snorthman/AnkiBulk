from __future__ import annotations

from aqt.qt import QHBoxLayout, QPushButton, QSize, QVBoxLayout, QWidget

from AnkiBulk.icon import icon
from AnkiBulk.toggle import ToggleSwitch


class Group(QWidget):
    def __init__(self, toggle: ToggleSwitch, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._toggle = toggle

        layout = QVBoxLayout()
        layout.setContentsMargins(*[4] * 4)
        self.setLayout(layout)

        # Top row: toggle on the left, subclass buttons on the right
        self._top_row = QHBoxLayout()
        self._top_row.addWidget(toggle)
        self._top_row.addStretch()
        layout.addLayout(self._top_row)

        self._current_btn_group: QHBoxLayout | None = None

    @property
    def name(self) -> str:
        raise NotImplementedError()

    @property
    def index(self) -> int:
        raise NotImplementedError()

    def _add_separator(self) -> None:
        """End the current button group and start a new one."""
        self._current_btn_group = None

    def _add_icon_button(self, name: str, tooltip: str, callback) -> QPushButton:
        """Add an icon-only button to the current button group."""
        btn = QPushButton()
        btn.setObjectName("iconBtn")
        btn.setIcon(icon(name))
        btn.setIconSize(QSize(22, 22))
        btn.setToolTip(tooltip)
        btn.setAutoDefault(False)
        btn.setFlat(True)
        btn.clicked.connect(callback)

        if self._current_btn_group is None:
            # Start a new button group container
            container = QWidget()
            container.setObjectName("btnGroup")
            group_layout = QHBoxLayout()
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(0)
            container.setLayout(group_layout)
            self._top_row.addWidget(container)
            self._current_btn_group = group_layout

        self._current_btn_group.addWidget(btn)
        self._update_btn_group_roles(self._current_btn_group)
        return btn

    def _update_btn_group_roles(self, group_layout: QHBoxLayout) -> None:
        """Assign solo/first/middle/last properties for CSS targeting."""
        count = group_layout.count()
        for i in range(count):
            btn = group_layout.itemAt(i).widget()
            if btn is None:
                continue
            if count == 1:
                btn.setProperty("btnPos", "solo")
            elif i == 0:
                btn.setProperty("btnPos", "first")
            elif i == count - 1:
                btn.setProperty("btnPos", "last")
            else:
                btn.setProperty("btnPos", "middle")

    def showEvent(self, event) -> None:
        """Reparent the shared toggle into this group's top row when shown."""
        super().showEvent(event)
        if self._toggle.parent() is not self:
            self._top_row.insertWidget(0, self._toggle)
