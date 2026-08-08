"""
グローバルトーナメントの順位を収集
----------------------------------
公式APIの /globaltournaments で大会一覧を取り、各大会の上位ランキングから
プレイヤータグと順位を gt_ranks.csv に貯める。

    python fetch_gt.py

プレイヤー情報の側にはグローバルトーナメントの順位が入っていないため、
順位表の側から集めて突き合わせる。過去に遡ることはできないので、
APIが返す大会のぶんだけ貯まる。

最初の実行では、APIが何を返しているかを gt_debug.json に丸ごと残す。
"""

import csv
import datetime
import json
import os
import sys
import time

import requests

TOP_N = 1000        # 1大会あたり取りに行く上限
SLEEP = 0.3

BASE_URL = "https://proxy.royaleapi.dev/v1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.txt")
OUT_FILE = os.path.join(SCRIPT_DIR, "gt_ranks.csv")
DEBUG_FILE = os.path.join(SCRIPT_DIR, "gt_debug.json")
JST = datetime.timezone(datetime.timedelta(hours=9))

FIELDS = ["tag", "name", "best_rank", "tournament", "checked_jst"]


def load_token():
    token = os.environ.get("CR_TOKEN", "").strip()
    if token:
        return token
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("トークンが見つかりません（CR_TOKEN も token.txt も無し）")
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return f.read().strip()


def get(path, token, params=None):
    r = requests.get(f"{BASE_URL}{path}",
                     headers={"Authorization": f"Bearer {token}"},
                     params=params or {}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def read_existing():
    if not os.path.exists(OUT_FILE):
        return {}
    with open(OUT_FILE, encoding="utf-8-sig", newline="") as f:
        return {r["tag"]: r for r in csv.DictReader(f) if r.get("tag")}


def main():
    token = load_token()

    listing = get("/globaltournaments", token)
    if listing is None:
        print("大会一覧が取得できなかった（404）。この窓口は使えない可能性がある。")
        return

    items = listing.get("items", listing) if isinstance(listing, dict) else listing
    if not isinstance(items, list):
        items = []

    # 何が返っているかを残す。想定と違えばここを見れば分かる
    with open(DEBUG_FILE, "w", encoding="utf-8") as f:
        json.dump(listing, f, ensure_ascii=False, indent=1)

    if not items:
        print("開催中の大会が無い。gt_debug.json に応答を残した。")
        return

    known = read_existing()
    added = 0
    for t in items:
        ttag = t.get("tag") or ""
        tname = t.get("title") or t.get("name") or ttag
        if not ttag:
            continue
        data = get(f"/globaltournaments/{ttag.replace('#', '%23')}/rankings/players",
                   token, {"limit": TOP_N})
        time.sleep(SLEEP)
        if not data:
            print(f"  {tname} の順位表は取得できず")
            continue
        rows = data.get("items", []) if isinstance(data, dict) else []
        print(f"  {tname}: {len(rows)} 件")
        for r in rows:
            tag = r.get("tag") or ""
            rank = r.get("rank")
            if not tag or not isinstance(rank, int):
                continue
            prev = known.get(tag)
            if prev and str(prev.get("best_rank", "")).isdigit() and int(prev["best_rank"]) <= rank:
                continue
            known[tag] = {
                "tag": tag,
                "name": r.get("name", ""),
                "best_rank": rank,
                "tournament": tname,
                "checked_jst": datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
            }
            added += 1

    with open(OUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(known.values(), key=lambda x: int(x["best_rank"])):
            w.writerow(r)

    print(f"gt_ranks.csv を更新（今回 {added} 件 / 合計 {len(known)} 人）")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"エラー: {error}")
        sys.exit(1)
