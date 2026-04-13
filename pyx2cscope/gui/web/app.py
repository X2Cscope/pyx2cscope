"""This is the main Web entry point for Flask server.

This module holds and handles the main url and forward the relative urls to the specific
pages (blueprints).
"""
import logging
import os
import socket
import webbrowser

import serial.tools.list_ports
from flask import Flask, jsonify, render_template, request

from pyx2cscope import __version__, set_logger
from pyx2cscope.gui import web
from pyx2cscope.gui.web.scope import web_scope
from pyx2cscope.gui.web.ws_handlers import socketio

set_logger(logging.ERROR)

def create_app():
    """Create and configure the Flask application.

    Returns:
        Flask: Configured Flask application instance.
    """
    app = Flask(__name__)

    from pyx2cscope.gui.web.views.dashboard_view import dv_bp as dashboard_view
    from pyx2cscope.gui.web.views.scope_view import sv_bp as scope_view
    from pyx2cscope.gui.web.views.script_view import script_bp as script_view
    from pyx2cscope.gui.web.views.watch_view import wv_bp as watch_view

    app.register_blueprint(watch_view, url_prefix="/watch")
    app.register_blueprint(scope_view, url_prefix="/scope")
    app.register_blueprint(dashboard_view, url_prefix="/dashboard")
    app.register_blueprint(script_view, url_prefix="/scripting")

    app.add_url_rule("/", view_func=index)
    app.add_url_rule("/serial-ports", view_func=list_serial_ports)
    app.add_url_rule("/local-ips", view_func=get_local_ips)
    app.add_url_rule("/connect", view_func=connect, methods=["POST"])
    app.add_url_rule("/disconnect", view_func=disconnect)
    app.add_url_rule("/is-connected", view_func=is_connected)
    app.add_url_rule("/variables", view_func=variables_autocomplete, methods=["POST", "GET"])
    app.add_url_rule("/variables/all", view_func=get_variables, methods=["POST", "GET"])

    socketio.init_app(app)

    # IMPORTANT: Import after socketio exists to register all @socketio.on handlers
    from pyx2cscope.gui.web import ws_handlers  # noqa: F401

    return app


def index():
    """Web X2CScope url entry point. Calling the page {url_server} will render the web X2CScope view page."""
    return render_template("index.html", title="pyX2Cscope", version=__version__)


def list_serial_ports():
    """Return a list of all serial ports available on the server.

    call {server_url}/serial-ports to execute.
    """
    ports = serial.tools.list_ports.comports()
    return jsonify([port.device for port in ports])


def get_local_ips():
    """Return a list of local IP addresses for this host.

    call {server_url}/local-ips to execute.
    """
    ips = []
    try:
        # Get hostname
        hostname = socket.gethostname()
        # Get all IP addresses for this hostname
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            # Filter IPv4 addresses and exclude localhost
            if ':' not in ip and ip != '127.0.0.1' and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    # If no IPs found, add default
    if not ips:
        ips = ['0.0.0.0']

    return jsonify({"ips": ips})


def connect():
    """Connect pyX2CScope using arguments coming from the web.

    call {server_url}/connect to execute.
    """
    interface_type = request.form.get("interfaceType")
    elf_file = request.files.get("elfFile")

    interface_kwargs = {}

    if interface_type == "CAN":
        # CAN baud rate string to numeric mapping
        baud_rate_map = {
            "125K": 125000,
            "250K": 250000,
            "500K": 500000,
            "1M": 1000000,
        }
        can_bus_type = request.form.get("canBusType", "USB")
        can_channel = int(request.form.get("canChannel", 1))
        can_baud_rate = request.form.get("canBaudrate", "125K")
        can_mode = request.form.get("canMode", "Standard")
        can_tx_id = request.form.get("canTxId", "7F1")
        can_rx_id = request.form.get("canRxId", "7F0")

        # Map bus_type to bustype
        bustype_map = {
            'usb': 'pcan_usb',
            'pcan usb': 'pcan_usb',
            'lan': 'pcan_lan',
            'pcan lan': 'pcan_lan',
            'socketcan': 'socketcan',
            'socketcan (linux)': 'socketcan',
            'vector': 'vector',
            'kvaser': 'kvaser',
        }
        bustype = bustype_map.get(can_bus_type.lower(), 'pcan_usb')

        # Map mode to standard/extended
        mode_str = 'extended' if can_mode == "Extended" else 'standard'

        interface_kwargs = {
            "bustype": bustype,
            "channel": can_channel,
            "baud_rate": baud_rate_map.get(can_baud_rate, 125000),
            "id_tx": int(can_tx_id, 16),
            "id_rx": int(can_rx_id, 16),
            "mode": mode_str,
        }
    elif interface_type == "TCP_IP":
        host = request.form.get("host", "localhost")
        tcp_port = int(request.form.get("tcpPort", 12666))
        interface_kwargs = {
            "host": host,
            "tcp_port": tcp_port,
        }
    else:
        # SERIAL
        interface_arg_str = request.form.get("interfaceArgument")
        interface_value_str = request.form.get("interfaceValue")
        if interface_arg_str and interface_value_str:
            interface_kwargs = {interface_arg_str: interface_value_str}

    if elf_file and elf_file.filename.endswith((".elf", ".pkl", ".yml")):
        web_lib_path = os.path.join(os.path.dirname(web.__file__), "upload")
        if not os.path.exists(web_lib_path):
            os.makedirs(web_lib_path)
        file_name = os.path.join(web_lib_path, os.path.basename(elf_file.filename))
        try:
            elf_file.save(file_name)
            web_scope.connect(**interface_kwargs)
            web_scope.set_file(file_name)
            return jsonify({"status": "success"})
        except RuntimeError as e:
            return jsonify({"status": "error", "msg": str(e)}), 401
        except ValueError as e:
            return jsonify({"status": "error", "msg": str(e)}), 401
        except TimeoutError as e:
            return jsonify({"status": "error", "msg": str(e)}), 401
    return jsonify({"status": "error", "msg": "Interface argument or import file invalid."}), 400


def is_connected():
    """Check if pyX2Cscope is connected.

    call {server_url}/is_disconnect to execute.
    """
    return jsonify({"status": web_scope.is_connected()})


def disconnect():
    """Disconnect pyX2CScope.

    call {server_url}/disconnect to execute.
    """
    web_scope.disconnect()
    return jsonify({"status": "success"})


def variables_autocomplete():
    """Variable search filter.

    Receiving at least 3 letters, the function will search on pyX2Cscope parsed variables to find similar matches,
    returning a list of possible candidates. Access this function over {server_url}/variables.
    Use the query parameter ``sfr=true`` to search SFRs instead of firmware variables.
    """
    query = request.args.get("q", "")
    sfr = request.args.get("sfr", "false").lower() == "true"
    items = []
    if web_scope.is_connected():
        var_list = web_scope.list_sfr() if sfr else web_scope.list_variables()
        items = [
            {"id": var, "text": var}
            for var in var_list
            if query.lower() in var.lower()
        ]
    return jsonify({"items": items})


def get_variables():
    """List all variables.

    Returns a list of all variables available on the elf file.
    Access this function over {server_url}/variables/all.
    """
    items = [{"id": var, "text": var} for var in web_scope.list_variables()]
    return jsonify({"items": items})


def open_browser(host="localhost", web_port=5000):
    """Open a new browser pointing to the Flask server.

    Only opens if no clients are already connected (e.g., from a previous session).
    Existing browser tabs will reconnect automatically via Socket.IO.

    Args:
        host (str): the host address/name
        web_port (int): the host port.
    """
    # Wait for any existing browser tabs to reconnect
    socketio.sleep(2)

    # Check if any clients are already connected via Socket.IO
    has_clients = False
    try:
        if hasattr(socketio.server, 'eio') and hasattr(socketio.server.eio, 'sockets'):
            has_clients = len(socketio.server.eio.sockets) > 0
    except Exception:
        pass

    if not has_clients:
        url = "http://" + ("localhost" if host == "0.0.0.0" else host) + ":" + str(web_port)
        webbrowser.open(url)
        print("Browser opened: " + url)
    else:
        print("Browser tab already connected - refresh the page to reflect changes")


def main(host="localhost", web_port=5000, new=True, *args, **kwargs):
    """Web X2Cscope main function. Calling this function will start Web X2Cscope.

    Args:
        host (string): Default 'localhost'. Use 0.0.0.0 to open the server for external requests.
        web_port (int): Default 5000. The port where the web server is available.
        new (bool): Default True. Should a new browser window/tab be opened at start?
        *args: additional non-key arguments supplied on program call.
        **kwargs: additional keyed arguments supplied on program call.
    """
    app = create_app()

    log_level = kwargs["log_level"] if "log_level" in kwargs else "ERROR"
    app.logger.setLevel(log_level)
    logging.getLogger("werkzeug").setLevel(log_level)

    # check if keys elf and port were supplied
    if "elf" in kwargs and "port" in kwargs:
        # check if both keys are not None
        if kwargs["elf"] and kwargs["port"]:
            print("Loading elf file...")
            web_scope.connect(port=kwargs["port"])
            web_scope.set_file(kwargs["elf"])

    if new:
         socketio.start_background_task(open_browser, web_port=web_port)
    print("Listening at http://" + ("localhost" if host == "0.0.0.0" else host) + ":" + str(web_port))

    if host == "0.0.0.0":
        print("Server is open for external requests!")

    if os.environ.get('DEBUG') != 'true':
        socketio.run(app, debug=False, host=host, port=web_port,
                     allow_unsafe_werkzeug=True)
    else:
        socketio.run(app, debug=True, host=host, port=web_port,
                     allow_unsafe_werkzeug=True, use_reloader=False)

if __name__ == "__main__":
    main(new=True, host="0.0.0.0")
