"""
Uses Claude API to synthesize scraped content into conversation-ready snippets
for a non-technical consultant attending AI startup / enterprise conversations.

Uses requests (not the anthropic SDK) for maximum compatibility across environments.
"""

import json
import logging
from datetime import date
import requests
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

SYSTEM_PROMPT = """You are an expert AI/ML educator and communication coach.
Your job is to help a non-technical business consultant articulate AI and ML concepts
confidently to two audiences:
  1. Business Executives (C-suite, VPs, investors) — focus on ROI, strategy, risk, trends
  2. Senior Data Scientists — focus on technical nuance, model choices, trade-offs, tooling

The consultant is building an AI startup and needs to hold their own in both rooms.
Always use clear, confident language — no jargon without explanation.
Return ONLY valid JSON, no markdown fences."""


def _build_prompt(scraped_pages: list, today: str) -> str:
    content_block = ""
    for page in scraped_pages:
        if not page.content or page.error:
            continue
        content_block += f"\n\n### SOURCE: {page.source_name} ({page.category})\nURL: {page.url}\n{page.content[:1500]}"

    return f"""Today is {today}. Below is freshly scraped content from AI/ML newsletters, blogs, and resources.

---
{content_block}
---

Using the above source material, generate a JSON object with exactly these keys:

{{
  "conversation_starters": [
    {{
      "topic": "Short topic title",
      "hook": "One punchy sentence to open a conversation",
      "talking_points": ["point 1", "point 2", "point 3"],
      "source": "Which source this came from"
    }}
    // 3 items
  ],

  "recent_updates_opinions": [
    {{
      "headline": "What happened / what changed",
      "plain_english": "Explain it in 2 sentences for a non-technical person",
      "opinion": "A confident, informed take the consultant can share",
      "why_it_matters": "Business or technical impact"
    }}
    // 3 items
  ],

  "core_concepts": [
    {{
      "concept": "Concept name",
      "one_liner": "Definition in one sentence",
      "analogy": "A relatable non-technical analogy",
      "why_relevant_now": "Why this matters in current AI conversations"
    }}
    // 3 items
  ],

  "roadblocks_solutions": [
    {{
      "problem": "The issue or challenge",
      "context": "Why this is a real problem right now",
      "industry_response": "What practitioners / companies are doing about it",
      "consultant_angle": "How to frame this in a business conversation"
    }}
    // 3 items
  ],

  "mock_exec_conversation": {{
    "scenario": "Brief setup — who they are meeting and why",
    "dialogue": [
      {{"speaker": "Executive", "line": "..."}},
      {{"speaker": "Consultant", "line": "..."}},
      {{"speaker": "Executive", "line": "..."}},
      {{"speaker": "Consultant", "line": "..."}}
    ],
    "key_phrases_used": ["phrase 1", "phrase 2", "phrase 3"]
  }},

  "mock_ds_conversation": {{
    "scenario": "Brief setup — who they are meeting and why",
    "dialogue": [
      {{"speaker": "Data Scientist", "line": "..."}},
      {{"speaker": "Consultant", "line": "..."}},
      {{"speaker": "Data Scientist", "line": "..."}},
      {{"speaker": "Consultant", "line": "..."}}
    ],
    "key_phrases_used": ["phrase 1", "phrase 2", "phrase 3"]
  }},

  "dev_standards_update": {{
    "standard": "Conventional Commits (or other dev standard found in sources)",
    "what_it_is": "Plain English explanation",
    "why_ai_startups_care": "Connection to AI workflows, GitHub Copilot, CI/CD, etc.",
    "talking_point": "One smart thing to say about it in a tech conversation"
  }},

  "governance_frameworks": [
    {{
      "framework": "Framework name (e.g. NIST AI RMF, Microsoft Responsible AI, Google Responsible AI)",
      "owner": "Which company / body owns this framework",
      "core_pillars": ["pillar 1", "pillar 2", "pillar 3"],
      "one_liner": "What this framework is in one sentence",
      "how_companies_use_it": "Concrete example of how real tech companies apply this",
      "consultant_talking_point": "One sharp thing to say when this framework comes up in a meeting"
    }}
    // 3 items — one per governance source (Microsoft, Google, NIST)
  ],

  "ai_strategy_frameworks": [
    {{
      "framework": "Strategy framework or approach name",
      "source": "a16z / MIT Sloan / Stanford HAI",
      "core_idea": "The central strategic concept in 1-2 sentences",
      "real_world_application": "How companies are deploying this strategy today",
      "deployment_checklist": ["step or consideration 1", "step or consideration 2", "step or consideration 3"],
      "consultant_talking_point": "How to bring this up confidently in a C-suite strategy conversation"
    }}
    // 3 items — one per strategy source (a16z, MIT Sloan, Stanford HAI)
  ]
}}

Rules:
- Ground every item in the actual scraped source content above
- Keep language confident, consultant-appropriate — no filler words
- Mock conversations must feel realistic, not robotic
- governance_frameworks and ai_strategy_frameworks are PERMANENT REFERENCE sections — summarise the frameworks themselves (their structure, pillars, how they are used), not just today's news
- All other sections should reflect today {today}'s latest content
"""


def generate_digest(scraped_pages: list) -> dict:
    today = date.today().strftime("%B %d, %Y")
    prompt = _build_prompt(scraped_pages, today)

    logger.info("Calling Claude API to synthesize content...")

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 7000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }

    key_preview = ANTHROPIC_API_KEY[:12] + "..." if ANTHROPIC_API_KEY else "(empty)"
    logger.info("Using API key starting with: %s", key_preview)

    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers=headers,
            json=payload,
            timeout=300,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Anthropic API connection failed: {e}") from e

    if not resp.ok:
        raise RuntimeError(
            f"Anthropic API error {resp.status_code}: {resp.text[:500]}"
        )

    raw = resp.json()["content"][0]["text"].strip()

    # Strip markdown fences if model wraps output anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        digest = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed: %s\nRaw output snippet: %s", e, raw[:500])
        raise RuntimeError("Claude returned malformed JSON — check logs") from e

    logger.info("Content synthesis complete.")
    return digest
