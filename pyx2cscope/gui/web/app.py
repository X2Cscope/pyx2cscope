from flask import Flask, render_template, request, jsonify
import random
import serial
import serial.tools.list_ports

app = Flask(__name__)

watch_data = [ { 'live':0, 'variable':'test', 'type':'int64', 'value':3,
                 'scaling':1, 'offset':0, 'scaled_value':0, 'remove':0}
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
    global data
    query = request.args.get('q', '')
    filtered_options = [{"id":option['id'], "text":option['id']} for option in data if query.lower() in option['id'].lower()]
    return jsonify({"items": filtered_options})

def watch_view_data():
    return {'data': watch_data}

def get_variable(parameter):
    return { 'live':0, 'variable':parameter, 'type':'int64', 'value':random.randint(0, 100),
                 'scaling':1, 'offset':0, 'scaled_value':0, 'remove':0}

def watch_view_add():
    parameter = request.args.get('param', '')
    if not any(_data['variable'] == parameter for _data in watch_data):
        watch_data.append(get_variable(parameter))
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
    value = request.args.get('value', '')
    print("Parameter:" + param + ", value:" + value)
    return jsonify({"status": "success"})


app.add_url_rule('/', view_func=index)
app.add_url_rule('/serial-ports', view_func=list_serial_ports)
app.add_url_rule('/connect', view_func=connect, methods=['POST'])
app.add_url_rule('/disconnect', view_func=disconnect)
app.add_url_rule('/variables', view_func=variables_autocomplete, methods=["POST","GET"])
app.add_url_rule('/watch-view-data', view_func=watch_view_data, methods=["POST","GET"])
app.add_url_rule('/watch-view-add', view_func=watch_view_add, methods=["POST","GET"])
app.add_url_rule('/watch-view-remove', view_func=watch_view_remove, methods=["POST","GET"])
app.add_url_rule('/watch-view-update', view_func=watch_view_update, methods=["POST","GET"])


# Simulated data for demonstration purposes
data = [
    {"id": "motor.A", "text": random.randint(0, 100)},
    {"id": "motor.B", "text": random.randint(0, 100)},
    {"id": "motor.C", "text": random.randint(0, 100)}
]


selected_scope_data = []

scope_data = [
    {"time": i, "value": random.randint(0, 100)} for i in range(100)
]




@app.route('/add-scope-search')
def add_variable_on_scope():
    global selected_scope_data
    parameter = request.args.get('param', '')
    if parameter not in selected_data:
        selected_scope_data.append(parameter)
    return jsonify({"status": "success"})

@app.route('/add-scope-variable')
def add_scope_variable():
    return jsonify({"status": "success"})

@app.route('/data')
def get_data():
    global selected_data
    result = []
    for param in selected_data:
        result.append({"param": param, "value": random.randint(0, 100)})
    return jsonify(result)

@app.route('/scope')
def get_scope_data():
    global scope_data
    scope_data = [
        {"time": i, "value": random.randint(0, 100)} for i in range(100)
    ]
    return jsonify(scope_data)

if __name__ == '__main__':
    app.run(debug=False)