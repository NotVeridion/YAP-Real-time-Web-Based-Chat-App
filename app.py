from flask import Flask, request, render_template, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import random
import string
import re

CHATBOX_MESSAGE_LIMIT = 25 # Message limit for chat box messages. If threshold is met, pops oldest message off.

app = Flask(__name__)
app.config['SECRET_KEY'] = "secretkeyfornow"
socketio = SocketIO(app)

rooms = {}

def generate_room_code(length=4):
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=length))
        if code not in rooms:
            return code

@app.route("/", methods=["POST", "GET"])
def home():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()

        # Username validation
        if not name:
            return render_template("home.html", error="Please enter a username.", code=code, name=name)
        if len(name) > 15:
            return render_template("home.html", error="Username must be 15 characters or less.", code=code, name=name)
        if not re.match(r'^[a-zA-Z0-9 _-]+$', name):
            return render_template("home.html", error="Username must be letters, numbers, spaces, underscores, or dashes only.", code=code, name=name)

        if "join" in request.form:
            if not code:
                return render_template("home.html", error="Please enter a room code.", code=code, name=name)
            if not re.match(r'^[A-Z]{4}$', code):
                return render_template("home.html", error="Room code must be exactly 4 capital letters.", code=code, name=name)
            if code not in rooms:
                return render_template("home.html", error="Room not found.", code=code, name=name)

        if "create" in request.form:
            if code:
                if not re.match(r'^[A-Z]{4}$', code):
                    return render_template("home.html", error="Room code must be exactly 4 capital letters.", code=code, name=name)
                if code in rooms:
                    return render_template("home.html", error=f"Room code '{code}' is already taken. Choose a new one.", code=code, name=name)
            if not code:
                code = generate_room_code()
            rooms[code] = {"users": [], "members": 0, "messages": [], "userColorMap": {}}

        session["name"] = name
        session["room"] = code
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    name = session.get("name")
    code = session.get("room")
    if not name or not code or code not in rooms:
        return redirect(url_for("home"))
    return render_template("room.html", code=code, name=name)

# ── CLIENT-TO-SERVER SOCKET EVENTS ──────────────────────────

@socketio.on("connect")
def on_connect():
    name = session.get("name")
    room = session.get("room")
    if not name or not room:
        return
    
    join_room(room)
    rooms[room]["members"] += 1
    rooms[room]["users"].append(name)
    rooms[room]["userColorMap"][name] = "#6ca8ff"
    emit("user_connected", {"name": name, "users": rooms[room]["users"], "userColorMap": rooms[room]["userColorMap"]}, to=room)
    emit("message_history", {"messages": rooms[room]["messages"]})

@socketio.on("disconnect")
def on_disconnect():
    name = session.get("name")
    room = session.get("room")
    leave_room(room)
    if room in rooms:
        if name in rooms[room]["users"]:
            rooms[room]["users"].remove(name)
            rooms[room]["userColorMap"].pop(name)
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
            return
    emit("user_disconnected", {"name": name, "users": rooms[room]["users"], "userColorMap": rooms[room]["userColorMap"]}, to=room)

@socketio.on("message")
def on_message(data):
    room = session.get("room")
    name = session.get("name")
    if room not in rooms:
        return
    content = {"name": name, "message": data["data"]}
    if (len(rooms[room]["messages"]) >= CHATBOX_MESSAGE_LIMIT):
        rooms[room]["messages"].pop(0)
    rooms[room]["messages"].append(content)
    send(content, to=room)

@socketio.on("color_change")
def color_change(data):
    room = session.get("room")
    name = data["name"]
    color = data["color"]
    rooms[room]["userColorMap"][name] = color
    emit("color_change", {"name": name, "color": color}, to=room)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, allow_unsafe_werkzeug=True, host="0.0.0.0", port=port)