from flask_socketio import SocketIO
import os

# Only enable eventlet in production, not during debugging
if os.environ.get('DEBUG', None) is None:  # None means production
    import eventlet
    eventlet.monkey_patch()
    socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

    def create_lock():
        return eventlet.semaphore.Semaphore()
else:
    socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
    import threading

    def create_lock():
        return threading.Lock()
