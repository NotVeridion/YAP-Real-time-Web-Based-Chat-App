from flask import Flask, request, render_template, redirect, url_for
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = "secretkeyfornow"
socketio = SocketIO(app)

@app.route("/", methods=["POST", "GET"])
def home():
    # A little bit done early to route to room.html for testing front-end
    # feel free to change but leave some way to enter room.html ty -matthew
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")

        if not name or not code:
            return render_template("home.html")
        else:
            return redirect(url_for("room"))
        
    return render_template("home.html")

@app.route("/room")
def room():
    return render_template("room.html")

if __name__ == "__main__":
    socketio.run(app, debug=True)