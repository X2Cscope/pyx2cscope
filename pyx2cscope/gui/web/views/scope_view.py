"""Scope View Blueprint. This module handle all urls called over {server_url}/scope-view.

Calling the url {server_url}/scope-view, will render the scope-view page. 
Attention: this page should be called only after a successful setup connection on the {server_url}
"""""
import os

from flask import Blueprint, Response, jsonify, render_template, request

from pyx2cscope.gui import web
from pyx2cscope.gui.web import get_x2c
from pyx2cscope.xc2scope import TriggerConfig

sv = Blueprint('scope_view', __name__, template_folder='templates')

scope_data = []
scope_trigger = False
scope_burst = False
scope_sample = 1
scope_time_sample = 50e-3

def index():
    """Scope View url entry point. Calling the page {url}/scope-view will render the scope view page."""
    return render_template('sv_index.html', title="ScopeView - pyX2Cscope")

def _get_variable(parameter):
    variable = get_x2c().get_variable(parameter)
    colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF", "#800080", "#CCCCCC"]
    return {'trigger':0, 'enable':1, 'variable':variable, 'color':colors[len(scope_data)],
            'gain':1 , 'offset':0, 'remove':0}

def get_data():
    """Return the scope-view data.

    Calling the link {watch-view-url}/data will execute this function.
    """
    result = []
    for data in scope_data:
        result.append({f:v.name if f == "variable" else v for f,v in data.items()})
    return {'data': result}

def add():
    """Add a parameter to the scope-view table.

    Calling the link {scope-view-url}/add will execute this function.
    """
    parameter = request.args.get('param', '')
    if not any(_data['variable'].name == parameter for _data in scope_data):
        data = _get_variable(parameter)
        scope_data.append(data)
        get_x2c().add_scope_channel(data["variable"])
    return jsonify({"status": "success"})

def remove():
    """Remove the parameter from the scope-view table.

    Calling the link {scope-view-url}/remove will execute this function.
    """
    parameter = request.args.get('param', '')
    for data in scope_data:
        if data['variable'].name == parameter:
            scope_data.remove(data)
            get_x2c().remove_scope_channel(data["variable"])
            break
    return jsonify({"status": "success"})

def _set_trigger(data, param, field, value):
    if field == "trigger":
        value = float(value)
        if data["variable"].name != param:
            data["trigger"] = 0.0 if value == 1.0 else data["trigger"]

def _set_fields(data, param, field, value):
    if data["variable"].name == param:
        data[field] = value if field == "color" else float(value)

def _set_enable(data, param, field, value):
    if field == "enable":
        if data["variable"].name == param:
            if float(value):
                get_x2c().add_scope_channel(data["variable"])
            else:
                get_x2c().remove_scope_channel(data["variable"])

def update():
    """Update edited values on the scope-view table.

    Calling the link {scope-view-url}/update will execute this function.
    """
    param = request.args.get('param', '')
    field = request.args.get('field', '').lower()
    value = request.args.get('value', '')
    for data in scope_data:
        _set_trigger(data, param, field, value)
        _set_enable(data, param, field, value)
        _set_fields(data, param, field, value)
    return jsonify({"status": "success"})

def form_sample():
    """Handles the sample form.

    Arguments expected are the input field triggerAction (on, off, shot),
    sampleTime (1,2,3, etc.), and sampleFreq
    """
    global scope_trigger, scope_burst, scope_sample, scope_time_sample
    param = request.form.get('triggerAction', 'off')
    field = request.form.get('sampleTime', '1')
    freq = request.form.get('sampleFreq', '20')
    scope_burst = True if param == "shot" else False
    scope_trigger = True if param == "on" else False
    scope_sample = int(field)
    scope_time_sample = 1/int(freq)
    get_x2c().set_sample_time(scope_sample)
    if scope_trigger or scope_burst:
        get_x2c().request_scope_data()
    return jsonify({"trigger": param != "off"})

def form_trigger():
    """Handles the trigger form.

    Expected arguments are trigger_enable (on, off), triggerEdge (rising, falling), triggerLevel (int),
    and triggerDelay (-30, -20, ..., 20, 30).
    """
    trigger = {
        "trigger_mode": 1 if (request.form.get('triggerEnable', 'off').lower() == "enable") else 0,
        "trigger_edge": 1 if (request.form.get('triggerEdge', '').lower() == "rising") else 0,
        "trigger_level": int(request.form.get('triggerLevel', '0')),
        "trigger_delay": int(request.form.get('triggerDelay', '0'))
    }
    variable = [channel["variable"] for channel in scope_data if channel["trigger"] == 1.0]
    if trigger["trigger_mode"] and len(variable) == 1:
        get_x2c().set_scope_trigger(TriggerConfig(variable[0], **trigger))
    else:
        get_x2c().reset_scope_trigger()

    return jsonify({"trigger": trigger})

def _get_chart_label(size=100):
    return [i * scope_time_sample * scope_sample for i in range(0, size)]

def _get_datasets():
    data = []
    channel_data = get_x2c().get_scope_channel_data()
    for channel in scope_data:
        # if variable is disable on scope_data, it is not available on channel_data
        if channel["variable"].name in channel_data:
            variable = channel["variable"].name
            data_line = [l * channel["gain"] + channel["offset"] for l in channel_data[variable]]
            item = {"label": variable, "pointRadius": 0, "borderColor": channel["color"],
                    "backgroundColor": channel["color"], "data": data_line}
            data.append(item)
    if scope_trigger:
        get_x2c().request_scope_data()
    return data

def chart():
    """Return the chart data ready for chart.js framework.

    Calling the link {watch-view-url}/chart will execute this function.
    For this function to return valid data, variables must be added on the scope channel and optional trigger
    parameters. Finally, a command of burst or sample need to be called. Date will be returned only if data is
    available. This function calls in the background x2cscope.is_scope_data_ready()
    """
    ready = get_x2c().is_scope_data_ready()
    finish = True if ready and scope_burst else False
    datasets = []
    label = []
    if ready:
        datasets = _get_datasets()
        size = len(datasets[0]["data"]) if len(datasets) > 0 else 100
        label = _get_chart_label(size)
    return jsonify({"ready": ready, "finish": finish, "data": datasets, "labels": label})

def chart_export():
    """Generate and Download the scope-view graphic's data to a csv file.

    Calling the link {scope-view-url}/export will collect all the variable arrays depicted on the chart
    and generate a csv file ready for download.
    """
    datasets = _get_datasets()
    size = len(datasets[0]["data"]) if len(datasets) > 0 else 100
    label = _get_chart_label(size)
    csv = "index; " + "; ".join([sc["label"] for sc in datasets]) + "\n"
    data = [d["data"] for d in datasets]
    data[:0] = [label]  # place labels as first item im list
    for i in zip(*data):
        csv += "\n" + "; ".join(map(str,i))
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=chart.csv"})

def load():
    """Receive the scope view config file.

    Calling the link {scope-view-url}/load will store the parameters supplied and update the scope view table.
    """
    global scope_data
    cfg_file = request.files.get('file')
    if cfg_file and cfg_file.filename.endswith('.cfg'):
        web_lib_path = os.path.join(os.path.dirname(web.__file__), "upload")
        filename = os.path.join(web_lib_path, "scope.cfg")
        cfg_file.save(filename)
        data = eval(open(filename).read())
        if isinstance(data, list):
            if len(data) > 0:
                if isinstance(data[0], dict):
                    if "trigger" in data[0].keys():
                        scope_data = data
                        get_x2c().clear_scope_channel()
                        for item in scope_data:
                            item["variable"] = get_x2c().get_variable(item["variable"])
                            get_x2c().add_scope_channel(item["variable"])
                        return jsonify({"status": "success"})
        return jsonify({"status": "error", "msg": "Invalid ScopeConfig file."}), 400

def save():
    """Generate and Download the scope config file.

    Calling the link {scope-view-url}/save will collect all the variable present at the scope view table
    and generate a config file returning a .cfg file ready for download.
    """
    data = get_data()
    return Response(
        str((data["data"])),
        mimetype="application/octet-stream",
        headers={"Content-disposition": "attachment; filename=scope.cfg"})

sv.add_url_rule('/', view_func=index, methods=["GET"])
sv.add_url_rule('/data', view_func=get_data, methods=["POST","GET"])
sv.add_url_rule('/add', view_func=add, methods=["POST","GET"])
sv.add_url_rule('/remove', view_func=remove, methods=["POST","GET"])
sv.add_url_rule('/update', view_func=update, methods=["POST","GET"])
sv.add_url_rule('/chart', view_func=chart, methods=["POST","GET"])
sv.add_url_rule('/export', view_func=chart_export, methods=["POST","GET"])
sv.add_url_rule('/form-sample', view_func=form_sample, methods=["POST","GET"])
sv.add_url_rule('/form-trigger', view_func=form_trigger, methods=["POST","GET"])
sv.add_url_rule('/load', view_func=load, methods=["POST","GET"])
sv.add_url_rule('/save', view_func=save, methods=["POST","GET"])