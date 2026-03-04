"""Script View Blueprint - handles scripting-related HTTP endpoints."""

from flask import Blueprint, jsonify, render_template

from pyx2cscope.gui.resources import get_resource_path

script_bp = Blueprint("script_view", __name__)


@script_bp.route("/")
def script_view():
    """Render the standalone script view page."""
    return render_template("index_scripting.html", title="Script View")


@script_bp.route("/help")
def script_help():
    """Return the script help content as markdown."""
    help_content = _load_help_content()
    return jsonify({"markdown": help_content})


def _load_help_content() -> str:
    """Load help content from the shared resources markdown file."""
    try:
        help_path = get_resource_path("script_help.md")
        with open(help_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"# Error\n\nCould not load help file: {e}"
