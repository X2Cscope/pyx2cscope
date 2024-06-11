import random

from flask import Blueprint, jsonify, request, Response

sv = Blueprint('scope_view', __name__, template_folder='templates')

scope_data = []

def get_variable(parameter):
    colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF", "#800080", "#CCCCCC"]
    return {'trigger':0, 'enable':0, 'variable':parameter, 'color':colors[len(scope_data)],
            'gain':0 , 'offset':0, 'remove':0}

def get_data():
    return {'data': scope_data}

def is_data_ready():
    return {"ready": True, "finish": True}

def add():
    parameter = request.args.get('param', '')
    if not any(_data['variable'] == parameter for _data in scope_data):
        scope_data.append(get_variable(parameter))
    return jsonify({"status": "success"})

def remove():
    parameter = request.args.get('param', '')
    for _data in scope_data:
        if _data['variable'] == parameter:
            scope_data.remove(_data)
            break
    return jsonify({"status": "success"})

def update():
    param = request.args.get('param', '')
    field = request.args.get('field', '').lower()
    value = request.args.get('value', '')
    print("Parameter:" + param + ", field:" + field + ", value:" + value)
    for _data in scope_data:
        if _data["variable"] == param:
            _data[field] = value if field == "color" else float(value)
            break
    return jsonify({"status": "success"})

def form_sample():
    param = request.form.get('triggerAction', '')
    field = request.form.get('sampleTime', '')
    print("triggering", param)
    print("sampleTime", field)
    return jsonify({"trigger": param != "off"})

def form_trigger():
    trigger_enable = (request.form.get('triggerEnable', 'off').lower() == "enable")
    trigger_edge = (request.form.get('triggerEdge', '').lower() == "rising")
    trigger_level = float(request.form.get('triggerLevel', '0.0'))
    trigger_delay = float(request.form.get('triggerDelay', '0.0'))
    print("trigger", trigger_enable)
    print("edge", trigger_edge)
    print("level", trigger_level)
    print("delay", trigger_delay)
    return jsonify({"trigger": trigger_enable})

def _get_chart_label():
    return [i for i in range(0, 100)]

def _get_scope_data():
    data = []
    for channel in scope_data:
        item = {"label": channel["variable"], "pointRadius": 0, "borderColor": channel["color"],
                "backgroundColor": channel["color"], "data": [random.randint(0, 100) for i in range(100)]}
        data.append(item)
    return data

def chart():
    data = _get_scope_data()
    labels = _get_chart_label()
    return jsonify({"data": data, "labels": labels})

def chart_export():
    scope_data = _get_scope_data()
    labels = _get_chart_label()
    csv = "index; " + "; ".join([sc["label"] for sc in scope_data]) + "\n"
    data = [d["data"] for d in scope_data]
    data[:0] = [labels]  # place labels as first item im list
    for i in zip(*data):
        csv += "\n" + "; ".join(map(str,i))
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=chart.csv"})

sv.add_url_rule('/data', view_func=get_data, methods=["POST","GET"])
sv.add_url_rule('/data-ready', view_func=is_data_ready, methods=["POST","GET"])
sv.add_url_rule('/add', view_func=add, methods=["POST","GET"])
sv.add_url_rule('/remove', view_func=remove, methods=["POST","GET"])
sv.add_url_rule('/update', view_func=update, methods=["POST","GET"])
sv.add_url_rule('/chart', view_func=chart, methods=["POST","GET"])
sv.add_url_rule('/export', view_func=chart_export, methods=["POST","GET"])
sv.add_url_rule('/form-sample', view_func=form_sample, methods=["POST","GET"])
sv.add_url_rule('/form-trigger', view_func=form_trigger, methods=["POST","GET"])