"""
Uses Claude API to synthesize scraped content into conversation-ready snippets.

Two separate API calls with prompt caching to minimise cost:
  - Daily call  (sections 1-7): Haiku model, runs every digest.
  - Permanent call (sections 8-10): Sonnet model, cached weekly via
    output/permanent_cache.json (restored by GitHub Actions cache).

Prompt caching: each call splits into a static block (JSON schema — cached)
and a dynamic block (date + scraped content — not cached). The static block
is marked with cache_control so Anthropic reuses it across runs.
"""

import json
import logging
import os
from datetime import date
import requests
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MODEL_HAIKU

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
ANTHROPIC_BETA = "prompt-caching-2024-07-31"

PERMANENT_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "output", "permanent_cache.json"
)

PERMANENT_CATEGORIES = {
    "ai_governance", "ai_strategy_ref", "ai_enterprise", "ai_maturity",
    "ai_executive_advisory", "ai_business_case", "ai_change_management",
    "ai_enterprise_adoption",
}

# ── System prompt (cached) ────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert AI/ML educator and communication coach.
Your job is to help a non-technical business consultant articulate AI and ML concepts
confidently to two audiences:
  1. Business Executives (C-suite, VPs, investors) — focus on ROI, strategy, risk, trends
  2. Senior Data Scientists — focus on technical nuance, model choices, trade-offs, tooling

The consultant is building an AI startup and needs to hold their own in both rooms.
Always use clear, confident language — no jargon without explanation.
Return ONLY valid JSON, no markdown fences."""

# ── Static prompt blocks (cached) ────────────────────────────────────────────
# These contain only the JSON schema + rules — no date or scraped content.
# Anthropic caches them so subsequent runs skip re-processing these tokens.

DAILY_STATIC = """Using the source material provided, generate a JSON object with exactly these keys:

{
  "conversation_starters": [
    {
      "topic": "Short topic title",
      "hook": "One punchy sentence to open a conversation",
      "talking_points": ["point 1", "point 2", "point 3"],
      "source": "Which source this came from"
    }
    // 3 items
  ],

  "recent_updates_opinions": [
    {
      "headline": "What happened / what changed",
      "plain_english": "Explain it in 2 sentences for a non-technical person",
      "opinion": "A confident, informed take the consultant can share",
      "why_it_matters": "Business or technical impact"
    }
    // 3 items
  ],

  "core_concepts": [
    {
      "concept": "Concept name",
      "one_liner": "Definition in one sentence",
      "analogy": "A relatable non-technical analogy",
      "why_relevant_now": "Why this matters in current AI conversations"
    }
    // 3 items
  ],

  "roadblocks_solutions": [
    {
      "problem": "The issue or challenge",
      "context": "Why this is a real problem right now",
      "industry_response": "What practitioners / companies are doing about it",
      "consultant_angle": "How to frame this in a business conversation"
    }
    // 3 items
  ],

  "mock_exec_conversation": {
    "scenario": "Brief setup — who they are meeting and why",
    "dialogue": [
      {"speaker": "Executive", "line": "..."},
      {"speaker": "Consultant", "line": "..."},
      {"speaker": "Executive", "line": "..."},
      {"speaker": "Consultant", "line": "..."}
    ],
    "key_phrases_used": ["phrase 1", "phrase 2", "phrase 3"]
  },

  "mock_ds_conversation": {
    "scenario": "Brief setup — who they are meeting and why",
    "dialogue": [
      {"speaker": "Data Scientist", "line": "..."},
      {"speaker": "Consultant", "line": "..."},
      {"speaker": "Data Scientist", "line": "..."},
      {"speaker": "Consultant", "line": "..."}
    ],
    "key_phrases_used": ["phrase 1", "phrase 2", "phrase 3"]
  },

  "dev_standards_update": {
    "standard": "Conventional Commits (or other dev standard found in sources)",
    "what_it_is": "Plain English explanation",
    "why_ai_startups_care": "Connection to AI workflows, GitHub Copilot, CI/CD, etc.",
    "talking_point": "One smart thing to say about it in a tech conversation"
  }
}

Rules:
- Ground every item in the actual scraped source content provided
- Keep language confident, consultant-appropriate — no filler words
- Mock conversations must feel realistic, not robotic
- All sections must reflect today's latest content
- Be concise — every field should be 1-2 sentences maximum
"""

PERMANENT_STATIC = """Using the source material provided, generate a JSON object with exactly these keys:

{
  "governance_frameworks": [
    {
      "framework": "Framework name (e.g. NIST AI RMF, Microsoft Responsible AI, Google Responsible AI)",
      "owner": "Which company / body owns this framework",
      "core_pillars": ["pillar 1", "pillar 2", "pillar 3"],
      "one_liner": "What this framework is in one sentence",
      "how_companies_use_it": "Concrete example of how real tech companies apply this",
      "consultant_talking_point": "One sharp thing to say when this framework comes up in a meeting",
      "business_case": {
        "scenario": "A specific company type + business process or product (unique per framework)",
        "implementation_layers": [
          {"layer": "Layer name", "what_happens": "What this layer does in this scenario — 1 sentence"},
          {"layer": "Layer name", "what_happens": "..."},
          {"layer": "Layer name", "what_happens": "..."}
        ],
        "risks": [
          {"risk": "Specific risk in this scenario", "priority": "High", "mitigation": "Concrete mitigation — 1 sentence"},
          {"risk": "Another risk", "priority": "Medium", "mitigation": "..."},
          {"risk": "Another risk", "priority": "Low", "mitigation": "..."}
        ]
      }
    }
    // 3 items — one per governance source (Microsoft, Google, NIST)
  ],

  "ai_strategy_frameworks": [
    {
      "framework": "Strategy framework or approach name",
      "source": "a16z / MIT Sloan / Stanford HAI",
      "core_idea": "The central strategic concept in 1-2 sentences",
      "real_world_application": "How companies are deploying this strategy today",
      "deployment_checklist": ["step or consideration 1", "step or consideration 2", "step or consideration 3"],
      "consultant_talking_point": "How to bring this up confidently in a C-suite strategy conversation",
      "business_case": {
        "scenario": "A specific company type + business process or product (unique per framework)",
        "implementation_layers": [
          {"layer": "Layer name", "what_happens": "What this layer does in this scenario — 1 sentence"},
          {"layer": "Layer name", "what_happens": "..."},
          {"layer": "Layer name", "what_happens": "..."}
        ],
        "risks": [
          {"risk": "Specific risk in this scenario", "priority": "High", "mitigation": "Concrete mitigation — 1 sentence"},
          {"risk": "Another risk", "priority": "Medium", "mitigation": "..."},
          {"risk": "Another risk", "priority": "Low", "mitigation": "..."}
        ]
      }
    }
    // 3 items — one per strategy source (a16z, MIT Sloan, Stanford HAI)
  ],

  "enterprise_ai_toolkit": [
    {
      "topic": "One of: AI Maturity Assessment | Roadmap Definition | Executive Advisory | Business Case Development | Change Management | Enterprise AI Adoption",
      "source": "McKinsey / HBR / BCG / AI Business / WEF / Gartner",
      "framework_or_model": "Specific named framework or model",
      "description": "What this framework covers and why it matters — 2 sentences max",
      "key_steps_or_levels": ["step/level 1", "step/level 2", "step/level 3"],
      "how_consultant_uses_it": "Exactly how a consultant deploys this with a client — be specific",
      "client_talking_point": "The sentence that opens this topic in a client meeting",
      "business_case": {
        "scenario": "A specific company type + business process or product (unique per topic)",
        "implementation_layers": [
          {"layer": "Layer name", "what_happens": "What this layer does in this scenario — 1 sentence"},
          {"layer": "Layer name", "what_happens": "..."},
          {"layer": "Layer name", "what_happens": "..."}
        ],
        "risks": [
          {"risk": "Specific risk in this scenario", "priority": "High", "mitigation": "Concrete mitigation — 1 sentence"},
          {"risk": "Another risk", "priority": "Medium", "mitigation": "..."},
          {"risk": "Another risk", "priority": "Low", "mitigation": "..."}
        ]
      }
    }
    // 6 items — one per topic: Maturity Assessment, Roadmap Definition, Executive Advisory, Business Case, Change Management, Enterprise Adoption
  ]
}

Rules:
- Summarise the actual frameworks, models, and methodologies — not just today's news
- Every business_case must use a UNIQUE scenario (different industry / product each time)
- business_case risks must have priority labels: High / Medium / Low — list High risks first
- Keep language confident, consultant-appropriate — no filler words
- Be concise — every field should be 1-2 sentences maximum
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _content_block(scraped_pages: list, categories: set = None) -> str:
    block = ""
    for page in scraped_pages:
        if not page.content or page.error:
            continue
        if categories and page.category not in categories:
            continue
        block += (
            f"\n\n### SOURCE: {page.source_name} ({page.category})"
            f"\nURL: {page.url}\n{page.content[:1500]}"
        )
    return block


def _call_claude(static_prompt: str, dynamic_prompt: str, model: str, max_tokens: int) -> dict:
    """
    Makes a cached Claude API call.
    static_prompt: schema + rules (cached between runs).
    dynamic_prompt: date + scraped content (not cached, changes every run).
    """
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "anthropic-beta": ANTHROPIC_BETA,
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": static_prompt, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": dynamic_prompt},
                ],
            }
        ],
    }
    try:
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=300)
    except requests.RequestException as e:
        raise RuntimeError(f"Anthropic API connection failed: {e}") from e

    if not resp.ok:
        raise RuntimeError(f"Anthropic API error {resp.status_code}: {resp.text[:500]}")

    raw = resp.json()["content"][0]["text"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed: %s\nRaw output snippet: %s", e, raw[:500])
        raise RuntimeError("Claude returned malformed JSON — check logs") from e


def _load_permanent_cache() -> dict | None:
    try:
        with open(PERMANENT_CACHE_PATH, "r") as f:
            data = json.load(f)
        logger.info("Loaded permanent sections from cache.")
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_permanent_cache(data: dict):
    os.makedirs(os.path.dirname(PERMANENT_CACHE_PATH), exist_ok=True)
    with open(PERMANENT_CACHE_PATH, "w") as f:
        json.dump(data, f)
    logger.info("Permanent sections saved to cache.")


# ── Public API ────────────────────────────────────────────────────────────────

def generate_digest(scraped_pages: list) -> dict:
    today = date.today().strftime("%B %d, %Y")
    key_preview = ANTHROPIC_API_KEY[:12] + "..." if ANTHROPIC_API_KEY else "(empty)"
    logger.info("Using API key starting with: %s", key_preview)

    # Daily sections — Haiku, prompt-cached schema, fresh content every run
    logger.info("Calling Claude (%s) for daily sections 1-7...", CLAUDE_MODEL_HAIKU)
    daily_dynamic = (
        f"Today is {today}. Below is freshly scraped content from AI/ML newsletters, "
        f"blogs, and resources.\n\n---\n{_content_block(scraped_pages)}\n---\n"
    )
    daily = _call_claude(DAILY_STATIC, daily_dynamic, CLAUDE_MODEL_HAIKU, max_tokens=9000)
    logger.info("Daily sections complete.")

    # Permanent sections — Sonnet, prompt-cached schema, served from file cache weekly
    permanent = _load_permanent_cache()
    if permanent is None:
        logger.info("No weekly cache — calling Claude (%s) for permanent sections 8-10...", CLAUDE_MODEL)
        perm_dynamic = (
            f"Today is {today}. Below is content from AI governance, strategy, "
            f"and enterprise adoption sources.\n\n---\n"
            f"{_content_block(scraped_pages, categories=PERMANENT_CATEGORIES)}\n---\n"
        )
        permanent = _call_claude(PERMANENT_STATIC, perm_dynamic, CLAUDE_MODEL, max_tokens=9000)
        _save_permanent_cache(permanent)
        logger.info("Permanent sections complete and cached.")
    else:
        logger.info("Permanent sections served from weekly cache — Sonnet call skipped.")

    return {**daily, **permanent}
