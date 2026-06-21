"""
Stage 2 — grounded generation.

The generator sees ONLY the validated dossier and the user's profile. It never
sees raw web pages. Company claims may come only from the dossier; personal
claims only from the profile. Anything not present must be omitted, not guessed.
"""

from __future__ import annotations

from llm import complete_json
from schemas import CompanyDossier, UserProfile, GeneratedEmail


def _facts_block(d: CompanyDossier) -> str:
    lines = [f"COMPANY: {d.company_name}", f"SUMMARY: {d.one_line_summary}", "FACTS:"]
    for f in d.all_facts():
        lines.append(f"- {f.claim}  (source: {f.source_url})")
    return "\n".join(lines)


def _profile_block(p: UserProfile) -> str:
    links = []
    if p.github_url:
        links.append(f"GitHub: {p.github_url}")
    if p.portfolio_url:
        links.append(f"Portfolio: {p.portfolio_url}")
    return (
        f"NAME: {p.name}\nHEADLINE: {p.headline}\nSUMMARY: {p.summary}\n"
        f"SKILLS: {', '.join(p.skills)}\n"
        f"EXPERIENCE:\n" + "\n".join(f"- {e}" for e in p.experience) +
        f"\nGOALS: {p.goals}\nTARGET ROLE: {p.target_role}\nEMAIL: {p.contact_email}\n"
        + ("\n".join(links) if links else "")
    )


def generate_email(dossier: CompanyDossier, profile: UserProfile,
                   feedback: str | None = None) -> GeneratedEmail:
    rules = (
        "Write one short, highly personalized outreach email.\n"
        "RULES:\n"
        "1. Every statement about the company must be grounded in the COMPANY FACTS. "
        "Do not state any company fact that is not listed.\n"
        "2. Every statement about the applicant must come from the APPLICANT PROFILE.\n"
        "3. Connect a specific, real thing about the company to a specific strength of the applicant.\n"
        "4. If the facts are sparse, keep it short and honest rather than padding with flattery.\n"
        "5. Natural, human, specific. No clichés like 'I am excited to', no invented metrics.\n"
        "6. 120-180 words. Include a clear subject line."
    )
    if dossier.is_thin():
        rules += "\nNOTE: facts are sparse — keep the email brief and avoid specific company claims you cannot support."
    if feedback:
        rules += f"\n\nUSER REVISION REQUEST (reshape wording only, introduce no new facts): {feedback}"

    user = f"COMPANY FACTS:\n{_facts_block(dossier)}\n\nAPPLICANT PROFILE:\n{_profile_block(profile)}"
    return complete_json(system=rules, user=user, schema=GeneratedEmail, temperature=0.5)
