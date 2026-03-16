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

# --- Toggle ---

toggle_lock = Lock()
toggle_state = {"toggle": False, "online": 0}

_rate_lock = Lock()
_rate_limits: dict[str, float] = defaultdict(float)
RATE_LIMIT_SECONDS = 0.1
MAX_USERS = 10_000


def _client_ip() -> str:
    forwarded = request.environ.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() if forwarded else request.remote_addr


# --- Tug of war ---

tug_lock = Lock()
tug_sides: dict[str, str] = {}  # sid -> "red" | "blue"


def _tug_snapshot() -> dict:
    blue = sum(1 for s in tug_sides.values() if s == "blue")
    red = sum(1 for s in tug_sides.values() if s == "red")
    total = blue + red
    return {"blue": blue, "red": red, "position": blue / total if total > 0 else 0.5}


# --- Routes ---

@app.route("/")
def index():
    return render_template("toggle.html")


@app.route("/tug")
def tug_page():
    return render_template("tug.html")


# --- Toggle namespace ---

@socketio.on("connect", namespace="/toggle")
def toggle_connect():
    with toggle_lock:
        if toggle_state["online"] >= MAX_USERS:
            return False
        toggle_state["online"] += 1
        snapshot = dict(toggle_state)
    emit("state", {"toggle": snapshot["toggle"], "online": snapshot["online"]})
    emit("online", {"online": snapshot["online"]}, broadcast=True)


@socketio.on("disconnect", namespace="/toggle")
def toggle_disconnect():
    with toggle_lock:
        toggle_state["online"] = max(0, toggle_state["online"] - 1)
        online = toggle_state["online"]
    emit("online", {"online": online}, broadcast=True)


@socketio.on("set_toggle", namespace="/toggle")
def toggle_set(payload):
    ip = _client_ip()
    now = time.monotonic()
    with _rate_lock:
        if now - _rate_limits[ip] < RATE_LIMIT_SECONDS:
            return
        _rate_limits[ip] = now
    toggle_value = bool(payload.get("toggle", False))
    with toggle_lock:
        toggle_state["toggle"] = toggle_value
    emit("toggle", {"toggle": toggle_value}, broadcast=True)


# --- Tug namespace ---

@socketio.on("connect", namespace="/tug")
def tug_connect():
    emit("state", _tug_snapshot())


@socketio.on("disconnect", namespace="/tug")
def tug_disconnect():
    with tug_lock:
        tug_sides.pop(request.sid, None)
        snap = _tug_snapshot()
    emit("state", snap, broadcast=True)


@socketio.on("choose_side", namespace="/tug")
def tug_choose(payload):
    side = payload.get("side")
    if side not in ("red", "blue"):
        return
    with tug_lock:
        tug_sides[request.sid] = side
        snap = _tug_snapshot()
    emit("state", snap, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5002, debug=True)
