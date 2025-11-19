"""Watch View Blueprint. This module handle all urls called over {server_url}/watch-view.

Calling the url {server_url}/watch-view, will render the watch-view page. 
Attention: this page should be called only after a successful setup connection on the {server_url}
"""
import os

from flask import Blueprint, Response, jsonify, render_template, request

from pyx2cscope.gui import web
from pyx2cscope.gui.web.scope import web_scope

wv_bp = Blueprint("watch_view", __name__, template_folder="templates")

def index():
    """Watch View url entry point. Calling the page {url}/watch-view will render the watch view page."""
    return render_template("index_wv.html", title="WatchView - pyX2Cscope")


def get_data():
    """Return the watch-view data, additionally execute variable.get_value() on parameters tagged as 'live'.

    Calling the link {watch-view-url}/data will execute this function.
    """
    result = [web_scope.variable_to_json(v) for v in web_scope.watch_vars]
    return {"data": result}


def load():
    """Receive the watch view config file.

    Calling the link {watch-view-url}/load will store the parameters supplied and update the watch view table.
    """
    cfg_file = request.files.get("file")
    msg = "Invalid WatchConfig file."
    if cfg_file and cfg_file.filename.endswith(".cfg"):
        web_lib_path = os.path.join(os.path.dirname(web.__file__), "upload")
        filename = os.path.join(web_lib_path, "watch.cfg")
        cfg_file.save(filename)
        data = eval(open(filename).read())
        if isinstance(data, list) and data and isinstance(data[0], dict) and "variable" in data[0].keys():
            web_scope.clear_watch_var()
            for item in data:
                var = web_scope.add_watch_var(item["variable"])
                if var is None:
                    msg = "Variable " + item["variable"] + " is not available."
                else:
                    for key in item.keys():
                        if key in var and key != "variable":
                            var[key] = item[key]
            if "not available" not in msg:
                return jsonify({"status": "success"})
    return jsonify({"status": "error", "msg": msg}), 400


def save():
    """Generate and Download the watch config file.

    Calling the link {watch-view-url}/save will collect all the variable present at the watch view table
    and generate a config file returning a .cfg file ready for download.
    """
    data = get_data()
    return Response(
        str((data["data"])),
        mimetype="application/octet-stream",
        headers={"Content-disposition": "attachment; filename=watch.cfg"},
    )


wv_bp.add_url_rule("/", view_func=index, methods=["GET"])
wv_bp.add_url_rule("/data", view_func=get_data, methods=["POST", "GET"])
wv_bp.add_url_rule("/load", view_func=load, methods=["POST", "GET"])
wv_bp.add_url_rule("/save", view_func=save, methods=["POST", "GET"])
