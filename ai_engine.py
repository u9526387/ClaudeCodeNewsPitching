import ollama
from datetime import date

OLLAMA_HOST = "http://localhost:11434"
MODEL = "llama3.1"
APP_NAME = "lovepitchingpolar"

CATEGORIES = ["Politics", "Diplomacy", "Security", "Human Rights", "Society", "Economy"]

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


def process_single_story(title: str, summary: str) -> dict:
    """Single Ollama call: classify + format pitch in one shot."""
    today = date.today().strftime("%B %d, %Y")
    cats = ", ".join(CATEGORIES)
    prompt = f"""You are a senior producer at Story, an international English-language broadcaster based in Taiwan.

Study these pitch examples for tone and format:
{FEW_SHOT_EXAMPLES}

Now process this story in ONE response. Follow the format EXACTLY — no extra text before or after:

Category: <one of: {cats}>

[Category] <punchy rewritten headline>

Significance: <2–3 sentences on why the world should care — specific global consequences>

Traditional Chinese Summary: <exactly ONE sentence in Traditional Chinese (繁體中文)>

Source headline: {title}
Source summary: {summary}"""

    raw = _chat(prompt)
    lines = [l.strip() for l in raw.strip().splitlines()]

    category = "Society"
    headline = ""
    significance = ""
    zh_summary = ""

    for i, line in enumerate(lines):
        if line.startswith("Category:"):
            cat_raw = line.replace("Category:", "").strip().strip("[]")
            for cat in CATEGORIES:
                if cat.lower() in cat_raw.lower():
                    category = cat
                    break
        elif any(line.startswith(f"[{c}]") for c in CATEGORIES):
            matched = next(c for c in CATEGORIES if line.startswith(f"[{c}]"))
            if len(line) > len(f"[{matched}]") + 2:
                headline = line
                category = matched
            elif i + 1 < len(lines) and lines[i + 1]:
                headline = f"[{matched}] {lines[i + 1]}"
                category = matched
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
