import copy
import json
import time

from PyQt5.QtCore import QMimeData, QPoint, QRect, QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QDrag, QFont, QIcon, QKeySequence, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
)

from .canvas import MIME, Canvas
from .properties import PropertyEditor
from .registry import SPECS
from .svgimage import choose_svg
from .variables import VariableBridge, parse_source

FILTER = "Dashboard (*.dash.json *.json)"


class Palette(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setIndentation(12)
        self.setIconSize(QSize(20, 20))
        cats = {}
        for spec in SPECS.values():
            if spec.category not in cats:
                top = QTreeWidgetItem([spec.category])
                top.setFlags(Qt.ItemIsEnabled)
                f = top.font(0)
                f.setBold(True)
                top.setFont(0, f)
                self.addTopLevelItem(top)
                cats[spec.category] = top
            it = QTreeWidgetItem([spec.title])
            it.setData(0, Qt.UserRole, spec.type)
            it.setIcon(0, self._icon(spec.icon))
            it.setToolTip(0, "Drag onto the canvas (or double-click to add)")
            cats[spec.category].addChild(it)
        self.expandAll()

    @staticmethod
    def _icon(text):
        pm = QPixmap(20, 20)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setPen(QColor("#52514e"))
        f = QFont()
        f.setPointSizeF(9 if len(text) < 3 else 7)
        p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignCenter, text)
        p.end()
        return QIcon(pm)

    def startDrag(self, actions):
        it = self.currentItem()
        t = it and it.data(0, Qt.UserRole)
        if not t:
            return
        md = QMimeData()
        md.setData(MIME, t.encode())
        d = QDrag(self)
        d.setMimeData(md)
        d.setPixmap(it.icon(0).pixmap(24, 24))
        d.exec_(Qt.CopyAction)


class RunWindow(QMainWindow):
    """Separate top-level window that hosts the dashboard while Run mode is active."""

    def __init__(self, on_close):
        super().__init__()
        self._on_close = on_close
        self._placed = False

    def show_for(self, content, size, anchor):
        self.setCentralWidget(content)
        if not self._placed:
            # First run: size the window to fit the canvas (capped to the screen) and centre it.
            avail = (anchor.screen() or QApplication.primaryScreen()).availableGeometry()
            extra_h = sum(tb.sizeHint().height() for tb in self.findChildren(QToolBar))
            w = min(size.width() + 4, int(avail.width() * 0.95))
            h = min(size.height() + extra_h + 4, int(avail.height() * 0.9))
            self.resize(w, h)
            g = self.frameGeometry()
            g.moveCenter(anchor.frameGeometry().center())
            g.moveTopLeft(QPoint(max(avail.left(), g.left()), max(avail.top(), g.top())))
            self.move(g.topLeft())
            self._placed = True
        self.show()
        self.raise_()
        self.activateWindow()

    def take_content(self):
        self.hide()
        return self.takeCentralWidget()

    def closeEvent(self, e):
        # Closing the run window means "stop running"; the content is handed back to the editor.
        e.ignore()
        self._on_close()


class DashboardWindow(QMainWindow):
    """The dashboard editor, embedded as a tab of the pyX2Cscope window.

    Widgets can use a variable of the connected target as data source (``$name``, see ``variables.py``).
    """

    def __init__(self, app_state=None, parent=None):
        """Initialize the dashboard editor.

        Args:
            app_state: The pyX2Cscope AppState that provides the variables, or None for generators only.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.Widget)  # a tab page, not a top-level window
        self.app_state = app_state
        self.bridge = VariableBridge(app_state.read_variable_value, self._write_variable) if app_state is not None else None
        self.resize(1500, 920)
        self.path = None
        self.dirty = False
        self.undo_stack, self.redo_stack = [], []
        self._coalesce = None
        self.clipboard = None
        self.t0 = time.perf_counter()

        self.canvas = Canvas()
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        scroll.setStyleSheet("QScrollArea{background:#e1e0d9;}")
        self.scroll = scroll
        self.setCentralWidget(scroll)

        self.run_placeholder = QLabel(
            "The dashboard is running in a separate window.\n\n"
            "Press F5, click ■ Stop or close the run window to return to editing.")
        self.run_placeholder.setAlignment(Qt.AlignCenter)
        self.run_placeholder.setStyleSheet("QLabel{background:#e1e0d9; color:#52514e; font-size:11pt;}")

        self.palette_tree = Palette()
        self.palette_tree.itemDoubleClicked.connect(self._palette_add)
        dock = QDockWidget("Widgets", self)
        dock.setWidget(self.palette_tree)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self.palette_dock = dock

        self.props = PropertyEditor(self.canvas)
        self.props.variable_provider = self.variable_names
        pdock = QDockWidget("Properties", self)
        pdock.setWidget(self.props)
        pdock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, pdock)
        self.props_dock = pdock

        self.canvas.selectionChanged.connect(self._on_selection)
        self.canvas.geometryChanged.connect(self._on_geometry)
        self.canvas.aboutToChange.connect(lambda: self.checkpoint())
        self.canvas.contextRequested.connect(self._context_menu)
        self.canvas.widgetActivated.connect(self._activated)
        self.props.aboutToChange.connect(self.checkpoint)
        self.props.changed.connect(self._mark_dirty)
        self.props.backgroundRequested.connect(self.choose_background)

        self._build_actions()

        # Run mode shows the dashboard in its own window; F5 / Stop / closing it returns to editing.
        self.run_window = RunWindow(self._stop_run)
        rtb = self.run_window.addToolBar("Run")
        rtb.setObjectName("run")
        rtb.setMovable(False)
        rtb.addAction(self.a_run)
        self.run_window.addAction(self.a_run)

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.status = QLabel()
        self.statusBar().addPermanentWidget(self.status)
        self._update_title()
        self._on_selection()
        self._load_example()

    # ------------------------------------------------------------ actions & toolbar
    def _act(self, text, slot, shortcut=None, tip=None, checkable=False):
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.setStatusTip(tip or text)
        a.setCheckable(checkable)
        a.triggered.connect(slot)
        self.addAction(a)
        return a

    def _build_actions(self):
        A = self._act
        self.a_new = A("&New", self.new_file, QKeySequence.New)
        self.a_open = A("&Open…", self.open_file, QKeySequence.Open)
        self.a_save = A("&Save", self.save_file, QKeySequence.Save)
        self.a_saveas = A("Save &As…", self.save_as, QKeySequence.SaveAs)
        self.a_export = A("Export &PNG…", self.export_png)
        self.a_quit = A("E&xit", self.close, QKeySequence.Quit)
        self.a_undo = A("&Undo", self.undo, QKeySequence.Undo)
        self.a_redo = A("&Redo", self.redo, QKeySequence.Redo)
        self.a_cut = A("Cu&t", self.cut, QKeySequence.Cut)
        self.a_copy = A("&Copy", self.copy, QKeySequence.Copy)
        self.a_paste = A("&Paste", self.paste, QKeySequence.Paste)
        self.a_dup = A("&Duplicate", self.duplicate, "Ctrl+D")
        self.a_del = A("De&lete", self.delete, QKeySequence.Delete)
        self.a_all = A("Select &All", lambda: self.canvas.select(self.canvas.frames), QKeySequence.SelectAll)
        self.a_front = A("Bring to &Front", self.bring_front, "Ctrl+]")
        self.a_back = A("Send to &Back", self.send_back, "Ctrl+[")
        self.a_run = A("▶ Run", self.toggle_run, "F5", "Toggle between edit and run mode", True)
        self.a_snap = A("Snap to grid", self._toggle_snap, None, None, True)
        self.a_snap.setChecked(True)
        self.a_showgrid = A("Show grid", self._toggle_grid, None, None, True)
        self.a_showgrid.setChecked(True)
        self.a_canvas = A("Canvas Size…", self.canvas_size)
        self.a_bg = A("Background Picture…", self.choose_background, None,
                      "Use a scalable SVG picture as the canvas background")
        self.a_bg_clear = A("Remove Background Picture", self.clear_background)
        self.a_bg_fit = A("Fit Canvas to Picture", self.fit_canvas_to_background, None,
                          "Resize the canvas to the background picture's aspect ratio")

        align = [
            ("Align Left", lambda: self.align("left")), ("Align Center", lambda: self.align("hcenter")),
            ("Align Right", lambda: self.align("right")), ("Align Top", lambda: self.align("top")),
            ("Align Middle", lambda: self.align("vcenter")), ("Align Bottom", lambda: self.align("bottom")),
            ("Distribute Horizontally", lambda: self.distribute("h")),
            ("Distribute Vertically", lambda: self.distribute("v")),
            ("Same Width", lambda: self.same_size(True, False)),
            ("Same Height", lambda: self.same_size(False, True)),
            ("Same Size", lambda: self.same_size(True, True)),
        ]
        self.align_actions = [A(t, s) for t, s in align]

        mb = self.menuBar()
        m = mb.addMenu("&File")
        for a in (self.a_new, self.a_open, self.a_save, self.a_saveas, None, self.a_export, None, self.a_quit):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("&Edit")
        for a in (self.a_undo, self.a_redo, None, self.a_cut, self.a_copy, self.a_paste, self.a_dup,
                  self.a_del, None, self.a_all):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("&Layout")
        for a in self.align_actions[:6]:
            m.addAction(a)
        m.addSeparator()
        for a in self.align_actions[6:]:
            m.addAction(a)
        m.addSeparator()
        m.addAction(self.a_front)
        m.addAction(self.a_back)
        m = mb.addMenu("&View")
        for a in (self.a_snap, self.a_showgrid, self.a_canvas, None, self.a_bg, self.a_bg_fit, self.a_bg_clear,
                  None, self.palette_dock.toggleViewAction(),
                  self.props_dock.toggleViewAction()):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("&Run")
        m.addAction(self.a_run)
        mb.addMenu("&Help").addAction(A("&Keyboard && Mouse…", self.show_help, "F1"))

        tb = self.addToolBar("Main")
        tb.setObjectName("main")
        for a in (self.a_new, self.a_open, self.a_save, None, self.a_undo, self.a_redo, None,
                  self.a_copy, self.a_paste, self.a_del, None):
            tb.addSeparator() if a is None else tb.addAction(a)
        tb.addAction(self.a_snap)
        tb.addWidget(QLabel(" Grid "))
        self.grid_spin = QSpinBox()
        self.grid_spin.setRange(1, 100)
        self.grid_spin.setValue(self.canvas.grid)
        self.grid_spin.setSuffix(" px")
        self.grid_spin.valueChanged.connect(self._grid_changed)
        tb.addWidget(self.grid_spin)
        tb.addSeparator()
        tb.addAction(self.a_run)

        self.addToolBarBreak()
        tb2 = self.addToolBar("Layout")
        tb2.setObjectName("layout")
        for a in self.align_actions:
            tb2.addAction(a)
        tb2.addSeparator()
        tb2.addAction(self.a_front)
        tb2.addAction(self.a_back)

        for k, (dx, dy) in {Qt.Key_Left: (-1, 0), Qt.Key_Right: (1, 0), Qt.Key_Up: (0, -1), Qt.Key_Down: (0, 1)}.items():
            for mods, big, resize in ((0, False, False), (Qt.ShiftModifier, True, False),
                                      (Qt.ControlModifier, False, True), (Qt.ControlModifier | Qt.ShiftModifier, True, True)):
                def go(_=False, dx=dx, dy=dy, big=big, resize=resize):
                    s = self.canvas.grid if big else 1
                    self.canvas.nudge(dx * s, dy * s, resize)
                a = QAction(self)
                a.setShortcut(QKeySequence(int(k) | int(mods)))
                a.setShortcutContext(Qt.WidgetWithChildrenShortcut)
                a.triggered.connect(go)
                self.canvas.addAction(a)

    # ------------------------------------------------------------ undo
    def snapshot(self):
        d = self.canvas.to_dict()
        d["selection"] = [f.name for f in self.canvas.selection]
        return d

    def checkpoint(self, key=None):
        if key and key == self._coalesce:  # None / "" = always a new undo step
            return
        self._coalesce = key
        self.undo_stack.append(self.snapshot())
        del self.undo_stack[:-200]
        self.redo_stack.clear()
        self._mark_dirty()

    def _restore(self, d):
        self.canvas.load_dict(d)
        self.canvas.select([f for n in d.get("selection", []) if (f := self.canvas.frame_by_name(n))])
        self._coalesce = None
        self._mark_dirty()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.snapshot())
            self._restore(self.undo_stack.pop())

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.snapshot())
            self._restore(self.redo_stack.pop())

    # ------------------------------------------------------------ edit ops
    def _palette_add(self, item):
        t = item.data(0, Qt.UserRole)
        if not t or not self.canvas.edit_mode:
            return
        self.checkpoint()
        w, h = SPECS[t].size
        n = len(self.canvas.frames) % 10
        f = self.canvas.add_widget(t, QRect(20 + n * 20, 20 + n * 20, w, h))
        self.canvas.select([f])

    def copy(self):
        if self.canvas.selection:
            self.clipboard = [f.to_dict() for f in self.canvas.selection]
            QApplication.clipboard().setText(json.dumps({"widgets": self.clipboard}, indent=1))

    def cut(self):
        self.copy()
        self.delete()

    def paste(self):
        if not self.clipboard or not self.canvas.edit_mode:
            return
        self.checkpoint()
        new = []
        off = self.canvas.grid * 2 if self.canvas.snap else 20
        for d in self.clipboard:
            d["x"] += off
            d["y"] += off
            new.append(self.canvas.add_widget(d["type"], QRect(d["x"], d["y"], d["w"], d["h"]),
                                              copy.deepcopy(d["props"])))
        self.canvas.select(new)

    def duplicate(self):
        self.copy()
        self.paste()

    def delete(self):
        if self.canvas.selection and self.canvas.edit_mode:
            self.checkpoint()
            self.canvas.remove(list(self.canvas.selection))

    def bring_front(self):
        self.checkpoint()
        for f in self.canvas.selection:
            f.raise_()

    def send_back(self):
        self.checkpoint()
        for f in reversed(self.canvas.selection):
            f.lower()

    def align(self, how):
        sel = self.canvas.selection
        if len(sel) < 2:
            return
        self.checkpoint()
        ref = sel[-1].geometry()
        for f in sel[:-1]:
            g = f.geometry()
            x, y = g.x(), g.y()
            if how == "left": x = ref.left()
            elif how == "right": x = ref.x() + ref.width() - g.width()
            elif how == "hcenter": x = ref.x() + (ref.width() - g.width()) // 2
            elif how == "top": y = ref.top()
            elif how == "bottom": y = ref.y() + ref.height() - g.height()
            elif how == "vcenter": y = ref.y() + (ref.height() - g.height()) // 2
            f.move(x, y)
        self._on_geometry()

    def distribute(self, axis):
        sel = self.canvas.selection
        if len(sel) < 3:
            return
        self.checkpoint()
        h = axis == "h"
        fs = sorted(sel, key=lambda f: f.x() if h else f.y())
        size = sum(f.width() if h else f.height() for f in fs)
        a = fs[0].x() if h else fs[0].y()
        last = fs[-1]
        b = (last.x() + last.width()) if h else (last.y() + last.height())
        gap = (b - a - size) / (len(fs) - 1)
        pos = a
        for f in fs:
            f.move(round(pos), f.y()) if h else f.move(f.x(), round(pos))
            pos += (f.width() if h else f.height()) + gap
        self._on_geometry()

    def same_size(self, w, h):
        sel = self.canvas.selection
        if len(sel) < 2:
            return
        self.checkpoint()
        ref = sel[-1]
        for f in sel[:-1]:
            f.resize(ref.width() if w else f.width(), ref.height() if h else f.height())
        self._on_geometry()

    def _activated(self, frame):
        """Double-click on a widget: show its properties; for an SVG Picture, choose the file."""
        self.props_dock.raise_()
        if frame.type == "picture" and self.canvas.primary() is frame:
            self.props.choose_picture()

    def _context_menu(self, gpos):
        m = QMenu(self)
        if self.canvas.selection:
            for a in (self.a_cut, self.a_copy, self.a_dup, self.a_del, None, self.a_front, self.a_back):
                m.addSeparator() if a is None else m.addAction(a)
            if len(self.canvas.selection) > 1:
                sub = m.addMenu("Align / Size")
                for a in self.align_actions:
                    sub.addAction(a)
        else:
            m.addAction(self.a_paste)
            m.addAction(self.a_all)
            add = m.addMenu("Add Widget")
            local = self.canvas.mapFromGlobal(gpos)
            for spec in SPECS.values():
                add.addAction(spec.title, lambda t=spec.type: self._add_at(t, local))
            m.addSeparator()
            m.addAction(self.a_bg)
            if self.canvas.background:
                m.addAction(self.a_bg_fit)
                m.addAction(self.a_bg_clear)
        m.exec_(gpos)

    def _add_at(self, t, pos):
        self.checkpoint()
        w, h = SPECS[t].size
        f = self.canvas.add_widget(t, QRect(self.canvas._snap(pos.x()), self.canvas._snap(pos.y()), w, h))
        self.canvas.select([f])

    # ------------------------------------------------------------ view
    def _toggle_snap(self, on):
        self.canvas.snap = on

    def _toggle_grid(self, on):
        self.canvas.show_grid = on
        self.canvas.update()

    def _grid_changed(self, v):
        self.canvas.grid = v
        self.canvas.update()

    def canvas_size(self):
        txt, ok = QInputDialog.getText(self, "Canvas Size", "Width × Height (px):",
                                       text=f"{self.canvas.width()} x {self.canvas.height()}")
        if not ok:
            return
        try:
            w, h = (int(s) for s in txt.lower().replace("×", "x").split("x"))
        except ValueError:
            return
        self.checkpoint()
        self.canvas.resize(max(200, w), max(150, h))
        self._canvas_changed()

    def _canvas_changed(self):
        if not self.canvas.selection:
            self.props.refresh()
        self._update_bg_actions()

    def _update_bg_actions(self):
        edit, has = self.canvas.edit_mode, bool(self.canvas.background)
        self.a_bg.setEnabled(edit)
        self.a_bg_clear.setEnabled(edit and has)
        self.a_bg_fit.setEnabled(edit and has)

    def choose_background(self):
        if not self.canvas.edit_mode:
            return
        got = choose_svg(self, "Background Picture")
        if got:
            name, data = got
            self.checkpoint()
            self.canvas.set_background(data, name)
            self._canvas_changed()

    def clear_background(self):
        if self.canvas.background and self.canvas.edit_mode:
            self.checkpoint()
            self.canvas.set_background("")
            self._canvas_changed()

    def fit_canvas_to_background(self):
        """Keeps the canvas width and sets the height so the picture fills it exactly."""
        bg = self.canvas.background
        if not bg or not self.canvas.edit_mode:
            return
        nat = bg.natural_size()
        w = self.canvas.width()
        h = max(150, round(w * nat.height() / nat.width()))
        if h != self.canvas.height():
            self.checkpoint()
            self.canvas.resize(w, h)
            self._canvas_changed()

    # ------------------------------------------------------------ run mode
    def _stop_run(self):
        if self.a_run.isChecked():
            self.a_run.trigger()

    def _move_dashboard(self, to_run_window):
        if to_run_window:
            if self.centralWidget() is not self.scroll:
                return
            self.takeCentralWidget()
            self.setCentralWidget(self.run_placeholder)
            self.run_window.setWindowTitle(f"{self.path or 'Untitled'} — Dashboard (Run)")
            self.run_window.show_for(self.scroll, self.canvas.size(), self)
            self.canvas.setFocus()
        else:
            if self.centralWidget() is self.scroll:
                return
            self.run_window.take_content()
            self.takeCentralWidget()  # keep the placeholder alive for the next run
            self.setCentralWidget(self.scroll)
            self.activateWindow()

    def toggle_run(self, on):
        self._move_dashboard(on)
        self.canvas.set_edit_mode(not on)
        self.a_run.setText("■ Stop" if on else "▶ Run")
        for a in (self.a_cut, self.a_paste, self.a_dup, self.a_del, self.a_undo, self.a_redo, *self.align_actions):
            a.setEnabled(not on)
        self.palette_dock.setEnabled(not on)
        self.props_dock.setEnabled(not on)
        self._update_bg_actions()
        if on:
            self.t0 = time.perf_counter()
            for f in self.canvas.frames:
                if f.type in ("ytgraph", "xygraph"):
                    f.inner.clear()
            if self.bridge is not None:
                self.bridge.start(self._variable_sources())
                for f in self.canvas.frames:
                    if f.type == "slider":  # moving a slider writes its variable
                        f.inner.userChanged.connect(
                            lambda v, f=f: self.bridge.write(f.props.get("source", ""), v))
            self.timer.start()
            for f in self._loggers():
                f.inner.set_running(True)
        else:
            self.timer.stop()
            if self.bridge is not None:
                self.bridge.stop()
                for f in self.canvas.frames:
                    if f.type == "slider":
                        f.inner.userChanged.disconnect()
            for f in self._loggers():
                f.inner.set_running(False)  # closes the CSV file
            for f in self.canvas.frames:
                f.apply_props()
        self._update_status()

    def _variable_sources(self):
        """Return the data sources of all widgets that read a variable of the target."""
        sources = []
        for f in self.canvas.frames:
            for pr in f.spec.props:
                value = f.props.get(pr.key)
                if pr.kind == "source" and parse_source(value):
                    sources.append(value)
        return sources

    def _write_variable(self, name, value, sfr):
        return self.app_state.write_variable(name, value, sfr=sfr)

    def variable_names(self):
        """Return the firmware variable names and the SFR names of the connected target.

        Returns:
            tuple: ``(variables, sfrs)``, both empty when not connected.
        """
        if self.app_state is None or not self.app_state.is_connected():
            return [], []
        return self.app_state.get_variable_list(), self.app_state.get_sfr_list()

    def confirm_close(self):
        """Ask to save unsaved changes and stop Run mode before the application closes.

        Returns:
            bool: False when the user cancelled.
        """
        if not self._confirm_discard():
            return False
        self._stop_run()
        self.run_window.hide()
        return True

    def _loggers(self):
        return [f for f in self.canvas.frames if f.type == "logger"]

    def _resolve(self, frame, idx, source, t, freq, phase):
        """Returns (value, is_raw). Raw values come from another widget and skip amplitude scaling."""
        if parse_source(source) and self.bridge is not None:
            return self.bridge.value(source), True
        return 0.0, True

    def _tick(self):
        t = time.perf_counter() - self.t0
        for f in self.canvas.frames:
            if f.spec.tick:
                f.spec.tick(f, t, self._resolve)
        # Data Loggers sample on their own timer (configurable rate in ms), see datalogger.py

    # ------------------------------------------------------------ selection & status
    def _on_selection(self):
        self._update_bg_actions()
        sel = self.canvas.selection
        self.props.set_frame(self.canvas.primary(), len(sel))
        for a in self.align_actions:
            a.setEnabled(len(sel) >= 2 and self.canvas.edit_mode)
        self.align_actions[6].setEnabled(len(sel) >= 3)
        self.align_actions[7].setEnabled(len(sel) >= 3)
        self._update_status()

    def _on_geometry(self):
        self.props.sync_geometry()
        self._mark_dirty()
        self._update_status()

    def _update_status(self):
        mode = "EDIT" if self.canvas.edit_mode else "RUN"
        p = self.canvas.primary()
        s = f"{mode}  |  {len(self.canvas.frames)} widgets"
        if p:
            g = p.geometry()
            s += f"  |  {p.name}: x={g.x()} y={g.y()} w={g.width()} h={g.height()}"
        self.status.setText(s)

    # ------------------------------------------------------------ files
    def _mark_dirty(self):
        self.dirty = True
        self._update_title()

    def _update_title(self):
        name = self.path or "Untitled"
        self.setWindowTitle(f"{'*' if self.dirty else ''}{name} — Dashboard")

    def _confirm_discard(self):
        if not self.dirty:
            return True
        r = QMessageBox.question(self, "Unsaved changes", "Save changes to the current dashboard?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save_file()
        return r == QMessageBox.Discard

    def new_file(self):
        if self._confirm_discard():
            self.canvas.clear()
            self.canvas.set_background("")
            self._canvas_changed()
            self.path, self.dirty = None, False
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._update_title()

    def open_file(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open Dashboard", "", FILTER)
        if path:
            self.load(path)

    def load(self, path):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Open failed", str(e))
            return
        self.canvas.load_dict(d)
        self.grid_spin.setValue(self.canvas.grid)
        self.path, self.dirty = path, False
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._update_title()
        self._on_selection()

    def save_file(self):
        if not self.path:
            return self.save_as()
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.canvas.to_dict(), fh, indent=2)
        except OSError as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return False
        self.dirty = False
        self._update_title()
        self.statusBar().showMessage(f"Saved {self.path}", 3000)
        return True

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Dashboard", self.path or "dashboard.dash.json", FILTER)
        if not path:
            return False
        self.path = path
        return self.save_file()

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "dashboard.png", "PNG image (*.png)")
        if path:
            edit = self.canvas.edit_mode
            sel = list(self.canvas.selection)
            self.canvas.set_edit_mode(False)
            self.canvas.grab().save(path)
            self.canvas.set_edit_mode(edit)
            self.canvas.select(sel)

    def closeEvent(self, e):
        if self.confirm_close():
            e.accept()
        else:
            e.ignore()

    def show_help(self):
        QMessageBox.information(self, "Keyboard & Mouse", (
            "Drag a widget from the Widgets panel onto the canvas (or double-click it).\n"
            "Drag .svg files from Explorer onto the canvas to add them as SVG Pictures;\n"
            "double-click an SVG Picture to choose its file.\n\n"
            "Click — select    Ctrl/Shift+Click — add to selection\n"
            "Drag on empty canvas — rubber-band select\n"
            "Drag widget — move    Drag handle — resize\n"
            "Hold Alt while dragging — ignore grid snap\n"
            "Arrows — move 1 px    Shift+Arrows — move 1 grid step\n"
            "Ctrl+Arrows — resize 1 px    Ctrl+Shift+Arrows — resize 1 grid step\n"
            "Ctrl+C / X / V / D — copy, cut, paste, duplicate    Del — delete\n"
            "Ctrl+Z / Ctrl+Y — undo / redo    Ctrl+] / [ — bring front / send back\n"
            "F5 — toggle Run mode (opens the dashboard in its own window with live data\n"
            "in graphs, gauges, LCDs, progress bars; close that window to stop)\n\n"
            "Data Logger (palette → Data): in Run mode, Start / Pause / Stop logging the values\n"
            "of all widgets to a CSV file.\n\n"
            "Data source: a variable of the ELF file (connect in the Setup tab first). Gauges,\n"
            "graphs, LCDs and progress bars show it; a slider shows it and writes it when moved.\n"
            "Align/size operations use the last-clicked widget as the reference."))

    def _load_example(self):
        C = self.canvas
        C.add_widget("label", QRect(20, 20, 400, 34), {"text": "Process Monitor", "font_size": 16, "bold": True})
        C.add_widget("slider", QRect(20, 70, 300, 40), {"title": "Setpoint"}, "setpoint")
        C.add_widget("gauge", QRect(20, 120, 220, 220), {"title": "Setpoint", "units": "%"})
        C.add_widget("gauge", QRect(250, 120, 220, 220), {"title": "Load", "style": "semicircle", "units": "%"})
        C.add_widget("ytgraph", QRect(480, 70, 560, 270), {"title": "Signals over time"})
        C.add_widget("xygraph", QRect(1050, 70, 210, 270), {"title": "Lissajous"})
        C.add_widget("button", QRect(20, 360, 100, 30), {"text": "Start"})
        C.add_widget("checkbox", QRect(140, 362, 140, 26), {"text": "Enable logging"})
        C.add_widget("lcd", QRect(300, 350, 170, 50), {})
        C.add_widget("progress", QRect(480, 365, 560, 24), {})
        self.dirty = False
        self._update_title()
