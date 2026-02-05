"""Dashboard View Blueprint. This module handles all URLs called over {server_url}/dashboard-view.

Calling the URL {server_url}/dashboard-view will render the dashboard-view page.
Attention: this page should be called only after a successful setup connection on the {server_url}
"""
import os
import json

from flask import Blueprint, Response, jsonify, render_template, request
from flask_socketio import emit

# Assuming you have a similar structure as watch_view
# from pyx2cscope.gui import web
# from pyx2cscope.gui.web.scope import web_scope

dv_bp = Blueprint("dashboard_view", __name__, template_folder="templates")

# Store for widget variables
dashboard_data = {}


def index():
    """Dashboard View URL entry point. Calling the page {url}/dashboard-view will render the dashboard view page."""
    return render_template("index_dashboard.html", title="Dashboard - pyX2Cscope")


def get_data():
    """Return the dashboard variable data.

    Calling the link {dashboard-view-url}/data will return all current widget variable values.
    """
    return jsonify(dashboard_data)


def update_variable():
    """Update a widget variable value.

    Calling the link {dashboard-view-url}/update with POST data will update the variable.
    Expected JSON: {"variable": "var_name", "value": value}
    """
    try:
        data = request.json
        var_name = data.get('variable')
        value = data.get('value')

        if var_name:
            dashboard_data[var_name] = value
            # Emit socket event if socketio is available
            # socketio.emit('variable_update', {'variable': var_name, 'value': value}, namespace='/dashboard')
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Variable name required'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def save_layout():
    """Save dashboard layout to file.

    Calling the link {dashboard-view-url}/save-layout will save the current layout to a JSON file.
    """
    try:
        layout = request.json
        # Save to a configuration directory if available
        # web_lib_path = os.path.join(os.path.dirname(web.__file__), "upload")
        # For now, save to a default location
        with open('dashboard_layout.json', 'w') as f:
            json.dump(layout, f, indent=2)
        return jsonify({'status': 'success', 'message': 'Layout saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def load_layout():
    """Load dashboard layout from file.

    Calling the link {dashboard-view-url}/load-layout will load the saved layout.
    """
    try:
        if os.path.exists('dashboard_layout.json'):
            with open('dashboard_layout.json', 'r') as f:
                layout = json.load(f)
            return jsonify({'status': 'success', 'layout': layout})
        else:
            return jsonify({'status': 'error', 'message': 'No saved layout found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# Register URL rules
dv_bp.add_url_rule("/", view_func=index, methods=["GET"])
dv_bp.add_url_rule("/data", view_func=get_data, methods=["GET"])
dv_bp.add_url_rule("/update", view_func=update_variable, methods=["POST"])
dv_bp.add_url_rule("/save-layout", view_func=save_layout, methods=["POST"])
dv_bp.add_url_rule("/load-layout", view_func=load_layout, methods=["GET"])