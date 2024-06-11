from flask import Flask, render_template, request, jsonify, Response
import random
import serial
import serial.tools.list_ports
import logging

import numpy as np

app = Flask(__name__)
log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

watch_data = []
scope_data = []

# Simulated data for demonstration purposes
data = [
    {"id": "motor.A", "text": random.randint(0, 100)},
    {"id": "motor.B", "text": random.randint(0, 100)},
    {"id": "motor.C", "text": random.randint(0, 100)}
]

def index():
    return render_template('index.html', title="pyX2Cscope")

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return jsonify([port.device for port in ports])

def connect():
    uart = request.form.get('uart')
    elf_file = request.files.get('elfFile')

    if "default" not in uart and elf_file and elf_file.filename.endswith('.elf'):
        print(elf_file.filename)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

def disconnect():
    return jsonify({"status": "success"})

def variables_autocomplete():
    query = request.args.get('q', '')
    items = [{"id":option['id'], "text":option['id']} for option in data if query.lower() in option['id'].lower()]
    return jsonify({"items": items})

def read_variable(_data):
    # pyX2CScope read variable
    _data["value"] = random.randint(0, 100)
    _data["scaled_value"] = _data["value"] * _data["scaling"] + _data["offset"]

def get_watch_view_variable(parameter):
    return {'live':0, 'variable':parameter, 'type':'int64', 'value':random.randint(0, 100),
                 'scaling':1, 'offset':0, 'scaled_value':0, 'remove':0}

def get_scope_view_variable(parameter):
    colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF", "#800080", "#CCCCCC"]
    return {'trigger':0, 'enable':0, 'variable':parameter, 'color':colors[len(scope_data)],
            'gain':0 , 'offset':0, 'remove':0}

def watch_view_data():
    for _data in watch_data:
        if _data["live"]:
            read_variable(_data)
    return {'data': watch_data}

def watch_view_add():
    parameter = request.args.get('param', '')
    if not any(_data['variable'] == parameter for _data in watch_data):
        watch_data.append(get_watch_view_variable(parameter))
    return jsonify({"status": "success"})

def watch_view_remove():
    parameter = request.args.get('param', '')
    for _data in watch_data:
        if _data['variable'] == parameter:
            watch_data.remove(_data)
            break
    return jsonify({"status": "success"})

def watch_view_update():
    param = request.args.get('param', '')
    field = request.args.get('field', '').lower()
    value = request.args.get('value', '')
    print("Parameter:" + param + ", field:" + field + ", value:" + value)
    for _data in watch_data:
        if _data["variable"] == param:
            _data[field] = float(value)
            if field == "value":
                print("pyX2CScope variable write!")
            break
    return jsonify({"status": "success"})

def watch_view_read():
    for _data in watch_data:
        if not _data["live"]:
            read_variable(_data)
    return jsonify({"status": "success"})

def scope_view_data():
    return {'data': scope_data}

def scope_view_data_ready():
    return {"ready": True, "finish": True}

def scope_view_add():
    parameter = request.args.get('param', '')
    if not any(_data['variable'] == parameter for _data in scope_data):
        scope_data.append(get_scope_view_variable(parameter))
    return jsonify({"status": "success"})

def scope_view_remove():
    parameter = request.args.get('param', '')
    for _data in scope_data:
        if _data['variable'] == parameter:
            scope_data.remove(_data)
            break
    return jsonify({"status": "success"})

def scope_view_update():
    param = request.args.get('param', '')
    field = request.args.get('field', '').lower()
    value = request.args.get('value', '')
    print("Parameter:" + param + ", field:" + field + ", value:" + value)
    for _data in scope_data:
        if _data["variable"] == param:
            _data[field] = value if field == "color" else float(value)
            break
    return jsonify({"status": "success"})

def scope_view_form_sample():
    param = request.form.get('triggerAction', '')
    field = request.form.get('sampleTime', '')
    print("triggering", param)
    print("sampleTime", field)
    return jsonify({"trigger": param != "off"})

def scope_view_form_trigger():
    trigger_enable = (request.form.get('triggerEnable', 'off').lower() == "on")
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


def scope_view_chart():
    data = _get_scope_data()
    labels = _get_chart_label()
    return jsonify({"data": data, "labels": labels})

def scope_view_chart_export():
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

app.add_url_rule('/', view_func=index)
app.add_url_rule('/serial-ports', view_func=list_serial_ports)
app.add_url_rule('/connect', view_func=connect, methods=['POST'])
app.add_url_rule('/disconnect', view_func=disconnect)
app.add_url_rule('/variables', view_func=variables_autocomplete, methods=["POST","GET"])
app.add_url_rule('/watch-view-data', view_func=watch_view_data, methods=["POST","GET"])
app.add_url_rule('/watch-view-add', view_func=watch_view_add, methods=["POST","GET"])
app.add_url_rule('/watch-view-remove', view_func=watch_view_remove, methods=["POST","GET"])
app.add_url_rule('/watch-view-update', view_func=watch_view_update, methods=["POST","GET"])
app.add_url_rule('/watch-view-update-non-live', view_func=watch_view_read, methods=["POST","GET"])
app.add_url_rule('/scope-view-data', view_func=scope_view_data, methods=["POST","GET"])
app.add_url_rule('/scope-view-data-ready', view_func=scope_view_data_ready, methods=["POST","GET"])
app.add_url_rule('/scope-view-add', view_func=scope_view_add, methods=["POST","GET"])
app.add_url_rule('/scope-view-remove', view_func=scope_view_remove, methods=["POST","GET"])
app.add_url_rule('/scope-view-update', view_func=scope_view_update, methods=["POST","GET"])
app.add_url_rule('/scope-view-chart', view_func=scope_view_chart, methods=["POST","GET"])
app.add_url_rule('/scope-view-export', view_func=scope_view_chart_export, methods=["POST","GET"])
app.add_url_rule('/scope-view-form-sample', view_func=scope_view_form_sample, methods=["POST","GET"])
app.add_url_rule('/scope-view-form-trigger', view_func=scope_view_form_trigger, methods=["POST","GET"])

if __name__ == '__main__':
    app.run(debug=False)