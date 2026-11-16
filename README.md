# MedContent AI — Medical Content Generator

A Flask + SQLite + HTML/CSS/JavaScript project that generates healthcare and medical educational content using the OpenRouter API.

## Features
- Email/password registration and login
- Password hashing using Werkzeug
- SQLite user database
- Login-protected content generation API
- Medical-specific content formats, audiences and tones
- Medical safety instructions in the generation prompt
- Copy and download generated drafts

## Setup (Windows)
1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Create and activate a virtual environment (optional but recommended):
   - `py -m venv venv`
   - `venv\\Scripts\\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and add your OpenRouter API key and a private Flask secret key.
6. Run: `python backend/app.py`
8. Open `http://127.0.0.1:5000` in your browser and create an account.

## Google Colab
Install dependencies, set `OPENROUTER_API_KEY` in Colab secrets/environment, change directory to the extracted project folder and run `python backend/app.py`. Use Colab's port 5000 proxy to open the app.

## Important
This is a student/demo application. Do not enter patient-identifiable information. Generated content is educational, may contain errors, and must be reviewed by a qualified healthcare professional before publication or use. It must not be used for diagnosis or treatment decisions. Before public deployment, set a strong secret key, enable HTTPS, configure secure cookies, add rate limiting/CSRF protection, and use a production WSGI server.
