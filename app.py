import eventlet
eventlet.monkey_patch()

import os
import time
from collections import defaultdict
from threading import Lock

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "https://living-internet-theory.com",
        "https://www.living-internet-theory.com",
    ],
    async_mode="eventlet",
)

state_lock = Lock()
state = {
    "toggle": False,
    "online": 0,
}

_rate_lock = Lock()
_rate_limits: dict[str, float] = defaultdict(float)
RATE_LIMIT_SECONDS = 0.5


def _client_ip() -> str:
    forwarded = request.environ.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() if forwarded else request.remote_addr


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    with state_lock:
        state["online"] += 1
        snapshot = dict(state)
    emit("state", {"toggle": snapshot["toggle"], "online": snapshot["online"]})
    emit("online", {"online": snapshot["online"]}, broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    with state_lock:
        state["online"] = max(0, state["online"] - 1)
        online = state["online"]
    emit("online", {"online": online}, broadcast=True)


@socketio.on("set_toggle")
def handle_set_toggle(payload):
    ip = _client_ip()
    now = time.monotonic()
    with _rate_lock:
        if now - _rate_limits[ip] < RATE_LIMIT_SECONDS:
            return
        _rate_limits[ip] = now
    toggle_value = bool(payload.get("toggle", False))
    with state_lock:
        state["toggle"] = toggle_value
    emit("toggle", {"toggle": toggle_value}, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5002, debug=True)
