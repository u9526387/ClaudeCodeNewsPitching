# 🐻‍❄️ Story News Agent

A local AI news pitcher for Taiwan stories, running on Ollama via a Streamlit dashboard accessible through a permanent Ngrok link.

## What it does

Scrapes Taiwan news sources every refresh, runs each story through a local `llama3.1` model to generate a formatted pitch, and flags stories that would make the cut for international outlets like BBC, CNN, or TaiwanPlus.

Each pitch includes:
- A punchy rewritten headline with category tag
- A **Significance** paragraph explaining why the world should care
- A one-sentence **Traditional Chinese summary**
- An **⭐ International Cut** verdict with justification (strict criteria — most stories don't qualify)

---

## Stack

| Layer | Tool |
|---|---|
| UI | Streamlit (dark mode) |
| AI | Ollama · llama3.1 (local, no API keys) |
| Scraper | requests + BeautifulSoup |
| Tunnel | Ngrok (permanent domain) |

---

## Sources

| Source | Language |
|---|---|
| Taipei Times | English |
| Focus Taiwan | English |
| CNA Politics | Chinese |
| Executive Yuan | Chinese |
| PTS News | Chinese |

---

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Install and start Ollama**
```bash
# Download from https://ollama.com
ollama pull llama3.1
```

**3. Configure credentials**

Edit `.env` (never committed to git):
```
APP_USERNAME=editor
APP_PASSWORD=your_password
```

**4. Launch**
```bash
bash start.sh
```

This starts Streamlit on port 8501 and opens the permanent Ngrok tunnel automatically.

**Local:** `http://localhost:8501`  
**Public:** `https://rope-mushily-opium.ngrok-free.dev`

---

## Project structure

```
lovepitchingpolar/
├── app.py            # Streamlit UI + auth
├── ai_engine.py      # Ollama pitch generation
├── scraper.py        # Multi-source HTML scraper
├── start.sh          # One-command launcher
├── requirements.txt
├── .env              # Credentials (gitignored)
└── CLAUDE.md         # Project constitution
```

---

## Notes

- No Anthropic or OpenAI API keys used anywhere
- `.env` is gitignored — credentials never leave your machine
- The Ngrok free domain is permanent once claimed; the URL never changes
- If Ollama fails to load (Metal GPU error on macOS), `start.sh` restarts it in CPU-only mode automatically
