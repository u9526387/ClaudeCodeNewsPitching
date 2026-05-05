import re
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

APP_NAME = "lovepitchingpolar"

KEYWORDS = [
    "defense", "cross-strait", "semiconductor", "military", "diplomacy",
    "human rights", "economy", "china", "taiwan strait", "pla", "invasion",
    "sanctions", "trade", "security", "sovereignty", "missile", "legislature",
    "election", "tsmc", "chip", "legislative yuan", "executive yuan",
    "ministry", "president", "parliament", "legislation", "bill", "policy",
    "strait", "beijing", "weapon", "arms", "tariff", "geopolit",
    "立法院", "國防", "外交", "經濟", "兩岸", "國會", "關稅",
    "中國", "美國", "軍事", "台灣", "解放軍", "制裁", "貿易", "半導體",
    "移工", "原住民", "鄭麗文", "賴清德", "黃國昌", "九合一選舉",
    "labor rights", "labour rights", "勞工", "勞權",
]

# Stricter keyword set for Executive Yuan — excludes 行政院 so routine press releases don't pass
_EY_KEYWORDS = [
    "國防", "外交", "兩岸", "關稅", "軍事", "半導體", "防衛", "美國",
    "軍購", "中共", "解放軍", "安全", "制裁", "貿易", "晶片", "台海",
]

# Google News RSS queries — each covers a distinct topic cluster
GOOGLE_NEWS_QUERIES = [
    # Topic-based (pulls from Reuters, AP, Bloomberg, Nikkei, etc.)
    "taiwan defense military security",
    "taiwan china cross-strait PLA strait",
    "taiwan semiconductor chip TSMC economy",
    "taiwan diplomacy foreign affairs international",
    "taiwan politics legislature election",
    "taiwan human rights civil society",
    "taiwan tariff trade US sanctions",
    # Site-specific: sources that are JS-rendered and can't be scraped directly
    "site:taiwannews.com.tw",          # Taiwan News (Next.js, no static HTML)
    "legislative yuan taiwan bill",    # Legislative Yuan (AJAX-rendered)
]

# Terms that confirm a story is actually about/relevant to Taiwan.
# A story must contain at least one of these — passing topic keywords alone is not enough.
TAIWAN_TERMS = [
    # English
    "taiwan", "taipei", "tsmc", "cross-strait", "taiwan strait",
    "legislative yuan", "executive yuan", "formosa",
    "lai ching-te", "william lai", "han kuo-yu", "ko wen-je",
    # Chinese
    "台灣", "台北", "中華民國", "立法院", "行政院", "民進黨", "國民黨",
    "賴清德", "黃國昌", "鄭麗文", "兩岸", "台海", "挺台", "對台",
    "九合一", "移工", "原住民",
]

# Sources whose entire output is Taiwan-focused by definition — skip the Taiwan check.
# CNA and PTS are NOT here: their pages mix Taiwan and international stories, so they
# need the explicit Taiwan-term check just like any other source.
_TRUSTED_TAIWAN_SOURCES = {
    "Focus Taiwan",    # every story is Taiwan-focused
    "Executive Yuan",  # Taiwan government press releases
    "Ketagalan Media", # Taiwan politics/society analysis
    "AmCham Topics",   # Taiwan business and security
    "Taiwan News",     # Taiwan-focused English outlet
}


def _is_taiwan_story(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    return any(t.lower() in combined for t in TAIWAN_TERMS)


SKIP_DOMAINS = {
    "facebook.com", "instagram.com", "youtube.com", "twitter.com",
    "x.com", "threads.com", "line.me", "tiktok.com",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8",
}

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _matches_keywords(text: str) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in KEYWORDS)


def _resolve_url(href: str, base: str) -> str:
    if not href or href.startswith("javascript"):
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return base.rstrip("/") + href
    return base.rstrip("/") + "/" + href


def _clean_title(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^\d+([A-Z])', r'\1', text)
    text = re.sub(r'([a-z])([A-Z])', r'\1 | \2', text)
    return text.split(" | ")[0].strip()


def _make_story(title: str, link: str, source: str, summary: str = "") -> Optional[dict]:
    title = _clean_title(title)
    if len(title) < 10:
        return None
    if any(d in link for d in SKIP_DOMAINS):
        return None
    if not _matches_keywords(title + " " + summary):
        return None
    if source not in _TRUSTED_TAIWAN_SOURCES and not _is_taiwan_story(title, summary):
        return None
    return {
        "title":     title,
        "link":      link,
        "summary":   summary,
        "source":    source,
        "timestamp": _now_utc(),
    }


def _fetch(url: str) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [fetch error] {url}: {e}")
        return None


# ── Google News RSS (primary source) ─────────────────────────────────────────

def _scrape_google_news(query: str) -> list:
    encoded = requests.utils.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
        stories = []
        for entry in feed.entries[:12]:
            title = entry.get("title", "")
            link  = entry.get("link", "")
            # Strip " - Source Name" suffix Google appends
            source_name = ""
            if hasattr(entry, "source") and entry.source.get("title"):
                source_name = entry.source["title"]
                if title.endswith(f" - {source_name}"):
                    title = title[: -(len(source_name) + 3)].strip()
            summary_html = entry.get("summary", "")
            summary = BeautifulSoup(summary_html, "html.parser").get_text(separator=" ").strip()
            s = _make_story(title, link, source_name or "Google News", summary)
            if s:
                stories.append(s)
        return stories
    except Exception as e:
        print(f"  [Google News '{query[:30]}']: {e}")
        return []


# ── Taiwan-local HTML scrapers (supplement) ───────────────────────────────────

def _scrape_taipei_times() -> list:
    soup = _fetch("https://www.taipeitimes.com")
    if not soup:
        return []
    stories, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/News/" not in href or "/archives/" not in href:
            continue
        title = _clean_title(a.get_text(strip=True))
        link = _resolve_url(href, "https://www.taipeitimes.com")
        if link in seen or not link:
            continue
        seen.add(link)
        s = _make_story(title, link, "Taipei Times")
        if s:
            stories.append(s)
    return stories


def _scrape_focus_taiwan() -> list:
    soup = _fetch("https://focustaiwan.tw")
    if not soup:
        return []
    stories, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(r'/\w+/\d{12}', href):
            continue
        title = a.get_text(strip=True)
        link = _resolve_url(href, "https://focustaiwan.tw")
        if link in seen or not link:
            continue
        seen.add(link)
        s = _make_story(title, link, "Focus Taiwan")
        if s:
            stories.append(s)
    return stories


def _scrape_cna() -> list:
    soup = _fetch("https://www.cna.com.tw/list/aipl.aspx")
    if not soup:
        return []
    stories, seen = [], set()
    for a in soup.select("ul.mainList a, a._ellipsis_simple"):
        title = re.sub(r'\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}$', '', a.get_text(strip=True)).strip()
        href = a.get("href", "")
        link = _resolve_url(href, "https://www.cna.com.tw")
        if link in seen or not link:
            continue
        seen.add(link)
        s = _make_story(title, link, "CNA")
        if s:
            stories.append(s)
    return stories


def _scrape_executive_yuan() -> list:
    soup = _fetch("https://www.ey.gov.tw/Page/278197D37F0FCDA")
    if not soup:
        return []
    stories, seen = [], set()
    for a in soup.select(".newslist a, ul li a, h3 a, h2 a"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        link = _resolve_url(href, "https://www.ey.gov.tw")
        if link in seen or not link:
            continue
        seen.add(link)
        if len(title) < 10:
            continue
        if not any(kw in title for kw in _EY_KEYWORDS):
            continue
        stories.append({
            "title": title, "link": link,
            "summary": "", "source": "Executive Yuan", "timestamp": _now_utc(),
        })
    return stories


def _scrape_pts() -> list:
    soup = _fetch("https://news.pts.org.tw/dailynews")
    if not soup:
        return []
    stories, seen = [], set()
    for a in soup.select("h2 a"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not href or "/article/" not in href:
            continue
        link = _resolve_url(href, "https://news.pts.org.tw")
        if link in seen or not link:
            continue
        seen.add(link)
        s = _make_story(title, link, "PTS")
        if s:
            stories.append(s)
    return stories


def _scrape_ketagalan() -> list:
    soup = _fetch("https://www.ketagalanmedia.com")
    if not soup:
        return []
    stories, seen = [], set()
    for a in soup.select("h2 a, .entry-title a"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not re.search(r'ketagalanmedia\.com/20\d{2}/', href):
            continue
        if href in seen:
            continue
        seen.add(href)
        s = _make_story(title, href, "Ketagalan Media")
        if s:
            stories.append(s)
    return stories


def _scrape_amcham() -> list:
    soup = _fetch("https://topics.amcham.com.tw")
    if not soup:
        return []
    stories, seen = [], set()
    for a in soup.select("h2 a, h3 a"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not re.search(r'amcham\.com\.tw/20\d{2}/', href):
            continue
        if href in seen:
            continue
        seen.add(href)
        s = _make_story(title, href, "AmCham Topics")
        if s:
            stories.append(s)
    return stories


# ── Main entry point ───────────────────────────────────────────────────────────

_HTML_SCRAPERS = [
    ("Taipei Times",    _scrape_taipei_times),
    ("Focus Taiwan",    _scrape_focus_taiwan),
    ("CNA",             _scrape_cna),
    ("Executive Yuan",  _scrape_executive_yuan),
    ("PTS",             _scrape_pts),
    ("Ketagalan Media", _scrape_ketagalan),
    ("AmCham Topics",   _scrape_amcham),
]


def fetch_stories() -> list:
    all_stories = []
    tasks = {}

    with ThreadPoolExecutor(max_workers=20) as executor:
        # Google News queries
        for query in GOOGLE_NEWS_QUERIES:
            tasks[executor.submit(_scrape_google_news, query)] = f"Google News: {query[:35]}"
        # Taiwan-local HTML scrapers
        for name, fn in _HTML_SCRAPERS:
            tasks[executor.submit(fn)] = name

        for future in as_completed(tasks):
            label = tasks[future]
            try:
                results = future.result()
                if results:
                    print(f"  [{label}] {len(results)} stories")
                all_stories.extend(results)
            except Exception as e:
                print(f"  [{label}] error: {e}")

    # Deduplicate by normalised title (first 55 chars)
    seen, unique = set(), []
    for s in all_stories:
        key = re.sub(r'\s+', ' ', s["title"].lower())[:55]
        if key not in seen:
            seen.add(key)
            unique.append(s)

    print(f"  Total unique stories: {len(unique)}")
    return unique


if __name__ == "__main__":
    print(f"[{APP_NAME}] Fetching stories...\n")
    results = fetch_stories()
    print(f"\nTotal: {len(results)} stories\n")
    for s in results:
        print(f"  [{s['source']}] {s['title'][:80]}")
        print(f"           {s['link']}\n")
