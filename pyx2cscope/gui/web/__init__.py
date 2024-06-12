from flask import Flask
import logging

from pyx2cscope.xc2scope import X2CScope

x2cScope : X2CScope

def connect_x2c(*args, **kwargs):
    global x2cScope
    x2cScope = X2CScope(**kwargs)
    x2cScope.list_variables()

def get_x2c() -> X2CScope:
    return x2cScope

def create_app(log_level=logging.ERROR):
    app = Flask(__name__)
    app.logger.setLevel(log_level)
    return app