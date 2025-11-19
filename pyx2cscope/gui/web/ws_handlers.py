from flask_socketio import emit
from urllib.parse import parse_qs

from pyx2cscope.gui.web.extensions import socketio
from pyx2cscope.gui.web.scope import web_scope


def background_x2cscope_task():
    """Background x2cScope thread"""
    while True:
        watch_values = web_scope.watch_poll()
        scope_values = web_scope.scope_poll()
        if watch_values:
            socketio.emit("watch_data_update", watch_values, namespace="/watch-view")
        if scope_values:
            socketio.emit("scope_chart_update", scope_values, namespace="/scope-view")
            if web_scope.scope_trigger is False:
                socketio.emit("sample_control_updated", {
                    "status": "success", "data": {"triggerAction": "off"}
                },  namespace="/scope-view")
        socketio.sleep(0.1)

@socketio.on("connect")
def handle_connect():
    print("Client connected (app)")
    if not hasattr(socketio, "bg_thread"):
        socketio.bg_thread = socketio.start_background_task(background_x2cscope_task)

@socketio.on("connect", namespace="/watch-view")
def handle_connect_watch():
    print("Client connected (watch_view)")
    if not hasattr(socketio, "bg_thread"):
        socketio.bg_thread = socketio.start_background_task(background_x2cscope_task)

@socketio.on("disconnect", namespace="/watch-view")
def handle_disconnect_watch():
    print("Client disconnected (watch_view)")

@socketio.on("connect", namespace="/scope-view")
def handle_connect_watch():
    print("Client connected (scope_view)")

@socketio.on("disconnect", namespace="/scope-view")
def handle_disconnect_scope():
    print("Client disconnected (scope_view)")

@socketio.on("update_watch_var", namespace="/watch-view")
def handle_update_watch_var(data):
    param = data.get("param", None)
    field = data.get("field", None)
    value = data.get("value", None)
    if all([param, field, value]) is not None:
        data = web_scope.set_watch_var(param, field, value)
        emit("watch_data_update", data, broadcast=True)

@socketio.on("set_watch_rate", namespace="/watch-view")
def handle_set_watch_rate(data):
    var = data.get("rate", 1)
    web_scope.set_watch_rate(var)

@socketio.on("refresh_watch_data", namespace="/watch-view")
def handle_refresh_watch_data():
    web_scope.set_watch_refresh()

@socketio.on("add_watch_var", namespace="/watch-view")
def handle_add_watch_var(data):
    var = data.get("var")
    if var:
        web_scope.add_watch_var(var)
        emit("watch_table_update", {"var": var}, broadcast=True)

@socketio.on("remove_watch_var", namespace="/watch-view")
def handle_remove_watch_var(data):
    var = data.get("var")
    if var:
        web_scope.remove_watch_var(var)
        emit("watch_table_update", {"var": var}, broadcast=True)

# Scope variables
@socketio.on("add_scope_var", namespace="/scope-view")
def handle_add_scope_var(data):
    var = data.get("var")
    if var:
        web_scope.add_scope_var(var)
        emit("scope_table_update", {"var": var}, broadcast=True)

@socketio.on("remove_scope_var", namespace="/scope-view")
def handle_remove_scope_var(data):
    var = data.get("var")
    if var:
        web_scope.remove_scope_var(var)
        emit("scope_table_update", {"var": var}, broadcast=True)

@socketio.on("update_scope_var", namespace="/scope-view")
def handle_update_scope_var(data):
    param = data.get("param", None)
    field = data.get("field", None)
    value = data.get("value", None)
    if all([param, field, value]) is not None:
        data = web_scope.set_scope_var(param, field, value)
        emit("scope_table_update", data, broadcast=True)


@socketio.on("update_sample_control", namespace="/scope-view")
def handle_update_sample_control(data):
    data = {k: v[0] if v else '' for k, v in parse_qs(data).items()}
    trigger_action = data.get('triggerAction', 'off')
    sample_time = int(data.get('sampleTime', 1))
    sample_freq = float(data.get('sampleFreq', 20))
    web_scope.scope_set_sample(trigger_action, sample_time, sample_freq)
    emit("sample_control_updated", {
        "status": "success",
        "message": "Trigger settings updated successfully",
        "data": {
            "triggerAction": trigger_action,
            "sampleTime": sample_time,
            "sampleFreq": sample_freq,
        }
    }, broadcast=True)

@socketio.on("update_trigger_control", namespace="/scope-view")
def handle_update_trigger_control(data):
    data = {k: int(v[0]) if v else 0 for k, v in parse_qs(data).items()}
    web_scope.scope_set_trigger(**data)
    emit("trigger_control_updated", {
        "status": "success",
        "message": "Trigger settings updated successfully",
        "data": data
    }, broadcast=True)
