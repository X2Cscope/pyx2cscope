"""Scope View Blueprint. This module handle all urls called over {server_url}/scope-view.

Calling the url {server_url}/scope-view, will render the scope-view page. 
Attention: this page should be called only after a successful setup connection on the {server_url}
"""
import os

from flask import Blueprint, Response, jsonify, render_template, request

from pyx2cscope.gui.web.scope import web_scope
from pyx2cscope.gui import web

sv_bp = Blueprint("scope_view", __name__, template_folder="templates")

def index():
    """Scope View url entry point. Calling the page {url}/scope-view will render the scope view page."""
    return render_template("index_sv.html", title="ScopeView - pyX2Cscope")


def get_data():
    """Return the scope-view data.

    Calling the link {scope-view-url}/data will execute this function.
    """
    result = [web_scope.variable_to_json(v) for v in web_scope.scope_vars]
    return {"data": result}


def chart_export():
    """Generate and Download the scope-view graphic's data to a csv file.

    Calling the link {scope-view-url}/export will collect all the variable arrays depicted on the chart
    and generate a csv file ready for download.
    """
    datasets = web_scope.get_scope_datasets()
    size = len(datasets[0]["data"]) if len(datasets) > 0 else 100
    label = web_scope.get_scope_chart_label(size)
    csv = "time (ms); " + "; ".join([sc["label"] for sc in datasets]) + "\n"
    data = [d["data"] for d in datasets]
    data[:0] = [label]  # place labels as first item im list
    for i in zip(*data):
        csv += "\n" + "; ".join(map(str, i))
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=chart.csv"},
    )


def load():
    """Receive the scope view config file.

    Calling the link {scope-view-url}/load will store the parameters supplied and update the scope view table.
    """
    cfg_file = request.files.get("file")
    msg = "Invalid ScopeConfig file."
    if cfg_file and cfg_file.filename.endswith(".cfg"):
        web_lib_path = os.path.join(os.path.dirname(web.__file__), "upload")
        filename = os.path.join(web_lib_path, "scope.cfg")
        cfg_file.save(filename)
        data = eval(open(filename).read())
        if isinstance(data, list) and data and isinstance(data[0], dict) and "variable" in data[0].keys():
            web_scope.clear_scope_var()
            for item in data:
                web_scope.clear_scope_var()
                var = web_scope.add_scope_var(item["variable"])
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
    """Generate and Download the scope config file.

    Calling the link {scope-view-url}/save will collect all the variable present at the scope view table
    and generate a config file returning a .cfg file ready for download.
    """
    data = get_data()
    return Response(
        str((data["data"])),
        mimetype="application/octet-stream",
        headers={"Content-disposition": "attachment; filename=scope.cfg"},
    )


sv_bp.add_url_rule("/", view_func=index, methods=["GET"])
sv_bp.add_url_rule("/data", view_func=get_data, methods=["POST", "GET"])
sv_bp.add_url_rule("/export", view_func=chart_export, methods=["POST", "GET"])
sv_bp.add_url_rule("/load", view_func=load, methods=["POST", "GET"])
sv_bp.add_url_rule("/save", view_func=save, methods=["POST", "GET"])
