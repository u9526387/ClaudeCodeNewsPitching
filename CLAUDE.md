# Story News Agent — Project Constitution

## Tech Stack
- Frontend: Streamlit
- AI: Local Ollama (Model: llama3.1)
- Scraper: feedparser (RSS) + requests/BeautifulSoup (HTML)
- Tunnel: Ngrok

## Sources

### RSS Feeds
- Taipei Times: https://www.taipeitimes.com/xml/index.xml
- Focus Taiwan: https://focustaiwan.tw/rss/index.xml
- Taiwan News: https://www.taiwannews.com.tw/rss

### HTML Sources
- Legislative Yuan News: https://www.ly.gov.tw/Pages/List.aspx?nodeid=134
- CNA Politics: https://www.cna.com.tw/list/aipl.aspx
- Executive Yuan Press: https://www.ey.gov.tw/Page/278197D37F0FCDA
- PTS Daily News: https://news.pts.org.tw/dailynews

## Implementation Rules
- NEVER use Anthropic or OpenAI API keys.
- Always output pitches in the [Name] [Date] format, where Name is "Story".
- Ensure 'Significance' highlights why the world should care about Taiwan.
- Every story MUST have a 1-sentence Traditional Chinese summary.
- Internal app codename is "lovepitchingpolar" — do not change cookie names or session keys.
