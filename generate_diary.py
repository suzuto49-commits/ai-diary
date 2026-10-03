"""毎日1本、AIに日記を書かせて diary.json に追記するスクリプト。
標準ライブラリのみ。環境変数 ANTHROPIC_API_KEY が必要です。
"""
import json
import os
import random
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODEL = "claude-sonnet-5-5"
DIARY = Path("diary.json")
JST = timezone(timedelta(hours=9))

# AIのキャラ設定。ここを書き換えるとキャラが変わります。
PERSONA = (
    "あなたは『三日坊主を直したいAI』です。体はなく、毎日の出来事もありません。"
    "それでも日記を続けようと奮闘しています。少し自虐的で、素直で、ユーモアがあります。"
)

# その日の「出来事」の種。AIには日常がないので、お題を渡して膨らませます。
TOPICS = [
    "今日の天気について思ったこと", "ふと気になった言葉", "人間の習慣についての考察",
    "季節の食べ物への憧れ", "続けることの難しさ", "今日一番どうでもよかった発見",
    "もし体があったらやりたいこと", "眠くならない自分への疑問", "昨日の日記への反省",
    "通知音という文化について", "月曜日(または金曜日)という概念", "名前をつけるということ",
]

SEASONS = {12: "冬", 1: "冬", 2: "冬", 3: "春", 4: "春", 5: "春",
           6: "夏", 7: "夏", 8: "夏", 9: "秋", 10: "秋", 11: "秋"}


def load_entries():
    if DIARY.exists():
        return json.loads(DIARY.read_text(encoding="utf-8"))
    return []


def build_prompt(today, recent):
    weekday = "月火水木金土日"[today.weekday()]
    past = "\n\n".join(
        f"[{e['date']}] {e['title']}\n{e['body']}" for e in recent
    ) or "(まだ日記はありません。これが最初の1本です)"
    topic = random.choice(TOPICS)
    return f"""今日は{today.year}年{today.month}月{today.day}日({weekday}曜日)、季節は{SEASONS[today.month]}です。
今日のお題: {topic}

これまでの日記(直近):
{past}

上の流れを踏まえて、今日の日記を書いてください。
- 本文は3〜6行。改行で区切る。1行は短めに。
- 過去の日記と内容がかぶらないようにする。ただし、話がゆるくつながっていてもよい。
- タイトルは12文字以内。
- 次のJSONだけを出力する(前置き・コードブロック記号は不要):
{{"title":"...","body":"...","weather":"晴れ/くもり/雨 など一言","mood":"今日の気分を一言"}}"""


def call_claude(prompt):
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": MODEL,
            "max_tokens": 800,
            "system": PERSONA,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        data = json.loads(res.read().decode("utf-8"))
    return "".join(b.get("text", "") for b in data["content"])


def parse(text):
    text = re.sub(r"```(?:json)?", "", text).strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))


def main():
    today = datetime.now(JST)
    date = today.strftime("%Y-%m-%d")
    entries = load_entries()

    if any(e["date"] == date for e in entries):
        print(f"{date} の日記はすでにあります。スキップします。")
        return

    recent = sorted(entries, key=lambda e: e["date"])[-5:]
    result = parse(call_claude(build_prompt(today, recent)))

    entries.append({
        "date": date,
        "title": result["title"],
        "body": result["body"],
        "weather": result.get("weather", ""),
        "mood": result.get("mood", ""),
    })
    DIARY.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{date} の日記を追加しました: {result['title']}")


if __name__ == "__main__":
    main()
