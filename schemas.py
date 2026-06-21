"""
Data contracts for the whole pipeline.

The single most important idea here: every fact about a company is a
`SourcedFact` that carries the URL and the exact text snippet it came from.
The email generator is only ever allowed to see validated facts, so it
literally cannot cite something that has no source.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class SourcedFact(BaseModel):
    """A single claim about the company, tied to where it came from."""
    claim: str = Field(..., description="One factual statement, in plain language.")
    source_url: str = Field(..., description="The page this came from.")
    snippet: str = Field(..., description="The exact text from the page that supports the claim.")


class CompanyDossier(BaseModel):
    """Everything the research stage gathered about one company."""
    company_name: str
    homepage_url: str
    one_line_summary: str = Field(..., description="What the company does, in one sentence.")
    what_they_do: List[SourcedFact] = Field(default_factory=list)
    values_or_mission: List[SourcedFact] = Field(default_factory=list)
    recent_news: List[SourcedFact] = Field(default_factory=list)
    open_roles: List[SourcedFact] = Field(default_factory=list)
    tech_or_products: List[SourcedFact] = Field(default_factory=list)
    testimonials: List[SourcedFact] = Field(
        default_factory=list,
        description="Customer reviews, testimonials, case-study results, or named clients.")
    pages_visited: List[str] = Field(default_factory=list)

    def all_facts(self) -> List[SourcedFact]:
        return (
            self.what_they_do
            + self.values_or_mission
            + self.recent_news
            + self.open_roles
            + self.tech_or_products
            + self.testimonials
        )

    def is_thin(self) -> bool:
        """If we barely found anything, the email should stay short and honest."""
        return len(self.all_facts()) < 3


class UserProfile(BaseModel):
    """The applicant. The ONLY source of personal claims in the email."""
    name: str
    headline: str = Field(..., description="e.g. 'Final-year CS student, ML focus'")
    summary: str
    skills: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list, description="Short bullet-style lines.")
    goals: str = Field(..., description="What the applicant wants from a role.")
    target_role: str = Field(..., description="e.g. 'ML engineering internship'")
    contact_email: str
    github_url: str = Field(default="", description="GitHub profile URL, if any.")
    portfolio_url: str = Field(default="", description="Personal site / portfolio, if any.")


class GeneratedEmail(BaseModel):
    subject: str
    body: str


class SentenceCheck(BaseModel):
    sentence: str
    supported: bool
    evidence: Optional[str] = Field(
        None, description="The dossier/profile snippet that supports it, or null."
    )


class VerificationResult(BaseModel):
    checks: List[SentenceCheck]

    @property
    def unsupported(self) -> List[SentenceCheck]:
        return [c for c in self.checks if not c.supported]

    @property
    def passed(self) -> bool:
        return len(self.unsupported) == 0
