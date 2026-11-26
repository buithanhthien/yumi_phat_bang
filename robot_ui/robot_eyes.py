"""Animated eyes for the dashboard's idle page."""
import math
import time

from PyQt6.QtCore import QRectF, QTimer, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget


EXPRESSION_SECONDS = 5
# Left/right opening, inward tilt, corner radius and horizontal gaze.
EXPRESSIONS = (
    (1.0, 1.0, 0, 45, 0),       # Bình thường
    (0.40, 0.40, 0, 90, 0),     # Vui
    (1.20, 0.85, 0, 56, 66),    # Tò mò
    (1.22, 1.22, 0, 78, 0),     # Ngạc nhiên
    (0.43, 0.43, -13, 32, -22), # Buồn ngủ
    (0.22, 1.0, 0, 55, 0),      # Nháy mắt
)


class RobotEyes(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibleName('Biểu cảm robot')
        self._started = time.monotonic()
        self._animation = QTimer(self)
        self._animation.setInterval(33)
        self._animation.timeout.connect(self.update)

    def showEvent(self, event):
        super().showEvent(event)
        self._started = time.monotonic()
        self._animation.start()
        self.update()

    def hideEvent(self, event):
        self._animation.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        elapsed = time.monotonic() - self._started
        step, phase = divmod(elapsed, EXPRESSION_SECONDS)
        current = EXPRESSIONS[int(step) % len(EXPRESSIONS)]
        previous = EXPRESSIONS[(int(step) - 1) % len(EXPRESSIONS)] if step else current
        blend = min(phase / 0.28, 1.0)
        blend = blend * blend * (3 - 2 * blend)
        left, right, tilt, radius, gaze = (
            a + (b - a) * blend for a, b in zip(previous, current)
        )
        blink_phase = (elapsed + 1.4) % 3.7
        blink = 1 - 0.88 * math.sin(math.pi * blink_phase / 0.22) if blink_phase < 0.22 else 1

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#050b14'))
        painter.translate(self.width() / 2, self.height() / 2)
        scale = min(self.width() / 920, self.height() / 510)
        painter.scale(scale, scale)
        painter.setPen(Qt.PenStyle.NoPen)

        for side, opening in ((-1, left), (1, right)):
            painter.save()
            painter.translate(side * 175 + gaze, 0)
            painter.rotate(side * tilt)
            height = 200 * opening * blink
            corner = min(radius, height / 2)
            for margin, color in ((17, '#092733'), (8, '#155266'), (0, '#69e9ff')):
                painter.setBrush(QColor(color))
                bounds = QRectF(-111 - margin, -height / 2 - margin,
                                222 + 2 * margin, height + 2 * margin)
                painter.drawRoundedRect(bounds, corner + margin, corner + margin)
            painter.restore()
