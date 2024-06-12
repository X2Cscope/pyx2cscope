import logging
import serial.tools.list_ports
import os

from flask import render_template, request, jsonify

from pyx2cscope.gui.web import create_app, connect_x2c, get_x2c
from views.watch_view import wv as watch_view
from views.scope_view import sv as scope_view

app = create_app(log_level=logging.DEBUG)
app.register_blueprint(watch_view, url_prefix='/watch-view')
app.register_blueprint(scope_view, url_prefix='/scope-view')

def index():
    return render_template('index.html', title="pyX2Cscope")

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return jsonify([port.device for port in ports])

def connect():
    uart = request.form.get('uart')
    elf_file = request.files.get('elfFile')

    if "default" not in uart and elf_file and elf_file.filename.endswith('.elf'):
        file_name = os.path.join("upload", "elf_file.elf")
        elf_file.save(file_name)
        connect_x2c(port=uart, elf_file=file_name)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

def disconnect():
    get_x2c().disconnect()
    return jsonify({"status": "success"})

def variables_autocomplete():
    query = request.args.get('q', '')
    x2c = get_x2c()
    items = [{"id":var, "text":var} for var in x2c.list_variables() if query.lower() in var.lower()]
    return jsonify({"items": items})

app.add_url_rule('/', view_func=index)
app.add_url_rule('/serial-ports', view_func=list_serial_ports)
app.add_url_rule('/connect', view_func=connect, methods=['POST'])
app.add_url_rule('/disconnect', view_func=disconnect)
app.add_url_rule('/variables', view_func=variables_autocomplete, methods=["POST","GET"])

if __name__ == '__main__':
    app.run(debug=False)