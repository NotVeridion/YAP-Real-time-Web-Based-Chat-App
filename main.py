from flask import Flask, request, render_template, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import random
import string

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
    # A little bit done early to route to room.html for testing front-end
    # feel free to change but leave some way to enter room.html ty -matthew
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")

        if not name:
            return render_template("home.html", error="Please enter a username.", code=code, name=name)

        if "join" in request.form:
            if not code:
                return render_template("home.html", error="Please enter a room code.", code=code, name=name)
            if code not in rooms:
                return render_template("home.html", error="Room not found.", code=code, name=name)

        if "create" in request.form:
            code = generate_room_code()
            rooms[code] = {"members": 0, "messages": []}

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
    # Send message history to the new joiner
    emit("message_history", {"messages": rooms[room]["messages"]})
    # Broadcast join notification to everyone in room
    send({"name": name, "message": "has entered the room"}, to=room)

@socketio.on("disconnect")
def on_disconnect():
    name = session.get("name")
    room = session.get("room")
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    send({"name": name, "message": "has left the room"}, to=room)

@socketio.on("message")
def on_message(data):
    room = session.get("room")
    name = session.get("name")
    if room not in rooms:
        return
    content = {"name": name, "message": data["data"]}
    rooms[room]["messages"].append(content)
    # Broadcast message to ALL clients in the room
    send(content, to=room, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, debug=True)