import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Optional

APP_NAME = "lovepitchingpolar"

KEYWORDS = [
    "defense", "cross-strait", "semiconductor", "military", "diplomacy",
    "human rights", "economy", "china", "taiwan strait", "pla", "invasion",
    "sanctions", "trade", "security", "sovereignty", "missile", "legislature",
    "election", "tsmc", "chip", "legislative yuan", "executive yuan",
    "ministry", "president", "parliament", "legislation", "bill", "policy",
    "strait", "beijing", "weapon", "arms", "tariff", "geopolit",
    "立法院", "行政院", "國防", "外交", "經濟", "兩岸", "國會", "關稅",
]

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

NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


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
    """Trim titles that run into their own subheadline (no space between sentences)."""
    text = text.strip()
    # Strip leading page numbers like "1China..." or "2Military..."
    text = re.sub(r'^\d+([A-Z])', r'\1', text)
    # Split where lowercase runs directly into uppercase (concatenated sentences)
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
    return {
        "title":     title,
        "link":      link,
        "summary":   summary,
        "source":    source,
        "timestamp": NOW_UTC,
    }


def _fetch(url: str) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [fetch error] {url}: {e}")
        return None


# ── Per-source scrapers ────────────────────────────────────────────────────────

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
        # Article URLs look like /category/YYYYMMDDNNNN
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
    for a in soup.select("a._ellipsis_simple"):
        title = a.get_text(strip=True)
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
        s = _make_story(title, link, "Executive Yuan")
        if s:
            stories.append(s)
    return stories


def _scrape_pts() -> list:
    soup = _fetch("https://news.pts.org.tw/dailynews")
    if not soup:
        return []
    stories, seen = [], set()
    for a in soup.select("article a, .news-item a, h2 a, h3 a, .title a"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        link = _resolve_url(href, "https://news.pts.org.tw")
        if link in seen or not link:
            continue
        seen.add(link)
        s = _make_story(title, link, "PTS")
        if s:
            stories.append(s)
    return stories


# ── Main entry point ───────────────────────────────────────────────────────────

SCRAPERS = [
    ("Taipei Times",  _scrape_taipei_times),
    ("Focus Taiwan",  _scrape_focus_taiwan),
    ("CNA",           _scrape_cna),
    ("Executive Yuan",_scrape_executive_yuan),
    ("PTS",           _scrape_pts),
]


def fetch_stories(hours: int = 24) -> list:
    all_stories = []
    for name, fn in SCRAPERS:
        try:
            results = fn()
            print(f"  [{name}] {len(results)} stories")
            all_stories.extend(results)
        except Exception as e:
            print(f"  [{name}] error: {e}")

    # Deduplicate by normalised title
    seen, unique = set(), []
    for s in all_stories:
        key = re.sub(r'\s+', ' ', s["title"].lower())[:60]
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


if __name__ == "__main__":
    print(f"[{APP_NAME}] Fetching stories...\n")
    results = fetch_stories()
    print(f"\nTotal: {len(results)} stories\n")
    for s in results:
        print(f"  [{s['source']}] {s['title'][:80]}")
        print(f"           {s['link']}\n")
