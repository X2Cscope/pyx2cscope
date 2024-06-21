"""Watch View Blueprint. This module handle all urls called over {server_url}/watch-view.

Calling the url {server_url}/watch-view, will render the watch-view page. 
Attention: this page should be called only after a successful setup connection on the {server_url}
"""""
import os

from flask import Blueprint, Response, jsonify, render_template, request

from pyx2cscope.gui import web
from pyx2cscope.gui.web import get_x2c

wv = Blueprint('watch_view', __name__, template_folder='templates')

watch_data = []

def index():
    """Watch View url entry point. Calling the page {url}/watch-view will render the watch view page."""
    return render_template('index_wv.html', title="WatchView - pyX2Cscope")

def _read_variable(_data):
    # pyX2CScope read variable
    value = _data["variable"].get_value()
    _data["value"] = value
    _data["scaled_value"] = value * _data["scaling"] + _data["offset"]

def _get_variable(parameter):
    variable = get_x2c().get_variable(parameter)
    value = variable.get_value()
    primitive = variable.__class__.__name__.lower().replace("variable","")
    return {'live':0, 'variable':variable, 'type':primitive, 'value':value,
                 'scaling':1, 'offset':0, 'scaled_value':value, 'remove':0}

def get_data():
    """Return the watch-view data, additionally execute variable.get_value() on parameters tagged as 'live'.

    Calling the link {watch-view-url}/data will execute this function.
    """
    result = []
    for _data in watch_data:
        if _data["live"]:
            _read_variable(_data)
        result.append({f:v.name if f == "variable" else v for f,v in _data.items()})
    return {"data": result}

def add():
    """Add a parameter to the watch-view table.

    Calling the link {watch-view-url}/add will execute this function.
    """
    parameter = request.args.get('param', '')
    if not any(_data['variable'].name == parameter for _data in watch_data):
        watch_data.append(_get_variable(parameter))
    return jsonify({"status": "success"})

def remove():
    """Remove the parameter from the watch-view table.

    Calling the link {watch-view-url}/remove will execute this function.
    """
    parameter = request.args.get('param', '')
    for _data in watch_data:
        if _data['variable'].name == parameter:
            watch_data.remove(_data)
            break
    return jsonify({"status": "success"})

def update():
    """Update edited values on the watch-view table.

    Calling the link {watch-view-url}/update will execute this function.
    """
    param = request.args.get('param', '')
    field = request.args.get('field', '').lower()
    value = request.args.get('value', '')
    for _data in watch_data:
        if _data["variable"].name == param:
            _data[field] = float(value)
            if field == "value":
                _data["variable"].set_value( _data[field])
            break
    return jsonify({"status": "success"})

def read():
    """Read the value of all parameters on the watch view table that are not target as "live".

    Calling the link {watch-view-url}/update-non-live will execute this function.
    """
    for _data in watch_data:
        if not _data["live"]:
            _read_variable(_data)
    return jsonify({"status": "success"})

def load():
    """Receive the watch view config file.

    Calling the link {watch-view-url}/load will store the parameters supplied and update the watch view table.
    """
    global watch_data
    cfg_file = request.files.get('file')
    if cfg_file and cfg_file.filename.endswith('.cfg'):
        web_lib_path = os.path.join(os.path.dirname(web.__file__), "upload")
        filename = os.path.join(web_lib_path, "watch.cfg")
        cfg_file.save(filename)
        data = eval(open(filename).read())
        if isinstance(data, list):
            if len(data) > 0:
                if isinstance(data[0], dict):
                    if "live" in data[0].keys():
                        watch_data = data
                        for item in watch_data:
                            item["variable"] = get_x2c().get_variable(item["variable"])
                        return jsonify({"status": "success"})
        return jsonify({"status": "error", "msg": "Invalid WatchConfig file."}), 400

def save():
    """Generate and Download the watch config file.

    Calling the link {watch-view-url}/save will collect all the variable present at the watch view table
    and generate a config file returning a .cfg file ready for download.
    """
    data = get_data()
    return Response(
        str((data["data"])),
        mimetype="application/octet-stream",
        headers={"Content-disposition": "attachment; filename=watch.cfg"})

wv.add_url_rule('/', view_func=index, methods=["GET"])
wv.add_url_rule('/data', view_func=get_data, methods=["POST","GET"])
wv.add_url_rule('/add', view_func=add, methods=["POST","GET"])
wv.add_url_rule('/remove', view_func=remove, methods=["POST","GET"])
wv.add_url_rule('/update', view_func=update, methods=["POST","GET"])
wv.add_url_rule('/update-non-live', view_func=read, methods=["POST","GET"])
wv.add_url_rule('/load', view_func=load, methods=["POST","GET"])
wv.add_url_rule('/save', view_func=save, methods=["POST","GET"])