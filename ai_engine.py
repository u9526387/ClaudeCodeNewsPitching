import ollama
from datetime import date

OLLAMA_HOST = "http://localhost:11434"
MODEL = "llama3.1"
APP_NAME = "lovepitchingpolar"

CATEGORIES = ["Diplomacy", "Security", "Human Rights", "Society", "Economy"]

# Few-shot examples to anchor tone and style
FEW_SHOT_EXAMPLES = """
Example 1:
Story: Taiwan's foreign minister meets EU counterparts in Brussels to discuss trade resilience amid China pressure.
Category: [Diplomacy]
Significance: As China ramps up economic coercion against nations that engage with Taiwan, this meeting signals that democratic allies are quietly building a parallel diplomatic network — one that Beijing cannot easily sanction or block. For global trade partners, Taiwan's ability to maintain these back-channel relationships is a bellwether for how the rules-based order holds up under pressure.
Traditional Chinese Summary: 台灣外交部長赴布魯塞爾與歐盟官員會面，雙方就抵禦中國貿易施壓的韌性策略進行深入討論。

Example 2:
Story: PLA conducts live-fire drills near the Taiwan Strait, deploying destroyer fleet in simulated blockade exercise.
Category: [Security]
Significance: Beijing's increasingly frequent and sophisticated military exercises around Taiwan are no longer just political theater — defence analysts say the drills are rehearsals, compressing the timeline for a potential conflict that would disrupt $5 trillion in annual global shipping and trigger a semiconductor supply crisis worldwide.
Traditional Chinese Summary: 中國人民解放軍在台灣海峽附近舉行實彈演習，以驅逐艦艦隊模擬封鎖行動，引發國際社會高度關注。

Example 3:
Story: TSMC announces new Arizona fab delay as Taiwan government urges the company to keep advanced nodes onshore.
Category: [Economy]
Significance: The tug-of-war over where TSMC builds its most advanced chips cuts to the heart of a global debate: can the world de-risk its semiconductor supply chain without hollowing out the very island that produces 90% of the most cutting-edge chips? Taiwan's answer — and America's response — will shape the tech industry for a generation.
Traditional Chinese Summary: 台積電宣布亞利桑那新廠延期，台灣政府同時呼籲公司將最先進製程留在台灣本土生產。
"""


def _chat(prompt: str) -> str:
    client = ollama.Client(host=OLLAMA_HOST)
    response = client.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.3},
    )
    return response["message"]["content"].strip()


def classify_story(title: str, summary: str) -> str:
    prompt = f"""You are a news editor for Story, an international English-language broadcaster.
Classify the story below into exactly ONE of these categories: {', '.join(CATEGORIES)}.

Reply with ONLY the category name — no brackets, no explanation.

Story title: {title}
Story summary: {summary}

Category:"""
    result = _chat(prompt).strip("[]").strip()
    # Validate; fall back to closest match
    for cat in CATEGORIES:
        if cat.lower() in result.lower():
            return cat
    return "Society"


def format_pitch(title: str, summary: str, category: str) -> dict:
    today = date.today().strftime("%B %d, %Y")
    prompt = f"""You are a senior producer at Story, an international English-language broadcaster based in Taiwan.
Your job is to write compelling story pitches for a global audience.

Study these examples of the exact tone and format required:
{FEW_SHOT_EXAMPLES}

Now write a pitch for the following story. Follow the format EXACTLY:

Line 1: [{category}] <the story headline, rewritten to be punchy and clear>
Line 2: (blank)
Line 3: Significance: <2–3 sentences explaining WHY THE WORLD should care about Taiwan in this context. Be specific about global consequences — trade, security, democracy. Do NOT be vague.>
Line 4: (blank)
Line 5: Traditional Chinese Summary: <exactly ONE sentence in Traditional Chinese (繁體中文) that summarizes the story>

Source headline: {title}
Source summary: {summary}

Do not add any commentary before or after the formatted pitch. Output only the pitch."""

    raw = _chat(prompt)

    lines = [l.strip() for l in raw.strip().splitlines()]

    headline = ""
    significance = ""
    zh_summary = ""

    for i, line in enumerate(lines):
        if line.startswith(f"[{category}]"):
            # Model sometimes puts category alone, headline on next line
            if len(line.strip()) > len(f"[{category}]") + 2:
                headline = line
            elif i + 1 < len(lines) and lines[i + 1]:
                headline = f"[{category}] {lines[i + 1]}"
            else:
                headline = line
        elif line.startswith("Significance:"):
            significance = line.replace("Significance:", "").strip()
        elif line.startswith("Traditional Chinese Summary:"):
            zh_summary = line.replace("Traditional Chinese Summary:", "").strip()

    return {
        "category": category,
        "headline": headline or f"[{category}] {title}",
        "significance": significance,
        "zh_summary": zh_summary,
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
        category = classify_story(story["title"], story["summary"])
        pitch = format_pitch(story["title"], story["summary"], category)
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
