"""Flask-SocketIO extensions and lock creation utilities.

This module provides SocketIO configuration and lock creation functions
that adapt to the current environment (production or debug mode).
"""
import os

from flask_socketio import SocketIO

# Only enable eventlet in production, not during debugging
if os.environ.get('DEBUG', None) is None:  # None means production
    import eventlet
    eventlet.monkey_patch()
    socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

    def create_lock():
        """Create an eventlet-based semaphore lock.

        Returns:
            eventlet.semaphore.Semaphore: A semaphore lock for thread synchronization.
        """
        return eventlet.semaphore.Semaphore()
else:
    socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
    import threading

    def create_lock():
        """Create a threading-based lock.

        Returns:
            threading.Lock: A lock for thread synchronization.
        """
        return threading.Lock()
