from flask import Flask
import logging

from pyx2cscope.xc2scope import X2CScope

x2cScope : X2CScope
x2cScope_init = False

def connect_x2c(*args, **kwargs):
    global x2cScope, x2cScope_init
    x2cScope = X2CScope(**kwargs)
    x2cScope.list_variables()
    x2cScope_init = True

def disconnect_x2c(*args, **kwargs):
    global x2cScope, x2cScope_init
    x2cScope.disconnect()
    x2cScope_init = False

def get_x2c() -> X2CScope:
    return x2cScope if x2cScope_init else None

def create_app(log_level=logging.ERROR):
    app = Flask(__name__)
    app.logger.setLevel(log_level)
    return app