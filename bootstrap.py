"""
Loads your secrets so you never hard-code keys.

- Locally: reads a `.env` file (used by cli.py and local runs) if present.
- On Streamlit / Streamlit Community Cloud: app.py also mirrors st.secrets
  into environment variables.

Safe to import anywhere; does nothing if python-dotenv or .env is missing.
Your real keys live in `.env` (local) or the host's Secrets UI (deployed) —
NEVER in the code, and NEVER committed to git (see .gitignore).
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads .env from the current folder if it exists
except Exception:
    pass
