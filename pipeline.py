"""
Glue: run the full pipeline for one company, or a batch of them.
"""

from __future__ import annotations
from dataclasses import dataclass

from schemas import CompanyDossier, UserProfile, GeneratedEmail, VerificationResult
from research import research_company
from generate import generate_email
from verify import verify_email


@dataclass
class Result:
    dossier: CompanyDossier
    email: GeneratedEmail
    verification: VerificationResult


def run_one(company: str, profile: UserProfile, log=print) -> Result:
    log(f"\n=== Researching {company} ===")
    dossier = research_company(company, log=log)
    log(f"Gathered {len(dossier.all_facts())} facts from {len(dossier.pages_visited)} pages.")

    email = generate_email(dossier, profile)
    verification = verify_email(email, dossier, profile)
    log(f"Verification: {'PASS' if verification.passed else f'{len(verification.unsupported)} unsupported'}")
    return Result(dossier=dossier, email=email, verification=verification)


def run_batch(companies: list[str], profile: UserProfile, log=print) -> dict[str, Result]:
    return {c: run_one(c, profile, log=log) for c in companies}
