import os
import streamlit as st
import streamlit_authenticator as stauth
from dotenv import load_dotenv
from datetime import date, datetime, timezone, timedelta
from scraper import fetch_stories
from ai_engine import process_stories

TAIWAN_TZ = timezone(timedelta(hours=8))
AUTO_REFRESH_HOUR = 20  # 8pm Taiwan time

load_dotenv()

APP_USERNAME = os.getenv("APP_USERNAME", "editor")
APP_PASSWORD = os.getenv("APP_PASSWORD", "taiwanplus2026")
APP_NAME = os.getenv("APP_NAME", "lovepitchingpolar")

CATEGORIES = ["Politics", "Diplomacy", "Security", "Human Rights", "Society", "Economy"]

CATEGORY_COLORS = {
    "Security":     "#FF4B4B",
    "Diplomacy":    "#4B9EFF",
    "Economy":      "#00C49A",
    "Human Rights": "#FF9F40",
    "Society":      "#A78BFA",
    "Politics":     "#F59E0B",
}

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="lovepitchingpolar",
    page_icon="🐻‍❄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS — City Boy dark aesthetic ─────────────────────────────────────
st.markdown("""
<style>
  /* Base */
  html, body, [data-testid="stAppViewContainer"] {
    background-color: #0D0D0D;
    color: #E8E8E8;
    font-family: 'Inter', 'SF Pro Display', -apple-system, sans-serif;
  }
  [data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 1px solid #222;
  }
  /* Header */
  .brand-header {
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #FFFFFF;
    padding: 0.2rem 0 1.4rem 0;
  }
  .brand-sub {
    font-size: 0.65rem;
    letter-spacing: 0.22em;
    color: #555;
    text-transform: uppercase;
    margin-top: -1.2rem;
    padding-bottom: 1.6rem;
  }
  /* Pitch card */
  .pitch-card {
    background: #141414;
    border: 1px solid #242424;
    border-radius: 10px;
    padding: 1.4rem 1.6rem 1rem 1.6rem;
    margin-bottom: 1.2rem;
    transition: border-color 0.2s;
  }
  .pitch-card:hover { border-color: #333; }
  .pitch-cat {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 0.7rem;
  }
  .pitch-headline {
    font-size: 1.05rem;
    font-weight: 600;
    color: #FFFFFF;
    line-height: 1.4;
    margin-bottom: 0.8rem;
  }
  .pitch-headline a {
    color: #FFFFFF;
    text-decoration: none;
  }
  .pitch-headline a:hover { color: #aaa; }
  .pitch-sig-label {
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #555;
    margin-bottom: 0.25rem;
  }
  .pitch-sig {
    font-size: 0.9rem;
    color: #C0C0C0;
    line-height: 1.65;
    margin-bottom: 1rem;
  }
  .pitch-zh {
    font-size: 0.88rem;
    color: #888;
    border-left: 2px solid #2A2A2A;
    padding-left: 0.8rem;
    margin-bottom: 1rem;
    line-height: 1.6;
  }
  .pitch-meta {
    font-size: 0.68rem;
    color: #444;
    letter-spacing: 0.06em;
  }
  /* Copy button */
  .copy-btn {
    display: inline-block;
    margin-top: 0.6rem;
    padding: 6px 16px;
    background: #1A1A1A;
    border: 1px solid #303030;
    border-radius: 6px;
    color: #888;
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.15s;
  }
  .copy-btn:hover { background: #222; color: #ccc; border-color: #444; }
  /* Divider */
  hr { border-color: #1E1E1E; }
  /* Streamlit overrides */
  .stButton > button {
    background: #1A1A1A !important;
    color: #888 !important;
    border: 1px solid #303030 !important;
    border-radius: 6px !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
  }
  .stButton > button:hover {
    background: #222 !important;
    color: #ccc !important;
    border-color: #444 !important;
  }
  [data-testid="stCheckbox"] label { color: #888; font-size: 0.82rem; }
  div[data-testid="stMetricValue"] { color: #FFF; }
  .stSpinner > div { color: #555 !important; }
</style>
""", unsafe_allow_html=True)


# ── Auth setup ────────────────────────────────────────────────────────────────
hashed_pw = stauth.Hasher.hash(APP_PASSWORD)

credentials = {
    "usernames": {
        APP_USERNAME: {
            "name": "Editor",
            "password": hashed_pw,
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    cookie_name="lovepitchingpolar_auth",
    key="super_secret_key_lpp",
    cookie_expiry_days=7,
)

authenticator.login(location="main", fields={"Form name": "Login — Story"})

auth_status = st.session_state.get("authentication_status")

if auth_status is False:
    st.error("Incorrect username or password.")
    st.stop()

if auth_status is None:
    st.markdown("""
    <div style='color:#444;font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;
    text-align:center;padding-top:3rem;'>Taiwan · News · Intelligence</div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="brand-header">🐻‍❄️ lovepitchingpolar</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Story News Agent</div>', unsafe_allow_html=True)

    st.markdown("**Filter by Category**")
    selected_cats = []
    for cat in CATEGORIES:
        color = CATEGORY_COLORS.get(cat, "#888")
        checked = st.checkbox(f"{cat}", value=True, key=f"cat_{cat}")
        if checked:
            selected_cats.append(cat)

    st.markdown("---")
    intl_only = st.checkbox("⭐ International cuts only", value=False, key="intl_only")

    st.markdown("---")
    refresh = st.button("↻  Refresh News", use_container_width=True)

    # Auto-refresh info
    tw_now = datetime.now(TAIWAN_TZ)
    next_refresh = tw_now.replace(hour=AUTO_REFRESH_HOUR, minute=0, second=0, microsecond=0)
    if tw_now.hour >= AUTO_REFRESH_HOUR:
        next_refresh += timedelta(days=1)
    hrs_until = int((next_refresh - tw_now).total_seconds() // 3600)
    mins_until = int(((next_refresh - tw_now).total_seconds() % 3600) // 60)
    st.markdown(f"""
    <div style='font-size:0.62rem;color:#333;letter-spacing:0.08em;padding-top:0.4rem;'>
    Auto-refresh at 8pm Taiwan time<br>Next: {hrs_until}h {mins_until}m
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    authenticator.logout("Logout", "sidebar")

    st.markdown("""
    <div style='font-size:0.62rem;color:#333;letter-spacing:0.1em;text-transform:uppercase;
    padding-top:1rem;'>Powered by Ollama · llama3.1</div>
    """, unsafe_allow_html=True)


# ── Fallback stories if RSS returns nothing ────────────────────────────────────
def _fallback_stories():
    return [
        {
            "title": "PLA warships cross Taiwan Strait median line in fourth consecutive day of drills",
            "summary": "Chinese PLA navy vessels crossed the median line for a fourth day running, the largest sustained incursion since 2022 exercises, as Taiwan's military tracked movements and scrambled fighter jets.",
            "source": "Focus Taiwan", "timestamp": "2026-04-30 06:00 UTC", "link": "#",
        },
        {
            "title": "TSMC Q1 profit hits record on AI chip orders; Taiwan government urges onshore production",
            "summary": "TSMC posted its highest quarterly profit on AI chip demand while Taiwan officials warned against offshoring advanced nodes.",
            "source": "Taipei Times", "timestamp": "2026-04-30 05:00 UTC", "link": "#",
        },
        {
            "title": "US Senate passes Taiwan Defense Act with $2 billion military aid package",
            "summary": "Senate unanimously passed the Taiwan Defense Act, fast-tracking arms sales and $2 billion in aid as tensions rise.",
            "source": "Taiwan News", "timestamp": "2026-04-30 04:00 UTC", "link": "#",
        },
    ]


# ── Clipboard JS component ─────────────────────────────────────────────────────
def copy_button(pitch_text: str, key: str):
    safe = pitch_text.replace("`", "'").replace("\\", "\\\\").replace("\n", "\\n")
    html = f"""
    <button class="copy-btn" onclick="
      navigator.clipboard.writeText(`{safe}`)
        .then(() => {{ this.innerText = '✓ Copied'; setTimeout(() => this.innerText = '⧉ Copy Pitch', 1800); }})
        .catch(() => {{
          var ta = document.createElement('textarea');
          ta.value = `{safe}`;
          document.body.appendChild(ta); ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
          this.innerText = '✓ Copied'; setTimeout(() => this.innerText = '⧉ Copy Pitch', 1800);
        }});
    ">⧉ Copy Pitch</button>
    """
    st.components.v1.html(html, height=50)


# ── Auto-refresh at 8pm Taiwan time ───────────────────────────────────────────
def _should_auto_refresh() -> bool:
    tw_now = datetime.now(TAIWAN_TZ)
    if tw_now.hour < AUTO_REFRESH_HOUR:
        return False
    last = st.session_state.get("last_auto_refresh_date")
    today_str = tw_now.strftime("%Y-%m-%d")
    return last != today_str

if _should_auto_refresh():
    st.session_state.last_auto_refresh_date = datetime.now(TAIWAN_TZ).strftime("%Y-%m-%d")
    refresh = True

# ── Session state / data loading ──────────────────────────────────────────────
if "pitches" not in st.session_state or refresh:
    with st.spinner("Fetching and analysing stories..."):
        raw = fetch_stories(hours=72)
        if not raw:
            raw = _fallback_stories()
        st.session_state.pitches = process_stories(raw[:10])
    st.session_state.fetch_time = datetime.now(TAIWAN_TZ).strftime("%B %d, %Y — %H:%M Taiwan time")


# ── Main feed ─────────────────────────────────────────────────────────────────
col_title, col_btn = st.columns([5, 1])
with col_title:
    st.markdown(f"""
    <div style='padding:0.4rem 0 0.4rem 0;'>
      <span style='font-size:1.6rem;font-weight:700;letter-spacing:-0.02em;color:#FFF;'>
        Today's Pitches
      </span>
      <span style='font-size:0.7rem;color:#444;letter-spacing:0.1em;
      text-transform:uppercase;margin-left:1rem;'>
        {st.session_state.get("fetch_time", "")}
      </span>
    </div>
    """, unsafe_allow_html=True)
with col_btn:
    st.markdown("<div style='padding-top:0.5rem;'>", unsafe_allow_html=True)
    if st.button("↻ Refresh", key="main_refresh", use_container_width=True):
        st.session_state.pop("pitches", None)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("<div style='margin-bottom:1.4rem;'></div>", unsafe_allow_html=True)

pitches = [p for p in st.session_state.pitches if p.get("category") in selected_cats]
if st.session_state.get("intl_only"):
    pitches = [p for p in pitches if p.get("international_cut")]

cut_pitches  = [p for p in pitches if p.get("international_cut")]
rest_pitches = [p for p in pitches if not p.get("international_cut")]

if not pitches:
    st.markdown('<div style="color:#444;padding:3rem 0;">No pitches match the selected filters.</div>', unsafe_allow_html=True)


def render_pitch(pitch, idx):
    cat = pitch.get("category", "Society")
    color = CATEGORY_COLORS.get(cat, "#888")
    intl_cut = pitch.get("international_cut", False)
    intl_reason = pitch.get("international_reason", "")
    headline_raw = pitch.get("headline", pitch.get("title", ""))
    display_headline = headline_raw
    for c in CATEGORIES:
        display_headline = display_headline.replace(f"[{c}] ", "").replace(f"[{c}]", "")

    link = pitch.get("link", "#")
    sig = pitch.get("significance", "")
    zh = pitch.get("zh_summary", "")
    source = pitch.get("source", "")
    ts = pitch.get("timestamp", "")
    formatted_text = pitch.get("formatted", "")

    card_border = "#FFD700" if intl_cut else "#242424"
    card_bg = "#161400" if intl_cut else "#141414"
    intl_badge = '<span style="background:#FFD70022;color:#FFD700;font-size:0.62rem;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;padding:3px 10px;border-radius:20px;margin-left:0.5rem;">⭐ International Cut</span>' if intl_cut else ""
    intl_reason_html = f'<div style="font-size:0.8rem;color:#FFD700;opacity:0.85;margin-bottom:0.8rem;font-style:italic;">✦ {intl_reason}</div>' if intl_cut and intl_reason else ""

    st.markdown(f"""
    <div class="pitch-card" style="background:{card_bg};border-color:{card_border};">
      <span class="pitch-cat" style="background:{color}22;color:{color};">{cat}</span>{intl_badge}
      <div class="pitch-headline" style="margin-top:0.6rem;">
        <a href="{link}" target="_blank">{display_headline}</a>
      </div>
      {intl_reason_html}
      <div class="pitch-sig-label">Significance</div>
      <div class="pitch-sig">{sig}</div>
      <div class="pitch-zh">🀄 {zh}</div>
      <div class="pitch-meta">{source} · {ts}</div>
    </div>
    """, unsafe_allow_html=True)
    copy_button(formatted_text, key=f"copy_{idx}_{cat}")

    jerry_today   = pitch.get("jerry_today", "")
    jerry_feature = pitch.get("jerry_feature", "")
    if jerry_today or jerry_feature:
        with st.expander("💡 Jerry says: How to develop this story"):
            if jerry_today:
                st.markdown(f"""
                <div style='background:#0F0F0F;border:1px solid #1E2E1E;border-radius:8px;
                padding:1rem 1.2rem;margin-bottom:0.8rem;'>
                  <div style='font-size:0.62rem;font-weight:700;letter-spacing:0.18em;
                  text-transform:uppercase;color:#4CAF50;margin-bottom:0.5rem;'>
                  ⚡ Today — What you can do right now
                  </div>
                  <p style='color:#C0C0C0;font-size:0.88rem;line-height:1.75;
                  margin:0;'>{jerry_today}</p>
                </div>
                """, unsafe_allow_html=True)
            if jerry_feature:
                st.markdown(f"""
                <div style='background:#0F0F0F;border:1px solid #1E1A2E;border-radius:8px;
                padding:1rem 1.2rem;'>
                  <div style='font-size:0.62rem;font-weight:700;letter-spacing:0.18em;
                  text-transform:uppercase;color:#A78BFA;margin-bottom:0.5rem;'>
                  🔭 Long-term — Feature story to pursue
                  </div>
                  <p style='color:#C0C0C0;font-size:0.88rem;line-height:1.75;
                  margin:0;'>{jerry_feature}</p>
                </div>
                """, unsafe_allow_html=True)
    st.markdown("")


# ── Pinned: International Cuts ────────────────────────────────────────────────
if cut_pitches:
    st.markdown("""
    <div style='font-size:0.65rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
    color:#FFD700;padding:0.2rem 0 0.8rem 0;'>⭐ International Cuts</div>
    """, unsafe_allow_html=True)
    for i, pitch in enumerate(cut_pitches):
        render_pitch(pitch, f"cut_{i}")

# ── Divider between sections ──────────────────────────────────────────────────
if cut_pitches and rest_pitches:
    st.markdown("""
    <div style='display:flex;align-items:center;gap:1rem;margin:1.2rem 0 1.6rem 0;'>
      <div style='flex:1;height:1px;background:#1E1E1E;'></div>
      <div style='font-size:0.62rem;letter-spacing:0.18em;text-transform:uppercase;color:#333;
      white-space:nowrap;'>Other Stories</div>
      <div style='flex:1;height:1px;background:#1E1E1E;'></div>
    </div>
    """, unsafe_allow_html=True)

# ── Rest of stories ───────────────────────────────────────────────────────────
for i, pitch in enumerate(rest_pitches):
    render_pitch(pitch, f"rest_{i}")
