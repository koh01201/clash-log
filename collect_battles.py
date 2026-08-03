"""
Clash Royale バトルログ収集スクリプト
"""

import csv
import datetime
import os
import sys
import urllib.parse

import requests

# ============ 設定 ============
PLAYER_TAG = "#LQQQQPUL0"
# =============================

BASE_URL = "https://proxy.royaleapi.dev/v1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.txt")
OUT_FILE = os.path.join(SCRIPT_DIR, "battles.csv")
LOG_FILE = os.path.join(SCRIPT_DIR, "log.txt")

FIELDS = [
    "battle_key",
    "battle_time_jst",
    "jst_date",
    "jst_hour",
    "weekday",
    "battle_time_utc",
    "battle_type",
    "game_mode",
    "result",
    "my_crowns",
    "opp_crowns",
    "my_king_hp",
    "my_princess_hp",
    "opp_king_hp",
    "opp_princess_hp",
    "my_trophies_start",
    "trophy_change",
    "opp_trophies_start",
    "team_size",
    "my_deck",
    "opp_deck",
]


def log(message):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_token():
    # クラウド実行時は環境変数(Secrets)から、手元では token.txt から読む
    token = os.environ.get("CR_TOKEN", "").strip()
    if token:
        return token
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("トークンが見つかりません（CR_TOKEN も token.txt も無し）")
    with open(TOKEN_FILE, encoding="utf-8") as f:
        token = f.read().strip()
    if not token:
        raise RuntimeError("token.txt が空です。")
    return token


def fetch_battlelog(token):
    encoded_tag = urllib.parse.quote(PLAYER_TAG)
    url = f"{BASE_URL}/players/{encoded_tag}/battlelog"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 403:
        raise RuntimeError("403エラー。トークンが無効か、IP登録が違います。")
    if response.status_code == 404:
        raise RuntimeError(f"404エラー。プレイヤータグ {PLAYER_TAG} が見つかりません。")
    response.raise_for_status()
    return response.json()


def to_jst(battle_time):
    naive_utc = datetime.datetime.strptime(battle_time[:15], "%Y%m%dT%H%M%S")
    return naive_utc + datetime.timedelta(hours=9)


def pick_me(team):
    target = PLAYER_TAG.upper().lstrip("#")
    for player in team:
        if str(player.get("tag", "")).upper().lstrip("#") == target:
            return player
    return team[0]


def join_cards(player):
    return "|".join(card.get("name", "?") for card in player.get("cards", []))


def join_princess(player):
    return "|".join(str(hp) for hp in player.get("princessTowersHitPoints", []) or [])


def flatten(battle):
    team = battle.get("team", [])
    opponent = battle.get("opponent", [])
    if not team or not opponent:
        return None

    me = pick_me(team)
    opp = opponent[0]

    battle_time = battle.get("battleTime", "")
    jst = to_jst(battle_time)
    battle_key = f"{battle_time}_{opp.get('tag', '?')}"

    my_crowns = me.get("crowns", 0)
    opp_crowns = opp.get("crowns", 0)
    if my_crowns > opp_crowns:
        result = "win"
    elif my_crowns < opp_crowns:
        result = "loss"
    else:
        result = "draw"

    return {
        "battle_key": battle_key,
        "battle_time_jst": jst.strftime("%Y-%m-%d %H:%M:%S"),
        "jst_date": jst.strftime("%Y-%m-%d"),
        "jst_hour": jst.hour,
        "weekday": jst.weekday(),
        "battle_time_utc": battle_time,
        "battle_type": battle.get("type", ""),
        "game_mode": (battle.get("gameMode") or {}).get("name", ""),
        "result": result,
        "my_crowns": my_crowns,
        "opp_crowns": opp_crowns,
        "my_king_hp": me.get("kingTowerHitPoints", 0),
        "my_princess_hp": join_princess(me),
        "opp_king_hp": opp.get("kingTowerHitPoints", 0),
        "opp_princess_hp": join_princess(opp),
        "my_trophies_start": me.get("startingTrophies", ""),
        "trophy_change": me.get("trophyChange", ""),
        "opp_trophies_start": opp.get("startingTrophies", ""),
        "team_size": len(team),
        "my_deck": join_cards(me),
        "opp_deck": join_cards(opp),
    }


def load_existing_keys():
    if not os.path.exists(OUT_FILE):
        return set()
    with open(OUT_FILE, encoding="utf-8-sig", newline="") as f:
        return {row["battle_key"] for row in csv.DictReader(f)}


def append_rows(rows):
    is_new_file = not os.path.exists(OUT_FILE)
    encoding = "utf-8-sig" if is_new_file else "utf-8"
    with open(OUT_FILE, "a", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new_file:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    token = load_token()
    battles = fetch_battlelog(token)

    known = load_existing_keys()
    new_rows = []
    for battle in battles:
        row = flatten(battle)
        if row is None:
            continue
        if row["battle_key"] in known:
            continue
        known.add(row["battle_key"])
        new_rows.append(row)

    new_rows.sort(key=lambda r: r["battle_time_utc"])

    if new_rows:
        append_rows(new_rows)

    log(f"取得 {len(battles)} 件 / 新規 {len(new_rows)} 件 / 累計 {len(known)} 件")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        log(f"エラー: {error}")
        sys.exit(1)
