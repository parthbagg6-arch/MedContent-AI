import os
import sqlite3
from pathlib import Path

import streamlit as st
from openai import OpenAI
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"

st.set_page_config(page_title="MedContent AI", page_icon="✚", layout="wide")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def register_user(name, email, password):
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                (name.strip(), email.strip().lower(), generate_password_hash(password))
            )
        return True, "Account created. You can now sign in."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."

def authenticate(email, password):
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email=?",
            (email.strip().lower(),)
        ).fetchone()
    if user and check_password_hash(user["password_hash"], password):
        return dict(user)
    return None

def get_client():
    key = ""
    model = "nvidia/nemotron-3-ultra-550b-a35b:free"
    try:
        key = st.secrets.get("OPENROUTER_API_KEY", "")
        model = st.secrets.get("OPENROUTER_MODEL", model)
    except Exception:
        pass
    key = key or os.getenv("OPENROUTER_API_KEY", "")
    model = os.getenv("OPENROUTER_MODEL", model)
    if not key:
        return None, model
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key), model

def generate_content(topic, content_type, audience, tone):
    client, model = get_client()
    if client is None:
        raise RuntimeError("AI service is not configured. Add OPENROUTER_API_KEY in Streamlit Secrets.")
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
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are MedContent AI, a careful medical and healthcare content writing assistant. You create educational content, not individual medical advice."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=1200
    )
    return response.choices[0].message.content or ""

init_db()
if "user" not in st.session_state:
    st.session_state.user = None
if "generated_content" not in st.session_state:
    st.session_state.generated_content = ""

st.markdown("""
<style>
:root { color-scheme: light; }
.block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem;}
.stApp {background: linear-gradient(135deg,#f4f8fb 0%,#eef5f4 55%,#f8f7fc 100%);}
.hero {background:linear-gradient(115deg,#102f42,#176b69);padding:2rem 2.2rem;border-radius:22px;color:white;margin-bottom:1.3rem;box-shadow:0 12px 35px #12384a20;}
.hero h1 {color:white;font-size:2.35rem;margin:0 0 .35rem 0;}
.hero p {color:#d8eeeb;margin:0;font-size:1.02rem;}
.panel {background:white;border:1px solid #e3ecee;border-radius:18px;padding:1.35rem 1.5rem;box-shadow:0 8px 26px #173c4a0b;}
.small-muted {color:#637780;font-size:.9rem;}
div[data-testid="stForm"] {background:white;border:1px solid #e3ecee;border-radius:18px;padding:1.3rem;}
.stButton>button, .stFormSubmitButton>button {border-radius:10px;font-weight:650;}
.notice {background:#e9f4f2;border-left:4px solid #27877c;padding:.9rem 1rem;border-radius:9px;color:#244c50;margin:1rem 0;}
footer {color:#6c7d83;text-align:center;margin-top:2rem;font-size:.85rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>✚ MedContent AI</h1>
  <p>Healthcare content studio · Clear, responsible medical communication</p>
</div>
""", unsafe_allow_html=True)

if st.session_state.user is None:
    left, right = st.columns([1.05, 1.2], gap="large")
    with left:
        st.markdown("""
        <div class="panel">
          <h2>Make medical knowledge easier to understand.</h2>
          <p>Create clear healthcare content for patients, students and medical professionals.</p>
          <hr>
          <p>✦ Audience-aware writing<br>✦ Multiple medical content formats<br>✦ Copy and download drafts<br>✦ Passwords securely hashed</p>
          <p class="small-muted">Your workspace is private. Do not enter patient-identifiable information.</p>
        </div>
        """, unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        mode = st.radio("Welcome", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed")
        if mode == "Create account":
            with st.form("register_form", clear_on_submit=False):
                name = st.text_input("Full name", placeholder="Your name")
                email = st.text_input("Email address", placeholder="name@example.com")
                password = st.text_input("Password", type="password", help="At least 8 characters")
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create account", use_container_width=True)
            if submitted:
                if not name.strip() or not email.strip() or not password:
                    st.error("Please fill in all fields.")
                elif "@" not in email or "." not in email.split("@")[-1]:
                    st.error("Enter a valid email address.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = register_user(name, email, password)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
        else:
            with st.form("login_form"):
                email = st.text_input("Email address", placeholder="name@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                if not email or not password:
                    st.error("Enter your email and password.")
                else:
                    user = authenticate(email, password)
                    if user:
                        st.session_state.user = {"id": user["id"], "name": user["name"], "email": user["email"]}
                        st.rerun()
                    else:
                        st.error("Incorrect email or password.")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    user = st.session_state.user
    top1, top2 = st.columns([4,1])
    with top1:
        st.subheader(f"Welcome, {user['name']} 👋")
        st.caption("Your healthcare writing workspace")
    with top2:
        if st.button("Log out", use_container_width=True):
            st.session_state.user = None
            st.session_state.generated_content = ""
            st.rerun()

    st.markdown('<div class="notice">ⓘ <b>Responsible use:</b> This tool creates educational content only. It does not diagnose conditions, prescribe treatment, or replace advice from a qualified healthcare professional.</div>', unsafe_allow_html=True)
    form_col, result_col = st.columns([1,1], gap="large")
    with form_col:
        st.markdown("### ✎ Build your content")
        with st.form("generator_form"):
            topic = st.text_area("Medical topic or brief", height=155, max_chars=1500,
                                 placeholder="e.g. Explain the importance of regular blood pressure monitoring for adults...")
            content_type = st.selectbox("Content format", [
                "Patient Education Article", "Medical Blog", "Healthcare Awareness Post",
                "Clinical Topic Summary", "Medical Newsletter", "Hospital Website Copy",
                "Medical Student Notes", "Research Topic Overview"
            ])
            audience = st.selectbox("Target audience", [
                "General public", "Patients and caregivers", "Medical students",
                "Healthcare professionals", "Children and parents", "Hospital administrators"
            ])
            tone = st.selectbox("Writing tone", [
                "Clear and reassuring", "Professional and informative",
                "Simple and beginner-friendly", "Academic and formal",
                "Empathetic and supportive"
            ])
            generate = st.form_submit_button("✦ Generate medical content", use_container_width=True)
        if generate:
            if not topic.strip():
                st.error("Enter a medical topic or brief first.")
            else:
                with st.spinner("Generating your medical content..."):
                    try:
                        st.session_state.generated_content = generate_content(topic.strip(), content_type, audience, tone)
                    except Exception as exc:
                        st.error(str(exc))
    with result_col:
        st.markdown("### ✦ Your content")
        content = st.session_state.generated_content
        if content:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown(content)
            st.markdown('</div>', unsafe_allow_html=True)
            st.download_button("↓ Download .txt", data=content, file_name="medcontent-draft.txt",
                               mime="text/plain", use_container_width=True)
            st.caption("Select and copy the text above to copy it to your clipboard.")
        else:
            st.markdown("""
            <div class="panel">
              <h3>Your draft will appear here</h3>
              <p class="small-muted">Enter a medical topic, select your audience and generate your first draft.</p>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("---")
    a,b,c = st.columns(3)
    a.markdown("**01 · Medical-first prompts**<br><span class='small-muted'>Designed for healthcare communication.</span>", unsafe_allow_html=True)
    b.markdown("**02 · Audience-aware writing**<br><span class='small-muted'>Adapt language for different readers.</span>", unsafe_allow_html=True)
    c.markdown("**03 · Responsible output**<br><span class='small-muted'>Educational content with safety reminders.</span>", unsafe_allow_html=True)

st.markdown("<footer>© 2026 MedContent AI · Healthcare content assistance · Not medical advice</footer>", unsafe_allow_html=True)
