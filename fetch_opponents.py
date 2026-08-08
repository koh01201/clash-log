"""
対戦相手の情報を収集
--------------------
battles.csv に出てくる相手のタグをもとに、公式APIの /players/{tag} を引き、
名前・レート戦の過去最高順位・グローバルトーナメントの最高順位を
opponents.csv に貯める。

    python fetch_opponents.py

一度取った相手は再取得しない（RECHECK_DAYS 日を過ぎたものだけ取り直す）。
1回の実行で取りに行く人数は MAX_PER_RUN 件までに抑える。
"""

import csv
import datetime
import json
import os
import sys
import time
import urllib.parse

import requests

MAX_PER_RUN = 40          # 1回の実行で問い合わせる人数の上限
RECHECK_DAYS = 30         # 既知の相手を取り直す間隔
SLEEP = 0.25              # 連続アクセスの間隔（秒）

BASE_URL = "https://proxy.royaleapi.dev/v1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.txt")
BATTLES_FILE = os.path.join(SCRIPT_DIR, "battles.csv")
OUT_FILE = os.path.join(SCRIPT_DIR, "opponents.csv")
JST = datetime.timezone(datetime.timedelta(hours=9))

SCHEMA = "6"     # 判定方法を変えたら上げる。古い行は取り直す

FIELDS = [
    "ver", "tag", "name", "checked_jst",
    "pol_best_rank", "pol_best_trophies", "pol_best_league",
    "gt_best_rank", "gt_badge",
    "ladder_best_rank", "ladder_best_trophies", "ladder_best_season",
    "ladder_prev_rank", "league_raw",
    "exp_level", "trophies", "best_trophies",
    "battle_count", "wins", "losses",
]


def load_token():
    token = os.environ.get("CR_TOKEN", "").strip()
    if token:
        return token
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("トークンが見つかりません（CR_TOKEN も token.txt も無し）")
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return f.read().strip()


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def opponent_tags():
    """battles.csv に出てくる相手タグを、新しい試合の順に並べて返す。"""
    rows = read_csv(BATTLES_FILE)
    rows.sort(key=lambda r: r.get("battle_time_utc", ""), reverse=True)
    seen, out = set(), []
    for r in rows:
        tag = (r.get("opp_tag") or "").strip()
        if not tag:
            key = r.get("battle_key", "")
            tag = key.split("_", 1)[1] if "_" in key else ""
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


def is_fresh(row):
    if str(row.get("ver", "")) != SCHEMA:
        return False
    try:
        d = datetime.datetime.strptime(row.get("checked_jst", "")[:10], "%Y-%m-%d")
    except ValueError:
        return False
    return (datetime.datetime.now() - d).days < RECHECK_DAYS


def pick(d, key, field):
    b = d.get(key) or {}
    v = b.get(field) if isinstance(b, dict) else None
    return "" if v is None else v


def best_tournament(badges):
    """グローバルトーナメントの最高順位。バッジ名を正規化して照合する。"""
    best, name = "", ""
    for b in badges or []:
        norm = "".join(ch for ch in str(b.get("name", "")).lower() if ch.isalnum())
        if "globaltournament" not in norm:
            continue
        p = b.get("progress")
        if isinstance(p, int) and (best == "" or p < best):
            best, name = p, str(b.get("name", ""))
    return best, name


def ladder_ranks(d):
    """Top Ladder（旧トロフィーランキング）の成績。
    バッジではなく leagueStatistics に入っている。"""
    ls = d.get("leagueStatistics") or {}
    if not isinstance(ls, dict):
        return "", "", "", "", ""
    best = ls.get("bestSeason") or {}
    prev = ls.get("previousSeason") or {}

    def g(block, key):
        v = block.get(key) if isinstance(block, dict) else None
        return "" if v is None else v

    return (g(best, "rank"), g(best, "trophies"), g(best, "id"),
            g(prev, "rank"), json.dumps(ls, ensure_ascii=False))


def fetch(tag, token):
    url = f"{BASE_URL}/players/{urllib.parse.quote(tag)}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def main():
    tags = opponent_tags()
    known = {r["tag"]: r for r in read_csv(OUT_FILE) if r.get("tag")}
    todo = [t for t in tags if t not in known or not is_fresh(known[t])][:MAX_PER_RUN]

    if not todo:
        print(f"新しい相手はいない（登録済み {len(known)} 人 / 出現 {len(tags)} 人）")
        return

    token = load_token()
    added = 0
    for tag in todo:
        try:
            d = fetch(tag, token)
        except Exception as error:
            print(f"  {tag} は取得できず: {error}")
            continue
        time.sleep(SLEEP)
        if not d:
            continue
        gt_rank, gt_name = best_tournament(d.get("badges"))
        ld_rank, ld_tro, ld_season, ld_prev, ls_raw = ladder_ranks(d)
        known[tag] = {
            "ver": SCHEMA,
            "tag": tag,
            "name": d.get("name", ""),
            "checked_jst": datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
            "pol_best_rank": pick(d, "bestPathOfLegendSeasonResult", "rank"),
            "pol_best_trophies": pick(d, "bestPathOfLegendSeasonResult", "trophies"),
            "pol_best_league": pick(d, "bestPathOfLegendSeasonResult", "leagueNumber"),
            "gt_best_rank": gt_rank,
            "gt_badge": gt_name,
            "ladder_best_rank": ld_rank,
            "ladder_best_trophies": ld_tro,
            "ladder_best_season": ld_season,
            "ladder_prev_rank": ld_prev,
            "league_raw": ls_raw,
            "exp_level": d.get("expLevel", ""),
            "trophies": d.get("trophies", ""),
            "best_trophies": d.get("bestTrophies", ""),
            "battle_count": d.get("battleCount", ""),
            "wins": d.get("wins", ""),
            "losses": d.get("losses", ""),
        }
        added += 1

    rows = sorted(known.values(), key=lambda r: str(r.get("tag", "")))
    with open(OUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for k in FIELDS:
                r.setdefault(k, "")
            w.writerow(r)

    print(f"opponents.csv を更新（今回 {added} 人 / 合計 {len(rows)} 人 / 出現 {len(tags)} 人）")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"エラー: {error}")
        sys.exit(1)
