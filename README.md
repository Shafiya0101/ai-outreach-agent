# AI Outreach Agent

An agentic system that, given a company website, researches it and writes **one
highly personalized, fact-checked outreach email** — grounded in your real
resume and GitHub. Built with plain Python (no workflow tools), runs locally or
deploys free to the web.

**🔗 Live demo:** https://ai-outreach-agent-abcd.streamlit.app/ (access password required — ask me)

---

## What it does (4 stages)

1. **Research agent** (`research.py`) — a real tool-use loop. The model decides
   when to `web_search` and which pages to `fetch_url` (home → about → careers →
   news → testimonials/case-studies), then calls `finish`. Pages are distilled
   into a `CompanyDossier` where **every fact carries its source URL and a
   verbatim snippet**.
2. **Grounded generation** (`generate.py`) — the writer sees *only* the validated
   dossier + your profile, never raw web pages, so it cannot cite an ungrounded fact.
3. **Verification** (`verify.py`) — an independent pass labels each sentence
   supported / unsupported and quotes the evidence. Unsupported sentences are
   surfaced in the UI (and can be auto-stripped).
4. **Human-in-the-loop** (`app.py`) — revise with feedback ("more technical",
   "mention their funding"); it regenerates from the *same* facts and re-verifies.

### Your profile, built automatically
Instead of hand-writing details, upload your **resume (PDF)** and paste your
**GitHub link**. `profile_builder.py` extracts a structured profile from the
resume and pulls your real public repos + bio from GitHub. Links you type in the
sidebar always override anything extracted, and the parser never invents URLs.

### Why this controls hallucination
- Facts are separated from prose: company claims come only from the dossier,
  personal claims only from your resume/GitHub.
- The company URL is found by search, never guessed.
- Structured outputs are validated by Pydantic; invalid JSON auto-retries.
- A second model independently checks the draft against the sources.
- Testimonials and reviews are captured as sourced facts, so social proof in the
  email still traces back to a real page.
- Sparse research → a deliberately short, honest email instead of invented praise.

---

## Setup (local)

Requires Python 3.10+.

```bash
python -m venv venv
# Windows:
venv\Scripts\Activate.ps1
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project folder (this is git-ignored — never commit it):

```
MISTRAL_API_KEY=your-mistral-key
APP_PASSWORD=pick-a-demo-password
# TAVILY_API_KEY=optional-search-key
```

Get a **free** Mistral key at console.mistral.ai (no credit card; phone
verification only). A Tavily key (tavily.com) is optional — it lets the agent
find official sites and recent news from a company *name*. Without it, pass full
`https://` homepage URLs.

Edit `profile.json` only if you want a default profile; normally you'll build
your profile from a resume in the app.

---

## Run

Visual app (recommended — has the resume upload + revision loop + fact-check panel):
```bash
streamlit run app.py
```

Command line (batch):
```bash
python cli.py "https://www.example.com" "Another Company"
```

> **Note on the free tier:** Mistral's free plan is rate-limited (~2 requests/
> minute), so a single email takes a couple of minutes; the app waits out the
> limit automatically. A paid tier removes this.

---

## Deploy free (Streamlit Community Cloud)

1. Push this repo to GitHub (your `.env` stays out via `.gitignore`).
2. Go to share.streamlit.io, sign in with GitHub.
3. **Create app → Deploy from GitHub**: pick the repo, branch `main`, main file `app.py`.
4. **Advanced settings → Secrets**, paste (TOML format):
   ```toml
   MISTRAL_API_KEY = "your-mistral-key"
   APP_PASSWORD = "your-demo-password"
   ```
5. Deploy. You get a live `https://….streamlit.app` URL. The password gate keeps
   strangers from spending your free quota.

---

## Files
| File | Role |
|------|------|
| `schemas.py` | Pydantic contracts; `SourcedFact` is the anti-hallucination backbone |
| `llm.py` | One swappable LLM wrapper (Mistral via OpenAI-compatible API) |
| `tools.py` | `web_search` + `fetch_url` |
| `research.py` | Agentic tool-use loop → dossier (incl. testimonials) |
| `profile_builder.py` | Resume (PDF) parsing + GitHub enrichment |
| `generate.py` | Grounded email writer |
| `verify.py` | Sentence-level fact check |
| `pipeline.py` | Chains the stages; batch runner |
| `app.py` | Streamlit UI: profile builder, drafting, revision, fact-check, password gate |
| `cli.py` | Batch CLI |
| `bootstrap.py` | Loads secrets from `.env` |

## Swapping the LLM
Change `BASE_URL` / `MODEL` / the API-key env var in `llm.py`. Everything else
is provider-agnostic.
