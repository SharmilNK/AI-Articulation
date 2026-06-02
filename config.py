import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "sharmilkn@gmail.com").strip()
DIGEST_TIME = os.getenv("DIGEST_TIME", "07:00")

CLAUDE_MODEL = "claude-sonnet-4-6"

SOURCES = [
    {
        "url": "https://www.lennysnewsletter.com",
        "name": "Lenny's Newsletter",
        "category": "product_ai",
    },
    {
        "url": "https://www.lennysnewsletter.com/archive?sort=top",
        "name": "Lenny's Newsletter Archive",
        "category": "product_ai",
    },
    {
        "url": "https://bridge.adiagrawal.com/",
        "name": "Bridge by Adi Agrawal",
        "category": "ai_strategy",
    },
    {
        "url": "https://www.conventionalcommits.org/en/v1.0.0/",
        "name": "Conventional Commits Spec",
        "category": "dev_standards",
    },
    {
        "url": "https://www.intuitiveautonomy.org/multi-agent-systems",
        "name": "Intuitive Autonomy — Multi-Agent Systems",
        "category": "ai_technical",
    },
    {
        "url": "https://www.intuitiveautonomy.org/",
        "name": "Intuitive Autonomy",
        "category": "ai_technical",
    },
    {
        "url": "https://enterpriseaiexecutive.ai/",
        "name": "Enterprise AI Executive",
        "category": "enterprise_ai",
    },
    {
        "url": "https://www.tomorrowtoolbox.com/courses/imrl",
        "name": "Tomorrow Toolbox — IMRL Course",
        "category": "ai_learning",
    },
    {
        "url": "https://maven.com/x/maven-rewind-2025",
        "name": "Maven Rewind 2025",
        "category": "ai_trends",
    },
    {
        "url": "https://www.aisnakeoil.com/",
        "name": "AI Snake Oil",
        "category": "ai_news",
    },
    {
        "url": "https://www.theunwindai.com/",
        "name": "The Unwind AI",
        "category": "ai_news",
    },
    # ── AI Governance Frameworks (permanent reference) ──────────────────────
    {
        "url": "https://www.microsoft.com/en-us/ai/responsible-ai",
        "name": "Microsoft Responsible AI",
        "category": "ai_governance",
    },
    {
        "url": "https://ai.google/responsibility/responsible-ai-practices/",
        "name": "Google Responsible AI Practices",
        "category": "ai_governance",
    },
    {
        "url": "https://airc.nist.gov/home",
        "name": "NIST AI Risk Management Framework",
        "category": "ai_governance",
    },
    # ── AI Strategy (permanent reference) ───────────────────────────────────
    {
        "url": "https://a16z.com/ai/",
        "name": "a16z AI",
        "category": "ai_strategy_ref",
    },
    {
        "url": "https://sloanreview.mit.edu/tag/artificial-intelligence/",
        "name": "MIT Sloan Management Review — AI",
        "category": "ai_strategy_ref",
    },
    {
        "url": "https://hai.stanford.edu",
        "name": "Stanford HAI",
        "category": "ai_strategy_ref",
    },
    # ── Enterprise AI Adoption (permanent reference) ─────────────────────────
    {
        "url": "https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai",
        "name": "McKinsey State of AI",
        "category": "ai_enterprise",
    },
    {
        "url": "https://hbr.org/topic/subject/ai-and-machine-learning",
        "name": "Harvard Business Review — AI",
        "category": "ai_enterprise",
    },
    {
        "url": "https://www.bcg.com/beyond-consulting/bcg-x",
        "name": "BCG X — AI",
        "category": "ai_enterprise",
    },
    {
        "url": "https://aibusiness.com/",
        "name": "AI Business",
        "category": "ai_enterprise",
    },
    {
        "url": "https://www.weforum.org/stories/2024/01/future-of-jobs-2025-artificial-intelligence/",
        "name": "World Economic Forum — AI Jobs Report",
        "category": "ai_enterprise",
    },
    {
        "url": "https://www.gartner.com/en/topics/generative-ai",
        "name": "Gartner Generative AI",
        "category": "ai_enterprise",
    },
    # ── AI Maturity & Roadmap (specific free frameworks) ─────────────────────
    {
        "url": "https://cloud.google.com/blog/topics/ai-machine-learning",
        "name": "Google Cloud AI Blog",
        "category": "ai_maturity",
    },
    {
        "url": "https://www.ibm.com/topics/artificial-intelligence",
        "name": "IBM AI Topics",
        "category": "ai_maturity",
    },
    {
        "url": "https://aws.amazon.com/ai/",
        "name": "AWS AI",
        "category": "ai_maturity",
    },
    # ── Executive Advisory, Business Case, Change Management, Adoption ────────
    {
        "url": "https://www2.deloitte.com/us/en/insights/topics/technology/ai-dossier.html",
        "name": "Deloitte AI Institute",
        "category": "ai_executive_advisory",
    },
    {
        "url": "https://www.ibm.com/thought-leadership/institute-business-value/en-us/report/ai-roi",
        "name": "IBM Institute for Business Value — AI ROI",
        "category": "ai_business_case",
    },
    {
        "url": "https://www.prosci.com/artificial-intelligence",
        "name": "Prosci AI Change Management",
        "category": "ai_change_management",
    },
    {
        "url": "https://cloud.google.com/transform/ai-adoption",
        "name": "Google Cloud AI Adoption Framework",
        "category": "ai_enterprise_adoption",
    },
    {
        "url": "https://www.microsoft.com/en-us/ai",
        "name": "Microsoft AI",
        "category": "ai_enterprise_adoption",
    },
]

CONTENT_SECTIONS = [
    "conversation_starters",
    "recent_updates_opinions",
    "core_concepts",
    "roadblocks_solutions",
    "mock_exec_conversation",
    "mock_ds_conversation",
    "dev_standards_update",
    "governance_frameworks",
    "ai_strategy_frameworks",
    "enterprise_ai_toolkit",
]
