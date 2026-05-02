# Story News Agent — Project Constitution

## Tech Stack
- Frontend: Streamlit
- AI: Local Ollama (Model: llama3.1)
- Scraper: feedparser (Google News RSS) + requests/BeautifulSoup (HTML)
- Tunnel: Ngrok

## Sources

### Primary: Google News RSS (topic queries + site-specific)
These cover hundreds of outlets automatically — Reuters, AP, Bloomberg, Nikkei, plus all Taiwan-focused sources.

Topic queries (last 2 days):
- taiwan defense military security
- taiwan china cross-strait PLA strait
- taiwan semiconductor chip TSMC economy
- taiwan diplomacy foreign affairs international
- taiwan politics legislature election
- taiwan human rights civil society
- taiwan tariff trade US sanctions

Site-specific queries (for JS-rendered sources that can't be scraped directly):
- site:taiwannews.com.tw — Taiwan News (Next.js app, no static HTML)
- legislative yuan taiwan bill — Legislative Yuan (AJAX-rendered, no accessible RSS)

### Supplement: Taiwan-local HTML scrapers
These sites are scraped directly for content that may not surface quickly on Google News.

| Source | URL | Notes |
|---|---|---|
| Taipei Times | https://www.taipeitimes.com | English, /News/archives/ links |
| Focus Taiwan | https://focustaiwan.tw | English, /category/YYYYMMDDNNNN pattern |
| CNA Politics | https://www.cna.com.tw/list/aipl.aspx | Chinese, ul.mainList selector |
| Executive Yuan | https://www.ey.gov.tw/Page/278197D37F0FCDA | Chinese, strict keyword filter applied |
| PTS Daily News | https://news.pts.org.tw/dailynews | Chinese, h2 a selector |
| Ketagalan Media | https://www.ketagalanmedia.com | English Taiwan analysis |
| AmCham Topics | https://topics.amcham.com.tw | English Taiwan business/security |

### Excluded (JS-rendered, covered via Google News RSS instead)
- Taiwan News: https://www.taiwannews.com.tw — Next.js, no RSS → use site:taiwannews.com.tw query
- Legislative Yuan: https://www.ly.gov.tw/Pages/List.aspx?nodeid=134 — AJAX form, no accessible feed → use legislative yuan query

## Crawler Behaviour
- Runs once on manual refresh or automatically at 8pm Taiwan time
- Google News queries + HTML scrapers run in parallel (ThreadPoolExecutor)
- Typically returns 80–120 candidate stories per run
- Stories are filtered by keyword relevance before AI processing
- Processed pitches cached in pitch_cache.json (7-day TTL)
- Each refresh processes up to 20 NEW (uncached) stories via Ollama
- Subsequent same-day refreshes are near-instant (cache hits)

## Implementation Rules
- NEVER use Anthropic or OpenAI API keys.
- Always output pitches in the [Name] [Date] format, where Name is "Story".
- Ensure 'Significance' highlights why the world should care about Taiwan.
- Every story MUST have a 1-sentence Traditional Chinese summary.
- Internal app codename is "lovepitchingpolar" — do not change cookie names or session keys.
