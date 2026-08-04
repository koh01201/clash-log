"""
カード一覧の取得
----------------
公式APIの /cards からカード名とアイコン画像のURLの対応表を作り、
cards.json として保存する。

    python fetch_cards.py

画像そのものは保存しない。公式のURLを記録するだけ。
一度取れば当分変わらないので、7日以内に取得済みなら何もしない。
"""

import datetime
import json
import os
import sys

import requests

BASE_URL = "https://proxy.royaleapi.dev/v1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.txt")
OUT_FILE = os.path.join(SCRIPT_DIR, "cards.json")
MAX_AGE_DAYS = 7


def load_token():
    token = os.environ.get("CR_TOKEN", "").strip()
    if token:
        return token
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("トークンが見つかりません（CR_TOKEN も token.txt も無し）")
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return f.read().strip()


def is_fresh():
    """7日以内に取得済みなら True。"""
    if not os.path.exists(OUT_FILE):
        return False
    try:
        with open(OUT_FILE, encoding="utf-8") as f:
            data = json.load(f)
        fetched = datetime.datetime.fromisoformat(data.get("fetched", ""))
    except Exception:
        return False
    age = datetime.datetime.now(datetime.timezone.utc) - fetched
    return age < datetime.timedelta(days=MAX_AGE_DAYS) and data.get("cards")


def main():
    if is_fresh():
        print("cards.json は最新（7日以内に取得済み）。何もしない。")
        return

    token = load_token()
    response = requests.get(
        f"{BASE_URL}/cards",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if response.status_code == 403:
        raise RuntimeError("403エラー。トークンかIP登録を確認。")
    response.raise_for_status()
    payload = response.json()

    cards = {}
    # items にカード、supportItems にタワートループが入る
    for group in ("items", "supportItems"):
        for card in payload.get(group, []) or []:
            name = card.get("name")
            icons = card.get("iconUrls") or {}
            url = icons.get("medium") or icons.get("evolutionMedium")
            if name and url:
                cards[name] = url

    if not cards:
        raise RuntimeError("カードが1枚も取得できなかった。応答の形式を確認。")

    data = {
        "fetched": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cards": cards,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"cards.json を書き出しました（{len(cards)} 枚）")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"エラー: {error}")
        sys.exit(1)
