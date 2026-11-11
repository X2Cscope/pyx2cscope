import math
from collections import deque

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from . import theme


def nice_ticks(lo, hi, target=5):
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / max(1, target)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.ceil(lo / step - 1e-9) * step
    ticks = []
    v = start
    while v <= hi + step * 1e-6:
        ticks.append(round(v, 10))
        v += step
    return ticks


def fmt(v):
    if abs(v) >= 10000:
        return f"{v / 1000:.0f}K"
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:.2f}".rstrip("0").rstrip(".")


class _Colored:
    """Custom colours set from the widget properties ('' or missing = theme default)."""

    colors = {}

    def color(self, key, fallback):
        c = self.colors.get(key)
        return QColor(c) if c else QColor(fallback)


class _PlotBase(_Colored, QWidget):
    def __init__(self):
        super().__init__()
        self.colors = {}
        self.title = ""
        self.show_grid = True
        self.setMinimumSize(80, 60)
        self.setAutoFillBackground(False)

    def _frame(self, p):
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(theme.GRID, 1))
        p.setBrush(self.color("bg", theme.SURFACE))
        p.drawRoundedRect(r, 6, 6)
        top = 8
        if self.title:
            f = QFont(self.font())
            f.setPointSizeF(10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(self.color("fg", theme.INK))
            p.drawText(QRectF(10, 6, self.width() - 20, 20), Qt.AlignLeft | Qt.AlignVCenter, self.title)
            top = 30
        return top

    def _axes(self, p, plot, xlo, xhi, ylo, yhi, xlabel=None):
        grid = self.color("grid", theme.GRID)
        axis = self.color("grid", theme.AXIS)
        muted = self.color("fg", theme.MUTED)
        small = QFont(self.font())
        small.setPointSizeF(8)
        p.setFont(small)
        for yv in nice_ticks(ylo, yhi, max(2, int(plot.height() / 40))):
            y = plot.bottom() - (yv - ylo) / (yhi - ylo) * plot.height()
            if self.show_grid:
                p.setPen(QPen(grid, 1))
                p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(muted)
            p.drawText(QRectF(0, y - 8, plot.left() - 6, 16), Qt.AlignRight | Qt.AlignVCenter, fmt(yv))
        for xv in nice_ticks(xlo, xhi, max(2, int(plot.width() / 70))):
            x = plot.left() + (xv - xlo) / (xhi - xlo) * plot.width()
            if self.show_grid:
                p.setPen(QPen(grid, 1))
                p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            p.setPen(muted)
            p.drawText(QRectF(x - 30, plot.bottom() + 3, 60, 14), Qt.AlignCenter, fmt(xv))
        p.setPen(QPen(axis, 1))
        p.drawLine(plot.bottomLeft(), plot.bottomRight())
        p.drawLine(plot.bottomLeft(), plot.topLeft())
        if xlabel:
            p.setPen(muted)
            p.drawText(QRectF(plot.left(), plot.bottom() + 16, plot.width(), 14), Qt.AlignRight, xlabel)


class YTGraph(_PlotBase):
    def __init__(self):
        super().__init__()
        self.timespan = 10.0
        self.y_min, self.y_max = -1.0, 1.0
        self.autoscale = False
        self.line_width = 2.0
        self.series_names = []
        self.buffers = []

    def set_series(self, names):
        if names != self.series_names:
            self.series_names = list(names)
            self.buffers = [deque() for _ in names]

    def push(self, t, values):
        for buf, v in zip(self.buffers, values):
            buf.append((t, v))
            while buf and buf[0][0] < t - self.timespan:
                buf.popleft()
        self.update()

    def clear(self):
        for b in self.buffers:
            b.clear()

    def paintEvent(self, _):
        p = QPainter(self)
        top = self._frame(p)
        legend_h = 18 if len(self.series_names) >= 2 else 0
        plot = QRectF(46, top + legend_h + 4, self.width() - 58, self.height() - top - legend_h - 40)
        if plot.width() < 20 or plot.height() < 20:
            return
        ylo, yhi = self.y_min, self.y_max
        pts = [v for b in self.buffers for _, v in b]
        if self.autoscale and pts:
            ylo, yhi = min(pts), max(pts)
            pad = (yhi - ylo) * 0.1 or 1.0
            ylo, yhi = ylo - pad, yhi + pad
        if yhi <= ylo:
            yhi = ylo + 1
        self._axes(p, plot, -self.timespan, 0, ylo, yhi, "time (s)")
        tnow = max((b[-1][0] for b in self.buffers if b), default=0)
        p.setClipRect(plot.adjusted(-1, -6, 6, 6))
        for i, buf in enumerate(self.buffers):
            if len(buf) < 2:
                continue
            col = self.series_color(i)
            path = QPainterPath()
            for j, (t, v) in enumerate(buf):
                x = plot.right() - (tnow - t) / self.timespan * plot.width()
                y = plot.bottom() - (min(max(v, ylo), yhi) - ylo) / (yhi - ylo) * plot.height()
                path.moveTo(x, y) if j == 0 else path.lineTo(x, y)
            p.setPen(QPen(col, self.line_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
            end = path.currentPosition()
            p.setPen(QPen(self.color("bg", theme.SURFACE), 2))
            p.setBrush(col)
            p.drawEllipse(end, 4.5, 4.5)
        p.setClipping(False)
        if legend_h:
            self._legend(p, plot.left(), top)

    def series_color(self, i):
        return self.color(f"s{i + 1}", theme.SERIES[i % len(theme.SERIES)])

    def _legend(self, p, x, y):
        f = QFont(self.font())
        f.setPointSizeF(8)
        p.setFont(f)
        fm = p.fontMetrics()
        for i, name in enumerate(self.series_names):
            col = self.series_color(i)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(QRectF(x, y + 5, 12, 4), 2, 2)
            p.setPen(self.color("fg", theme.INK_2))
            p.drawText(QPointF(x + 16, y + 11), name)
            x += 30 + fm.horizontalAdvance(name)


class XYGraph(_PlotBase):
    def __init__(self):
        super().__init__()
        self.x_min, self.x_max = -1.0, 1.0
        self.y_min, self.y_max = -1.0, 1.0
        self.trail = 300
        self.mode = "line"
        self.line_width = 2.0
        self.points = deque()

    def push(self, x, y):
        self.points.append((x, y))
        while len(self.points) > max(2, self.trail):
            self.points.popleft()
        self.update()

    def clear(self):
        self.points.clear()

    def paintEvent(self, _):
        p = QPainter(self)
        top = self._frame(p)
        plot = QRectF(46, top + 4, self.width() - 58, self.height() - top - 26)
        if plot.width() < 20 or plot.height() < 20:
            return
        xlo, xhi = self.x_min, self.x_max if self.x_max > self.x_min else self.x_min + 1
        ylo, yhi = self.y_min, self.y_max if self.y_max > self.y_min else self.y_min + 1
        self._axes(p, plot, xlo, xhi, ylo, yhi)
        if not self.points:
            return
        col = self.color("line", theme.SERIES[0])

        def to_px(x, y):
            return QPointF(plot.left() + (x - xlo) / (xhi - xlo) * plot.width(),
                           plot.bottom() - (y - ylo) / (yhi - ylo) * plot.height())

        p.setClipRect(plot.adjusted(-6, -6, 6, 6))
        pts = [to_px(x, y) for x, y in self.points]
        if self.mode == "line" and len(pts) > 1:
            path = QPainterPath(pts[0])
            for q in pts[1:]:
                path.lineTo(q)
            p.setPen(QPen(col, self.line_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        elif self.mode == "scatter":
            p.setPen(Qt.NoPen)
            n = len(pts)
            for i, q in enumerate(pts):
                c = QColor(col)
                c.setAlphaF(0.15 + 0.85 * (i + 1) / n)
                p.setBrush(c)
                p.drawEllipse(q, 3, 3)
        p.setPen(QPen(self.color("bg", theme.SURFACE), 2))
        p.setBrush(col)
        p.drawEllipse(pts[-1], 5, 5)


class Gauge(_Colored, QWidget):
    def __init__(self):
        super().__init__()
        self.colors = {}
        self.title = ""
        self.units = ""
        self.minimum, self.maximum = 0.0, 100.0
        self.value = 0.0
        self.warning, self.critical = 70.0, 90.0
        self.decimals = 1
        self.style = "arc 270°"
        self.major_ticks = 5
        self.show_frame = False
        self.setMinimumSize(80, 80)

    def set_value(self, v):
        self.value = v
        self.update()

    def _color(self):
        if self.value >= self.critical:
            return self.color("critical", theme.STATUS_CRITICAL)
        if self.value >= self.warning:
            return self.color("warning", theme.STATUS_WARNING)
        return self.color("arc", theme.ACCENT)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # transparent by default: only a chosen background colour and/or the optional frame are drawn
        bg = self.color("bg", QColor(0, 0, 0, 0))
        if bg.alpha() or self.show_frame:
            p.setPen(QPen(theme.GRID, 1) if self.show_frame else Qt.NoPen)
            p.setBrush(bg if bg.alpha() else Qt.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
        semi = self.style.startswith("semi")
        start, span = (180.0, -180.0) if semi else (225.0, -270.0)
        top = 26 if self.title else 8
        avail_w = self.width() - 24
        avail_h = self.height() - top - 12
        radius = min(avail_w / 2, avail_h * (0.9 if semi else 0.5))
        if radius < 15:
            return
        thick = max(6.0, radius * 0.14)
        cx = self.width() / 2
        cy = top + (radius + (avail_h - radius) * 0.35 if semi else avail_h / 2 + 4)
        arc = QRectF(cx - radius + thick / 2, cy - radius + thick / 2, 2 * radius - thick, 2 * radius - thick)
        rng = self.maximum - self.minimum or 1
        frac = min(max((self.value - self.minimum) / rng, 0), 1)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(self.color("track", theme.ACCENT_TRACK), thick, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc, int(start * 16), int(span * 16))
        if frac > 0:
            p.setPen(QPen(self._color(), thick, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(arc, int(start * 16), int(span * frac * 16))
        f = QFont(self.font())
        f.setPointSizeF(7.5)
        p.setFont(f)
        p.setPen(self.color("fg", theme.MUTED))
        inner = radius - thick - 8
        for i in range(self.major_ticks + 1):
            k = i / max(1, self.major_ticks)
            ang = math.radians(start + span * k)
            tv = self.minimum + rng * k
            tx, ty = cx + math.cos(ang) * inner, cy - math.sin(ang) * inner
            p.drawText(QRectF(tx - 22, ty - 8, 44, 16), Qt.AlignCenter, fmt(round(tv, 2)))
        vf = QFont(self.font())
        vf.setPointSizeF(max(9.0, radius * 0.22))
        vf.setBold(True)
        p.setFont(vf)
        p.setPen(self.color("fg", theme.INK))
        txt = f"{self.value:.{self.decimals}f}"
        vy = cy - radius * (0.3 if semi else 0.15)
        p.drawText(QRectF(cx - radius, vy - radius * 0.2, 2 * radius, radius * 0.4), Qt.AlignCenter, txt)
        if self.units:
            uf = QFont(self.font())
            uf.setPointSizeF(max(7.0, radius * 0.09))
            p.setFont(uf)
            p.setPen(self.color("fg", theme.INK_2))
            p.drawText(QRectF(cx - radius, vy + radius * 0.18, 2 * radius, radius * 0.2), Qt.AlignCenter, self.units)
        if self.title:
            tf = QFont(self.font())
            tf.setPointSizeF(10)
            tf.setBold(True)
            p.setFont(tf)
            p.setPen(self.color("fg", theme.INK))
            p.drawText(QRectF(10, 4, self.width() - 20, 20), Qt.AlignLeft | Qt.AlignVCenter, self.title)


class ValueSlider(QWidget):
    valueChanged = pyqtSignal(float)
    userChanged = pyqtSignal(float)  # the value was moved by the user, not set by a data source

    def __init__(self):
        super().__init__()
        self.minimum, self.maximum, self.step = 0.0, 100.0, 1.0
        self.decimals = 0
        self._silent = False
        self._title = QLabel()
        self._val = QLabel()
        self._val.setMinimumWidth(40)
        self._val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._slider = QSlider()
        self._slider.valueChanged.connect(self._changed)
        self._layout = None
        self.set_orientation("horizontal")

    def set_orientation(self, o):
        horiz = o == "horizontal"
        if self._layout is not None:
            for w in (self._title, self._slider, self._val):
                self._layout.removeWidget(w)
            QWidget().setLayout(self._layout)
        self._slider.setOrientation(Qt.Horizontal if horiz else Qt.Vertical)
        lay = QHBoxLayout() if horiz else QVBoxLayout()
        lay.setContentsMargins(6, 4, 6, 4)
        lay.addWidget(self._title)
        lay.addWidget(self._slider, 1)
        lay.addWidget(self._val)
        if not horiz:
            for w in (self._title, self._val, self._slider):
                lay.setAlignment(w, Qt.AlignHCenter)
            self._val.setAlignment(Qt.AlignCenter)
        self._layout = lay
        self.setLayout(lay)

    def configure(self, title, mn, mx, step, value, decimals, ticks):
        self._title.setText(title)
        self._title.setVisible(bool(title))
        self.minimum, self.maximum = mn, max(mx, mn + 1e-9)
        self.step = step if step > 0 else 1.0
        self.decimals = decimals
        n = max(1, round((self.maximum - self.minimum) / self.step))
        self._slider.blockSignals(True)
        self._slider.setRange(0, n)
        self._slider.setTickPosition(QSlider.TicksBelow if ticks else QSlider.NoTicks)
        self._slider.setTickInterval(max(1, n // 10))
        self._slider.setValue(round((value - self.minimum) / self.step))
        self._slider.blockSignals(False)
        self._update_label()

    def value(self):
        return self.minimum + self._slider.value() * self.step

    def show_value(self, show):
        self._val.setVisible(show)

    def is_dragged(self):
        return self._slider.isSliderDown()

    def set_value_silently(self, v):
        """Move the slider to v (a value read from the target) without reporting a user change."""
        self._silent = True
        try:
            self._slider.setValue(round((min(max(v, self.minimum), self.maximum) - self.minimum) / self.step))
        finally:
            self._silent = False

    def _changed(self, _):
        self._update_label()
        self.valueChanged.emit(self.value())
        if not self._silent:
            self.userChanged.emit(self.value())

    def _update_label(self):
        self._val.setText(f"{self.value():.{self.decimals}f}")
