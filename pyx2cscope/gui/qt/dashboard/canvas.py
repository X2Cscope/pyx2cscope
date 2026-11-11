import os

from PyQt5.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QRubberBand, QWidget

from . import theme
from .registry import SPECS, default_props
from .svgimage import EXTENSIONS, MODES, SvgPicture, read_svg_file, scaled_size

MIME = "application/x-dashboard-widget"
HANDLE = 7
MIN_W, MIN_H = 16, 10

# handle index -> (dx_left, dy_top, dx_right, dy_bottom) multipliers
HANDLES = {
    0: (1, 1, 0, 0), 1: (0, 1, 0, 0), 2: (0, 1, 1, 0), 3: (0, 0, 1, 0),
    4: (0, 0, 1, 1), 5: (0, 0, 0, 1), 6: (1, 0, 0, 1), 7: (1, 0, 0, 0),
}
CURSORS = {0: Qt.SizeFDiagCursor, 4: Qt.SizeFDiagCursor, 2: Qt.SizeBDiagCursor, 6: Qt.SizeBDiagCursor,
           1: Qt.SizeVerCursor, 5: Qt.SizeVerCursor, 3: Qt.SizeHorCursor, 7: Qt.SizeHorCursor}


def handle_rects(w, h):
    s = HANDLE
    xs = (0, (w - s) // 2, w - s)
    ys = (0, (h - s) // 2, h - s)
    pos = [(xs[0], ys[0]), (xs[1], ys[0]), (xs[2], ys[0]), (xs[2], ys[1]),
           (xs[2], ys[2]), (xs[1], ys[2]), (xs[0], ys[2]), (xs[0], ys[1])]
    return [QRect(x, y, s, s) for x, y in pos]


class Overlay(QWidget):
    """Edit-mode layer above a widget: draws selection and handles mouse move/resize."""

    def __init__(self, frame):
        super().__init__(frame)
        self.frame = frame
        self.setMouseTracking(True)
        self.hover = False

    def paintEvent(self, _):
        p = QPainter(self)
        sel = self.frame.selected
        if not (sel or self.hover):
            return
        col = QColor(theme.SELECTION)
        if not sel:
            col.setAlpha(110)
        p.setPen(QPen(col, 1, Qt.SolidLine if sel else Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        if sel and self.frame.canvas.primary() is self.frame:
            p.setBrush(QColor("#ffffff"))
            p.setPen(QPen(col, 1))
            for r in handle_rects(self.width(), self.height()):
                p.drawRect(r.adjusted(0, 0, -1, -1))
        elif sel:
            p.fillRect(self.rect(), QColor(42, 120, 214, 18))

    def _hit(self, pos):
        if self.frame.selected and self.frame.canvas.primary() is self.frame:
            for i, r in enumerate(handle_rects(self.width(), self.height())):
                if r.adjusted(-2, -2, 2, 2).contains(pos):
                    return i
        return None

    def enterEvent(self, _):
        self.hover = True
        self.update()

    def leaveEvent(self, _):
        self.hover = False
        self.update()

    def mousePressEvent(self, e):
        c = self.frame.canvas
        c.setFocus()
        if e.button() == Qt.RightButton:
            if not self.frame.selected:
                c.select([self.frame])
            c.context_menu(e.globalPos())
            return
        if e.button() != Qt.LeftButton:
            return
        handle = self._hit(e.pos())
        if e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
            c.toggle(self.frame)
            if not self.frame.selected:
                return
        elif not self.frame.selected:
            c.select([self.frame])
        c.begin_drag(self.frame, handle, e.globalPos())

    def mouseMoveEvent(self, e):
        c = self.frame.canvas
        if e.buttons() & Qt.LeftButton and c.dragging():
            c.drag_to(e.globalPos(), bool(e.modifiers() & Qt.AltModifier))
            return
        h = self._hit(e.pos())
        self.setCursor(CURSORS[h] if h is not None else Qt.SizeAllCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.frame.canvas.end_drag()

    def mouseDoubleClickEvent(self, e):
        self.frame.canvas.widgetActivated.emit(self.frame)


class WidgetFrame(QWidget):
    def __init__(self, canvas, type_, name, props):
        super().__init__(canvas)
        self.canvas = canvas
        self.type = type_
        self.spec = SPECS[type_]
        self.name = name
        self.props = props
        self.selected = False
        self.inner = self.spec.create()
        self.inner.setParent(self)
        self.overlay = Overlay(self)
        self.apply_props()

    def apply_props(self):
        self.spec.apply(self.inner, self.props)

    def resizeEvent(self, e):
        self.inner.setGeometry(self.rect())
        self.overlay.setGeometry(self.rect())

    @property
    def decoration(self):
        return bool(self.spec.extra.get("decoration"))

    def set_edit_mode(self, edit):
        self.overlay.setVisible(edit)
        if edit:
            self.overlay.raise_()
        if self.decoration:
            # in Run mode, pictures don't catch clicks meant for the widgets underneath
            self.setAttribute(Qt.WA_TransparentForMouseEvents, not edit)
        self.inner.update()

    def set_selected(self, s):
        self.selected = s
        self.overlay.update()

    def to_dict(self):
        g = self.geometry()
        return {"type": self.type, "name": self.name, "x": g.x(), "y": g.y(),
                "w": g.width(), "h": g.height(), "props": dict(self.props)}


class Canvas(QWidget):
    selectionChanged = pyqtSignal()
    geometryChanged = pyqtSignal()
    aboutToChange = pyqtSignal()
    widgetActivated = pyqtSignal(object)
    contextRequested = pyqtSignal(QPoint)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), theme.PAGE)
        self.setPalette(pal)
        self.frames = []
        self.selection = []
        self.grid = 10
        self.snap = True
        self.show_grid = True
        self.edit_mode = True
        self.background = SvgPicture()
        self.bg_name = ""
        self.bg_mode = "fit"
        self.bg_opacity = 100  # percent
        self._drag = None
        self._band = QRubberBand(QRubberBand.Rectangle, self)
        self._band_origin = None
        self.resize(1280, 800)

    # ------------------------------------------------------------ model
    def unique_name(self, type_):
        used = {f.name for f in self.frames}
        i = 1
        while f"{type_}{i}" in used:
            i += 1
        return f"{type_}{i}"

    def add_widget(self, type_, rect, props=None, name=None, new=True):
        """new=True: a widget added by the user. Decorations (SVG pictures) are then stacked
        behind the normal widgets. new=False (loading/undo) keeps the stacking order as given."""
        props = {**default_props(type_), **(props or {})}
        f = WidgetFrame(self, type_, name or self.unique_name(type_), props)
        f.setGeometry(rect)
        f.set_edit_mode(self.edit_mode)
        f.show()
        self.frames.append(f)
        if new and f.decoration:
            self.stack_behind_widgets(f)
        return f

    def stack_behind_widgets(self, f):
        """Places f above the other decorations but under every normal widget."""
        order = [c for c in self.children() if isinstance(c, WidgetFrame) and c is not f]
        first = next((c for c in order if not c.decoration), None)
        if first is not None:
            f.stackUnder(first)

    def add_svg_file(self, path, pos):
        """Creates an SVG Picture widget for a dropped file, centred at pos. Returns the frame or None."""
        try:
            data = read_svg_file(path)
        except (OSError, ValueError, EOFError):
            return None
        pic = SvgPicture()
        pic.set_data(data)
        w, h = scaled_size(pic)
        w, h = min(w, self.width()), min(h, self.height())
        x = max(0, min(self._snap(pos.x() - w // 2), self.width() - w))
        y = max(0, min(self._snap(pos.y() - h // 2), self.height() - h))
        return self.add_widget("picture", QRect(x, y, w, h),
                               {"picture": {"name": os.path.basename(path), "svg": data}})

    def remove(self, frames):
        for f in frames:
            self.frames.remove(f)
            f.deleteLater()
        self.selection = [s for s in self.selection if s not in frames]
        self.selectionChanged.emit()

    def clear(self):
        self.remove(list(self.frames))

    def frame_by_name(self, name):
        return next((f for f in self.frames if f.name == name), None)

    def set_background(self, data="", name="", mode=None, opacity=None):
        self.background.set_data(data)
        self.bg_name = name if data else ""
        if mode in MODES:
            self.bg_mode = mode
        if opacity is not None:
            self.bg_opacity = max(0, min(100, int(opacity)))
        self.update()

    def to_dict(self):
        ordered = sorted(self.frames, key=lambda f: self.children().index(f))
        c = {"width": self.width(), "height": self.height(), "grid": self.grid}
        if self.background:
            c["background"] = {"name": self.bg_name, "mode": self.bg_mode, "opacity": self.bg_opacity,
                               "svg": self.background.data}
        return {"canvas": c, "widgets": [f.to_dict() for f in ordered]}

    def load_dict(self, d):
        self.clear()
        c = d.get("canvas", {})
        self.resize(c.get("width", 1280), c.get("height", 800))
        self.grid = c.get("grid", self.grid)
        bg = c.get("background") or {}
        self.set_background(bg.get("svg", ""), bg.get("name", ""), bg.get("mode", "fit"), bg.get("opacity", 100))
        for w in d.get("widgets", []):
            if w.get("type") in SPECS:
                self.add_widget(w["type"], QRect(w["x"], w["y"], w["w"], w["h"]), w.get("props"), w.get("name"),
                                new=False)
        self.update()

    # ------------------------------------------------------------ selection
    def primary(self):
        return self.selection[-1] if self.selection else None

    def select(self, frames):
        for f in self.selection:
            f.set_selected(False)
        self.selection = list(frames)
        for f in self.selection:
            f.set_selected(True)
        for f in self.frames:
            f.overlay.update()
        self.selectionChanged.emit()

    def toggle(self, frame):
        sel = [f for f in self.selection if f is not frame]
        if not frame.selected:
            sel.append(frame)
        self.select(sel)

    # ------------------------------------------------------------ drag / resize
    def _snap(self, v, force_off=False):
        if not self.snap or force_off or self.grid <= 1:
            return v
        return round(v / self.grid) * self.grid

    def dragging(self):
        return self._drag is not None

    def begin_drag(self, frame, handle, gpos):
        self._drag = {"frame": frame, "handle": handle, "start": gpos, "moved": False,
                      "geoms": {f: f.geometry() for f in self.selection}}

    def drag_to(self, gpos, free):
        d = self._drag
        delta = gpos - d["start"]
        if not d["moved"]:
            if delta.manhattanLength() < 3:
                return
            self.aboutToChange.emit()
            d["moved"] = True
        if d["handle"] is None:
            anchor = d["geoms"][d["frame"]]
            nx = self._snap(anchor.x() + delta.x(), free) - anchor.x()
            ny = self._snap(anchor.y() + delta.y(), free) - anchor.y()
            for f, g in d["geoms"].items():
                x = max(0, min(g.x() + nx, self.width() - g.width()))
                y = max(0, min(g.y() + ny, self.height() - g.height()))
                f.move(x, y)
        else:
            f, g = d["frame"], d["geoms"][d["frame"]]
            ml, mt, mr, mb = HANDLES[d["handle"]]
            l, t, r, b = g.left(), g.top(), g.left() + g.width(), g.top() + g.height()
            if ml:
                l = min(self._snap(l + delta.x(), free), r - MIN_W)
            if mr:
                r = max(self._snap(r + delta.x(), free), l + MIN_W)
            if mt:
                t = min(self._snap(t + delta.y(), free), b - MIN_H)
            if mb:
                b = max(self._snap(b + delta.y(), free), t + MIN_H)
            l, t = max(0, l), max(0, t)
            r, b = min(self.width(), r), min(self.height(), b)
            f.setGeometry(QRect(l, t, r - l, b - t))
        self.geometryChanged.emit()

    def end_drag(self):
        self._drag = None

    def nudge(self, dx, dy, resize=False):
        if not self.selection:
            return
        self.aboutToChange.emit()
        for f in self.selection:
            g = f.geometry()
            if resize:
                f.resize(max(MIN_W, g.width() + dx), max(MIN_H, g.height() + dy))
            else:
                f.move(max(0, g.x() + dx), max(0, g.y() + dy))
        self.geometryChanged.emit()

    # ------------------------------------------------------------ mode & painting
    def set_edit_mode(self, edit):
        self.edit_mode = edit
        if not edit:
            self.select([])
        for f in self.frames:
            f.set_edit_mode(edit)
        self.setAcceptDrops(edit)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        self.background.paint(p, self.width(), self.height(), self.bg_mode, self.bg_opacity / 100,
                              self.devicePixelRatioF())
        if not (self.edit_mode and self.show_grid and self.grid >= 4):
            return
        p.setPen(QPen(theme.AXIS, 1))
        step = self.grid * max(1, round(20 / self.grid))
        for x in range(0, self.width(), step):
            for y in range(0, self.height(), step):
                p.drawPoint(x, y)

    # ------------------------------------------------------------ mouse on empty area
    def mousePressEvent(self, e):
        self.setFocus()
        if not self.edit_mode:
            return
        if e.button() == Qt.LeftButton:
            if not (e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)):
                self.select([])
            self._band_origin = e.pos()
            self._band.setGeometry(QRect(self._band_origin, QSize()))
            self._band.show()
        elif e.button() == Qt.RightButton:
            self.select([])
            self.context_menu(e.globalPos())

    def mouseMoveEvent(self, e):
        if self._band_origin is not None:
            self._band.setGeometry(QRect(self._band_origin, e.pos()).normalized())

    def mouseReleaseEvent(self, e):
        if self._band_origin is None:
            return
        r = self._band.geometry()
        self._band.hide()
        self._band_origin = None
        if r.width() > 2 or r.height() > 2:
            extra = [f for f in self.frames if r.intersects(f.geometry()) and f not in self.selection]
            self.select(self.selection + extra)

    def context_menu(self, gpos):
        self.contextRequested.emit(gpos)

    # ------------------------------------------------------------ drop from palette
    @staticmethod
    def _svg_paths(md):
        return [u.toLocalFile() for u in md.urls()
                if u.isLocalFile() and u.toLocalFile().lower().endswith(EXTENSIONS)] if md.hasUrls() else []

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME) or self._svg_paths(e.mimeData()):
            e.acceptProposedAction()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, e):
        paths = self._svg_paths(e.mimeData())
        if paths and not e.mimeData().hasFormat(MIME):
            # .svg files dragged from Explorer: one SVG Picture widget each, slightly cascaded
            self.aboutToChange.emit()
            pos = e.pos()
            new = [f for i, p in enumerate(paths) if (f := self.add_svg_file(p, pos + QPoint(i, i) * 20))]
            if new:
                self.select(new)
                self.setFocus()
            e.acceptProposedAction()
            return
        type_ = bytes(e.mimeData().data(MIME)).decode()
        if type_ not in SPECS:
            return
        self.aboutToChange.emit()
        w, h = SPECS[type_].size
        pos = e.pos()
        x = max(0, min(self._snap(pos.x() - w // 2), self.width() - w))
        y = max(0, min(self._snap(pos.y() - h // 2), self.height() - h))
        f = self.add_widget(type_, QRect(x, y, w, h))
        self.select([f])
        self.setFocus()
        e.acceptProposedAction()
