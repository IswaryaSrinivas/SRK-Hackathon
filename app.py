from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3, os, re, secrets

app = Flask(__name__, template_folder="templates")
app.config.update(
    SECRET_KEY=os.environ.get("SHAKTI_SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # Set True behind HTTPS in production.
)
DB_PATH = os.path.join(os.path.dirname(__file__), "shakti_shield.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            identity TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL UNIQUE,
            data TEXT NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS mentor_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            name TEXT NOT NULL, mentor TEXT NOT NULL, topic TEXT DEFAULT '',
            status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS community_posts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            topic TEXT DEFAULT '', message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS safety_reports(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            profile TEXT DEFAULT '', reason TEXT NOT NULL, details TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id))""")

def signed_in(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(error="Please sign in to continue."), 401
        return fn(*args, **kwargs)
    return wrapper

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify(status="ok", app="Shakti Shield")

@app.post("/api/register")
def register():
    d = request.get_json(silent=True) or {}
    name = str(d.get("name", "")).strip()
    identity = str(d.get("identity", "")).strip().lower()
    password = str(d.get("password", ""))
    if len(name) < 2 or len(identity) < 3 or len(password) < 8:
        return jsonify(error="Enter your name, email/phone, and a password with at least 8 characters."), 400
    if len(password) > 128:
        return jsonify(error="Password is too long."), 400
    try:
        with db() as c:
            cur = c.execute("INSERT INTO users(name,identity,password_hash) VALUES(?,?,?)",
                            (name, identity, generate_password_hash(password)))
            uid = cur.lastrowid
    except sqlite3.IntegrityError:
        return jsonify(error="An account with that email/phone already exists. Please sign in."), 409
    session.clear()
    session["user_id"] = uid
    session["user_name"] = name
    return jsonify(ok=True, user={"name": name, "identity": identity}), 201

@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    identity = str(d.get("identity", "")).strip().lower()
    password = str(d.get("password", ""))
    with db() as c:
        user = c.execute("SELECT id,name,identity,password_hash FROM users WHERE identity=?", (identity,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Email/phone or password is incorrect."), 401
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return jsonify(ok=True, user={"name": user["name"], "identity": user["identity"]})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@app.get("/api/me")
@signed_in
def me():
    return jsonify(user={"name": session.get("user_name")})

@app.post("/api/plan")
@signed_in
def save_plan():
    import json
    data = request.get_json(silent=True) or {}
    with db() as c:
        c.execute("""INSERT INTO plans(user_id,data,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
                     ON CONFLICT(user_id) DO UPDATE SET data=excluded.data,updated_at=CURRENT_TIMESTAMP""",
                  (session["user_id"], json.dumps(data, ensure_ascii=False)))
    return jsonify(ok=True)

@app.post("/api/mentor-requests")
@signed_in
def mentor_request():
    d = request.get_json(silent=True) or {}
    name, mentor = str(d.get("name","")).strip(), str(d.get("mentor","")).strip()
    if not name or not mentor:
        return jsonify(error="Name and mentor are required."), 400
    with db() as c:
        cur = c.execute("INSERT INTO mentor_requests(user_id,name,mentor,topic) VALUES(?,?,?,?)",
                        (session["user_id"], name[:100], mentor[:120], str(d.get("topic",""))[:300]))
    return jsonify(ok=True, id=cur.lastrowid), 201

@app.post("/api/community/posts")
@signed_in
def create_post():
    d = request.get_json(silent=True) or {}
    message = str(d.get("message","")).strip()
    if not message or len(message) > 400:
        return jsonify(error="Write a message of 1–400 characters."), 400
    with db() as c:
        cur = c.execute("INSERT INTO community_posts(user_id,topic,message) VALUES(?,?,?)",
                        (session["user_id"], str(d.get("topic",""))[:100], message))
    return jsonify(ok=True, id=cur.lastrowid), 201

@app.post("/api/safety-reports")
@signed_in
def safety_report():
    d = request.get_json(silent=True) or {}
    reason = str(d.get("reason","")).strip()
    if not reason:
        return jsonify(error="Choose a report reason."), 400
    with db() as c:
        cur = c.execute("INSERT INTO safety_reports(user_id,profile,reason,details) VALUES(?,?,?,?)",
                        (session["user_id"], str(d.get("profile",""))[:120], reason[:120], str(d.get("details",""))[:1000]))
    return jsonify(ok=True, id=cur.lastrowid), 201

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
