import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import Optional

APP_NAME = "lovepitchingpolar"

RSS_FEEDS = [
    {"name": "Taipei Times", "url": "https://www.taipeitimes.com/xml/index.xml"},
    {"name": "Focus Taiwan",  "url": "https://focustaiwan.tw/rss/index.xml"},
    {"name": "Taiwan News",   "url": "https://www.taiwannews.com.tw/rss"},
]

# Each entry: (source_name, url, css_selector_for_links, base_url_for_relative_links)
HTML_SOURCES = [
    (
        "Legislative Yuan",
        "https://www.ly.gov.tw/Pages/List.aspx?nodeid=134",
        "ul.newslist li a, .list-group-item a, h3 a, h2 a",
        "https://www.ly.gov.tw",
    ),
    (
        "CNA Politics",
        "https://www.cna.com.tw/list/aipl.aspx",
        "ul.listnostylee li a, .item a, h2 a, h3 a",
        "https://www.cna.com.tw",
    ),
    (
        "Executive Yuan",
        "https://www.ey.gov.tw/Page/278197D37F0FCDA",
        ".newslist a, ul li a, h3 a, h2 a",
        "https://www.ey.gov.tw",
    ),
    (
        "PTS News",
        "https://news.pts.org.tw/dailynews",
        "article a, .news-item a, h2 a, h3 a, .title a",
        "https://news.pts.org.tw",
    ),
]

KEYWORDS = [
    "defense", "cross-strait", "semiconductor", "military", "diplomacy",
    "human rights", "economy", "china", "taiwan strait", "pla", "invasion",
    "sanctions", "trade", "security", "sovereignty", "missile", "legislature",
    "election", "tsmc", "chip", "legislative yuan", "executive yuan",
    "ministry", "president", "parliament", "legislation", "bill", "policy",
    "立法院", "行政院", "國防", "外交", "經濟", "兩岸", "國會",
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
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def _entry_timestamp(entry) -> Optional[datetime]:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t is None:
        return None
    return datetime(*t[:6], tzinfo=timezone.utc)


def _is_recent(ts: Optional[datetime], hours: int = 24) -> bool:
    if ts is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return ts >= cutoff


def _matches_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)


def _resolve_url(href: str, base: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return base.rstrip("/") + href
    return base.rstrip("/") + "/" + href


def fetch_rss_stories(hours: int = 24) -> list:
    stories = []
    for feed_meta in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_meta["url"])
            for entry in feed.entries:
                ts = _entry_timestamp(entry)
                if not _is_recent(ts, hours):
                    continue
                text = (entry.get("title") or "") + " " + (entry.get("summary") or "")
                if not _matches_keywords(text):
                    continue
                stories.append({
                    "title":     entry.get("title", "").strip(),
                    "link":      entry.get("link", ""),
                    "summary":   entry.get("summary", "").strip(),
                    "source":    feed_meta["name"],
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M UTC") if ts else "Unknown",
                })
        except Exception as e:
            print(f"  [RSS error] {feed_meta['name']}: {e}")
    return stories


def fetch_html_stories(source_name: str, url: str, selector: str, base_url: str) -> list:
    stories = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for a in soup.select(selector):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not title or not href or len(title) < 8:
                continue
            link = _resolve_url(href, base_url)
            if link in seen:
                continue
            seen.add(link)

            if any(d in link for d in SKIP_DOMAINS):
                continue

            if not _matches_keywords(title):
                continue

            stories.append({
                "title":     title,
                "link":      link,
                "summary":   "",
                "source":    source_name,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            })
    except Exception as e:
        print(f"  [HTML error] {source_name}: {e}")
    return stories


def fetch_stories(hours: int = 24) -> list:
    stories = []

    # RSS feeds (with timestamp filtering)
    stories.extend(fetch_rss_stories(hours))

    # HTML sources (no reliable timestamp — include all matching headlines)
    for source_name, url, selector, base_url in HTML_SOURCES:
        stories.extend(fetch_html_stories(source_name, url, selector, base_url))

    # Deduplicate by title
    seen_titles = set()
    unique = []
    for s in stories:
        key = s["title"].lower()[:60]
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(s)

    unique.sort(key=lambda s: s["timestamp"], reverse=True)
    return unique


if __name__ == "__main__":
    print(f"[{APP_NAME}] Fetching stories...\n")
    results = fetch_stories(hours=72)
    print(f"Found {len(results)} stories total\n")
    for s in results:
        print(f"  [{s['source']}] {s['timestamp']}")
        print(f"  {s['title']}")
        print(f"  {s['link']}\n")
