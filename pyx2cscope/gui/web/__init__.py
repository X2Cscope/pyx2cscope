from flask import Flask
import logging
import random

x2cScope = None

data = [
    {"id": "motor.A", "text": random.randint(0, 100)},
    {"id": "motor.B", "text": random.randint(0, 100)},
    {"id": "motor.C", "text": random.randint(0, 100)}
]

def create_app(log_level=logging.ERROR):
    app = Flask(__name__)
    #log = logging.getLogger('werkzeug')
    #log.setLevel(log_level)
    return app