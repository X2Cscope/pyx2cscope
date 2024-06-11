import random

from flask import Blueprint, jsonify, request

wv = Blueprint('watch_view', __name__, template_folder='templates')

watch_data = []

def read_variable(_data):
    # pyX2CScope read variable
    _data["value"] = random.randint(0, 100)
    _data["scaled_value"] = _data["value"] * _data["scaling"] + _data["offset"]

def get_variable(parameter):
    return {'live':0, 'variable':parameter, 'type':'int64', 'value':random.randint(0, 100),
                 'scaling':1, 'offset':0, 'scaled_value':0, 'remove':0}
def get_data():
    for _data in watch_data:
        if _data["live"]:
            read_variable(_data)
    return {'data': watch_data}

def add():
    parameter = request.args.get('param', '')
    if not any(_data['variable'] == parameter for _data in watch_data):
        watch_data.append(get_variable(parameter))
    return jsonify({"status": "success"})

def remove():
    parameter = request.args.get('param', '')
    for _data in watch_data:
        if _data['variable'] == parameter:
            watch_data.remove(_data)
            break
    return jsonify({"status": "success"})

def update():
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

def read():
    for _data in watch_data:
        if not _data["live"]:
            read_variable(_data)
    return jsonify({"status": "success"})

wv.add_url_rule('/data', view_func=get_data, methods=["POST","GET"])
wv.add_url_rule('/add', view_func=add, methods=["POST","GET"])
wv.add_url_rule('/remove', view_func=remove, methods=["POST","GET"])
wv.add_url_rule('/update', view_func=update, methods=["POST","GET"])
wv.add_url_rule('/update-non-live', view_func=read, methods=["POST","GET"])