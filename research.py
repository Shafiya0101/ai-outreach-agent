"""
Stage 1 — the agent.

We give the model two tools and let IT decide the sequence: usually
search -> fetch homepage -> fetch /about -> fetch /careers -> stop.
When it calls `finish`, we take everything it fetched and distill it into a
validated CompanyDossier where every fact carries its source.

Tool-calling here uses the OpenAI/Mistral format (tool_calls on the message).
"""

from __future__ import annotations
import json
from typing import List, Dict, Any

from llm import complete, complete_json
from tools import web_search, fetch_url
from schemas import CompanyDossier

MAX_STEPS = 8

# OpenAI/Mistral-style tool definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web. Use to find the company's official site or recent news.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch and read the clean text of a single web page.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Call when you have gathered enough about the company to write a tailored email.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

SYSTEM = """You are a research agent. Your job: gather factual information about ONE company
from its own website (and recent news) so a personalized outreach email can be written.

Strategy:
1. If you were given a name (not a URL), web_search for the official site first.
2. Fetch the homepage, then the most useful pages: about, mission/values, careers, products, blog/news,
   and any testimonials / reviews / case-studies / customers page (social proof is valuable).
3. Stop (call finish) once you understand what they do, what they value, any current hiring or news,
   and any customer testimonials or notable clients.
Do NOT fetch more than necessary. Never invent URLs — only fetch URLs you found via search or links."""


def research_company(company: str, log=print) -> CompanyDossier:
    """Run the tool-use loop, then distill collected text into a dossier."""
    messages: List[Dict[str, Any]] = [
        {"role": "user", "content": f"Research this company and gather facts: {company}"}
    ]
    collected: List[Dict[str, str]] = []  # {url, text}

    for step in range(MAX_STEPS):
        resp = complete(system=SYSTEM, messages=messages, tools=TOOLS, temperature=0.2)
        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []

        if not tool_calls:  # model just talked; stop
            log(f"[step {step}] model produced no tool call, stopping.")
            break

        # record the assistant turn (must include the tool_calls we are answering)
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })

        stop = False
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            if name == "finish":
                log(f"[step {step}] agent finished.")
                stop = True
                result = "ok"
            elif name == "web_search":
                hits = web_search(args.get("query", ""))
                log(f"[step {step}] search: {args.get('query','')} -> {len(hits)} hits")
                result = json.dumps(hits)[:3000]
            elif name == "fetch_url":
                url = args.get("url", "")
                text = fetch_url(url)
                log(f"[step {step}] fetch: {url} ({len(text)} chars)")
                collected.append({"url": url, "text": text})
                result = text[:3000]
            else:
                result = f"unknown tool: {name}"

            # every tool_call must get a matching tool result message
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": result,
            })

        if stop:
            break

    return _distill(company, collected, log)


def _distill(company: str, collected: List[Dict[str, str]], log=print) -> CompanyDossier:
    """Turn raw fetched pages into a structured, sourced dossier."""
    if not collected:
        log("No pages fetched; returning minimal dossier.")
        return CompanyDossier(company_name=company, homepage_url="",
                              one_line_summary="No information could be gathered.")

    corpus = "\n\n".join(
        f"=== SOURCE: {c['url']} ===\n{c['text']}" for c in collected
    )[:24000]

    system = (
        "Extract a structured dossier from the sources below. Every fact MUST include the "
        "exact source_url it came from and a verbatim snippet from that source. "
        "Capture any customer testimonials, reviews, case-study results, or named clients in the "
        "'testimonials' field (with their source). "
        "Do not add anything not present in the sources. If a category has nothing, leave it empty."
    )
    dossier = complete_json(system=system, user=corpus, schema=CompanyDossier)
    dossier.pages_visited = [c["url"] for c in collected]
    if not dossier.company_name:
        dossier.company_name = company
    return dossier
