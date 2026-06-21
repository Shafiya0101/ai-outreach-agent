"""
CLI batch runner.

  python cli.py "Anthropic" "https://stripe.com" "Hugging Face"

Prints one verified email per company. Good for the "list of target companies"
part of the brief without the UI.
"""

from __future__ import annotations
import bootstrap  # noqa: F401  -> loads .env
import json
import sys

from schemas import UserProfile
from pipeline import run_batch


def main() -> None:
    companies = sys.argv[1:]
    if not companies:
        print('Usage: python cli.py "Company A" "https://company-b.com" ...')
        sys.exit(1)

    profile = UserProfile(**json.load(open("profile.json")))
    results = run_batch(companies, profile)

    for company, r in results.items():
        print("\n" + "=" * 70)
        print(f"COMPANY: {company}")
        print(f"SUBJECT: {r.email.subject}\n")
        print(r.email.body)
        if not r.verification.passed:
            print("\n[!] Unsupported sentences flagged:")
            for c in r.verification.unsupported:
                print(f"    - {c.sentence}")


if __name__ == "__main__":
    main()
