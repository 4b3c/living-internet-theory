from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Shared global state
state = {
    "toggle": False,
    "online": 0,
}


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    state["online"] += 1
    emit("state", {"toggle": state["toggle"], "online": state["online"]})
    emit("online", {"online": state["online"]}, broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    state["online"] = max(0, state["online"] - 1)
    emit("online", {"online": state["online"]}, broadcast=True)


@socketio.on("set_toggle")
def handle_set_toggle(payload):
    toggle_value = bool(payload.get("toggle", False))
    state["toggle"] = toggle_value
    emit("toggle", {"toggle": state["toggle"]}, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5002, debug=True)
