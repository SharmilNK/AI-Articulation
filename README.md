# AI Articulation Daily Digest

A daily AI conversation coach for consultants — crawls top AI/ML newsletters and blogs,
synthesizes the content via Claude, and emails a formatted Word document with
ready-to-use talking points, concept explainers, and mock dialogues.

---

## What it generates each day

| # | Section | Purpose |
|---|---------|---------|
| 1 | **Conversation Starters** | 4–5 punchy hooks to open any AI discussion |
| 2 | **Recent Updates & Opinions** | What changed in AI this week + a confident take |
| 3 | **Core AI/ML Concepts** | Plain-English explanations with analogies |
| 4 | **Roadblocks & Solutions** | Current AI pain points + what the industry is doing |
| 5 | **Mock Conversations** | Scripted dialogues — one with an executive, one with a data scientist |
| 6 | **GitHub & Dev Standards** | Conventional Commits and other dev standards that matter in AI startups |

---

## Sources crawled

- Lenny's Newsletter (free articles)
- Spill the GPTea (Substack)
- Bridge by Adi Agrawal
- Intuitive Autonomy (multi-agent systems)
- Enterprise AI Executive
- Tomorrow Toolbox — IMRL Course
- Maven Rewind 2025
- Conventional Commits Spec

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/sharmilnk/ai-articulation.git
cd ai-articulation
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com/) |
| `GMAIL_USER` | Your Gmail address (e.g. `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | **App Password** — NOT your regular password. [Generate one here](https://myaccount.google.com/apppasswords) (requires 2FA enabled) |
| `RECIPIENT_EMAIL` | Where to send the digest (default: `sharmilkn@gmail.com`) |
| `DIGEST_TIME` | Daily send time in 24h format, e.g. `07:00` |

### 3. Run

```bash
# Run once right now and send email
python main.py

# Generate doc only (no email) — good for testing
python main.py --dry-run

# Run as a daily scheduler (keeps process alive)
python main.py --schedule
```

Generated `.docx` files are saved to the `output/` folder.

---

## Architecture

```
main.py                    <- entry point (CLI flags)
config.py                  <- all settings + source URLs
src/
  crawler.py               <- scrapes all sources (free content only)
  content_processor.py     <- Claude API synthesis -> structured JSON
  doc_generator.py         <- builds the Word document
  email_sender.py          <- Gmail SMTP delivery
  pipeline.py              <- orchestrates steps 1-4
  scheduler.py             <- daily schedule runner
output/                    <- generated .docx files (git-ignored)
```

---

## Gmail App Password Setup

Regular Gmail passwords don't work with SMTP when 2FA is on.
You need an App Password:

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Security -> 2-Step Verification (must be enabled)
3. App Passwords -> create one named "AI Articulation"
4. Copy the 16-character password into your `.env` as `GMAIL_APP_PASSWORD`
