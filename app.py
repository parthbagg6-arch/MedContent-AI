import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = BASE_DIR / "users.db"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-before-deployment")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a35b:free")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY) if API_KEY else None


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Please log in to continue."}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not name or not email or not password:
        return jsonify(error="Please fill in all fields."), 400
    if len(password) < 8:
        return jsonify(error="Password must be at least 8 characters."), 400
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(error="Enter a valid email address."), 400
    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                (name, email, generate_password_hash(password))
            )
            session.clear()
            session["user_id"] = cur.lastrowid
            session["user_name"] = name
        return jsonify(success=True, name=name)
    except sqlite3.IntegrityError:
        return jsonify(error="An account with this email already exists."), 409


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Incorrect email or password."), 401
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return jsonify(success=True, name=user["name"])


@app.get("/api/me")
def me():
    if not session.get("user_id"):
        return jsonify(logged_in=False)
    return jsonify(logged_in=True, name=session.get("user_name", "User"))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(success=True)


@app.post("/api/generate")
@login_required
def generate():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    content_type = (data.get("content_type") or "Patient Education Article").strip()
    audience = (data.get("audience") or "General public").strip()
    tone = (data.get("tone") or "Clear and reassuring").strip()
    if not topic:
        return jsonify(error="Enter a medical topic or brief first."), 400
    if len(topic) > 1500:
        return jsonify(error="Please keep the topic under 1,500 characters."), 400
    if client is None:
        return jsonify(error="AI service is not configured. Add OPENROUTER_API_KEY to your environment."), 503

    prompt = f"""Create a well-structured {content_type} about: {topic}
Intended audience: {audience}
Tone: {tone}

DOMAIN RULES:
- Stay within healthcare, medicine, public health, clinical education, or medical communication.
- Use medically responsible, evidence-aware language and explain technical terms.
- Do not invent studies, statistics, citations, drug dosages, or clinical guidelines.
- Do not diagnose an individual, prescribe treatment, or recommend changing medication.
- If the topic involves symptoms, diagnosis, medicines, or treatment, clearly state that the content is educational and readers should consult a qualified healthcare professional for personal advice.
- Mention urgent/emergency care only in general terms when relevant; do not create false reassurance.
- If a requested claim is uncertain or controversial, say so rather than presenting it as fact.
- Make the output useful, readable, original, and formatted with headings and bullet points where appropriate.
Return the content only, followed by a short medical-information disclaimer."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are MedContent AI, a careful medical and healthcare content writing assistant. You create educational content, not individual medical advice."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=1200
        )
        content = response.choices[0].message.content or ""
        return jsonify(content=content)
    except Exception as exc:
        app.logger.exception("Content generation failed: %s", exc)
        return jsonify(error="Content generation failed. Check your API key, model availability, and connection."), 502


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
