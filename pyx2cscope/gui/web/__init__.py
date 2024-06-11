from flask import Flask
import logging
import random


data = [
    {"id": "motor.A", "text": random.randint(0, 100)},
    {"id": "motor.B", "text": random.randint(0, 100)},
    {"id": "motor.C", "text": random.randint(0, 100)}
]

def create_x2cscope(*args, **kwargs):
    global x2cScope
    x2cScope = X2CScope(**kwargs)
    x2cScope.list_variables()

def create_app(log_level=logging.ERROR):
    app = Flask(__name__)
    #log = logging.getLogger('werkzeug')
    #log.setLevel(log_level)
    return app