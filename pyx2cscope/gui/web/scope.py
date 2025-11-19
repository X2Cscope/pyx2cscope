import time

from pandas.core.dtypes.inference import is_number

from pyx2cscope.gui.web import extensions
from pyx2cscope.x2cscope import X2CScope, TriggerConfig


class WebScope:
    def __init__(self):
        self.watch_vars = []
        self.watch_rate = 1 # in seconds
        self.watch_refresh = 0
        self.watch_next = time.time()

        self.scope_vars = []
        self.scope_trigger = False
        self.scope_burst = False
        self.scope_sample_time = 1
        self.scope_time_sampling = 50e-3

        self.x2c_scope :X2CScope | None = None
        self._lock = extensions.create_lock()

    def _get_watch_variable_as_dict(self, variable, value=None):
        primitive = variable.__class__.__name__.lower().replace("variable", "")
        if value is None:
            with self._lock:
                value = variable.get_value()
        value = round(value, 4) if primitive == "float" else value
        return {
            "live": 0,
            "variable": variable,
            "type": primitive,
            "value": value,
            "scaling": 1,
            "offset": 0,
            "scaled_value": value,
            "remove": 0,
        }

    def _get_scope_variable_as_dict(self, variable):
        colors = [
            "#FF0000",
            "#00FF00",
            "#0000FF",
            "#FFFF00",
            "#00FFFF",
            "#FF00FF",
            "#800080",
            "#CCCCCC",
        ]
        return {
            "trigger": 0,
            "enable": 1,
            "variable": variable,
            "color": colors[len(self.scope_vars)],
            "gain": 1,
            "offset": 0,
            "remove": 0,
        }

    @staticmethod
    def _update_watch_fields(data: dict):
        data["scaled_value"] = data["value"] * data["scaling"] + data["offset"]
        if data["type"] == "float":
            data["value"] = round(data["value"], 4)
            data["scaled_value"] = round(data["scaled_value"], 4)

    def _read_watch_variable(self, data: dict):
        with self._lock:
            # pyX2CScope read variable
            data["value"] = data["variable"].get_value()
            self._update_watch_fields(data)
            return self.variable_to_json(data)

    @staticmethod
    def variable_to_json(data: dict):
        return {f: v.info.name if f == "variable" else v for f, v in data.items()}

    def set_watch_var(self, var, field, value):
        with self._lock:
            for variable in self.watch_vars:
                if variable["variable"].info.name == var:
                    variable[field] = float(value)
                    if field == "value":
                        variable["variable"].set_value(variable[field])
                    self._update_watch_fields(variable)
                    return [self.variable_to_json(variable)]
            return []

    def set_watch_refresh(self):
        self.watch_refresh = 1

    def set_watch_rate(self, rate):
        if is_number(rate) and 0 < rate < 6:
            self.watch_rate = rate

    def clear_watch_var(self):
        self.watch_vars.clear()

    def add_watch_var(self, var):
        var_dict = None
        if not any(_data["variable"].info.name == var for _data in self.watch_vars):
            variable = self.x2c_scope.get_variable(var)
            if variable is not None:
                var_dict = self._get_watch_variable_as_dict(variable)
                self.watch_vars.append(var_dict)
        return var_dict

    def remove_watch_var(self, var):
        for variable in self.watch_vars:
            if variable["variable"].info.name == var:
                self.watch_vars.remove(variable)
                break

    def watch_poll(self):
        current_time = time.time()
        if current_time < self.watch_next and self.watch_refresh == 0:
            return []

        # Update next polling time
        self.watch_next = current_time + self.watch_rate

        # Poll the variables, this is thread safe
        result = [self._read_watch_variable(v)
                for v in self.watch_vars
                if v["live"] == 1 or self.watch_refresh == 1]

        if self.watch_refresh == 1:
            self.watch_refresh = 0

        return result

    def clear_scope_var(self):
        with self._lock:
            self.scope_vars.clear()
            self.x2c_scope.clear_all_scope_channel()

    def add_scope_var(self, var):
        var_dict = None
        if not any(data["variable"].info.name == var for data in self.scope_vars):
            variable = self.x2c_scope.get_variable(var)
            if variable is not None:
                var_dict = self._get_scope_variable_as_dict(variable)
                self.scope_vars.append(var_dict)
                self.x2c_scope.add_scope_channel(variable)
        return var_dict

    def remove_scope_var(self, var):
        for variable in self.scope_vars:
            if variable["variable"].info.name == var:
                self.scope_vars.remove(variable)
                self.x2c_scope.remove_scope_channel(variable["variable"])
                break

    def set_scope_var(self, param, field, value):
        with self._lock:
            for variable in self.scope_vars:
                self._scope_set_trigger(variable, param, field, value)
                self._scope_set_enable(variable, param, field, value)
                self._scope_set_fields(variable, param, field, value)
            return []

    @staticmethod
    def _scope_set_trigger(data, param, field, value):
        if field == "trigger":
            value = float(value)
            if data["variable"].info.name != param:
                data["trigger"] = 0.0 if value == 1.0 else data["trigger"]

    @staticmethod
    def _scope_set_fields(data, param, field, value):
        if data["variable"].info.name == param:
            data[field] = value if field == "color" else float(value)

    def _scope_set_enable(self, data, param, field, value):
        if field == "enable":
            if data["variable"].info.name == param:
                if float(value):
                    self.x2c_scope.add_scope_channel(data["variable"])
                else:
                    self.x2c_scope.remove_scope_channel(data["variable"])

    def scope_set_trigger(self, **kwargs):
        if kwargs["trigger_mode"] == 1:
            for var in self.scope_vars:
                if var["trigger"]:
                    trigger_config = TriggerConfig(var["variable"], **kwargs)
                    self.x2c_scope.set_scope_trigger(trigger_config)
                    return
        self.x2c_scope.reset_scope_trigger()

    def scope_set_sample(self, trigger_action, sample_time, sample_freq):
        if self.x2c_scope is None:
            return
        with self._lock:
            if self.scope_sample_time != sample_time:
                self.scope_sample_time = sample_time
                self.x2c_scope.set_sample_time(self.scope_sample_time)
            self.scope_time_sampling = self.x2c_scope.get_scope_sample_time(1 / (sample_freq * 100))
            if "shot" in trigger_action:
                self.scope_burst = True
            trigger_action = False if "off" in trigger_action else True
            if self.scope_trigger != trigger_action:
                if trigger_action:
                    self.x2c_scope.request_scope_data()
                self.scope_trigger = trigger_action

    def scope_poll(self):
        with self._lock:
            if self.scope_trigger:
                if self.x2c_scope.is_scope_data_ready():
                    datasets = self.get_scope_datasets()
                    size = len(datasets[0]["data"]) if len(datasets) > 0 else 1000
                    labels = self.get_scope_chart_label(size)

                    if self.scope_burst:
                        self.scope_burst = False
                        self.scope_trigger = False
                    else:
                        self.x2c_scope.request_scope_data()

                    return {"datasets": datasets, "labels": labels}
            return {}

    def get_scope_datasets(self):
        data = []
        channel_data = self.x2c_scope.get_scope_channel_data()
        for channel in self.scope_vars:
            # if variable is disabled on scope_data, it is not available on channel_data
            if channel["variable"].info.name in channel_data:
                variable = channel["variable"].info.name
                data_line = [
                    sample * channel["gain"] + channel["offset"] for sample in channel_data[variable]
                ]
                item = {
                    "label": variable,
                    "pointRadius": 0,
                    "borderColor": channel["color"],
                    "backgroundColor": channel["color"],
                    "data": data_line,
                }
                data.append(item)
        return data

    def get_scope_chart_label(self, size=100):
        return [i * self.scope_time_sampling for i in range(0, size)]

    def connect(self, *args, **kwargs):
        self.x2c_scope = X2CScope(*args, **kwargs)

    def set_file(self, import_file):
        self.x2c_scope.import_variables(import_file)

    def list_variables(self):
        return self.x2c_scope.list_variables()

    def disconnect(self):
        self.x2c_scope.disconnect()
        self.x2c_scope = None

    def is_connected(self):
        return self.x2c_scope is not None

web_scope = WebScope()
