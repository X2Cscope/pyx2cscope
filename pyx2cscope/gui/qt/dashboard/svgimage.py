"""Scalable SVG pictures: the canvas background and the 'SVG Picture' widget.

The SVG text is embedded in the dashboard file (not linked), so a dashboard stays complete when
it is moved or shared. Rendering is cached in a pixmap per size/mode, so live updates in Run mode
don't re-render the vector drawing on every repaint.
"""

import gzip
import os

from PyQt5.QtCore import QByteArray, QRectF, QSizeF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget

MODES = ("fit", "fill", "stretch", "center", "tile")
FILTER = "SVG image (*.svg *.svgz)"
EXTENSIONS = (".svg", ".svgz")


def parse(data):
    r = QSvgRenderer(QByteArray(data.encode("utf-8")))
    if not r.isValid():
        return None
    r.setAspectRatioMode(Qt.IgnoreAspectRatio)  # we compute the target rectangle ourselves
    return r


def read_svg_file(path):
    """Returns the SVG text of a .svg/.svgz file. Raises OSError or ValueError."""
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    try:
        data = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        data = raw.decode("latin-1")
    if parse(data) is None:
        raise ValueError("The file is not a valid SVG image.")
    return data


def choose_svg(parent, title):
    """File dialog -> (file name, svg text), or None if cancelled / invalid (an error is shown)."""
    path, _ = QFileDialog.getOpenFileName(parent, title, "", FILTER)
    if not path:
        return None
    try:
        return os.path.basename(path), read_svg_file(path)
    except (OSError, ValueError, EOFError) as e:
        QMessageBox.critical(parent, title, f"Could not load {path}:\n{e}")
        return None


class SvgPicture:
    def __init__(self):
        self.data = ""
        self.renderer = None
        self._cache = None
        self._key = None

    def set_data(self, data):
        data = data or ""
        if data == self.data:
            return
        self.data = data
        self.renderer = parse(data) if data else None
        self._cache = None

    def __bool__(self):
        return self.renderer is not None

    def natural_size(self):
        s = QSizeF(self.renderer.defaultSize())
        if s.isEmpty():
            s = self.renderer.viewBoxF().size()
        return s if not s.isEmpty() else QSizeF(100, 100)

    def target_rect(self, w, h, mode):
        nat = self.natural_size()
        if mode in ("fit", "fill"):
            k = (min if mode == "fit" else max)(w / nat.width(), h / nat.height())
            nat = QSizeF(nat.width() * k, nat.height() * k)
        elif mode != "center":  # stretch
            return QRectF(0, 0, w, h)
        return QRectF((w - nat.width()) / 2, (h - nat.height()) / 2, nat.width(), nat.height())

    def _render(self, w, h, mode, dpr):
        pm = QPixmap(max(1, round(w * dpr)), max(1, round(h * dpr)))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        if mode == "tile":
            nat = self.natural_size()
            tw, th = max(8.0, nat.width()), max(8.0, nat.height())
            tile = QPixmap(max(1, round(tw * dpr)), max(1, round(th * dpr)))
            tile.setDevicePixelRatio(dpr)
            tile.fill(Qt.transparent)
            tp = QPainter(tile)
            tp.setRenderHint(QPainter.Antialiasing)
            self.renderer.render(tp, QRectF(0, 0, tw, th))
            tp.end()
            p.fillRect(QRectF(0, 0, w, h), QBrush(tile))
        else:
            self.renderer.render(p, self.target_rect(w, h, mode))
        p.end()
        return pm

    def paint(self, painter, w, h, mode="fit", opacity=1.0, dpr=1.0):
        if not self or w <= 0 or h <= 0 or opacity <= 0:
            return
        key = (w, h, mode, dpr)
        if self._cache is None or self._key != key:
            self._cache, self._key = self._render(w, h, mode, dpr), key
        painter.save()
        painter.setOpacity(opacity)
        painter.drawPixmap(0, 0, self._cache)
        painter.restore()


def scaled_size(picture, box=300, minimum=40):
    """Natural size of a picture, shrunk to fit a box x box square (aspect kept), at least `minimum`."""
    nat = picture.natural_size()
    w, h = nat.width(), nat.height()
    k = min(1.0, box / w, box / h)
    w, h = w * k, h * k
    if max(w, h) < minimum:
        k = minimum / max(w, h)
        w, h = w * k, h * k
    return max(16, round(w)), max(10, round(h))


class PictureWidget(QWidget):
    """Canvas widget showing an SVG picture scaled to its frame (the 'SVG Picture' widget)."""

    def __init__(self):
        super().__init__()
        self.picture = SvgPicture()
        self.mode = "fit"
        self.opacity = 1.0
        self.fill = None
        self.setMinimumSize(4, 4)

    def _editing(self):
        canvas = getattr(self.parentWidget(), "canvas", None)
        return canvas is None or canvas.edit_mode

    def paintEvent(self, _):
        p = QPainter(self)
        if self.fill is not None:
            p.fillRect(self.rect(), self.fill)
        if self.picture:
            self.picture.paint(p, self.width(), self.height(), self.mode, self.opacity, self.devicePixelRatioF())
        elif self._editing():  # empty picture: placeholder in edit mode only
            p.setPen(QPen(QColor("#898781"), 1, Qt.DashLine))
            p.drawRect(self.rect().adjusted(0, 0, -1, -1))
            p.drawText(self.rect().adjusted(4, 4, -4, -4), Qt.AlignCenter | Qt.TextWordWrap,
                       "SVG Picture\nchoose a file in Properties")
