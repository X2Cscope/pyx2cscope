from PyQt5.QtCore import QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .svgimage import MODES, choose_svg
from .variables import make_source, parse_source


def color_text(c):
    """Colour -> stored string: '#rrggbb', or '#aarrggbb' when it is semi-transparent."""
    return c.name(QColor.HexArgb if c.alpha() < 255 else QColor.HexRgb)


class ColorEditor(QWidget):
    """Swatch button that opens a colour dialog, plus a reset button that returns to the default."""

    picked = pyqtSignal(str)

    def __init__(self, value, fallback, title):
        super().__init__()
        self.value, self.fallback, self.title = value, fallback, title
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.button = QToolButton()
        self.button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.button.setIconSize(QSize(28, 14))
        self.button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.button.setToolTip("Click to choose a colour")
        self.button.clicked.connect(self._choose)
        self.reset = QToolButton()
        self.reset.setText("↺")
        self.reset.setToolTip("Reset to the default colour")
        self.reset.clicked.connect(lambda: self._emit(""))
        lay.addWidget(self.button, 1)
        lay.addWidget(self.reset)
        self._refresh()

    def _refresh(self):
        pm = QPixmap(28, 14)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        shown = self.value or self.fallback
        if shown:
            # checkerboard under the colour so transparency is visible
            for i in range(0, 28, 7):
                for j in range(0, 14, 7):
                    p.fillRect(i, j, 7, 7, QColor("#ffffff") if (i + j) // 7 % 2 == 0 else QColor("#d6d6d6"))
            p.fillRect(pm.rect(), QColor(shown))
        else:
            p.setPen(QPen(QColor("#898781"), 1, Qt.DashLine))
            p.drawLine(0, 13, 27, 0)
        p.setPen(QColor("#898781"))
        p.drawRect(pm.rect().adjusted(0, 0, -1, -1))
        p.end()
        self.button.setIcon(QIcon(pm))
        self.button.setText(self.value.upper() if self.value else "Default")
        self.reset.setEnabled(bool(self.value))

    def _choose(self):
        start = QColor(self.value or self.fallback or "#ffffff")
        c = QColorDialog.getColor(start, self, self.title, QColorDialog.ShowAlphaChannel)
        if c.isValid():
            self._emit(color_text(c))

    def _emit(self, v):
        self.value = v
        self._refresh()
        self.picked.emit(v)


class PropertyEditor(QScrollArea):
    """Edits name, geometry and type-specific properties of the primary selected widget."""

    aboutToChange = pyqtSignal(str)  # coalescing key ("" = never merged)
    changed = pyqtSignal()
    backgroundRequested = pyqtSignal()  # "Choose…" for the canvas background picture

    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.variable_provider = None  # callable -> (variable names, SFR names) of the connected target
        self.frame = None
        self._geo = {}
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumWidth(270)
        self._build_empty()

    def _build_empty(self, text="Select a widget on the canvas\nto edit its properties."):
        w = QLabel(text)
        w.setAlignment(Qt.AlignCenter)
        w.setStyleSheet("color:#898781; padding:20px;")
        self.setWidget(w)

    def refresh(self):
        # deferred: the request may come from a button inside the panel that is about to be replaced
        QTimer.singleShot(0, lambda: self.set_frame(self.frame, max(1, len(self.canvas.selection))))

    def _build_canvas(self):
        """Shown when nothing is selected: settings of the canvas itself."""
        c = self.canvas
        host = QWidget()
        outer = QVBoxLayout(host)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.addWidget(QLabel(f"<b>Canvas</b>  <span style='color:#898781'>{c.width()} × {c.height()} px</span>"))
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        pic = QWidget()
        pl = QHBoxLayout(pic)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(2)
        name = QLabel((c.bg_name or "picture.svg") if c.background else "(none)")
        name.setStyleSheet("" if c.background else "color:#898781")
        name.setToolTip(c.bg_name)
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        choose = QToolButton()
        choose.setText("Choose…")
        choose.setToolTip("Choose an SVG file as background picture")
        choose.clicked.connect(lambda: self.backgroundRequested.emit())
        clear = QToolButton()
        clear.setText("✕")
        clear.setToolTip("Remove the background picture")
        clear.setEnabled(bool(c.background))
        clear.clicked.connect(lambda: self._set_bg(data=""))
        pl.addWidget(name, 1)
        pl.addWidget(choose)
        pl.addWidget(clear)
        form.addRow("Background", pic)

        mode = QComboBox()
        mode.addItems(MODES)
        mode.setCurrentText(c.bg_mode)
        mode.setToolTip("fit: whole picture visible, aspect kept\n"
                        "fill: covers the canvas, aspect kept (edges may be cut)\n"
                        "stretch: exactly the canvas size, aspect ignored\n"
                        "center: natural size, centred\n"
                        "tile: natural size, repeated")
        mode.currentTextChanged.connect(lambda v: self._set_bg(mode=v))
        form.addRow("Scaling", mode)

        op = QSpinBox()
        op.setRange(0, 100)
        op.setSuffix(" %")
        op.setValue(c.bg_opacity)
        op.setKeyboardTracking(False)
        op.valueChanged.connect(lambda v: self._set_bg(opacity=v))
        form.addRow("Opacity", op)
        for w in (mode, op):
            w.setEnabled(bool(c.background))
        outer.addLayout(form)

        hint = QLabel("Select a widget on the canvas to edit its properties.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#898781; padding-top:12px;")
        outer.addWidget(hint)
        outer.addStretch(1)
        self.setWidget(host)

    def _set_bg(self, data=None, name=None, mode=None, opacity=None):
        c = self.canvas
        key = "canvas.bg_opacity" if opacity is not None else "canvas.bg_mode" if mode is not None else None
        if (data is None or data == c.background.data) and (mode is None or mode == c.bg_mode) \
                and (opacity is None or opacity == c.bg_opacity):
            return
        self.aboutToChange.emit(key or "")
        c.set_background(c.background.data if data is None else data,
                         c.bg_name if name is None else name, mode, opacity)
        self.changed.emit()
        if data is not None:
            self.refresh()

    def set_frame(self, frame, count=1):
        self.frame = frame
        if frame is None:
            self._build_canvas()
            return
        host = QWidget()
        outer = QVBoxLayout(host)
        outer.setContentsMargins(8, 8, 8, 8)
        head = QLabel(f"<b>{frame.spec.title}</b>" + (f"  <span style='color:#898781'>({count} selected)</span>" if count > 1 else ""))
        outer.addWidget(head)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        name = QLineEdit(frame.name)
        name.editingFinished.connect(lambda: self._rename(name))
        form.addRow("Name", name)

        geo_row = QWidget()
        gl = QHBoxLayout(geo_row)
        gl.setContentsMargins(0, 0, 0, 0)
        self._geo = {}
        for key in ("x", "y", "w", "h"):
            sb = QSpinBox()
            sb.setRange(0 if key in "xy" else 10, 10000)
            sb.setPrefix(f"{key.upper()} ")
            sb.setKeyboardTracking(False)
            sb.valueChanged.connect(self._geo_changed)
            gl.addWidget(sb)
            self._geo[key] = sb
        form.addRow("Geometry", geo_row)
        self.sync_geometry()
        outer.addLayout(form)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        outer.addWidget(line)

        form2 = QFormLayout()
        form2.setLabelAlignment(Qt.AlignRight)
        series_count = frame.props.get("series")
        others = [f.name for f in self.canvas.frames if f is not frame and f.spec.value]
        for pr in frame.spec.props:
            if series_count and pr.key[:1] == "s" and pr.key[1:2].isdigit() and int(pr.key[1]) > series_count:
                continue
            editor = self._editor(pr, frame.props[pr.key], others)
            form2.addRow(pr.label, editor)
        outer.addLayout(form2)
        outer.addStretch(1)
        self.setWidget(host)

    def _source_editor(self, key, value):
        """Data source editor: shows the chosen ELF variable, "..." picks one, "x" clears it."""
        from pyx2cscope.gui.qt.dialogs.variable_selection import VariableSelectionDialog

        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setPlaceholderText("no variable")
        parsed = parse_source(value)
        edit.setText(("SFR " if parsed and parsed[1] else "") + parsed[0] if parsed else "")
        edit.setToolTip("Variable of the ELF file that this widget uses as data")
        pick = QToolButton()
        pick.setText("…")
        pick.setToolTip("Choose a variable of the ELF file")
        clear = QToolButton()
        clear.setText("×")
        clear.setToolTip("Remove the variable")
        row.addWidget(edit, 1)
        row.addWidget(pick)
        row.addWidget(clear)

        def choose():
            names, sfrs = self.variable_provider() if self.variable_provider else ([], [])
            if not names and not sfrs:
                QMessageBox.information(self, "Variable", "Connect to the target in the Setup tab first, "
                                        "so the variables of the ELF file are available.")
                return
            dlg = VariableSelectionDialog(names, self, sfr_variables=sfrs)
            if dlg.exec_() and dlg.selected_variable:
                edit.setText(("SFR " if dlg.sfr_selected else "") + dlg.selected_variable)
                self._set(key, make_source(dlg.selected_variable, dlg.sfr_selected))

        def remove():
            edit.setText("")
            self._set(key, "")

        pick.clicked.connect(choose)
        clear.clicked.connect(remove)
        return w

    def _editor(self, pr, value, others):
        k = pr.key
        if pr.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
            w.toggled.connect(lambda v: self._set(k, v))
        elif pr.kind == "int":
            w = QSpinBox()
            w.setRange(int(max(pr.lo, -2**31)), int(min(pr.hi, 2**31 - 1)))
            w.setValue(int(value))
            w.setKeyboardTracking(False)
            w.valueChanged.connect(lambda v: self._set(k, v))
        elif pr.kind == "float":
            w = QDoubleSpinBox()
            w.setDecimals(3)
            w.setRange(pr.lo, pr.hi)
            w.setValue(float(value))
            w.setKeyboardTracking(False)
            w.valueChanged.connect(lambda v: self._set(k, v))
        elif pr.kind == "source":
            w = self._source_editor(k, value)
        elif pr.kind == "choice":
            w = QComboBox()
            opts = list(pr.options)
            if value not in opts:
                opts.append(value)
            w.addItems(opts)
            w.setCurrentText(value)
            w.currentTextChanged.connect(lambda v: self._set(k, v))
        elif pr.kind == "color":
            w = ColorEditor(str(value or ""), pr.fallback, pr.label)
            w.picked.connect(lambda v: self._set(k, v))
        elif pr.kind == "svg":
            w = self._svg_editor(value if isinstance(value, dict) else {})
        elif pr.kind == "file":
            w = QWidget()
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(2)
            edit = QLineEdit(str(value))
            edit.setPlaceholderText("asked when logging starts")
            edit.setToolTip("Path of the CSV file. Leave empty to be asked when you press Start")
            edit.editingFinished.connect(lambda: self._set(k, edit.text().strip()))
            browse = QToolButton()
            browse.setText("…")
            browse.setToolTip("Choose the CSV file")

            def pick():
                path, _ = QFileDialog.getSaveFileName(self, pr.label, edit.text() or "datalog.csv",
                                                      "CSV file (*.csv);;All files (*)",
                                                      options=QFileDialog.DontConfirmOverwrite)
                if path:
                    edit.setText(path)
                    self._set(k, path)
            browse.clicked.connect(pick)
            row.addWidget(edit, 1)
            row.addWidget(browse)
        elif pr.kind in ("text", "items"):
            w = QPlainTextEdit(str(value))
            w.setFixedHeight(80)
            if pr.kind == "items":
                w.setPlaceholderText("One item per line")
            w.textChanged.connect(lambda: self._set(k, w.toPlainText()))
        else:
            w = QLineEdit(str(value))
            w.textEdited.connect(lambda v: self._set(k, v))
        return w

    # ------------------------------------------------------------ SVG picture property
    def _svg_editor(self, value):
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        has = bool(value.get("svg"))
        name = QLabel((value.get("name") or "picture.svg") if has else "(none)")
        name.setStyleSheet("" if has else "color:#898781")
        name.setToolTip(value.get("name", ""))
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        lay.addWidget(name)
        row = QHBoxLayout()
        row.setSpacing(2)
        choose = QToolButton()
        choose.setText("Choose…")
        choose.setToolTip("Load an SVG file into this picture (double-clicking the widget does the same)")
        choose.clicked.connect(self.choose_picture)
        aspect = QToolButton()
        aspect.setText("Original aspect")
        aspect.setToolTip("Keep the width and set the height to the picture's own aspect ratio")
        aspect.setEnabled(has)
        aspect.clicked.connect(self.picture_aspect)
        clear = QToolButton()
        clear.setText("✕")
        clear.setToolTip("Remove the picture")
        clear.setEnabled(has)
        clear.clicked.connect(lambda: (self._set("picture", {"name": "", "svg": ""}), self.refresh()))
        row.addWidget(choose)
        row.addWidget(aspect)
        row.addWidget(clear)
        row.addStretch(1)
        lay.addLayout(row)
        return box

    def choose_picture(self):
        f = self.frame
        if f is None or f.type != "picture":
            return
        got = choose_svg(self, "SVG Picture")
        if not got:
            return
        first = not f.props.get("picture", {}).get("svg")
        self._set("picture", {"name": got[0], "svg": got[1]})
        if first:  # a freshly added picture takes the drawing's aspect ratio
            self.picture_aspect()
        self.refresh()

    def picture_aspect(self):
        f = self.frame
        if f is None or not f.inner.picture:
            return
        nat = f.inner.picture.natural_size()
        h = max(10, round(f.width() * nat.height() / nat.width()))
        if h != f.height():
            self.aboutToChange.emit("")
            f.resize(f.width(), h)
            self.canvas.geometryChanged.emit()

    def _set(self, key, value):
        f = self.frame
        if f is None or f.props.get(key) == value:
            return
        self.aboutToChange.emit(f"{f.name}.{key}")
        targets = [s for s in self.canvas.selection if s.type == f.type] or [f]
        for t in targets:
            t.props[key] = dict(value) if isinstance(value, dict) else value
            t.apply_props()
        self.changed.emit()
        if key == "series":
            self.set_frame(f, len(self.canvas.selection))

    def _rename(self, edit):
        f = self.frame
        new = edit.text().strip()
        if not new or new == f.name:
            return
        if self.canvas.frame_by_name(new):
            edit.setText(f.name)
            return
        self.aboutToChange.emit(f"{f.name}.name")
        old = f.name
        f.name = new
        for o in self.canvas.frames:
            for pk, pv in o.props.items():
                if pv == f"@{old}":
                    o.props[pk] = f"@{new}"
        self.changed.emit()

    def sync_geometry(self):
        if not self.frame or not self._geo:
            return
        g = self.frame.geometry()
        for key, v in zip("xywh", (g.x(), g.y(), g.width(), g.height())):
            sb = self._geo[key]
            sb.blockSignals(True)
            sb.setValue(v)
            sb.blockSignals(False)

    def _geo_changed(self):
        if not self.frame:
            return
        self.aboutToChange.emit(f"{self.frame.name}.geometry")
        v = {k: sb.value() for k, sb in self._geo.items()}
        self.frame.setGeometry(QRect(v["x"], v["y"], v["w"], v["h"]))
        self.changed.emit()
