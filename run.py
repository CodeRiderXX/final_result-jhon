import os
from app import create_app
from flask import request, abort

# Self-restart feature for development
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    Observer = None
    FileSystemEventHandler = object

class RestartHandler(FileSystemEventHandler):
    def __init__(self, restart_callback):
        self.restart_callback = restart_callback
    def on_any_event(self, event):
        print('Detected change, restarting backend...')
        self.restart_callback()

app = create_app()

# Simple firewall: allow all IPs by default, but block any in BLOCKED_IPS
BLOCKED_IPS = set()  # Add any IPs you want to block

@app.before_request
def firewall():
    ip = request.remote_addr
    if ip in BLOCKED_IPS:
        abort(403)

def run_server():
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == '__main__':
    if Observer:
        import sys
        import threading
        import signal
        import time
        def restart():
            os.execv(sys.executable, [sys.executable] + sys.argv)
        event_handler = RestartHandler(restart)
        observer = Observer()
        observer.schedule(event_handler, path='.', recursive=True)
        observer.start()
        try:
            run_server()
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    else:
        run_server()