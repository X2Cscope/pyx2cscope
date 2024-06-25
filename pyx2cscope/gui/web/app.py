"""This is the main Web entry point for Flash server.

This module holds and handles the main url and forward the relative urls to the specific
pages (blueprints).
"""

import logging
import os
import webbrowser
from threading import Timer

import serial.tools.list_ports
from flask import jsonify, render_template, request

from pyx2cscope import set_logger
from pyx2cscope.gui import web
from pyx2cscope.gui.web import connect_x2c, create_app, disconnect_x2c, get_x2c
from pyx2cscope.gui.web.views.scope_view import sv as scope_view
from pyx2cscope.gui.web.views.watch_view import wv as watch_view

set_logger(logging.INFO)


def index():
    """Web X2CScope url entry point. Calling the page {url_server} will render the web X2CScope view page."""
    return render_template('index.html', title="pyX2Cscope")


def list_serial_ports():
    """Return a list of all serial ports available on the server.

    call {server_url}/serial-ports to execute.
    """
    ports = serial.tools.list_ports.comports()
    return jsonify([port.device for port in ports])


def connect():
    """Connect pyX2CScope.

    call {server_url}/connect to execute.
    """
    uart = request.form.get('uart')
    elf_file = request.files.get('elfFile')
    if "default" not in uart and elf_file and elf_file.filename.endswith('.elf'):
        web_lib_path = os.path.join(os.path.dirname(web.__file__), "upload")
        if not os.path.exists(web_lib_path):
            os.makedirs(web_lib_path)
        file_name = os.path.join(web_lib_path, "elf_file.elf")
        try:
            elf_file.save(file_name)
            connect_x2c(port=uart, elf_file=file_name)
            return jsonify({"status": "success"})
        except RuntimeError as e:
            return jsonify({"status": "error", "msg": str(e)}), 401
        except ValueError as e:
            return jsonify({"status": "error", "msg": str(e)}), 401
    return jsonify({"status": "error", "msg": "COM Port or ELF file invalid."}), 400


def is_connected():
    """Check if pyX2Cscope is connected.

    call {server_url}/is_disconnect to execute.
    """
    return jsonify({"status": (get_x2c() is not None)})


def disconnect():
    """Disconnect pyX2CScope.

    call {server_url}/disconnect to execute.
    """
    disconnect_x2c()
    return jsonify({"status": "success"})


def variables_autocomplete():
    """Variable search filter.

    Receiving at least 3 letters, the function will search on pyX2Cscope parsed variables to find similar matches,
    returning a list of possible candidates. Access this function over {server_url}/variables.
    """
    query = request.args.get('q', '')
    x2c = get_x2c()
    items = [{"id": var, "text": var} for var in x2c.list_variables() if query.lower() in var.lower()]
    return jsonify({"items": items})


def get_variables():
    """List all variables.

    Returns a list of all variables available on the elf file.
    Access this function over {server_url}/variables/all.
    """
    x2c = get_x2c()
    items = [{"id": var, "text": var} for var in x2c.list_variables()]
    return jsonify({"items": items})


def open_browser(host="localhost", port=5000):
    """Open a new browser pointing to the Flask server.

    Args:
        host (str): the host address/name
        port (int): the host port.
    """
    webbrowser.open("http://" + host + ":" + str(port))


def main(host="localhost", port=5000, new=True, *args, **kwargs):
    """Web X2Cscope main function. Calling this function will start Web X2Cscope.

    Args:
        host (string): Default 'localhost'. Use 0.0.0.0 to open the server for external requests.
        port (int): Default 5000. The port where the server is available.
        new (bool): Default True. Should a new browser window/tab be opened at start?
        *args: additional non-key arguments supplied on program call.
        **kwargs: additional keyed arguments supplied on program call.
    """
    if new:
        Timer(1, open_browser).start()
    print("Listening at http://" + ("localhost" if host == "0.0.0.0" else host) + ":" + str(port))

    app = create_app()
    app.register_blueprint(watch_view, url_prefix='/watch-view')
    app.register_blueprint(scope_view, url_prefix='/scope-view')

    app.add_url_rule('/', view_func=index)
    app.add_url_rule('/serial-ports', view_func=list_serial_ports)
    app.add_url_rule('/connect', view_func=connect, methods=['POST'])
    app.add_url_rule('/disconnect', view_func=disconnect)
    app.add_url_rule('/is-connected', view_func=is_connected)
    app.add_url_rule('/variables', view_func=variables_autocomplete, methods=["POST", "GET"])
    app.add_url_rule('/variables/all', get_variables, methods=["POST", "GET"])

    log_level = kwargs["log_level"] if "log_level" in kwargs else "ERROR"
    app.logger.setLevel(log_level)
    logging.getLogger("werkzeug").setLevel(log_level)

    app.run(debug=False, host=host, port=port)

if __name__ == '__main__':
    main(new=True)

