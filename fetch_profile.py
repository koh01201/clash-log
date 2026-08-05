"""
プレイヤー情報の記録
--------------------
公式APIの /players/{tag} を取得し、レート（伝説の道の成績）や通算成績を
profile.csv に追記する。値が前回から変わったときだけ1行増える。

    python fetch_profile.py

バトルログにはレートが入っていないため、シーズンの最終レートや自己ベストは
こちらから取る。過去に遡ることはできないので、記録は今日以降のぶんが貯まる。
"""

import csv
import datetime
import json
import os
import sys
import urllib.parse

import requests

PLAYER_TAG = "#LQQQQPUL0"          # collect_battles.py と同じタグ

BASE_URL = "https://proxy.royaleapi.dev/v1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.txt")
OUT_FILE = os.path.join(SCRIPT_DIR, "profile.csv")
JST = datetime.timezone(datetime.timedelta(hours=9))

FIELDS = [
    "checked_jst",
    "trophies", "best_trophies",
    "wins", "losses", "battle_count",
    "pol_current_league", "pol_current_trophies", "pol_current_rank",
    "pol_last_league", "pol_last_trophies", "pol_last_rank",
    "pol_best_league", "pol_best_trophies", "pol_best_rank",
    "pol_raw",
]
# 比較に使う列（時刻以外）
COMPARE = FIELDS[1:]


def load_token():
    token = os.environ.get("CR_TOKEN", "").strip()
    if token:
        return token
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("トークンが見つかりません（CR_TOKEN も token.txt も無し）")
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return f.read().strip()


def pick(data, key, field):
    block = data.get(key) or {}
    if not isinstance(block, dict):
        return ""
    v = block.get(field)
    return "" if v is None else v


def fetch(token):
    url = f"{BASE_URL}/players/{urllib.parse.quote(PLAYER_TAG)}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code == 403:
        raise RuntimeError("403エラー。トークンかIP登録を確認。")
    if r.status_code == 404:
        raise RuntimeError(f"404エラー。タグ {PLAYER_TAG} が見つかりません。")
    r.raise_for_status()
    return r.json()


def build_row(d):
    row = {
        "checked_jst": datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
        "trophies": d.get("trophies", ""),
        "best_trophies": d.get("bestTrophies", ""),
        "wins": d.get("wins", ""),
        "losses": d.get("losses", ""),
        "battle_count": d.get("battleCount", ""),
    }
    for tag, key in (("current", "currentPathOfLegendSeasonResult"),
                     ("last", "lastPathOfLegendSeasonResult"),
                     ("best", "bestPathOfLegendSeasonResult")):
        row[f"pol_{tag}_league"] = pick(d, key, "leagueNumber")
        row[f"pol_{tag}_trophies"] = pick(d, key, "trophies")
        row[f"pol_{tag}_rank"] = pick(d, key, "rank")

    # 実際にどんな項目が返っているかを残す（達成日などが含まれるか確認するため）
    raw = {k: d.get(k) for k in
           ("currentPathOfLegendSeasonResult", "lastPathOfLegendSeasonResult",
            "bestPathOfLegendSeasonResult") if d.get(k)}
    row["pol_raw"] = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    return row


def last_row():
    if not os.path.exists(OUT_FILE):
        return None
    with open(OUT_FILE, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[-1] if rows else None


def main():
    token = load_token()
    row = build_row(fetch(token))

    prev = last_row()
    if prev and all(str(prev.get(k, "")) == str(row.get(k, "")) for k in COMPARE):
        print("profile.csv に変化なし。追記しない。")
        return

    is_new = not os.path.exists(OUT_FILE)
    with open(OUT_FILE, "a", encoding="utf-8-sig" if is_new else "utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            w.writeheader()
        w.writerow(row)

    print("profile.csv に追記しました "
          f"（現在レート {row['pol_current_trophies']} / 自己ベスト {row['pol_best_trophies']}）")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"エラー: {error}")
        sys.exit(1)
