from dataclasses import dataclass, field
from typing import Callable

from PyQt5.QtCore import QDateTime, Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDial,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QLabel,
    QLCDNumber,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QToolButton,
)

from . import theme
from .datalogger import FILE_MODES, MAX_MS, MIN_MS, SEPARATORS, LoggerWidget, sample_ms
from .instruments import Gauge, ValueSlider, XYGraph, YTGraph
from .svgimage import MODES as SVG_MODES
from .svgimage import PictureWidget
from .variables import parse_source


@dataclass
class Prop:
    key: str
    label: str
    kind: str  # str, text, int, float, bool, choice, source, items, color, svg, file
    default: object
    options: tuple = ()
    lo: float = -1e9
    hi: float = 1e9
    fallback: str = ""  # color props: colour used while the value is "" (shown in the swatch)


@dataclass
class Spec:
    type: str
    title: str
    category: str
    size: tuple
    props: list
    create: Callable
    apply: Callable
    tick: Callable = None
    value: Callable = None
    icon: str = ""
    extra: dict = field(default_factory=dict)
    log: Callable = None  # log(frame) -> [(csv column, value), ...] for the Data Logger; None = not logged


ALIGN = {"left": Qt.AlignLeft | Qt.AlignVCenter, "center": Qt.AlignCenter, "right": Qt.AlignRight | Qt.AlignVCenter}

SPECS = {}


def register(spec):
    SPECS[spec.type] = spec
    return spec


def _font(w, p):
    f = w.font()
    f.setPointSizeF(p.get("font_size", 9))
    f.setBold(p.get("bold", False))
    w.setFont(f)


def _items(text):
    return [s for s in str(text).splitlines() if s.strip()]


FONT = [Prop("font_size", "Font size", "float", 9.0, lo=5, hi=72), Prop("bold", "Bold", "bool", False)]
ENABLED = [Prop("enabled", "Enabled", "bool", True), Prop("tooltip", "Tooltip", "str", "")]


def _color(key, label, fallback=""):
    """A colour property. '' means "default": the theme colour, or the widget style's own colour."""
    return Prop(key, label, "color", "", fallback=fallback.name() if isinstance(fallback, QColor) else fallback)


TEXT_COLOR = _color("fg_color", "Text color")
BG_COLOR = _color("bg_color", "Background")
COLORS = [TEXT_COLOR, BG_COLOR]
ACCENT = _color("accent_color", "Accent color")


def _colors(w, p):
    """Applies the fg/bg/accent colour props through the palette, so the native style is kept."""
    pal = QPalette()
    fg, bg, accent = p.get("fg_color"), p.get("bg_color"), p.get("accent_color")
    if fg:
        for group in (QPalette.Active, QPalette.Inactive):  # disabled text stays greyed out
            for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
                pal.setColor(group, role, QColor(fg))
    if bg:
        for role in (QPalette.Window, QPalette.Base, QPalette.Button):
            pal.setColor(role, QColor(bg))
    if accent:
        for role in (QPalette.Accent, QPalette.Highlight):
            pal.setColor(role, QColor(accent))
    w.setPalette(pal)
    w.setAutoFillBackground(bool(bg))


def _common(w, p):
    w.setEnabled(p.get("enabled", True))
    w.setToolTip(p.get("tooltip", ""))
    _colors(w, p)


# ---------------------------------------------------------------- standard widgets

def _apply_label(w, p):
    w.setText(p["text"])
    w.setAlignment(ALIGN[p["align"]])
    w.setWordWrap(p["wrap"])
    w.setFrameShape(QFrame.Box if p["frame"] else QFrame.NoFrame)
    _font(w, p)
    _common(w, p)


register(Spec("label", "Label", "Standard", (120, 28), [
    Prop("text", "Text", "str", "Label"),
    Prop("align", "Alignment", "choice", "left", ("left", "center", "right")),
    Prop("wrap", "Word wrap", "bool", False),
    Prop("frame", "Frame", "bool", False),
    *FONT, *COLORS, *ENABLED], QLabel, _apply_label, icon="Aa"))


def _apply_button(w, p):
    w.setText(p["text"])
    w.setCheckable(p["checkable"])
    _font(w, p)
    _common(w, p)


register(Spec("button", "Push Button", "Standard", (100, 30), [
    Prop("text", "Text", "str", "Button"),
    Prop("checkable", "Toggle button", "bool", False),
    *FONT, *COLORS, *ENABLED], QPushButton, _apply_button,
    value=lambda w: 1.0 if w.isChecked() or w.isDown() else 0.0, icon="[ ]"))


def _apply_check(w, p):
    w.setText(p["text"])
    w.setChecked(p["checked"])
    _font(w, p)
    _common(w, p)


register(Spec("checkbox", "Check Box", "Standard", (120, 26), [
    Prop("text", "Text", "str", "Check box"),
    Prop("checked", "Checked", "bool", False),
    *FONT, *COLORS, ACCENT, *ENABLED], QCheckBox, _apply_check, value=lambda w: float(w.isChecked()), icon="☑"))

register(Spec("radio", "Radio Button", "Standard", (120, 26), [
    Prop("text", "Text", "str", "Option"),
    Prop("checked", "Checked", "bool", False),
    *FONT, *COLORS, ACCENT, *ENABLED], QRadioButton, _apply_check, value=lambda w: float(w.isChecked()), icon="◉"))


def _apply_lineedit(w, p):
    w.setText(p["text"])
    w.setPlaceholderText(p["placeholder"])
    w.setReadOnly(p["readonly"])
    w.setEchoMode(QLineEdit.Password if p["password"] else QLineEdit.Normal)
    _font(w, p)
    _common(w, p)


register(Spec("lineedit", "Text Box", "Standard", (160, 28), [
    Prop("text", "Text", "str", ""),
    Prop("placeholder", "Placeholder", "str", "Enter text…"),
    Prop("readonly", "Read only", "bool", False),
    Prop("password", "Password", "bool", False),
    *FONT, *COLORS, *ENABLED], QLineEdit, _apply_lineedit, icon="ab|"))


def _apply_textedit(w, p):
    w.setPlainText(p["text"])
    w.setReadOnly(p["readonly"])
    _font(w, p)
    _common(w, p)


register(Spec("textedit", "Multiline Text", "Standard", (200, 100), [
    Prop("text", "Text", "text", ""),
    Prop("readonly", "Read only", "bool", False),
    *FONT, *COLORS, *ENABLED], QPlainTextEdit, _apply_textedit, icon="¶"))


def _apply_spin(w, p):
    w.setRange(p["minimum"], p["maximum"])
    w.setSingleStep(p["step"])
    w.setValue(p["value"])
    w.setPrefix(p["prefix"])
    w.setSuffix(p["suffix"])
    if isinstance(w, QDoubleSpinBox):
        w.setDecimals(p["decimals"])
    _font(w, p)
    _common(w, p)


register(Spec("spinbox", "Spin Box", "Standard", (100, 28), [
    Prop("minimum", "Minimum", "int", 0), Prop("maximum", "Maximum", "int", 100),
    Prop("step", "Step", "int", 1, lo=1), Prop("value", "Value", "int", 0),
    Prop("prefix", "Prefix", "str", ""), Prop("suffix", "Suffix", "str", ""),
    *FONT, *COLORS, *ENABLED], QSpinBox, _apply_spin, value=lambda w: float(w.value()), icon="1⇵"))

register(Spec("doublespin", "Numeric Box", "Standard", (110, 28), [
    Prop("minimum", "Minimum", "float", 0.0), Prop("maximum", "Maximum", "float", 100.0),
    Prop("step", "Step", "float", 0.1, lo=0), Prop("value", "Value", "float", 0.0),
    Prop("decimals", "Decimals", "int", 2, lo=0, hi=8),
    Prop("prefix", "Prefix", "str", ""), Prop("suffix", "Suffix", "str", ""),
    *FONT, *COLORS, *ENABLED], QDoubleSpinBox, _apply_spin, value=lambda w: w.value(), icon="1.0"))


def _apply_combo(w, p):
    w.blockSignals(True)
    w.clear()
    w.addItems(_items(p["items"]))
    w.setCurrentIndex(min(p["index"], w.count() - 1))
    w.setEditable(p["editable"])
    w.blockSignals(False)
    _font(w, p)
    _common(w, p)


register(Spec("combo", "Drop-down List", "Standard", (140, 28), [
    Prop("items", "Items", "items", "Item 1\nItem 2\nItem 3"),
    Prop("index", "Selected index", "int", 0, lo=0),
    Prop("editable", "Editable", "bool", False),
    *FONT, *COLORS, *ENABLED], QComboBox, _apply_combo, value=lambda w: float(w.currentIndex()), icon="▾"))


def _apply_list(w, p):
    w.clear()
    w.addItems(_items(p["items"]))
    w.setAlternatingRowColors(p["alternate"])
    _font(w, p)
    _common(w, p)


register(Spec("list", "List Box", "Standard", (140, 110), [
    Prop("items", "Items", "items", "Item 1\nItem 2\nItem 3\nItem 4"),
    Prop("alternate", "Alternating rows", "bool", False),
    *FONT, *COLORS, *ENABLED], QListWidget, _apply_list, value=lambda w: float(w.currentRow()), icon="≡"))


def _apply_table(w, p):
    cols = _items(p["columns"])
    w.setColumnCount(len(cols))
    w.setHorizontalHeaderLabels(cols)
    w.setRowCount(p["rows"])
    w.verticalHeader().setVisible(p["row_headers"])
    w.horizontalHeader().setStretchLastSection(True)
    _font(w, p)
    _common(w, p)


register(Spec("table", "Table", "Standard", (260, 140), [
    Prop("columns", "Columns", "items", "Name\nValue\nUnit"),
    Prop("rows", "Rows", "int", 4, lo=0, hi=1000),
    Prop("row_headers", "Row headers", "bool", True),
    *FONT, *COLORS, *ENABLED], QTableWidget, _apply_table, icon="▦"))


def _apply_progress(w, p):
    w.setRange(int(p["minimum"]), int(p["maximum"]))
    w.setOrientation(Qt.Horizontal if p["orientation"] == "horizontal" else Qt.Vertical)
    w.setTextVisible(p["show_text"])
    w.setFormat(p["format"])
    w.setValue(int(p["value"]))
    _common(w, p)


def _tick_progress(frame, t, resolve):
    p = frame.props
    if not parse_source(p["source"]):
        return
    v, raw = resolve(frame, 0, p["source"], t, 0, 0)
    frame.inner.setValue(int(v))


register(Spec("progress", "Progress Bar", "Standard", (180, 24), [
    Prop("minimum", "Minimum", "int", 0), Prop("maximum", "Maximum", "int", 100),
    Prop("value", "Value", "int", 40),
    Prop("orientation", "Orientation", "choice", "horizontal", ("horizontal", "vertical")),
    Prop("show_text", "Show text", "bool", True), Prop("format", "Format", "str", "%p%"),
    Prop("source", "Data source", "source", ""),
    _color("accent_color", "Bar color"), *COLORS, *ENABLED], QProgressBar, _apply_progress, tick=_tick_progress, icon="▬"))


def _apply_group(w, p):
    w.setTitle(p["text"])
    w.setFlat(p["flat"])
    _font(w, p)
    _colors(w, p)


register(Spec("group", "Group Box", "Standard", (220, 150), [
    Prop("text", "Title", "str", "Group"), Prop("flat", "Flat", "bool", False), *FONT, *COLORS],
    QGroupBox, _apply_group, icon="⬚"))


def _make_line():
    f = QFrame()
    f.setFrameShadow(QFrame.Sunken)
    return f


def _apply_line(w, p):
    w.setFrameShape(QFrame.HLine if p["orientation"] == "horizontal" else QFrame.VLine)
    # a coloured line is drawn flat in that colour; the default is the style's sunken line
    w.setFrameShadow(QFrame.Plain if p.get("fg_color") else QFrame.Sunken)
    _colors(w, p)


register(Spec("line", "Separator Line", "Standard", (200, 10), [
    Prop("orientation", "Orientation", "choice", "horizontal", ("horizontal", "vertical")),
    _color("fg_color", "Line color")],
    _make_line, _apply_line, icon="—"))


def _apply_dial(w, p):
    w.setRange(int(p["minimum"]), int(p["maximum"]))
    w.setValue(int(p["value"]))
    w.setNotchesVisible(p["notches"])
    w.setWrapping(p["wrapping"])
    _common(w, p)


register(Spec("dial", "Dial / Knob", "Standard", (90, 90), [
    Prop("minimum", "Minimum", "int", 0), Prop("maximum", "Maximum", "int", 100),
    Prop("value", "Value", "int", 25), Prop("notches", "Show notches", "bool", True),
    Prop("wrapping", "Wrapping", "bool", False), BG_COLOR, *ENABLED],
    QDial, _apply_dial, value=lambda w: float(w.value()), icon="◔"))


def _apply_lcd(w, p):
    w.setDigitCount(p["digits"])
    w.setSegmentStyle({"flat": QLCDNumber.Flat, "outline": QLCDNumber.Outline,
                       "filled": QLCDNumber.Filled}[p["segment"]])
    w.display(p["value"])
    _colors(w, p)


def _tick_lcd(frame, t, resolve):
    p = frame.props
    if not parse_source(p["source"]):
        return
    v, raw = resolve(frame, 0, p["source"], t, 0, 0)
    frame.inner.display(f"{v:.{p['decimals']}f}")


register(Spec("lcd", "LCD Display", "Standard", (140, 50), [
    Prop("digits", "Digits", "int", 6, lo=1, hi=20), Prop("value", "Value", "float", 0.0),
    Prop("decimals", "Decimals", "int", 2, lo=0, hi=8),
    Prop("segment", "Segment style", "choice", "flat", ("flat", "outline", "filled")),
    Prop("source", "Data source", "source", ""),
    _color("fg_color", "Digit color"), BG_COLOR],
    QLCDNumber, _apply_lcd, tick=_tick_lcd, icon="88"))


def _apply_datetime(w, p):
    w.setDisplayFormat(p["format"])
    w.setCalendarPopup(p["calendar"])
    w.setDateTime(QDateTime.currentDateTime())
    _font(w, p)
    _common(w, p)


register(Spec("datetime", "Date / Time", "Standard", (170, 28), [
    Prop("format", "Display format", "str", "yyyy-MM-dd HH:mm"),
    Prop("calendar", "Calendar popup", "bool", True), *FONT, *COLORS, *ENABLED],
    QDateTimeEdit, _apply_datetime, icon="📅"))


def _apply_toolbutton(w, p):
    w.setText(p["text"])
    w.setCheckable(True)
    w.setChecked(p["checked"])
    w.setAutoRaise(p["flat"])
    _font(w, p)
    _common(w, p)


register(Spec("toggle", "Toggle Switch", "Standard", (90, 30), [
    Prop("text", "Text", "str", "ON/OFF"), Prop("checked", "Checked", "bool", False),
    Prop("flat", "Flat", "bool", False), *FONT, *COLORS, *ENABLED],
    QToolButton, _apply_toolbutton, value=lambda w: float(w.isChecked()), icon="⏻"))


# ---------------------------------------------------------------- instruments

MAX_SERIES = 4


def _plot_colors():
    return [_color("bg_color", "Background", theme.SURFACE), _color("fg_color", "Text color", theme.INK),
            _color("grid_color", "Grid / axis color", theme.GRID)]


def _instrument_colors(w, p, keys):
    w.colors = {k: p.get(f"{k}_color", "") for k in keys}


def _yt_props():
    props = [
        Prop("title", "Title", "str", "Y-T graph"),
        Prop("timespan", "Time span (s)", "float", 10.0, lo=0.5, hi=3600),
        Prop("y_min", "Y minimum", "float", -1.5), Prop("y_max", "Y maximum", "float", 1.5),
        Prop("autoscale", "Auto-scale Y", "bool", False),
        Prop("grid", "Show grid", "bool", True),
        Prop("line_width", "Line width", "float", 2.0, lo=0.5, hi=8),
        Prop("series", "Number of series", "int", 2, lo=1, hi=MAX_SERIES),
        *_plot_colors(),
    ]
    for i in range(1, MAX_SERIES + 1):
        props += [
            Prop(f"s{i}_name", f"Series {i} name", "str", f"Series {i}"),
            Prop(f"s{i}_source", f"Series {i} source", "source", ""),
            _color(f"s{i}_color", f"Series {i} color", theme.SERIES[i - 1]),
        ]
    return props


def _apply_yt(w, p):
    w.title = p["title"]
    w.timespan = p["timespan"]
    w.y_min, w.y_max = p["y_min"], p["y_max"]
    w.autoscale = p["autoscale"]
    w.show_grid = p["grid"]
    w.line_width = p["line_width"]
    w.set_series([p[f"s{i}_name"] for i in range(1, p["series"] + 1)])
    _instrument_colors(w, p, ("bg", "fg", "grid", *(f"s{i}" for i in range(1, MAX_SERIES + 1))))
    w.update()


def _tick_yt(frame, t, resolve):
    p = frame.props
    vals = []
    for i in range(1, p["series"] + 1):
        v, _raw = resolve(frame, i, p[f"s{i}_source"], t, 0, 0)
        vals.append(v)
    frame.inner.push(t, vals)


register(Spec("ytgraph", "Y-T Graph", "Instruments", (420, 240), _yt_props(),
              YTGraph, _apply_yt, tick=_tick_yt, icon="📈"))


def _apply_xy(w, p):
    w.title = p["title"]
    w.x_min, w.x_max = p["x_min"], p["x_max"]
    w.y_min, w.y_max = p["y_min"], p["y_max"]
    w.trail = p["trail"]
    w.mode = p["mode"]
    w.show_grid = p["grid"]
    w.line_width = p["line_width"]
    _instrument_colors(w, p, ("bg", "fg", "grid", "line"))
    w.update()


def _tick_xy(frame, t, resolve):
    p = frame.props
    x, _rx = resolve(frame, 1, p["x_source"], t, 0, 0)
    y, _ry = resolve(frame, 2, p["y_source"], t, 0, 0)
    frame.inner.push(x, y)


register(Spec("xygraph", "X-Y Graph", "Instruments", (300, 280), [
    Prop("title", "Title", "str", "X-Y graph"),
    Prop("mode", "Plot mode", "choice", "line", ("line", "scatter")),
    Prop("x_min", "X minimum", "float", -1.2), Prop("x_max", "X maximum", "float", 1.2),
    Prop("y_min", "Y minimum", "float", -1.2), Prop("y_max", "Y maximum", "float", 1.2),
    Prop("trail", "Trail length (points)", "int", 300, lo=2, hi=100000),
    Prop("grid", "Show grid", "bool", True),
    Prop("line_width", "Line width", "float", 2.0, lo=0.5, hi=8),
    Prop("x_source", "X source", "source", ""),
    Prop("y_source", "Y source", "source", ""),
    _color("line_color", "Line color", theme.SERIES[0]), *_plot_colors(),
], XYGraph, _apply_xy, tick=_tick_xy, icon="⌖"))


def _apply_gauge(w, p):
    w.title = p["title"]
    w.units = p["units"]
    w.minimum, w.maximum = p["minimum"], p["maximum"]
    w.warning, w.critical = p["warning"], p["critical"]
    w.decimals = p["decimals"]
    w.style = p["style"]
    w.major_ticks = p["ticks"]
    w.show_frame = p["frame"]
    _instrument_colors(w, p, ("bg", "fg", "arc", "track", "warning", "critical"))
    w.set_value(p["value"])


def _tick_gauge(frame, t, resolve):
    p = frame.props
    if not parse_source(p["source"]):
        return
    v, raw = resolve(frame, 0, p["source"], t, 0, 0)
    frame.inner.set_value(v)


register(Spec("gauge", "Gauge", "Instruments", (200, 200), [
    Prop("title", "Title", "str", "Gauge"),
    Prop("units", "Units", "str", "%"),
    Prop("style", "Style", "choice", "arc 270°", ("arc 270°", "semicircle")),
    Prop("minimum", "Minimum", "float", 0.0), Prop("maximum", "Maximum", "float", 100.0),
    Prop("value", "Static value", "float", 42.0),
    Prop("warning", "Warning threshold", "float", 70.0),
    Prop("critical", "Critical threshold", "float", 90.0),
    Prop("decimals", "Decimals", "int", 1, lo=0, hi=6),
    Prop("ticks", "Major ticks", "int", 5, lo=1, hi=20),
    Prop("source", "Data source", "source", ""),
    _color("arc_color", "Arc color", theme.ACCENT),
    _color("warning_color", "Warning color", theme.STATUS_WARNING),
    _color("critical_color", "Critical color", theme.STATUS_CRITICAL),
    _color("track_color", "Track color", theme.ACCENT_TRACK),
    _color("bg_color", "Background"),  # default: transparent
    Prop("frame", "Frame", "bool", False),
    _color("fg_color", "Text color", theme.INK),
], Gauge, _apply_gauge, tick=_tick_gauge, icon="◠"))


def _apply_slider(w, p):
    w.set_orientation(p["orientation"])
    w.configure(p["title"], p["minimum"], p["maximum"], p["step"], p["minimum"], p["decimals"], p["ticks"])
    w.show_value(p["show_value"])
    _common(w, p)


def _tick_slider(frame, t, resolve):
    p = frame.props
    if not parse_source(p["source"]) or frame.inner.is_dragged():
        return
    v, _raw = resolve(frame, 0, p["source"], t, 0, 0)
    frame.inner.set_value_silently(v)


register(Spec("slider", "Slider", "Instruments", (240, 40), [
    Prop("title", "Label", "str", "Value"),
    Prop("orientation", "Orientation", "choice", "horizontal", ("horizontal", "vertical")),
    Prop("minimum", "Minimum", "float", 0.0), Prop("maximum", "Maximum", "float", 100.0),
    Prop("step", "Step", "float", 1.0, lo=0),
    Prop("source", "Data source", "source", ""),
    Prop("decimals", "Decimals", "int", 0, lo=0, hi=6),
    Prop("ticks", "Tick marks", "bool", True),
    Prop("show_value", "Show value", "bool", True), *COLORS, ACCENT, *ENABLED],
    ValueSlider, _apply_slider, tick=_tick_slider, value=lambda w: w.value(), icon="⊶"))


# ---------------------------------------------------------------- graphics

NO_PICTURE = {"name": "", "svg": ""}


def _apply_picture(w, p):
    pic = p.get("picture")
    w.picture.set_data(pic.get("svg", "") if isinstance(pic, dict) else "")
    w.mode = p["mode"] if p["mode"] in SVG_MODES else "fit"
    w.opacity = max(0, min(100, int(p["opacity"]))) / 100
    w.fill = QColor(p["bg_color"]) if p.get("bg_color") else None
    w.update()


# "decoration": new instances are placed behind the normal widgets, and in Run mode clicks
# pass through to whatever is underneath.
register(Spec("picture", "SVG Picture", "Graphics", (200, 150), [
    Prop("picture", "Picture", "svg", NO_PICTURE),
    Prop("mode", "Scaling", "choice", "fit", SVG_MODES),
    Prop("opacity", "Opacity (%)", "int", 100, lo=0, hi=100),
    _color("bg_color", "Background"),
], PictureWidget, _apply_picture, icon="🖼", extra={"decoration": True}))


# ---------------------------------------------------------------- data logging

def _apply_logger(w, p):
    if "interval" in p:  # dashboards saved before the ms setting had "interval" in seconds
        p["sample_ms"] = sample_ms({"sample_ms": float(p.pop("interval")) * 1000})
    w.configure(p)
    _common(w, p)


register(Spec("logger", "Data Logger", "Data", (260, 92), [
    Prop("title", "Title", "str", "Data Logger"),
    Prop("file", "CSV file", "file", ""),
    Prop("sample_ms", "Sample period (ms)", "int", 1000, lo=MIN_MS, hi=MAX_MS),
    Prop("mode", "Existing file", "choice", "overwrite", FILE_MODES),
    Prop("separator", "Column separator", "choice", "comma", tuple(SEPARATORS)),
    Prop("decimal", "Decimal mark", "choice", ".", (".", ",")),
    Prop("auto_start", "Start with Run mode", "bool", False),
    *COLORS, *ENABLED,
], LoggerWidget, _apply_logger, value=lambda w: 1.0 if w.state == "logging" else 0.0, icon="⏺"))


def _one(get):
    return lambda f: [(f.name, get(f.inner))]


def _log_yt(f):
    w = f.inner
    return [(f"{f.name}.{n}", b[-1][1] if b else None) for n, b in zip(w.series_names, w.buffers)]


def _log_xy(f):
    x, y = f.inner.points[-1] if f.inner.points else (None, None)
    return [(f"{f.name}.x", x), (f"{f.name}.y", y)]


# What each widget type contributes to the CSV. Types not listed log their `value` if they have
# one; types without either (label, group box, line, table, picture, logger) are not logged.
LOG = {
    "lineedit": _one(lambda w: w.text()),
    "textedit": _one(lambda w: w.toPlainText()),
    "combo": _one(lambda w: w.currentText()),
    "list": _one(lambda w: w.currentItem().text() if w.currentItem() else ""),
    "progress": _one(lambda w: w.value()),
    "lcd": _one(lambda w: w.value()),
    "datetime": _one(lambda w: w.dateTime().toString(w.displayFormat())),
    "ytgraph": _log_yt,
    "xygraph": _log_xy,
    "gauge": _one(lambda w: w.value),
}
for _spec in SPECS.values():
    if _spec.type in LOG:
        _spec.log = LOG[_spec.type]
    elif _spec.value and _spec.type != "logger":
        _spec.log = (lambda get: lambda f: [(f.name, get(f.inner))])(_spec.value)


def default_props(type_):
    return {pr.key: dict(pr.default) if isinstance(pr.default, dict) else pr.default for pr in SPECS[type_].props}


__all__ = ["SPECS", "Prop", "Spec", "default_props"]
