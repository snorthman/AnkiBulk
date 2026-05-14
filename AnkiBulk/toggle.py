from __future__ import annotations

from aqt.qt import (
    QColor,
    QEasingCurve,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QPropertyAnimation,
    QRectF,
    QSize,
    QWidget,
    Qt,
    pyqtProperty,
    pyqtSignal,
)


class ToggleSwitch(QWidget):
    """A two-state sliding toggle, styled like Anki's Cards/Notes switch.

    Left state:  [● Label ]   — knob left, label right
    Right state: [ Label ●]   — label left, knob right
    Transition:  [    ●    ]  — labels hidden while knob slides
    """

    toggled = pyqtSignal(bool)

    _TRACK_HEIGHT = 26
    _THUMB_MARGIN = 3
    _LABEL_PAD = 2          # horizontal padding between knob and label
    _ANIMATION_MS = 300

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = False
        self._left_label = "left"
        self._right_label = "right"
        self._left_color = QColor("#60A5FA")
        self._right_color = QColor("#22C55E")
        self.set_labels(self._left_label, self._right_label)

        # Animation value: 0.0 = left, 1.0 = right
        self._position = 0.0
        self._animation = QPropertyAnimation(self, b"position", self)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.setDuration(self._ANIMATION_MS)

    def set_labels(self, left: str, right: str) -> None:
        self._left_label = left
        self._right_label = right
        fm = QFontMetrics(self._label_font())
        label_w = max(fm.horizontalAdvance(left), fm.horizontalAdvance(right))
        thumb_d = self._TRACK_HEIGHT - 2 * self._THUMB_MARGIN
        # Total = margin + thumb + pad + label + pad + margin
        self._total_width = self._THUMB_MARGIN * 2 + thumb_d + self._LABEL_PAD * 2 + label_w + 4
        self.setFixedSize(self._total_width, self._TRACK_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _label_font(self) -> QFont:
        font = self.font()
        font.setPointSize(8)
        return font

    @pyqtProperty(float)
    def position(self) -> float:
        return self._position

    @position.setter  # type: ignore[no-redef]
    def position(self, value: float) -> None:
        self._position = value
        self.update()

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool) -> None:
        if self._checked == value:
            return
        self._checked = value

        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(1.0 if self._checked else 0.0)
        self._animation.start()

        if not self.signalsBlocked():
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event) -> None:
        self.checked = not self._checked

    def sizeHint(self) -> QSize:
        return QSize(self._total_width, self._TRACK_HEIGHT)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        t = self._position
        m = self._THUMB_MARGIN
        thumb_d = h - 2 * m
        radius = h / 2

        # Interpolate track color
        lc, rc = self._left_color, self._right_color
        track_color = QColor(
            int(lc.red()   + t * (rc.red()   - lc.red())),
            int(lc.green() + t * (rc.green() - lc.green())),
            int(lc.blue()  + t * (rc.blue()  - lc.blue())),
        )

        # Draw track (rounded pill)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # Draw sliding thumb
        p.setBrush(QColor("#FFFFFF"))
        thumb_x = m + t * (w - thumb_d - 2 * m)
        p.drawEllipse(QRectF(thumb_x, m, thumb_d, thumb_d))

        # Draw label — fade based on distance from endpoints.
        # At t=0 or t=1 the label is fully visible; mid-transition it's hidden.
        # Use a curve that fades out quickly and fades in quickly near endpoints.
        fade = 1.0 - min(t, 1.0 - t) * 4.0  # 1→0 over first 25%, 0→1 over last 25%
        fade = max(0.0, min(1.0, fade))

        if fade > 0.0:
            font = self._label_font()
            p.setFont(font)
            p.setPen(QPen(QColor(255, 255, 255, int(fade * 255))))

            if t <= 0.5:
                # Left state: label to the right of the knob
                text_x = m + thumb_d + self._LABEL_PAD
                text_w = w - text_x - m
                text_rect = QRectF(text_x, 0, text_w, h)
                p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
                           self._left_label)
            else:
                # Right state: label to the left of the knob
                text_x = m
                text_w = w - thumb_d - 2 * m - self._LABEL_PAD
                text_rect = QRectF(text_x, 0, text_w, h)
                p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
                           self._right_label)

        p.end()
