# Personalized Outreach Agent

Given a list of target companies, an agentic system researches each company's
website and writes one highly personalized email per company — grounded in your
profile, with a built-in fact-check and a human revision loop. Real Python, no
workflow tools.

## How it works (4 stages)

1. **Research agent** (`research.py`) — a real tool-use loop. The model chooses
   when to `web_search` and which pages to `fetch_url` (home → about → careers →
   news), then calls `finish`. Collected pages are distilled into a
   `CompanyDossier` where **every fact carries its source URL and a verbatim snippet**.
2. **Grounded generation** (`generate.py`) — the writer sees *only* the validated
   dossier + your profile, never raw web pages. It cannot cite a fact that has no source.
3. **Verification** (`verify.py`) — an independent pass labels each sentence
   supported / unsupported and quotes the evidence. Unsupported sentences are
   surfaced (and can be auto-stripped).
4. **Human-in-the-loop** (`app.py`) — revise with feedback ("more technical",
   "mention their funding"); it regenerates from the *same* facts and re-verifies.

### Why this controls hallucination
- Facts are separated from prose: company claims come only from the dossier,
  personal claims only from your profile.
- The URL is found via search, never guessed.
- Structured outputs are validated by Pydantic; invalid JSON auto-retries.
- A second model independently checks the draft against the sources.
- Sparse research → a deliberately short, honest email instead of invented praise.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in your keys
export $(cat .env | xargs)  # or use python-dotenv / direnv
```

You need an `ANTHROPIC_API_KEY`. A `TAVILY_API_KEY` is optional but recommended
(lets the agent find official sites + recent news). Without it, pass full
homepage URLs directly.

Edit `profile.json` with your real details.

## Run

UI with the revision loop:
```bash
streamlit run app.py
```

Batch from the command line:
```bash
python cli.py "Anthropic" "https://stripe.com" "Hugging Face"
```

## Files
| File | Role |
|------|------|
| `schemas.py` | Pydantic contracts; `SourcedFact` is the anti-hallucination backbone |
| `llm.py` | One swappable LLM wrapper (`complete`, `complete_json`) |
| `tools.py` | `web_search` + `fetch_url` |
| `research.py` | Agentic tool-use loop → dossier |
| `generate.py` | Grounded email writer |
| `verify.py` | Sentence-level fact check |
| `pipeline.py` | Chains the stages; batch runner |
| `app.py` | Streamlit UI + revision loop |
| `cli.py` | Batch CLI |

## Swapping the LLM
Change the two functions in `llm.py`. Everything else is provider-agnostic.
