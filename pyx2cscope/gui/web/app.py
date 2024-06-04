from flask import Flask, render_template, request, jsonify
import random
import serial
import serial.tools.list_ports

app = Flask(__name__)

# Simulated data for demonstration purposes
data = [
    {"id": "motor.A", "text": random.randint(0, 100)},
    {"id": "motor.B", "text": random.randint(0, 100)},
    {"id": "motor.C", "text": random.randint(0, 100)}
]

selected_data = []
selected_scope_data = []

scope_data = [
    {"time": i, "value": random.randint(0, 100)} for i in range(100)
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/serial-ports')
def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return jsonify([port.device for port in ports])

@app.route('/connect', methods=['POST'])
def connect():
    uart = request.form.get('uart')
    elf_file = request.files.get('elfFile')

    if "default" not in uart and elf_file and elf_file.filename.endswith('.elf'):
        print(elf_file.filename)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/disconnect')
def disconnect():
    return jsonify({"status": "success"})

@app.route('/variables', methods=["POST","GET"])
def variables_autocomplete():
    global data
    query = request.args.get('q', '')
    filtered_options = [{"id":option['id'], "text":option['id']} for option in data if query.lower() in option['id'].lower()]
    return jsonify({"items": filtered_options})

@app.route('/add-scope-search')
def add_variable_on_scope():
    global selected_scope_data
    parameter = request.args.get('param', '')
    if parameter not in selected_data:
        selected_scope_data.append(parameter)
    return jsonify({"status": "success"})

@app.route('/add-parameter-search')
def add_variable_on_parameter():
    global selected_data
    parameter = request.args.get('param', '')
    if parameter not in selected_data:
        selected_data.append(parameter)
    return jsonify({"status": "success"})

@app.route('/delete-parameter-search')
def delete_variable_on_parameter():
    global selected_data
    parameter = request.args.get('param', '')
    if parameter in selected_data:
        selected_data.remove(parameter)
    return jsonify({"status": "success"})

@app.route('/update-parameter-value')
def update_parameter():
    param = request.args.get('param', '')
    value = request.args.get('value', '')
    print("Parameter:" + param + ", value:" + value)
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