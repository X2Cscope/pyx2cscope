"""Web X2CScope global module functions available over the subviews.

The pyX2Cscope object is stored at this level and available to all other subviews.
Additionally connect, disconnect and is_connected functions are available to handle
pyX2Cscope states.
"""
from flask import Flask

from pyx2cscope.xc2scope import X2CScope

x2c_scope : X2CScope
x2c_scope_init = False

def connect_x2c(*args, **kwargs):
    """Instantiate and Connect pyX2Cscope with the supplied arguments.

    Args:
        *args: non-keyed arguments.
        **kwargs: keyed arguments. Expected minimal "port" and "elf_file".
    """
    global x2c_scope, x2c_scope_init
    x2c_scope = X2CScope(**kwargs)
    x2c_scope.list_variables()
    x2c_scope_init = True

def disconnect_x2c(*args, **kwargs):
    """Disconnect and reset instance of pyX2Cscope.

    Args:
        *args: non-keyed arguments.
        **kwargs: keyed arguments.
    """
    global x2c_scope, x2c_scope_init  #TODO fix the global import
    x2c_scope.disconnect()
    x2c_scope_init = False

def get_x2c() -> X2CScope:
    """Return the module x2cScope object to all subviews."""
    return x2c_scope if x2c_scope_init else None

def create_app(log_level=None):
    """Create the Flask app.

    Args:
        log_level (int): Default ERROR. The log level to be used.
    """
    app = Flask(__name__)
    return app