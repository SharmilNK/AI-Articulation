# AI Articulation — Architecture & Orchestration Flow

> Modelled on the **a16z Emerging LLM App Stack** (andreessen horowitz, 2023).  
> Reference: _"Emerging Architectures for LLM Applications"_ — a16z / Matt Bornstein, Rajko Radovanovic.

---

## Stack Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DELIVERY LAYER                               │
│          Gmail SMTP · GitHub Actions Artifact Upload                │
├─────────────────────────────────────────────────────────────────────┤
│                     OUTPUT / UI LAYER                               │
│             python-docx · Styled Word Document (.docx)              │
├─────────────────────────────────────────────────────────────────────┤
│                   OUTPUT PARSING LAYER                              │
│          JSON parser · Markdown fence stripper · Validator          │
├─────────────────────────────────────────────────────────────────────┤
│                        LLM LAYER                                    │
│        Claude claude-sonnet-4-6 · Anthropic REST API (requests)         │
├─────────────────────────────────────────────────────────────────────┤
│                CONTEXT CONSTRUCTION LAYER                           │
│     Prompt template · Per-source content cap (1,500 chars)          │
├─────────────────────────────────────────────────────────────────────┤
│                    DATA INGESTION LAYER                             │
│   requests · BeautifulSoup4 · 31 sources · Rate limiter (1.5 s)    │
├─────────────────────────────────────────────────────────────────────┤
│                   ORCHESTRATION LAYER                               │
│       pipeline.py · main.py · GitHub Actions cron (07:00 UTC)      │
├─────────────────────────────────────────────────────────────────────┤
│                  CONFIGURATION / SECRETS LAYER                      │
│    python-dotenv · GitHub Repository Secrets · config.py            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Layer-by-Layer Breakdown

### 1. Configuration / Secrets Layer

| Item | Value / Location |
|------|-----------------|
| `ANTHROPIC_API_KEY` | GitHub Secret → env var |
| `GMAIL_USER` | GitHub Secret → env var |
| `GMAIL_APP_PASSWORD` | GitHub Secret → env var |
| `RECIPIENT_EMAIL` | GitHub Secret → env var (comma-separated list supported) |
| `DIGEST_TIME` | `.env` → defaults to `07:00` (local scheduler only) |
| `CLAUDE_MODEL` | Hardcoded in `config.py` → `claude-sonnet-4-6` |
| Source list | 31 URLs in `config.py` → `SOURCES[]` |

All env vars are `.strip()`'d at read time to guard against trailing newlines from secret copy-paste.

---

### 2. Orchestration Layer

**Entry point:** `main.py`

| Mode | Command | Behaviour |
|------|---------|-----------|
| One-shot | `python main.py` | Run pipeline once, send email |
| Dry run | `python main.py --dry-run` | Run pipeline, save doc, skip email |
| Scheduler | `python main.py --schedule` | Keep process alive, fire at `DIGEST_TIME` daily |
| Automated | GitHub Actions cron `0 7 * * *` | Runs at 07:00 UTC every day |

**Orchestrator:** `src/pipeline.py → run_pipeline(dry_run)`  
Linear 4-step pipeline. Each step is guarded; a failure at any step halts and returns `False` (exit code 1 in GitHub Actions).

```
Step 1 → Crawl     →  Step 2 → Synthesize  →  Step 3 → Build Doc  →  Step 4 → Email
  |                     |                        |                       |
  ▼ (on fail)           ▼ (on fail)              ▼ (on fail)            ▼ (on fail)
skip source           return False             return False           return False
continue rest
```

---

### 3. Data Ingestion Layer

**Module:** `src/crawler.py`

#### Tools

| Tool | Role |
|------|------|
| `requests` | HTTP GET with 15 s timeout |
| `BeautifulSoup4` (html.parser) | HTML parsing and text extraction |
| `time.sleep(1.5)` | Rate limiter — 1.5 s delay between requests |

#### Source Categories (31 total)

| Category | Count | Examples |
|----------|-------|---------|
| `product_ai` | 2 | Lenny's Newsletter, Lenny's Archive |
| `ai_strategy` | 1 | Bridge by Adi Agrawal |
| `dev_standards` | 1 | Conventional Commits Spec |
| `ai_technical` | 2 | Intuitive Autonomy, Multi-Agent Systems |
| `enterprise_ai` | 1 | Enterprise AI Executive |
| `ai_learning` | 1 | Tomorrow Toolbox IMRL |
| `ai_trends` | 1 | Maven Rewind 2025 |
| `ai_news` | 2 | AI Snake Oil, The Unwind AI |
| `ai_governance` | 3 | Microsoft Responsible AI, Google Responsible AI, NIST AI RMF |
| `ai_strategy_ref` | 3 | a16z AI, MIT Sloan AI, Stanford HAI |
| `ai_enterprise` | 6 | McKinsey, HBR, BCG X, AI Business, WEF, Gartner |
| `ai_maturity` | 3 | Google Cloud AI Blog, IBM AI Topics, AWS AI |
| `ai_executive_advisory` | 1 | Deloitte AI Institute |
| `ai_business_case` | 1 | IBM Institute for Business Value — AI ROI |
| `ai_change_management` | 1 | Prosci AI Change Management |
| `ai_enterprise_adoption` | 2 | Google Cloud AI Adoption, Microsoft AI |

#### Extractors

| Extractor | Triggered by | What it targets |
|-----------|-------------|-----------------|
| `_extract_substack()` | `substack.com` in URL | `.body`, `.post-content`, `/p/` links |
| `_extract_lenny()` | `lennysnewsletter.com` in URL | `.post-content`, `.free`, `/p/` links |
| `_extract_generic()` | Everything else | `<main>`, `<article>`, `.content`, `<body>` |

#### Output

Each source produces a `ScrapedPage` dataclass:
```python
@dataclass
class ScrapedPage:
    url: str
    source_name: str
    category: str
    title: str
    content: str        # capped at 8,000 chars at extraction
    links: list[str]
    error: Optional[str]
```

---

### 4. Context Construction Layer

**Module:** `src/content_processor.py → _build_prompt()`

| Parameter | Value | Why |
|-----------|-------|-----|
| Per-source content cap | 1,500 chars | Keeps total prompt size manageable |
| Sources included | Only pages where `content` is truthy and `error` is None | Skip failed/empty crawls |
| System prompt | Role-play: expert AI/ML educator coaching a consultant | Sets Claude's persona and audience |
| Date injection | `today = date.today().strftime("%B %d, %Y")` | Anchors daily sections to real date |

The prompt requests a single structured JSON object with **9 keys** — no additional text, no markdown fences.

---

### 5. LLM Layer

**Module:** `src/content_processor.py → generate_digest()`

| Parameter | Value |
|-----------|-------|
| Model | `claude-sonnet-4-6` |
| API | `https://api.anthropic.com/v1/messages` (REST, not SDK) |
| HTTP client | `requests.post()` — used instead of the `anthropic` SDK to avoid httpx connectivity failures on GitHub-hosted runners |
| `max_tokens` | 16,000 |
| `timeout` | 300 s |
| `anthropic-version` header | `2023-06-01` |

#### 9-Section Output Schema

| # | Key | Type | Refreshes |
|---|-----|------|-----------|
| 1 | `conversation_starters` | list[3] | Daily |
| 2 | `recent_updates_opinions` | list[3] | Daily |
| 3 | `core_concepts` | list[3] | Daily |
| 4 | `roadblocks_solutions` | list[3] | Daily |
| 5 | `mock_exec_conversation` | object | Daily |
| 6 | `mock_ds_conversation` | object | Daily |
| 7 | `dev_standards_update` | object | Daily |
| 8 | `governance_frameworks` | list[3] | Permanent reference + daily business case |
| 9 | `ai_strategy_frameworks` | list[3] | Permanent reference + daily business case |
| 10 | `enterprise_ai_toolkit` | list[6] | Permanent reference + daily business case |

**Business case schema** (sections 8, 9, 10 — one per framework, unique daily):
```json
{
  "scenario": "Specific company type + business process",
  "implementation_layers": [
    { "layer": "Layer name", "what_happens": "1-sentence description" }
  ],
  "risks": [
    { "risk": "Risk", "priority": "High|Medium|Low", "mitigation": "1 sentence" }
  ]
}
```

---

### 6. Output Parsing Layer

**Module:** `src/content_processor.py` (inline in `generate_digest()`)

| Step | Code | Purpose |
|------|------|---------|
| Strip markdown fences | `if raw.startswith("```"):` | Claude occasionally wraps output in code fences despite instruction |
| Strip `json` language tag | `if raw.startswith("json"): raw = raw[4:]` | Handles ` ```json ` prefix |
| Parse JSON | `json.loads(raw)` | Convert string → Python dict |
| Error logging | `logger.error(... raw[:500])` | Logs first 500 chars of malformed output for diagnosis |

---

### 7. Output / UI Layer

**Module:** `src/doc_generator.py → build_document()`

#### Tools

| Tool | Role |
|------|------|
| `python-docx` | Word document creation and styling |
| `docx.shared.RGBColor` | Risk priority colour coding |
| `docx.shared.Pt`, `Inches` | Font sizes and indentation |
| `docx.oxml` | Custom horizontal rule (section divider) |

#### Document Structure

| Element | Style |
|---------|-------|
| Cover title | 24 pt, bold, blue `#1A53A1`, centred |
| Section headings (H1) | 18 pt, bold, blue `#1A53A1` + horizontal rule |
| Sub-headings (H2) | 13 pt, bold, mid-blue `#2E74B5` |
| Body labels | 10 pt, bold label + normal value |
| Bullets | `List Bullet` style, 10 pt |
| Consultant dialogue | 10 pt italic, blue speaker label |
| Other speaker dialogue | 10 pt, grey speaker label |
| Business case scenario | 10 pt italic, indented 0.3" |
| Risk: High | Bold `[High]` label in red `#C00000` |
| Risk: Medium | Bold `[Medium]` label in orange `#FF7F00` |
| Risk: Low | Bold `[Low]` label in blue `#2E74B5` |

Output file: `output/AI_Articulation_Digest_YYYY-MM-DD.docx`

---

### 8. Delivery Layer

**Module:** `src/email_sender.py → send_digest()`

| Parameter | Value |
|-----------|-------|
| SMTP host | `smtp.gmail.com` |
| Port | 587 (STARTTLS) |
| Auth | Gmail App Password (not account password) |
| `RECIPIENT_EMAIL` | Comma-separated list — all recipients get the same email |
| Attachment | `.docx` file as `application/octet-stream` |
| Body | HTML — date, section list, source credits |
| Subject | `AI Articulation Digest — {date}` |

---

## Orchestration Flow (End-to-End)

```
GitHub Actions cron (07:00 UTC)
        │
        ▼
  main.py → run_pipeline()
        │
        ├─ Step 1: crawl_all(SOURCES)
        │       │
        │       ├─ For each of 31 sources:
        │       │     ├─ GET request (15 s timeout)
        │       │     ├─ Route to extractor (Substack / Lenny / generic)
        │       │     ├─ Paywall check → extract preview only if gated
        │       │     ├─ Cap content at 1,500 chars
        │       │     └─ Sleep 1.5 s
        │       │
        │       └─ Return list[ScrapedPage] (errors included, not raised)
        │
        ├─ Step 2: generate_digest(usable_pages)
        │       │
        │       ├─ Build prompt with date + source content blocks
        │       ├─ POST to Anthropic REST API (max_tokens=16000, timeout=300s)
        │       ├─ Strip markdown fences if present
        │       └─ json.loads() → Python dict
        │
        ├─ Step 3: build_document(digest, today_str)
        │       │
        │       ├─ Create Document(), set margins
        │       ├─ Render 9 sections with styled typography
        │       ├─ Render business cases with colour-coded risks
        │       └─ Save to output/AI_Articulation_Digest_YYYY-MM-DD.docx
        │
        └─ Step 4: send_digest(doc_path)
                │
                ├─ Validate credentials present
                ├─ Build HTML email body
                ├─ Attach .docx
                ├─ SMTP STARTTLS → login → sendmail
                └─ Return True/False
```

---

## Risks & Mitigations

### Data Ingestion Risks

| Risk | Likelihood | Impact | Current Mitigation |
|------|-----------|--------|-------------------|
| Source returns 403/404 | High | Low | Per-source try/catch; skip and log; pipeline continues |
| Source times out (15 s) | Medium | Low | Per-source timeout; skip and log |
| JavaScript-rendered page yields 0 chars | High | Low | Source still ingested; `_build_prompt` skips pages with empty content |
| Paywall blocks full article | Medium | Low | Paywall detector extracts preview text only |
| Bot-blocking (User-Agent detection) | Medium | Medium | Custom `User-Agent` header with project identifier |
| Rate limiting / IP ban | Low | High | 1.5 s crawl delay between requests |
| Source URL changes / site restructure | Medium | Medium | Manual URL update required in `config.py` |

### LLM Layer Risks

| Risk | Likelihood | Impact | Current Mitigation |
|------|-----------|--------|-------------------|
| JSON truncated mid-response | Medium | High | `max_tokens=16000`; previously caused failures at 12,000 |
| Claude wraps JSON in markdown fences | Medium | Medium | Fence-stripper runs before `json.loads()` |
| Malformed / partial JSON | Low | High | `json.JSONDecodeError` caught; error logged with 500-char snippet; pipeline returns False |
| Anthropic API outage | Low | High | `requests.RequestException` caught; raised as `RuntimeError`; pipeline returns False |
| `anthropic` SDK httpx failure on GitHub runners | Confirmed | High | **Resolved:** SDK removed; direct `requests.post()` used instead |
| Prompt too large → slow response | Medium | Medium | 1,500-char cap per source (down from 3,000) |
| API key invalid / expired | Low | High | 401 caught via `resp.ok` check; full error body logged |
| API key trailing newline | Confirmed (historical) | High | **Resolved:** `.strip()` on all env var reads |

### Output & Delivery Risks

| Risk | Likelihood | Impact | Current Mitigation |
|------|-----------|--------|-------------------|
| Missing JSON key in digest | Low | Low | `.get()` with default empty values throughout `doc_generator.py` |
| `output/` directory missing | Low | Medium | `os.makedirs(OUTPUT_DIR, exist_ok=True)` on every run |
| SMTP auth failure | Low | High | `SMTPAuthenticationError` caught; error logged; returns False |
| Gmail App Password not set | Low | High | Credential presence check before SMTP connection |
| `.docx` file not found at send time | Very low | Medium | `FileNotFoundError` caught; error logged; returns False |
| Multiple recipients — one address invalid | Low | Medium | `sendmail()` called with full list; Gmail rejects the batch |

### Infrastructure Risks

| Risk | Likelihood | Impact | Current Mitigation |
|------|-----------|--------|-------------------|
| GitHub Actions runner connectivity | Low | High | Confirmed working; `requests` used (not `httpx`) |
| Workflow times out (15 min cap) | Low | Medium | Claude call ≤ 5 min; crawl ≤ 2 min; total well under limit |
| GitHub Secret not set | Low | High | Step 2 fails with 401 or empty-key log; easy to diagnose |
| No usable sources scraped | Very low | High | `if not usable: return False` after Step 1 |

---

## Fallbacks

| Scenario | Fallback Behaviour |
|----------|--------------------|
| Source fetch fails | Skip source; continue crawling remaining 30 |
| Source yields 0 chars | Excluded from prompt by `_build_prompt` (`if not page.content`) |
| Paywalled content detected | Extract visible preview text only |
| Fewer than expected sources succeed | Pipeline continues as long as ≥ 1 source has content |
| All sources fail | `if not usable: logger.error(); return False` — clean abort |
| Claude wraps output in ` ```json ` | Fence-stripper normalises before parse |
| JSON parse fails | Error + 500-char log snippet; pipeline returns False |
| Email credentials missing | Log error; return False without attempting SMTP |
| SMTP fails | Log error; return False; doc is still saved to `output/` |
| Dry-run mode | Steps 1–3 run normally; Step 4 (email) skipped |

---

## Health Checks

### Automated (built-in)

| Check | Where | What it detects |
|-------|-------|----------------|
| Usable source count log | `pipeline.py:33` | `"19/31 sources scraped successfully"` — visible in Actions log |
| Zero-usable-source abort | `pipeline.py:35–37` | Hard stop with error log if nothing scraped |
| API key preview log | `content_processor.py:222` | Logs `sk-ant-api03-...` prefix — confirms correct secret is loaded |
| API response status check | `content_processor.py:235` | `if not resp.ok: raise RuntimeError(status + body)` |
| JSON parse error log | `content_processor.py:251` | Logs parse error + raw output snippet |
| Pipeline return value | `pipeline.py` | `True` = success, `False` = failure at any step |
| Process exit code | `main.py:51` | `sys.exit(0 if success else 1)` — GitHub Actions marks run as failed |
| Artifact upload | `daily-digest.yml` | `if: always()` — `.docx` uploaded even on partial failure |
| SMTP auth error | `email_sender.py:100` | Specific error message points to App Password setup |
| Per-source error log | `crawler.py:184` | `WARNING Skipping {name} — {reason}` for every failed source |

### Manual / Operational

| Check | How to run |
|-------|-----------|
| End-to-end test | `python main.py --dry-run` — generates doc without sending email |
| Inspect generated doc | Download artifact from GitHub Actions → `digest-{run_id}` |
| Verify API key is loaded | Look for `"Using API key starting with: sk-ant-api03"` in Actions log |
| Confirm email delivery | Check inbox at `RECIPIENT_EMAIL` after workflow completes |
| Re-run on failure | Actions → AI Articulation Daily Digest → Run workflow (manual trigger) |
| Monitor daily run | GitHub Actions → workflow history → check green/red status |

---

## Dependency Map

```
main.py
 ├── src/scheduler.py      (schedule library — local mode only)
 └── src/pipeline.py
      ├── config.py         (SOURCES, CLAUDE_MODEL, credentials)
      ├── src/crawler.py
      │    ├── requests
      │    └── beautifulsoup4
      ├── src/content_processor.py
      │    ├── requests      (direct REST call to Anthropic API)
      │    └── config.py     (ANTHROPIC_API_KEY, CLAUDE_MODEL)
      ├── src/doc_generator.py
      │    └── python-docx
      └── src/email_sender.py
           ├── smtplib       (stdlib)
           └── config.py     (GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL)
```

**Full dependency list (`requirements.txt`):**

| Package | Version | Role |
|---------|---------|------|
| `requests` | ≥ 2.31.0 | HTTP — crawling + Anthropic API calls |
| `beautifulsoup4` | ≥ 4.12.0 | HTML parsing |
| `python-docx` | ≥ 1.1.0 | Word document generation |
| `schedule` | ≥ 1.2.0 | Local daily scheduler |
| `python-dotenv` | ≥ 1.0.0 | `.env` file loading |

_Note: The `anthropic` Python SDK is intentionally excluded. It uses `httpx` internally, which fails to connect to `api.anthropic.com` on GitHub-hosted runners. Direct `requests.post()` is used instead._

---

## GitHub Actions CI/CD

**Workflow:** `.github/workflows/daily-digest.yml`

| Property | Value |
|----------|-------|
| Trigger | Cron `0 7 * * *` (07:00 UTC daily) + `workflow_dispatch` (manual) |
| Runner | `ubuntu-latest` |
| Python | 3.11 |
| Timeout | 15 minutes |
| Secrets injected | `ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `RECIPIENT_EMAIL` |
| Artifact | `output/*.docx` → `digest-{run_id}`, retained 7 days |
| Artifact upload | `if: always()` — runs even when pipeline fails |
| Failure signal | Exit code 1 → red ✗ in Actions UI + email notification (if configured) |
