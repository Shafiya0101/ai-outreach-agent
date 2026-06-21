"""
Builds a UserProfile from real inputs instead of hand-written JSON:

- parse_resume(pdf_bytes)  -> extract resume text, then have the LLM fill the
  structured UserProfile schema.
- enrich_with_github(...)  -> pull the person's public repos + bio from GitHub
  and fold them into the profile, so the email can mention real projects.

Both are grounded: the profile only contains what the resume/GitHub actually say.
"""

from __future__ import annotations
import io
import re
import httpx

from llm import complete_json
from schemas import UserProfile


def extract_pdf_text(data: bytes) -> str:
    """Pull plain text out of a (text-based) resume PDF."""
    import pdfplumber
    parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def parse_resume(pdf_bytes: bytes, github_url: str = "", contact_email_hint: str = "") -> UserProfile:
    raw = extract_pdf_text(pdf_bytes)[:12000]
    if not raw.strip():
        raise ValueError(
            "Couldn't read any text from that PDF. It may be a scanned image — "
            "try a text-based PDF, or fill the profile in by hand."
        )
    system = (
        "Extract a structured applicant profile from this resume text. "
        "Use ONLY information present in the resume. Keep each experience line short "
        "(one achievement each). For 'goals' and 'target_role', infer a short, reasonable "
        "value from the resume's focus if they are not stated explicitly. "
        "For github_url and portfolio_url: include a URL ONLY if it literally appears in the "
        "resume text. If no such link is present, leave that field as an empty string. "
        "Never invent or guess a URL."
    )
    profile = complete_json(system=system, user=f"RESUME:\n{raw}", schema=UserProfile)
    if github_url:
        profile.github_url = github_url
    if contact_email_hint and not profile.contact_email:
        profile.contact_email = contact_email_hint
    return profile


def _github_username(url: str) -> str | None:
    m = re.search(r"github\.com/([A-Za-z0-9-]+)", url or "")
    return m.group(1) if m else None


def enrich_with_github(profile: UserProfile, github_url: str) -> UserProfile:
    """Add the person's real public repos + bio. Uses GitHub's public API."""
    username = _github_username(github_url)
    if not username:
        return profile
    try:
        user = httpx.get(f"https://api.github.com/users/{username}", timeout=15).json()
        repos = httpx.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "updated", "per_page": 10}, timeout=15,
        ).json()
    except Exception:
        return profile  # network/ratelimit -> just skip enrichment

    profile.github_url = github_url
    if isinstance(user, dict):
        if user.get("bio") and user["bio"] not in profile.summary:
            profile.summary = f"{profile.summary} {user['bio']}".strip()
        # GitHub stores the user's website in the 'blog' field — use it as the
        # real portfolio link rather than guessing one.
        site = (user.get("blog") or "").strip()
        if site and not profile.portfolio_url:
            if not site.startswith("http"):
                site = "https://" + site
            profile.portfolio_url = site

    languages = set()
    if isinstance(repos, list):
        for r in repos:
            if not isinstance(r, dict) or r.get("fork"):
                continue
            if r.get("language"):
                languages.add(r["language"])
            name, desc = r.get("name"), (r.get("description") or "").strip()
            if name:
                line = f"GitHub project '{name}'" + (f": {desc}" if desc else "")
                if line not in profile.experience:
                    profile.experience.append(line)

    for lang in languages:
        if lang not in profile.skills:
            profile.skills.append(lang)

    profile.experience = profile.experience[:8]  # keep it tidy
    return profile
