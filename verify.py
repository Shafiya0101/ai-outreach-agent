"""
Stage 3 — verification.

A second, independent call. It splits the email into sentences and, for each,
decides whether the dossier or profile supports it. Unsupported sentences are
surfaced to the user (and can be auto-stripped). This is the demo moment:
you can literally show which sentences are grounded and which are not.
"""

from __future__ import annotations

from llm import complete_json
from schemas import CompanyDossier, UserProfile, GeneratedEmail, VerificationResult
from generate import _facts_block, _profile_block


def verify_email(email: GeneratedEmail, dossier: CompanyDossier,
                 profile: UserProfile) -> VerificationResult:
    system = (
        "You are a strict fact-checker. Below are the ONLY allowed sources of truth: "
        "COMPANY FACTS and APPLICANT PROFILE.\n"
        "Split the email into individual factual sentences. For each, decide whether it is "
        "supported by the sources. Generic pleasantries ('I'd welcome a chat') count as supported. "
        "Any specific claim about the company or applicant that is NOT in the sources is UNSUPPORTED. "
        "When supported, quote the supporting snippet as evidence."
    )
    user = (
        f"COMPANY FACTS:\n{_facts_block(dossier)}\n\n"
        f"APPLICANT PROFILE:\n{_profile_block(profile)}\n\n"
        f"EMAIL SUBJECT: {email.subject}\nEMAIL BODY:\n{email.body}"
    )
    return complete_json(system=system, user=user, schema=VerificationResult)


def strip_unsupported(email: GeneratedEmail, result: VerificationResult) -> GeneratedEmail:
    """Optional hard guard: remove sentences flagged unsupported."""
    bad = {c.sentence.strip() for c in result.unsupported}
    if not bad:
        return email
    kept = [s for s in email.body.replace("\n", " \n").split(". ")
            if s.strip().rstrip(".") not in {b.rstrip(".") for b in bad}]
    return GeneratedEmail(subject=email.subject, body=". ".join(kept))
