"""
Streamlit UI — the human-in-the-loop part of the requirement, plus a simple
password gate and secrets handling for safe deployment.

Run locally:  streamlit run app.py
Deploy:       push to GitHub, then deploy on share.streamlit.io
"""

from __future__ import annotations
import bootstrap  # noqa: F401  -> loads .env locally before anything else
import os
import json
import streamlit as st

# Mirror Streamlit secrets into environment variables (works locally via
# .streamlit/secrets.toml and on Streamlit Community Cloud's Secrets UI).
try:
    for _k in st.secrets.keys():
        _v = st.secrets[_k]
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

from schemas import UserProfile
from research import research_company
from generate import generate_email
from verify import verify_email

st.set_page_config(page_title="Personalized Outreach Agent", layout="wide")


# --- simple password gate (optional) ---------------------------------------
# If APP_PASSWORD is set (in .env or the host's secrets), visitors must enter it
# before they can use the app. This stops strangers on your public demo URL from
# spending your free API quota. If APP_PASSWORD is not set, the app is open.
def password_gate() -> None:
    expected = os.environ.get("APP_PASSWORD")
    if not expected:
        return  # no password configured -> open app
    if st.session_state.get("authed"):
        return
    st.title("Personalized Outreach Agent")
    entered = st.text_input("Enter access password", type="password")
    if entered:
        if entered == expected:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()


password_gate()

st.title("Personalized Outreach Agent")

# --- profile ---
with st.sidebar:
    st.header("Your profile")
    st.caption("Upload your resume and add your GitHub to auto-fill, or edit the JSON below.")

    resume_file = st.file_uploader("Resume (PDF)", type=["pdf"])
    github_url = st.text_input("GitHub profile URL (optional)", placeholder="https://github.com/you")
    portfolio_url = st.text_input("Portfolio / website URL (optional)", placeholder="https://yoursite.com")
    email_hint = st.text_input("Your email", placeholder="you@example.com")

    if st.button("Build profile from resume"):
        if not resume_file:
            st.warning("Upload a PDF resume first.")
        else:
            try:
                with st.spinner("Reading your resume + GitHub..."):
                    from profile_builder import parse_resume, enrich_with_github
                    prof = parse_resume(resume_file.read(), github_url=github_url,
                                        contact_email_hint=email_hint)
                    if github_url:
                        prof = enrich_with_github(prof, github_url)
                    # what YOU typed always wins over anything extracted/guessed
                    if portfolio_url:
                        prof.portfolio_url = portfolio_url
                    if github_url:
                        prof.github_url = github_url
                    if email_hint:
                        prof.contact_email = email_hint
                    st.session_state.profile_json = json.dumps(prof.model_dump(), indent=2)
                st.rerun()
            except Exception as e:
                st.error(f"Could not build profile: {e}")

    default = st.session_state.get("profile_json") or json.dumps(
        json.load(open("profile.json")), indent=2)
    profile_text = st.text_area("Profile JSON (review & edit)", default, height=320)
    try:
        profile = UserProfile(**json.loads(profile_text))
        st.success("Profile valid")
    except Exception as e:
        profile = None
        st.error(f"Invalid profile: {e}")

# --- session state ---
for k in ("dossier", "email", "verification"):
    st.session_state.setdefault(k, None)

company = st.text_input("Company name or homepage URL", placeholder="e.g. Mistral or https://...")

if st.button("Research & draft", disabled=not (company and profile)):
    with st.status("Running agent... (free tier is slow, please wait)", expanded=True) as status:
        st.session_state.dossier = research_company(company, log=lambda m: st.write(m))
        st.session_state.email = generate_email(st.session_state.dossier, profile)
        st.session_state.verification = verify_email(st.session_state.email, st.session_state.dossier, profile)
        status.update(label="Done", state="complete")

if st.session_state.email:
    left, right = st.columns([3, 2])

    with left:
        st.subheader("Draft email")
        st.text_input("Subject", st.session_state.email.subject, key="subj")
        st.text_area("Body", st.session_state.email.body, height=320, key="body")

        st.markdown("**Revise** (keeps the same researched facts):")
        feedback = st.text_input("e.g. 'more technical', 'shorter', 'mention their open ML role'")
        if st.button("Apply revision", disabled=not feedback):
            with st.spinner("Revising..."):
                st.session_state.email = generate_email(st.session_state.dossier, profile, feedback=feedback)
                st.session_state.verification = verify_email(
                    st.session_state.email, st.session_state.dossier, profile)
            st.rerun()

    with right:
        v = st.session_state.verification
        st.subheader("Fact check")
        if v.passed:
            st.success("All sentences grounded.")
        else:
            st.warning(f"{len(v.unsupported)} sentence(s) not supported by sources.")
        for c in v.checks:
            icon = "✅" if c.supported else "⚠️"
            with st.expander(f"{icon} {c.sentence[:70]}"):
                st.write("Evidence:" if c.supported else "No supporting source found.")
                if c.evidence:
                    st.caption(c.evidence)

        st.subheader("Sources")
        for f in st.session_state.dossier.all_facts():
            st.caption(f"• {f.claim} — {f.source_url}")
