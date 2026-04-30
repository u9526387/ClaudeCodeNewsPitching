import ollama
from datetime import date

OLLAMA_HOST = "http://localhost:11434"
MODEL = "llama3.1"
APP_NAME = "lovepitchingpolar"

CATEGORIES = ["Politics", "Diplomacy", "Security", "Human Rights", "Society", "Economy"]

# Fingerprints of few-shot example content — used to detect echo contamination
_EXAMPLE_FINGERPRINTS = [
    "tug-of-war over where tsmc builds",
    "台積電宣布亞利桑那新廠延期",
    "back-channel relationships is a bellwether",
    "台灣外交部長赴布魯塞爾",
    "compressing the timeline for a potential conflict",
    "中國人民解放軍在台灣海峽附近舉行實彈演習",
]

# Tone reference — shown as a system message, not in the user turn
_SYSTEM_TONE = """You are a senior producer at Story, an international English-language broadcaster based in Taiwan.

Here are three examples of the TONE and FORMAT you must follow. These are only tone references — do NOT copy or repeat them in your output under any circumstances:

[TONE EXAMPLE 1 — Diplomacy]
Significance: As China ramps up economic coercion against nations that engage with Taiwan, this meeting signals that democratic allies are quietly building a parallel diplomatic network — one Beijing cannot easily sanction or block.
Traditional Chinese Summary: 台灣外交部長赴布魯塞爾與歐盟官員會面，雙方就抵禦中國貿易施壓的韌性策略進行深入討論。

[TONE EXAMPLE 2 — Security]
Significance: Beijing's increasingly frequent military exercises around Taiwan are no longer just political theater — analysts say the drills are rehearsals compressing the timeline for a conflict that would disrupt $5 trillion in annual global shipping.
Traditional Chinese Summary: 中國人民解放軍在台灣海峽附近舉行實彈演習，引發國際社會高度關注。

[TONE EXAMPLE 3 — Economy]
Significance: The question of where cutting-edge chips are manufactured is no longer just a business decision — it is a test of whether the global tech supply chain can survive without Taiwan at its centre.
Traditional Chinese Summary: 全球科技供應鏈的未來，繫於台灣能否守住半導體製造的核心地位。

END OF TONE EXAMPLES. Everything below is a NEW story that has nothing to do with the examples above."""


def _chat(title: str, summary: str, prompt_body: str) -> str:
    """Two-turn chat: system sets tone context, user presents the actual story task."""
    client = ollama.Client(host=OLLAMA_HOST)
    response = client.chat(
        model=MODEL,
        messages=[
            {"role": "user",      "content": _SYSTEM_TONE},
            {"role": "assistant", "content": "Understood. I will use those only as tone references and generate completely original output for the new story you provide."},
            {"role": "user",      "content": f"{prompt_body}\n\nSource headline: {title}\nSource summary: {summary}"},
        ],
        options={"temperature": 0.4},
    )
    return response["message"]["content"].strip()


def _is_contaminated(text: str) -> bool:
    """Return True if the output appears to echo few-shot example content."""
    t = text.lower()
    return any(fp in t for fp in _EXAMPLE_FINGERPRINTS)


def process_single_story(title: str, summary: str) -> dict:
    """Single Ollama call: classify + format pitch in one shot."""
    today = date.today().strftime("%B %d, %Y")
    cats = ", ".join(CATEGORIES)
    prompt = f"""Process the story provided at the end of this message. Generate COMPLETELY ORIGINAL content based ONLY on that story — do not reference or copy the tone examples you were shown.

Follow the format EXACTLY — no extra text before or after:

Category: <one of: {cats}>

[Category] <punchy rewritten headline>

Significance: <2–3 sentences on why the world should care — specific global consequences>

Traditional Chinese Summary: <exactly ONE sentence in Traditional Chinese (繁體中文)>

International Cut: <YES or NO. Be very strict — only YES if ALL three apply: (1) a non-Taiwan audience would genuinely care without needing background context, (2) it has clear consequences beyond Taiwan's borders — geopolitical, economic, or security implications for other countries, (3) BBC World, CNN International, or Reuters would plausibly run this as a standalone story today. Local politics, domestic policy, and government routine do NOT qualify. Most stories should be NO.>

International Reason: <if YES, exactly one sentence explaining the specific cross-border consequence that makes this globally relevant; if NO, leave blank>

Jerry today: <You are Jerry, a veteran TV field reporter in Taiwan with 20 years of experience. A junior reporter has ONE DAY to add depth to THIS specific story. Give exactly 3 bullet points. Each bullet must follow this structure: "• [Who/What to do] — [Why this helps] → [Expected result]". Be ruthlessly realistic: never suggest calling presidents, ministers, or heads of state — they never pick up. Instead suggest: ministry spokespeople, academic researchers, industry association reps, factory floor workers, NGO staff, affected residents, local business owners, or documents/data available online. Each suggestion must be traceable to a specific detail in this story. Output as plain bullet points only, no headers.>

Jerry feature: <Still as Jerry. Suggest exactly 3 bullet points for a longer investigative or feature story that could grow from this. Each bullet must follow this structure: "• [Specific angle or story spine] — [Why it matters to a Taiwanese or international audience] → [What the reporter would need to do to pursue it]". Think about: which specific industry, neighbourhood, or community in Taiwan is quietly being shaped by the forces in this story; what structural trend, policy gap, or human cost it reveals; and what narrative device would make it compelling (follow one worker, one company, one bill, one neighbourhood). Be specific to this story's facts. Output as plain bullet points only, no headers.>"""

    raw = _chat(title, summary, prompt)

    # Retry once if output appears to echo example content rather than this story
    if _is_contaminated(raw):
        print(f"  [retry] Contaminated output detected for: {title[:50]}")
        raw = _chat(title, summary, prompt)

    lines = [l.strip() for l in raw.strip().splitlines()]

    category = "Society"
    headline = ""
    significance = ""
    zh_summary = ""
    international_cut = False
    international_reason = ""

    # Multi-line field collector
    current_field = None
    field_buffers = {
        "jerry_today": [],
        "jerry_feature": [],
    }

    FIELD_MARKERS = {
        "Significance:":                  "significance_inline",
        "Traditional Chinese Summary:":   "zh_inline",
        "International Cut:":             "intl_cut_inline",
        "International Reason:":          "intl_reason_inline",
        "Jerry today:":                   "jerry_today",
        "Jerry feature:":                 "jerry_feature",
    }

    for i, line in enumerate(lines):
        # Category and headline are single-line, handle first
        if line.startswith("Category:"):
            current_field = None
            cat_raw = line.replace("Category:", "").strip().strip("[]")
            for cat in CATEGORIES:
                if cat.lower() in cat_raw.lower():
                    category = cat
                    break
        elif any(line.startswith(f"[{c}]") for c in CATEGORIES):
            current_field = None
            matched = next(c for c in CATEGORIES if line.startswith(f"[{c}]"))
            if len(line) > len(f"[{matched}]") + 2:
                headline = line
                category = matched
            elif i + 1 < len(lines) and lines[i + 1]:
                headline = f"[{matched}] {lines[i + 1]}"
                category = matched
        else:
            # Check if this line starts a known field
            matched_marker = None
            for marker, field_key in FIELD_MARKERS.items():
                if line.startswith(marker):
                    matched_marker = (marker, field_key)
                    break

            if matched_marker:
                marker, field_key = matched_marker
                rest = line[len(marker):].strip()
                current_field = field_key
                if field_key == "significance_inline":
                    current_field = None
                    significance = rest
                elif field_key == "zh_inline":
                    current_field = None
                    zh_summary = rest
                elif field_key == "intl_cut_inline":
                    current_field = None
                    international_cut = "yes" in rest.lower()
                elif field_key == "intl_reason_inline":
                    current_field = None
                    international_reason = rest
                elif field_key in field_buffers:
                    if rest:
                        field_buffers[field_key].append(rest)
            elif current_field and current_field in field_buffers and line:
                field_buffers[current_field].append(line)

    jerry_today   = " ".join(field_buffers["jerry_today"]).strip()
    jerry_feature = " ".join(field_buffers["jerry_feature"]).strip()

    return {
        "category":           category,
        "headline":           headline or f"[{category}] {title}",
        "significance":       significance,
        "zh_summary":         zh_summary,
        "international_cut":  international_cut,
        "international_reason": international_reason,
        "jerry_today":        jerry_today,
        "jerry_feature":      jerry_feature,
        "formatted": (
            f"Story  {today}\n\n"
            f"{headline or f'[{category}] {title}'}\n\n"
            f"Significance: {significance}\n\n"
            f"Traditional Chinese Summary: {zh_summary}"
        ),
    }


def process_stories(stories) -> list:
    enriched = []
    for story in stories:
        print(f"  Processing: {story['title'][:60]}...")
        pitch = process_single_story(story["title"], story["summary"])
        enriched.append({**story, **pitch})
    return enriched


if __name__ == "__main__":
    # Test with a hardcoded headline representative of real feed content
    test_story = {
        "title": "China's PLA conducts large-scale military drills near Taiwan Strait amid rising tensions",
        "summary": (
            "The People's Liberation Army launched its largest naval and air exercise of the year "
            "near the Taiwan Strait on Wednesday, deploying destroyer fleets and long-range bombers "
            "in what analysts describe as a simulated blockade scenario targeting Taiwan's key ports."
        ),
        "source": "Focus Taiwan",
        "timestamp": "2026-04-30 08:00 UTC",
        "link": "https://focustaiwan.tw/cross-strait/test",
    }

    print(f"[{APP_NAME}] Testing AI engine with sample story...\n")
    print(f"Source: {test_story['title']}\n")
    print("--- Classifying ---")
    category = classify_story(test_story["title"], test_story["summary"])
    print(f"Category: [{category}]\n")

    print("--- Formatting Pitch ---")
    pitch = format_pitch(test_story["title"], test_story["summary"], category)

    print("\n" + "=" * 60)
    print(pitch["formatted"])
    print("=" * 60)
