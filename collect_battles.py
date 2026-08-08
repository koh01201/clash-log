"""
Clash Royale バトルログ収集スクリプト
------------------------------------
仕様:
  - 公式APIの battlelog を取得し、battles.csv に1試合1行で追記する
  - 何度実行しても同じ試合は重複しない（冪等）
  - エラーが起きても落ちずに log.txt に記録して終了する（次回実行で回復）
  - 時間帯分析のため、UTCの試合時刻をJSTに変換した列を持つ
"""

import csv
import datetime
import os
import sys
import urllib.parse

import requests

# ============ 設定 ここだけ書き換える ============
PLAYER_TAG = "#LQQQQPUL0"          # ゲーム内のプロフィールに出ている自分のタグ
# ===============================================

BASE_URL = "https://proxy.royaleapi.dev/v1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.txt")
OUT_FILE = os.path.join(SCRIPT_DIR, "battles.csv")
LOG_FILE = os.path.join(SCRIPT_DIR, "log.txt")

FIELDS = [
    "battle_key",          # 重複排除用のキー
    "battle_time_jst",     # 日本時間
    "jst_date",            # 日付（YYYY-MM-DD）
    "jst_hour",            # 時（0-23）← 時間帯分析の主役
    "weekday",             # 曜日（0=月 ... 6=日）
    "battle_time_utc",
    "battle_type",         # PvP, riverRacePvP など
    "game_mode",
    "result",              # win / loss / draw
    "my_crowns",
    "opp_crowns",
    "my_king_hp",
    "my_princess_hp",      # "1512|2534" のように | 区切り
    "opp_king_hp",
    "opp_princess_hp",
    "my_trophies_start",
    "trophy_change",
    "opp_trophies_start",
    "team_size",           # 1 なら1v1、2 なら2v2
    "my_deck",             # カード名を | 区切りで8枚
    "opp_deck",
    "opp_tag",             # 相手のプレイヤータグ
    "opp_name",            # 相手の表示名
]


def log(message):
    """実行結果を log.txt に1行追記する。"""
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_token():
    """クラウド実行時は環境変数(Secrets)から、手元では token.txt から読む。"""
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
    """公式APIからバトルログを取得する。"""
    encoded_tag = urllib.parse.quote(PLAYER_TAG)  # # は %23 に変換される
    url = f"{BASE_URL}/players/{encoded_tag}/battlelog"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 403:
        raise RuntimeError(
            "403エラー。トークンが無効か、キー作成時に登録したIPが違います。"
            "プロキシ経由の場合は 45.79.218.79 を登録しているか確認してください。"
        )
    if response.status_code == 404:
        raise RuntimeError(f"404エラー。プレイヤータグ {PLAYER_TAG} が見つかりません。")
    response.raise_for_status()
    return response.json()


def to_jst(battle_time):
    """'20260801T101500.000Z' 形式のUTC文字列を日本時間のdatetimeに変換する。"""
    naive_utc = datetime.datetime.strptime(battle_time[:15], "%Y%m%dT%H%M%S")
    return naive_utc + datetime.timedelta(hours=9)


def pick_me(team):
    """team配列から自分のエントリを取り出す。見つからなければ先頭を使う。"""
    target = PLAYER_TAG.upper().lstrip("#")
    for player in team:
        if str(player.get("tag", "")).upper().lstrip("#") == target:
            return player
    return team[0]


def join_cards(player):
    """デッキのカード名を | 区切りの文字列にする。"""
    return "|".join(card.get("name", "?") for card in player.get("cards", []))


def join_princess(player):
    """プリンセスタワーの残HPを | 区切りにする。全壊時はキーごと消えるので空になる。"""
    return "|".join(str(hp) for hp in player.get("princessTowersHitPoints", []) or [])


def flatten(battle):
    """APIの1試合分のJSONを、CSVの1行（辞書）に変換する。"""
    team = battle.get("team", [])
    opponent = battle.get("opponent", [])
    if not team or not opponent:
        return None

    me = pick_me(team)
    opp = opponent[0]

    battle_time = battle.get("battleTime", "")
    jst = to_jst(battle_time)

    # 重複排除キー: 試合時刻 + 相手のタグ（同じ秒に同じ相手と2試合は起こらない）
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
        "opp_tag": opp.get("tag", ""),
        "opp_name": opp.get("name", ""),
    }


def migrate():
    """列が増えたときに、既存の battles.csv を新しい形へ作り直す。"""
    if not os.path.exists(OUT_FILE):
        return
    with open(OUT_FILE, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        head = reader.fieldnames or []
        if head == FIELDS:
            return
        rows = list(reader)

    for r in rows:
        # 相手タグは battle_key の後半から復元できる
        if not r.get("opp_tag"):
            key = r.get("battle_key", "")
            r["opp_tag"] = key.split("_", 1)[1] if "_" in key else ""
        for k in FIELDS:
            r.setdefault(k, "")

    with open(OUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    log(f"battles.csv の列を更新しました（{len(head)} → {len(FIELDS)} 列）")


def load_existing_keys():
    """すでに保存済みの試合キーを集合として読み込む。"""
    if not os.path.exists(OUT_FILE):
        return set()
    with open(OUT_FILE, encoding="utf-8-sig", newline="") as f:
        return {row["battle_key"] for row in csv.DictReader(f)}


def append_rows(rows):
    """新しい試合をCSVに追記する。ファイルが無ければヘッダーも書く。"""
    is_new_file = not os.path.exists(OUT_FILE)
    # 新規作成のときだけBOMを付ける（Excelで文字化けさせないため）。
    # 追記時にutf-8-sigを使うとファイルの途中にBOMが混入するので分けている。
    encoding = "utf-8-sig" if is_new_file else "utf-8"
    with open(OUT_FILE, "a", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new_file:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    if "XXXXXXXX" in PLAYER_TAG:
        raise RuntimeError("PLAYER_TAG を自分のタグに書き換えてください。")

    migrate()
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

    # 古い試合から順に並べて追記する
    new_rows.sort(key=lambda r: r["battle_time_utc"])

    if new_rows:
        append_rows(new_rows)

    log(f"取得 {len(battles)} 件 / 新規 {len(new_rows)} 件 / 累計 {len(known)} 件")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # 落とさずにログへ
        log(f"エラー: {error}")
        sys.exit(1)
