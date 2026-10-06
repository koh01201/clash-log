"""
Clash Royale バトルログ 分析レポート生成
----------------------------------------
battles.csv を読み、report.html を出力する。
追加ライブラリ不要（Python標準機能のみ）。

    python analyze.py

設計の要点:
  - 勝率は「点」ではなく「区間」で描く（95%信頼区間 / Wilson法）
  - サンプルが少ない行は自動的に "参考値" として区別される
  - 何を除外したかを必ず画面に出す
"""

import csv
import datetime
import json
import html
import math
import os
from collections import defaultdict

# ============ 判断が入る設定：ここは自分で決める ============
SESSION_GAP_MINUTES = 30      # 前の試合からこの分数以上あいたら「別のセッション」とみなす
RELIABLE_N = 20               # この試合数未満は参考値として薄く表示する
RANKED_ONLY = True            # クラン戦などを除き、ランク戦だけで集計する
NEW_UI = True                 # True＝新しい1ページ型のサイト。False にすると旧ページ群に戻る
# =========================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IN_FILE = os.path.join(SCRIPT_DIR, "battles.csv")
OUT_FILE = os.path.join(SCRIPT_DIR, "report.html")

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]
JST = datetime.timezone(datetime.timedelta(hours=9))


def now_jst():
    """実行環境の時計に依存せず、必ず日本時間を返す。
    GitHub Actions上ではdatetime.now()が世界標準時になるため。"""
    return datetime.datetime.now(JST)


# ---------------- 統計 ----------------

def wilson(wins, total):
    """勝率の推定値と95%信頼区間（Wilson法）。試合数が少ないほど区間が広くなる。"""
    if total == 0:
        return 0.0, 0.0, 0.0
    z = 1.96
    p = wins / total
    d = 1 + z * z / total
    center = (p + z * z / (2 * total)) / d
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return p, max(0.0, center - margin), min(1.0, center + margin)


def needed_n(p1=0.50, p2=0.60):
    """2群の勝率差を検出するのに必要な1群あたりの試合数（α=0.05, 検出力80%）。"""
    z_a, z_b = 1.96, 0.84
    var = p1 * (1 - p1) + p2 * (1 - p2)
    return math.ceil((z_a + z_b) ** 2 * var / (p2 - p1) ** 2)


# ---------------- 読み込み ----------------

def load_rows():
    if not os.path.exists(IN_FILE):
        raise SystemExit(f"{IN_FILE} が見つかりません。先に収集を実行してください。")
    with open(IN_FILE, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        r["_dt"] = datetime.datetime.strptime(r["battle_time_jst"], "%Y-%m-%d %H:%M:%S")
        r["_hour"] = int(r["jst_hour"])
        r["_wd"] = int(r["weekday"])
    rows.sort(key=lambda r: r["_dt"])
    return rows


def is_ranked(row):
    text = (row.get("game_mode", "") + row.get("battle_type", "")).lower()
    return "ranked" in text or "ladder" in text


def add_sessions(rows):
    """時間の間隔でセッションに切り、各試合がセッション内で何戦目かを付ける。"""
    gap = datetime.timedelta(minutes=SESSION_GAP_MINUTES)
    session_id = 0
    position = 0
    prev_dt = None
    for r in rows:
        if prev_dt is None or r["_dt"] - prev_dt > gap:
            session_id += 1
            position = 0
        position += 1
        r["_session"] = session_id
        r["_pos"] = position
        prev_dt = r["_dt"]
    return rows


def prev_state(rows):
    """直前の連敗・連勝の状態を各試合に付ける（セッションをまたいだらリセット）。"""
    streak = 0  # 正=連勝, 負=連敗
    last_session = None
    for r in rows:
        if r["_session"] != last_session:
            streak = 0
            last_session = r["_session"]
        r["_prev_streak"] = streak
        if r["result"] == "win":
            streak = streak + 1 if streak > 0 else 1
        elif r["result"] == "loss":
            streak = streak - 1 if streak < 0 else -1
        else:
            streak = 0
    return rows


# ---------------- 集計 ----------------

def tally(rows, key_func):
    """key_func で分類し、(キー, 勝ち, 全体) の一覧を返す。引き分けは母数から除く。"""
    bucket = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["result"] == "draw":
            continue
        k = key_func(r)
        if k is None:
            continue
        bucket[k][1] += 1
        if r["result"] == "win":
            bucket[k][0] += 1
    return bucket


# ---------------- 共通の描画部品 ----------------

MIN_CARD_N = 5
TOP_CARDS = 10

PAGES = [
    ("chart.html", "推移"),
    ("mydeck.html", "使用デッキ"),
    ("enemy.html", "対戦相手"),
    ("chosi.html", "調子"),
    ("rate.html", "レート"),
    ("rivals.html", "強敵"),
    ("log.html", "対戦記録"),
]


CARDS_FILE = os.path.join(SCRIPT_DIR, "cards.json")


PROFILE_FILE = os.path.join(SCRIPT_DIR, "profile.csv")
OPPONENTS_FILE = os.path.join(SCRIPT_DIR, "opponents.csv")
GT_FILE = os.path.join(SCRIPT_DIR, "gt_ranks.csv")

# 強敵とみなす条件
RIVAL_POL_RANK = 10000     # レート戦の過去最高順位がこれ以内
RIVAL_GT_RANK = 1000       # グローバルトーナメントの最高順位がこれ以内
RIVAL_LADDER_RANK = 10000  # Top Ladder の最高順位がこれ以内
RIVAL_RT_RANK = 1000       # グローバルトーナメント Top1000（APIは「1,000位以内に入った回数」しか返さない）
# グローバルトーナメント1,000位以内で付くバッジ（ゲーム内で剣の絵に最高順位が出るもの）。
# APIの名前は LadderTournamentTop1000。最高順位の数字はAPIに含まれず、回数だけが返る。
RT_BADGE = "LadderTournamentTop1000"


def _rt_top1000(raw):
    """グローバルトーナメントで1,000位以内に入った回数。バッジが無ければ None。"""
    try:
        j = json.loads(raw or "")
    except (TypeError, ValueError):
        return None
    for b in j.get("badges") or []:
        if b.get("name") == RT_BADGE:
            return _num(b.get("progress")) or _num(b.get("level")) or 1
    return None


def load_opponents():
    """opponents.csv をタグ引きの辞書にする。"""
    if not os.path.exists(OPPONENTS_FILE):
        return {}
    try:
        csv.field_size_limit(1 << 30)
        out = {}
        with open(OPPONENTS_FILE, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if not r.get("tag"):
                    continue
                r["_rt"] = _rt_top1000(r.pop("raw_json", ""))
                out[r["tag"]] = r
        return out
    except Exception:
        return {}


def load_gt():
    """グローバルトーナメントの順位表（別途収集）。"""
    if not os.path.exists(GT_FILE):
        return {}
    try:
        with open(GT_FILE, encoding="utf-8-sig", newline="") as f:
            return {r["tag"]: r for r in csv.DictReader(f) if r.get("tag")}
    except Exception:
        return {}


def opp_ranks(tag):
    """相手の実績をまとめて返す。未取得なら空の辞書と同じ扱い。"""
    o = OPPONENTS.get(tag or "") or {}
    return {
        "name": o.get("name", ""),
        "pol": _num(o.get("pol_best_rank")),
        "gt": _num(o.get("gt_best_rank")) or _num((GT_RANKS.get(tag or "") or {}).get("best_rank")),
        "best": _num(o.get("pol_best_trophies")),
        "ladder": _num(o.get("ladder_best_rank")),
        "ladder_season": (o.get("ladder_best_season") or "").strip(),
        "rt": o.get("_rt"),
        "battles": _num(o.get("battle_count")),
    }


def is_rival(pol, gt, ladder=None, rt=None):
    return ((pol is not None and pol <= RIVAL_POL_RANK)
            or (gt is not None and gt <= RIVAL_GT_RANK)
            or (ladder is not None and ladder <= RIVAL_LADDER_RANK)
            or bool(rt))


def best_rank(pol, gt, ladder, rt):
    """条件に使う順位のうち最も良いものと、その出どころ。"""
    cands = [(v, lab) for v, lab in ((pol, "レート戦"), (gt, "グローバルトーナメント"),
                                     (ladder, "Top Ladder"),
                                     (RIVAL_RT_RANK if rt else None, "GT Top1000"))
             if v is not None]
    return min(cands, key=lambda c: c[0]) if cands else (None, "")


LEAGUES = {
    1: ("Master I", "#8AA0B5"),
    2: ("Master II", "#6E90AE"),
    3: ("Master III", "#4F7A9B"),
    4: ("Champion", "#C9A227"),
    5: ("Grand Champion", "#D08A2C"),
    6: ("Royal Champion", "#C0392B"),
    7: ("Ultimate Champion", "#7A3FBF"),
}
ULTIMATE = 7

# シーズン番号の基準：この時刻に遊んでいたシーズンの番号（2026-10-04 に本人確認）
SEASON_ANCHOR = ("2026-10-04 08:00:00", 87)

# 記録開始より前に達成した自己ベストの時期（APIから取得できないため手で持つ）
BEST_ACHIEVED_BEFORE = "2024年4月"


def league_name(n):
    return LEAGUES.get(n, (f"League {n}", "#8A939C"))[0]


def league_color(n):
    return LEAGUES.get(n, (f"League {n}", "#8A939C"))[1]


def load_profile():
    """profile.csv を古い順に読む。無ければ空。"""
    if not os.path.exists(PROFILE_FILE):
        return []
    try:
        with open(PROFILE_FILE, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def stage_cell(league, trophies, rank, size=40):
    """ステージ（未到達）ならステージ名、アルティメットならレートを返す。"""
    if league is None:
        return "-"
    col = league_color(league)
    body = '<span class="stxt">'
    if league >= ULTIMATE and trophies:
        body += (f'<span class="sname">レート</span>'
                 f'<b class="big">{trophies:,}</b>'
                 f'<span class="lgname" style="color:{col}">{esc(league_name(league))}</span>')
    else:
        body += f'<b class="lgname big2" style="color:{col}">{esc(league_name(league))}</b>'
        if trophies:
            body += f'<span class="sname">{trophies:,}</span>'
    if rank:
        body += f'<span class="sname">世界 {rank:,} 位</span>'
    return body + "</span>"



SEASONS = []        # [(このシーズンの最初の時刻, 番号), ...] 古い順。先頭の時刻は ""
SEASONS_JS = "[]"


def _plus1s(t):
    try:
        d = datetime.datetime.strptime(t[:19], "%Y-%m-%d %H:%M:%S")
        return (d + datetime.timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return t


def detect_seasons(rows, prof):
    """シーズンの切り替わりを探して番号を振る。

    切り替わりの判定はレートの記録（profile.csv）。前シーズンの最終成績が更新されたか、
    ステージがいちばん下まで戻った時点を切り替わりとみなす。
    正確な時刻は、ランク戦の対戦場の名前が変わった最初の試合で決める
    （シーズンごとに NewArena / NewArena2 が入れ替わる）。
    レートの記録が始まる前の切り替わりは、対戦場の名前の変化だけで判定する。
    """
    # レートの記録から：(旧シーズン最後の記録, 新シーズン最初の記録)
    pairs, prev = [], None
    for r in prof:
        t = (r.get("checked_jst") or "").strip()[:19]
        lg = _num(r.get("pol_current_league"))
        last = (r.get("pol_last_league"), r.get("pol_last_trophies"), r.get("pol_last_rank"))
        if not t or lg is None:
            continue
        if prev and (last != prev[2] or (lg < prev[1] and lg <= 2)):
            pairs.append((prev[0], t))
        prev = (t, lg, last)

    # 試合から：ランク戦の対戦場の名前が変わった試合
    flips, pm = [], None
    for r in sorted((x for x in rows if "pathoflegend" in (x.get("battle_type") or "").lower()),
                    key=lambda x: x["battle_time_jst"]):
        gm = (r.get("game_mode") or "").strip()
        if not gm:
            continue
        if pm is not None and gm != pm:
            flips.append(r["battle_time_jst"][:19])
        pm = gm

    first_prof = next(((r.get("checked_jst") or "").strip()[:19] for r in prof
                       if (r.get("checked_jst") or "").strip()), None)
    starts = [f for f in flips if first_prof is None or f < first_prof]
    for a, b in pairs:
        hit = [f for f in flips if a < f <= b]
        starts.append(hit[0] if hit else _plus1s(a))
    starts = sorted(set(starts))

    segs = [""] + starts
    at = SEASON_ANCHOR[0]
    idx = max(i for i, f in enumerate(segs) if f <= at)
    return [(f, SEASON_ANCHOR[1] + i - idx) for i, f in enumerate(segs)]


def season_of(t):
    """その時刻のシーズン番号。"""
    n = None
    for f, num in SEASONS:
        if f <= (t or "")[:19]:
            n = num
    return n


def season_decks(rows):
    """シーズンごとの最多使用デッキと成績。"""
    by = defaultdict(lambda: {"w": 0, "n": 0, "d0": None, "d1": None,
                              "decks": defaultdict(lambda: [0, 0]), "face": {}})
    for r in rows:
        if r["result"] == "draw":
            continue
        sn = season_of(r["battle_time_jst"])
        if sn is None:
            continue
        m = by[sn]
        m["n"] += 1
        if r["result"] == "win":
            m["w"] += 1
        d = r["battle_time_jst"][:10]
        m["d0"] = d if m["d0"] is None or d < m["d0"] else m["d0"]
        m["d1"] = d if m["d1"] is None or d > m["d1"] else m["d1"]
        cards = [c for c in r["my_deck"].split("|") if c]
        if not cards:
            continue
        k = "|".join(sorted(cards))
        m["decks"][k][1] += 1
        if r["result"] == "win":
            m["decks"][k][0] += 1
        m["face"].setdefault(k, cards[:8])

    out = []
    for sn in sorted(by, reverse=True):
        m = by[sn]
        if not m["decks"]:
            continue
        k = max(m["decks"], key=lambda x: m["decks"][x][1])
        dw, dn = m["decks"][k]
        out.append({
            "season": sn, "n": m["n"], "w": m["w"], "d0": m["d0"], "d1": m["d1"],
            "cards": m["face"].get(k, []), "dw": dw, "dn": dn,
            "kinds": len(m["decks"]),
        })
    return out


def season_deck_panel(rows):
    data = season_decks(rows)
    if not data:
        return ""
    body = []
    for d in data:
        wr = d["w"] / d["n"] * 100 if d["n"] else 0
        dwr = d["dw"] / d["dn"] * 100 if d["dn"] else 0
        span = f'{d["d0"][5:].replace("-", "/")}〜{d["d1"][5:].replace("-", "/")}'
        body.append(
            f'<tr><th>シーズン{d["season"]}<span class="sname">{span}・{d["n"]}試合・勝率{wr:.1f}%</span></th>'
            f'<td><div class="mdeck">{deck_grid(d["cards"])}'
            f'<span class="sname">{d["dn"]}試合使用（{d["kinds"]}種類中）・このデッキの勝率 {dwr:.1f}%</span>'
            "</div></td></tr>")
    return panel("シーズンごとの最多使用デッキ", f'<table class="kv">{"".join(body)}</table>',
                 "レート戦がいちばん下のステージに戻った時点を、シーズンの切り替わりとしている。",
                 f"番号は{SEASON_ANCHOR[0][:4]}年{int(SEASON_ANCHOR[0][5:7])}月"
                 f"{int(SEASON_ANCHOR[0][8:10])}日時点のシーズンを{SEASON_ANCHOR[1]}として数えている。"
                 "日付はそのシーズンで試合の記録がある範囲。いちばん多く使った構成を1つ表示している。")


def achieved_note(prof, key, value):
    """その値が記録上いつ現れたか。記録開始時点で既にあれば遡れない旨を返す。"""
    if value is None or not prof:
        return ""
    first = None
    for r in prof:
        if _num(r.get(key)) == value:
            first = r.get("checked_jst", "")[:10]
            break
    if not first:
        return ""
    if first == prof[0].get("checked_jst", "")[:10]:
        return f'<span class="sname">{esc(BEST_ACHIEVED_BEFORE)}に達成</span>'
    y, m = first.split("-")[:2]
    return f'<span class="sname">{y}年{int(m)}月に更新</span>'


RATE_PANEL = """
    <div class="toolbar"><div class="tgroup"><span class="tl">期間</span><div class="seg"><button id="p-7" class="ubtn">7日</button><button id="p-30" class="ubtn">30日</button><button id="p-90" class="ubtn">90日</button><button id="p-all" class="ubtn on">全期間</button></div></div></div>
    <div id="rchart"></div>
    <div class="rng">
      <div class="rlab"><span>表示範囲</span><b id="rlab">-</b></div>
      <div class="dual"><div class="dual-fill" id="rfill"></div><input id="r1" type="range" min="0" max="0" value="0" aria-label="表示範囲の始まり"><input id="r2" type="range" min="0" max="0" value="0" aria-label="表示範囲の終わり"></div>
    </div>
    <div class="legend2">
      <span><i class="lgline" style="border-color:#C8102E;border-top-width:2.5px"></i>レート・ステージ</span>
      <span><i class="lgline" style="border-color:#1C2126;border-top-width:1.5px"></i>勝率（30試合の移動平均）</span>
      <span><i class="lgbox" style="background:#EFE9F7;box-shadow:inset 0 0 0 1px #D9CCEE"></i>アルティメットチャンピオン</span>
      <span><i class="lgbox" style="background:#E4E8ED"></i>試合数</span>
      <span><i class="lgline" style="border-color:#868E97;border-top-width:1.5px;border-top-style:dashed"></i>シーズンの区切り</span>
    </div>"""


def rate_page_body(prof):
    if not prof:
        return panel("レート", '<p class="empty">まだ記録がない。次の実行から貯まりはじめる。</p>',
                     "ランク戦の成績はバトルログに含まれないため、プレイヤー情報から別に記録している。")

    cur = prof[-1]
    cl, ct, cr = (_num(cur.get("pol_current_league")), _num(cur.get("pol_current_trophies")),
                  _num(cur.get("pol_current_rank")))
    bl, bt, br = (_num(cur.get("pol_best_league")), _num(cur.get("pol_best_trophies")),
                  _num(cur.get("pol_best_rank")))

    best_rank = None
    for r in prof:
        for k in ("pol_current_rank", "pol_last_rank", "pol_best_rank"):
            v = _num(r.get(k))
            if v and (best_rank is None or v < best_rank):
                best_rank = v

    cur_sn = season_of((cur.get("checked_jst") or "").strip())
    kv = [(f"今シーズン（シーズン{cur_sn}）" if cur_sn else "今シーズン", stage_cell(cl, ct, cr))]
    if bl is not None:
        kv.append(("自己ベスト", stage_cell(bl, bt, br)
                   + achieved_note(prof, "pol_best_trophies", bt)))
    if ct and bt and cl is not None and bl is not None and cl >= ULTIMATE and bl >= ULTIMATE:
        kv.append(("ベストとの差", f"{ct - bt:+,}", "up" if ct >= bt else "down"))
    if best_rank:
        note = ""
        for k in ("pol_best_rank", "pol_last_rank", "pol_current_rank"):
            note = achieved_note(prof, k, best_rank)
            if note:
                break
        kv.append(("最高順位", f"世界 {best_rank:,} 位" + note))
    t, btr = _num(cur.get("trophies")), _num(cur.get("best_trophies"))
    if t is not None:
        kv.append(("トロフィー（通常）", f"{t:,}" + (f"　最高 {btr:,}" if btr else "")))
    w, l = _num(cur.get("wins")), _num(cur.get("losses"))
    if w is not None and l is not None and (w + l):
        kv.append(("通算成績", f"{w:,}勝 {l:,}敗（{w/(w+l)*100:.1f}%）"))

    seasons, seen = [], None
    for r in prof:
        key = (r.get("pol_last_league"), r.get("pol_last_trophies"), r.get("pol_last_rank"))
        if key == seen or _num(key[0]) is None:
            continue
        seen = key
        seasons.append((r.get("checked_jst", "")[:10], _num(key[0]), _num(key[1]), _num(key[2]),
                        season_of((r.get("checked_jst") or "").strip())))

    def sname(sn, d):
        lab = f"シーズン{sn - 1}" if sn else "前シーズン"
        return f'{lab}<span class="sname">{esc(d)} に確認</span>'

    if seasons:
        body = "".join(f"<tr><th>{sname(sn, d)}</th><td>{stage_cell(lg, tr, rk, 32)}</td></tr>"
                       for d, lg, tr, rk, sn in reversed(seasons))
        hist = f'<h3 class="sub2">シーズン別の最終成績</h3><table class="kv">{body}</table>'
    else:
        hist = ('<p class="note">シーズンが切り替わると、ここに前シーズンの最終成績が積み上がる。'
                "過去に遡って取得することはできないため、記録は今日以降のぶん。</p>")

    return (panel("現在の成績", table(kv) + hist,
                  "アルティメットチャンピオンに到達するまでレートは表示されないため、"
                  "それまではステージを表示する。")
            + panel("レートと勝率の推移", RATE_PANEL,
                    "上がレート、下が勝率。横軸は共通で、つまみを動かすと両方が連動する。",
                    "レートはランク戦の記録（全モード共通）。勝率と試合数は表示中のモードのもの。"
                    "紫の帯はアルティメットチャンピオンの範囲。"))



def load_icons():
    """cards.json からカード名→画像URLの表を読む。無ければ空（文字だけで動く）。"""
    if not os.path.exists(CARDS_FILE):
        return {}
    try:
        with open(CARDS_FILE, encoding="utf-8") as f:
            return json.load(f).get("cards", {}) or {}
    except Exception:
        return {}


ICONS = {}
PROFILE = []
OPPONENTS = {}
GT_RANKS = {}


def esc(text):
    return html.escape(str(text))


def icon_tag(name, x, y, w, h):
    """カード1枚分の画像。未登録なら灰色の枠で埋める。"""
    url = ICONS.get(name)
    if not url:
        return (f'<rect class="noicon" x="{x:.1f}" y="{y:.1f}" '
                f'width="{w:.1f}" height="{h:.1f}" rx="2"/>')
    return (f'<image href="{esc(url)}" x="{x:.1f}" y="{y:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" preserveAspectRatio="xMidYMid meet">'
            f'<title>{esc(name)}</title></image>')


def _chart_wide(items, baseline, baseline_label, icon_mode):
    row_h = {"none": 42, "deck": 46, "single": 54}[icon_mode]
    top, W = 36, 720
    height = top + row_h * len(items) + 4
    x0 = {"none": 210, "single": 210, "deck": 216}[icon_mode]
    x1 = 520
    span = x1 - x0

    def px(v):
        return x0 + span * v

    out = [f'<svg viewBox="0 0 {W} {height}" class="chart">']
    for g in (0, 0.25, 0.5, 0.75, 1.0):
        gx = px(g)
        out.append(f'<line class="gridv" x1="{gx:.1f}" y1="{top-10}" x2="{gx:.1f}" y2="{height-4}"/>')
        out.append(f'<text class="gtick" x="{gx:.1f}" y="{top-14}" text-anchor="middle">{int(g*100)}</text>')
    bx = px(baseline)
    out.append(f'<line class="base" x1="{bx:.1f}" y1="{top-10}" x2="{bx:.1f}" y2="{height-4}"/>')
    out.append(f'<text class="baselab" x="{bx:.1f}" y="{top-26}" text-anchor="middle">{esc(baseline_label)}</text>')

    for i, item in enumerate(items):
        label, wins, total = item[0], item[1], item[2]
        cards = item[3] if len(item) > 3 else []
        y = top + row_h * i + row_h / 2
        p, lo, hi = wilson(wins, total)
        cls = tone_class(p, baseline, total)
        w = max(10.0, px(hi) - px(lo))
        out.append(f'<line class="hair" x1="0" y1="{y+row_h/2:.1f}" x2="{W}" y2="{y+row_h/2:.1f}"/>')
        if icon_mode == "deck":
            for j, c in enumerate(cards[:8]):
                out.append(icon_tag(c, j * 25, y - 14, 22, 27))
        elif icon_mode == "single":
            if cards:
                out.append(icon_tag(cards[0], 0, y - 19, 32, 38))
            out.append(f'<text class="lab" x="40" y="{y+5:.1f}">{esc(label)}</text>')
        else:
            out.append(f'<text class="lab" x="0" y="{y+5:.1f}">{esc(label)}</text>')
        out.append(f'<rect class="band {cls}" x="{px(lo):.1f}" y="{y-4:.1f}" width="{w:.1f}" height="8" rx="4"/>')
        out.append(f'<circle class="mark {cls}" cx="{px(p):.1f}" cy="{y:.1f}" r="5.5"/>')
        out.append(f'<text class="val {cls}" x="600" y="{y+7:.1f}" text-anchor="end">{p*100:.1f}<tspan class="unit">%</tspan></text>')
        out.append(f'<text class="n" x="{W}" y="{y+5:.1f}" text-anchor="end">{wins}勝{total-wins}敗</text>')
    out.append("</svg>")
    return "".join(out)


def _chart_narrow(items, baseline, baseline_label, icon_mode):
    """スマホ用。1件を数段に分け、絵と数字を大きく出す。"""
    row_h = {"none": 64, "single": 90, "deck": 100}[icon_mode]
    top, W = 44, 380
    height = top + row_h * len(items) + 6
    x0 = 72 if icon_mode == "deck" else 24
    x1 = 286
    span = x1 - x0

    def px(v):
        return x0 + span * v

    bx = px(baseline)
    out = [f'<svg viewBox="0 0 {W} {height}" class="chart">']
    for g in (0, 0.25, 0.5, 0.75, 1.0):
        gx = px(g)
        if icon_mode != "deck":
            out.append(f'<line class="gridv" x1="{gx:.1f}" y1="{top-12}" x2="{gx:.1f}" y2="{height-6}"/>')
        out.append(f'<text class="gtick" x="{gx:.1f}" y="{top-16}" text-anchor="middle">{int(g*100)}</text>')
    if icon_mode != "deck":
        out.append(f'<line class="base" x1="{bx:.1f}" y1="{top-12}" x2="{bx:.1f}" y2="{height-6}"/>')
    out.append(f'<text class="baselab" x="{bx:.1f}" y="{top-28}" text-anchor="middle">{esc(baseline_label)}</text>')

    for i, item in enumerate(items):
        label, wins, total = item[0], item[1], item[2]
        cards = item[3] if len(item) > 3 else []
        base_y = top + row_h * i + 4
        p, lo, hi = wilson(wins, total)
        cls = tone_class(p, baseline, total)
        score = f"{wins}勝{total - wins}敗"

        if icon_mode == "deck":
            gap, iw = 4, 36
            ih = iw * 1.2
            offset = (W - (iw * 8 + gap * 7)) / 2
            for j, c in enumerate(cards[:8]):
                out.append(icon_tag(c, offset + j * (iw + gap), base_y + 6, iw, ih))
            by = base_y + 6 + ih + 22
            # 勝敗は帯の左、割合は帯の右。カードの上下に数字を置かない
            out.append(f'<text class="n" x="0" y="{by+5:.1f}">{score}</text>')
            out.append(f'<line class="base" x1="{bx:.1f}" y1="{by-15:.1f}" x2="{bx:.1f}" y2="{by+15:.1f}"/>')
        else:
            out.append(f'<text class="n" x="{W}" y="{base_y+13:.1f}" text-anchor="end">{score}</text>')
            if icon_mode == "single":
                if cards:
                    out.append(icon_tag(cards[0], 0, base_y, 38, 46))
                out.append(f'<text class="lab" x="46" y="{base_y+28:.1f}">{esc(label)}</text>')
                by = base_y + 46 + 18
            else:
                out.append(f'<text class="lab" x="0" y="{base_y+13:.1f}">{esc(label)}</text>')
                by = base_y + 20 + 18

        w = max(8.0, px(hi) - px(lo))
        out.append(f'<rect class="band {cls}" x="{px(lo):.1f}" y="{by-4:.1f}" width="{w:.1f}" height="8" rx="4"/>')
        out.append(f'<circle class="mark {cls}" cx="{px(p):.1f}" cy="{by:.1f}" r="5.5"/>')
        out.append(f'<text class="val {cls}" x="{W}" y="{by+7:.1f}" text-anchor="end">{p*100:.1f}<tspan class="unit">%</tspan></text>')
        out.append(f'<line class="hair" x1="0" y1="{base_y+row_h-12:.1f}" x2="{W}" y2="{base_y+row_h-12:.1f}"/>')
    out.append("</svg>")
    return "".join(out)


def tone_class(p, baseline, total):
    if total < RELIABLE_N:
        return "na"
    return "up" if p > baseline else "down" if p < baseline else "na"


def rate_rows(items, baseline=0.5, baseline_label="50%", icon_mode="none"):
    """画面幅に応じて2種類のレイアウトを出し分ける。"""
    if not items:
        return '<p class="empty">該当するデータがない。</p>'
    return ('<div class="wideonly">' + _chart_wide(items, baseline, baseline_label, icon_mode) + "</div>"
            + '<div class="narrowonly">'
            + _chart_narrow(items, baseline, baseline_label, icon_mode) + "</div>")


def table(pairs):
    """pairs: (項目, 値) または (項目, 値, "up"/"down"/"") """
    rows_html = []
    for item in pairs:
        k, v = item[0], item[1]
        cls = item[2] if len(item) > 2 else ""
        td = f'<td class="{cls}">' if cls else "<td>"
        rows_html.append(f'<tr><th>{esc(k)}</th>{td}{v}</tr>')
    return f'<table class="kv">{"".join(rows_html)}</table>'


def panel(title, inner, lead="", note=""):
    lead_html = f'<p class="lead">{esc(lead)}</p>' if lead else ""
    note_html = f'<p class="note">{esc(note)}</p>' if note else ""
    return f'<section class="panel"><h2>{esc(title)}</h2>{lead_html}{inner}{note_html}</section>'


CHART_JS = """(function () {
  var MODE = "__MODE__";
  var PATCHES = [];          // 例: ["2026-08-15"] を足すと縦線が入る
  var MA_WIN = 4;            // 移動平均の窓（バケット数）
  var SEASONS = __SEASONS__; // [{f: このシーズンの最初の時刻, n: 番号}] 古い順
  var RELIABLE_N = 20;
  var S = { unit: "week", lo: 0, hi: 0, rows: [], buckets: [], icons: {} };

  function narrow() {
    return document.documentElement.getAttribute("data-layout") === "narrow";
  }
  function esc(t) {
    return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function parseCSV(text) {
    var rows = [], row = [], cell = "", q = false, i, c;
    for (i = 0; i < text.length; i++) {
      c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else { q = false; } }
        else { cell += c; }
      } else if (c === '"') { q = true; }
      else if (c === ",") { row.push(cell); cell = ""; }
      else if (c === "\\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
      else if (c !== "\\r") { cell += c; }
    }
    if (cell.length || row.length) { row.push(cell); rows.push(row); }
    if (!rows.length) return [];
    var head = rows.shift().map(function (h) { return h.replace(/^\\uFEFF/, "").trim(); });
    return rows.filter(function (r) { return r.length === head.length; }).map(function (r) {
      var o = {}, k;
      for (k = 0; k < head.length; k++) o[head[k]] = r[k];
      return o;
    });
  }
  function classify(r) {
    var t = (r.battle_type || "").toLowerCase();
    if (t.indexOf("pathoflegend") >= 0) return "pol";
    return "etc";
  }
  function wilson(w, n) {
    if (!n) return [0, 0, 0];
    var z = 1.96, p = w / n, d = 1 + z * z / n;
    var c = (p + z * z / (2 * n)) / d;
    var m = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
    return [p, Math.max(0, c - m), Math.min(1, c + m)];
  }
  function weekKey(s) {
    var d = new Date(s.slice(0, 10) + "T00:00:00");
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    var mm = ("0" + (d.getMonth() + 1)).slice(-2), dd = ("0" + d.getDate()).slice(-2);
    return d.getFullYear() + "-" + mm + "-" + dd;
  }
  function keyOf(s, unit) {
    if (unit === "day") return s.slice(0, 10);
    if (unit === "month") return s.slice(0, 7) + "-01";
    return weekKey(s);
  }
  function seasonOf(t) {
    var n = null, j;
    for (j = 0; j < SEASONS.length; j++) if (SEASONS[j].f <= t) n = SEASONS[j].n;
    return n;
  }
  function bucketize(rows, unit) {
    var map = {}, order = [], i, k, r;
    for (i = 0; i < rows.length; i++) {
      r = rows[i];
      k = keyOf(r.battle_time_jst, unit);
      if (!map[k]) { map[k] = { key: k, w: 0, n: 0, games: 0, sc: {} }; order.push(k); }
      map[k].games++;
      var sn = seasonOf(r.battle_time_jst);
      if (sn !== null) map[k].sc[sn] = (map[k].sc[sn] || 0) + 1;
      if (r.result === "draw") continue;
      map[k].n++;
      if (r.result === "win") map[k].w++;
    }
    order.sort();
    return order.map(function (k) {
      var b = map[k], best = null, s2;
      for (s2 in b.sc) if (best === null || b.sc[s2] > b.sc[best]) best = s2;
      b.season = best === null ? null : +best;   // その期間でいちばん多く遊んだシーズン
      return b;
    });
  }
  function movingAvg(b, win) {
    return b.map(function (_, i) {
      var w = 0, n = 0, j;
      for (j = Math.max(0, i - win + 1); j <= i; j++) { w += b[j].w; n += b[j].n; }
      return n ? w / n : null;
    });
  }
  function fmtDate(k, unit) {
    var p = k.split("-");
    return unit === "month" ? p[0].slice(2) + "/" + p[1] : p[1] + "/" + p[2];
  }
  function tone(p, base, n) {
    if (n < RELIABLE_N) return "na";
    return p > base ? "up" : p < base ? "down" : "na";
  }

  /* ---------- 描画 ---------- */
  function draw() {
    var all = S.buckets, total = all.length;
    if (!total) { document.getElementById("chart").innerHTML =
      '<p class="empty">この期間のデータがない。</p>'; return; }

    /* 期間スライダーで選ばれた範囲だけを描く（範囲外は描かない） */
    var lo = Math.max(0, Math.min(S.lo, total - 1));
    var hi = Math.max(lo, Math.min(S.hi, total - 1));
    var nb = hi - lo + 1;

    var nw = narrow();
    var W = nw ? 380 : 720;
    var MH = nw ? 132 : 172, VH = nw ? 44 : 58, GAP = 30;
    var padL = 8, padR = nw ? 34 : 40, padT = 30;
    var H = padT + MH + GAP + VH + 20;
    var pw = W - padL - padR;
    var step = pw / nb;
    var x = function (i) { return padL + (i - lo + 0.5) * step; };   // 桁の中心
    var xe = function (i) { return padL + (i - lo) * step; };        // 桁の左端
    var y = function (v) { return padT + MH * (1 - v); };
    var vy0 = padT + MH + GAP, vy1 = vy0 + VH;
    var o = [];

    o.push('<svg viewBox="0 0 ' + W + ' ' + H + '" class="chart">');

    // 枠と地
    o.push('<rect class="plot" x="' + padL + '" y="' + padT + '" width="' + pw + '" height="' + MH + '"/>');
    o.push('<rect class="plot" x="' + padL + '" y="' + vy0 + '" width="' + pw + '" height="' + VH + '"/>');

    // 横罫と右軸
    [0, 0.25, 0.5, 0.75, 1].forEach(function (v) {
      if (v !== 0.5) {
        o.push('<line class="' + (v === 0 ? "axis" : "grid") + '" x1="' + padL + '" y1="' + y(v).toFixed(1) +
          '" x2="' + (padL + pw) + '" y2="' + y(v).toFixed(1) + '"/>');
      }
      o.push('<text class="tick" x="' + (padL + pw + 5) + '" y="' + (y(v) + 3.5).toFixed(1) + '">' +
        (v * 100) + (v === 1 ? "%" : "") + "</text>");
    });
    // 五分の基準
    o.push('<line class="fifty" x1="' + padL + '" y1="' + y(0.5).toFixed(1) +
      '" x2="' + (padL + pw) + '" y2="' + y(0.5).toFixed(1) + '"/>');

    // シーズンの区切り（期間内のみ）と、上の帯のシーズン名
    var i, mb = [];
    for (i = lo + 1; i <= hi; i++) {
      if (all[i].season !== null && all[i - 1].season !== null && all[i].season !== all[i - 1].season) mb.push(i);
    }
    mb.forEach(function (i2) {
      var mx = xe(i2).toFixed(1);
      o.push('<line class="seasonsep" x1="' + mx + '" y1="' + (padT - 22) + '" x2="' + mx + '" y2="' + vy1 + '"/>');
    });
    var edges = [lo].concat(mb).concat([hi + 1]);
    for (var e = 0; e + 1 < edges.length; e++) {
      var sx0 = xe(edges[e]), sx1 = xe(edges[e + 1]), sw = sx1 - sx0, snum = all[edges[e]].season;
      if (snum === null || sw < 26) continue;
      o.push('<text class="seasonlab" x="' + ((sx0 + sx1) / 2).toFixed(1) + '" y="' + (padT - 10) +
        '" text-anchor="middle">' + (sw >= 72 ? "シーズン" : "S") + snum + "</text>");
    }

    // 信頼区間
    var up = [], dn = [], lohi = {};
    for (i = lo; i <= hi; i++) lohi[i] = wilson(all[i].w, all[i].n);
    if (nb > 1) {
      for (i = lo; i <= hi; i++) up.push(x(i).toFixed(1) + "," + y(lohi[i][2]).toFixed(1));
      for (i = hi; i >= lo; i--) dn.push(x(i).toFixed(1) + "," + y(lohi[i][1]).toFixed(1));
      o.push('<polygon class="ciband" points="' + up.concat(dn).join(" ") + '"/>');
    } else {
      o.push('<line class="cistick" x1="' + x(lo).toFixed(1) + '" y1="' + y(lohi[lo][1]).toFixed(1) +
        '" x2="' + x(lo).toFixed(1) + '" y2="' + y(lohi[lo][2]).toFixed(1) + '"/>');
    }

    // 実測（細い黒）
    var pts = [];
    for (i = lo; i <= hi; i++) {
      pts.push(x(i).toFixed(1) + "," + y(all[i].n ? all[i].w / all[i].n : 0).toFixed(1));
    }
    if (nb > 1) o.push('<polyline class="rate" points="' + pts.join(" ") + '"/>');
    if (nb <= 40) for (i = lo; i <= hi; i++) {
      o.push('<circle class="pt" cx="' + x(i).toFixed(1) + '" cy="' +
        y(all[i].n ? all[i].w / all[i].n : 0).toFixed(1) + '" r="' + (nw ? 2.4 : 3) + '"/>');
    }

    // 移動平均（赤の太線）：期間外も含めて計算し、描くのは期間内だけ
    var ma = movingAvg(all, MA_WIN), mp = [];
    for (i = lo; i <= hi; i++) if (ma[i] !== null) mp.push(x(i).toFixed(1) + "," + y(ma[i]).toFixed(1));
    if (mp.length > 1) o.push('<polyline class="ma" points="' + mp.join(" ") + '"/>');

    // バランス調整日（期間内に入るものだけ）
    PATCHES.forEach(function (d) {
      for (i = 0; i < total; i++) {
        if (all[i].key >= d) {
          if (i >= lo && i <= hi) {
            var px2 = xe(i).toFixed(1);
            o.push('<line class="patch" x1="' + px2 + '" y1="' + padT + '" x2="' + px2 + '" y2="' + (padT + MH) + '"/>');
          }
          break;
        }
      }
    });

    // 出来高（縦の目盛りも期間内の最大に合わせる）
    var maxg = 1;
    for (i = lo; i <= hi; i++) if (all[i].games > maxg) maxg = all[i].games;
    [0, 0.5, 1].forEach(function (t) {
      var yy = vy1 - VH * t;
      o.push('<line class="' + (t === 0 ? "axis" : "grid") + '" x1="' + padL + '" y1="' + yy.toFixed(1) +
        '" x2="' + (padL + pw) + '" y2="' + yy.toFixed(1) + '"/>');
      o.push('<text class="tick" x="' + (padL + pw + 5) + '" y="' + (yy + 3.5).toFixed(1) + '">' +
        Math.round(maxg * t) + "</text>");
    });
    for (i = lo; i <= hi; i++) {
      var bh = VH * (all[i].games / maxg);
      o.push('<rect class="volbar" x="' + (xe(i) + step * 0.18).toFixed(1) +
        '" y="' + (vy1 - bh).toFixed(1) + '" width="' + Math.max(1, step * 0.64).toFixed(1) +
        '" height="' + bh.toFixed(1) + '" rx="' + Math.min(2, step * 0.2).toFixed(1) + '"/>');
    }

    // 横軸ラベル
    var used = [], yl = vy1 + 15, gap = nw ? 44 : 40;
    function room(px0) {
      for (var j = 0; j < used.length; j++) if (Math.abs(px0 - used[j]) < gap) return false;
      used.push(px0); return true;
    }
    var everyN = Math.max(1, Math.ceil(nb / (nw ? 4 : 9)));
    for (i = lo; i <= hi; i += everyN) {
      if (!room(x(i))) continue;
      o.push('<text class="tick" x="' + x(i).toFixed(1) + '" y="' + yl +
        '" text-anchor="middle">' + esc(fmtDate(all[i].key, S.unit)) + "</text>");
    }
    o.push('<text class="tick vlab" x="' + padL + '" y="' + (vy0 - 8) + '">プレイ回数</text>');

    // なぞると数字が出る
    o.push('<line class="xhair" x1="0" y1="' + padT + '" x2="0" y2="' + vy1 + '"/>');
    var unitLab = S.unit === "week" ? "の週" : "";
    for (i = lo; i <= hi; i++) {
      var b0 = all[i], ci = lohi[i];
      var lines = [(S.unit === "month" ? b0.key.slice(0, 7) : b0.key) + unitLab +
        (b0.season !== null ? "（シーズン" + b0.season + "）" : "")];
      if (b0.n) {
        lines.push("勝率 " + (b0.w / b0.n * 100).toFixed(1) + "%（" + b0.w + "勝" + (b0.n - b0.w) + "敗）");
        lines.push("95%信頼区間 " + (ci[1] * 100).toFixed(1) + "〜" + (ci[2] * 100).toFixed(1) + "%");
      }
      if (ma[i] !== null) lines.push("移動平均 " + (ma[i] * 100).toFixed(1) + "%");
      lines.push("プレイ回数 " + b0.games);
      o.push('<rect class="hit" x="' + xe(i).toFixed(1) + '" y="' + padT + '" width="' + step.toFixed(1) +
        '" height="' + (vy1 - padT) + '" data-cx="' + x(i).toFixed(1) + '" data-tip="' +
        esc(lines.join("\\n")) + '"/>');
    }
    o.push("</svg>");

    document.getElementById("chart").innerHTML = o.join("");
  }

  /* ---------- 期間内の集計 ---------- */
  function summary() {
    var b = S.buckets;
    if (!b.length) { document.getElementById("sum").innerHTML = ""; return; }
    var from = b[S.lo].key, to = b[S.hi].key;
    var rows = S.rows.filter(function (r) {
      var k = keyOf(r.battle_time_jst, S.unit);
      return k >= from && k <= to;
    });
    var wins = 0, dec = 0, i, r;
    for (i = 0; i < rows.length; i++) {
      if (rows[i].result === "draw") continue;
      dec++; if (rows[i].result === "win") wins++;
    }
    var wl = wilson(wins, dec), p = wl[0];

    var decks = {}, faces = {}, opp = {};
    for (i = 0; i < rows.length; i++) {
      r = rows[i];
      if (r.result === "draw") continue;
      var cards = (r.my_deck || "").split("|").filter(Boolean);
      var dk = cards.slice().sort().join("|");
      if (!decks[dk]) { decks[dk] = [0, 0]; faces[dk] = cards.slice(0, 8); }
      decks[dk][1]++; if (r.result === "win") decks[dk][0]++;
      var seen = {};
      (r.opp_deck || "").split("|").filter(Boolean).forEach(function (c) {
        if (seen[c]) return; seen[c] = 1;
        if (!opp[c]) opp[c] = [0, 0];
        opp[c][1]++; if (r.result === "win") opp[c][0]++;
      });
    }
    function best(obj, min, worst) {
      var k, out = null;
      for (k in obj) {
        if (obj[k][1] < min) continue;
        var v = obj[k][0] / obj[k][1];
        if (!out || (worst ? v < out.v : v > out.v)) out = { k: k, v: v, w: obj[k][0], n: obj[k][1] };
      }
      return out;
    }
    function img(c) {
      var u = S.icons[c];
      return u ? '<img src="' + esc(u) + '" alt="' + esc(c) + '">' : '<span class="noimg"></span>';
    }
    function box(lab, inner, w, n) {
      var q = wilson(w, n)[0];
      var t = q > p ? "up-t" : q < p ? "down-t" : "";
      return '<div class="hl"><span class="hl-lab">' + esc(lab) + "</span>" + inner +
        '<span class="hl-val ' + t + '">' + (q * 100).toFixed(1) +
        '<span class="hl-u">%</span></span><span class="hl-sub">' + w + "勝" + (n - w) + "敗</span></div>";
    }
    var boxes = [];
    var bd = best(decks, 5, false);
    if (bd) boxes.push(box("最も勝てているデッキ",
      '<div class="deck">' + faces[bd.k].map(img).join("") + "</div>", bd.w, bd.n));
    var wc = best(opp, 5, true), gc = best(opp, 5, false);
    if (wc) boxes.push(box("苦手な相手カード",
      '<div class="hl-card">' + img(wc.k) + "<b>" + esc(wc.k) + "</b></div>", wc.w, wc.n));
    if (gc) boxes.push(box("得意な相手カード",
      '<div class="hl-card">' + img(gc.k) + "<b>" + esc(gc.k) + "</b></div>", gc.w, gc.n));

    var html = '<table class="kv">' +
      '<tr><th>期間</th><td>' + esc(from) + " 〜 " + esc(to) + "</td></tr>" +
      '<tr><th>試合数</th><td>' + rows.length + " 試合</td></tr>" +
      '<tr><th>勝率</th><td class="' + (p > 0.5 ? "up" : p < 0.5 ? "down" : "") +
      '"><span class="big">' + (p * 100).toFixed(1) + '<span class="u">%</span></span></td></tr>' +
      '<tr><th>95%信頼区間</th><td>' + (wl[1] * 100).toFixed(1) + "% 〜 " +
      (wl[2] * 100).toFixed(1) + "%</td></tr>" +
      '<tr><th>勝敗</th><td><span class="up-t">' + wins + '勝</span> / <span class="down-t">' +
      (dec - wins) + "敗</span></td></tr></table>";
    if (boxes.length) html += '<div class="hl-grid" style="margin-top:12px">' + boxes.join("") + "</div>";
    document.getElementById("sum").innerHTML = html;
  }

  function refreshRange() {
    var a = document.getElementById("r1"), z = document.getElementById("r2");
    var nb = S.buckets.length;
    a.max = z.max = Math.max(0, nb - 1);
    a.value = S.lo; z.value = S.hi;
    document.getElementById("rlab").textContent =
      nb ? S.buckets[S.lo].key + " 〜 " + S.buckets[S.hi].key : "-";
    if (window.crFill) crFill();
  }

  function rebuild(keepRange) {
    var rows = S.all.filter(function (r) { return MODE === "all" || classify(r) === MODE; });
    S.rows = rows;
    S.buckets = bucketize(rows, S.unit);
    var w = 0, n = 0;
    rows.forEach(function (r) { if (r.result !== "draw") { n++; if (r.result === "win") w++; } });
    S.overall = n ? w / n : 0.5;
    if (!keepRange) { S.lo = 0; S.hi = Math.max(0, S.buckets.length - 1); }
    S.hi = Math.min(S.hi, Math.max(0, S.buckets.length - 1));
    S.lo = Math.min(S.lo, S.hi);
    refreshRange(); draw(); summary();
  }

  function bind() {
    ["day", "week", "month"].forEach(function (u) {
      var el = document.getElementById("u-" + u);
      if (!el) return;
      el.onclick = function () {
        S.unit = u;
        ["day", "week", "month"].forEach(function (v) {
          document.getElementById("u-" + v).className = "ubtn" + (v === u ? " on" : "");
        });
        rebuild(false);
      };
    });
    var a = document.getElementById("r1"), z = document.getElementById("r2");
    a.oninput = function () {
      S.lo = Math.min(+a.value, +z.value); S.hi = Math.max(+a.value, +z.value);
      refreshRange(); draw(); summary();
    };
    z.oninput = a.oninput;
    [["p-all", 0], ["p-90", 90], ["p-30", 30], ["p-7", 7]].forEach(function (q) {
      var el = document.getElementById(q[0]);
      if (!el) return;
      el.onclick = function () {
        ["p-all", "p-90", "p-30", "p-7"].forEach(function (id) {
          var e2 = document.getElementById(id);
          if (e2) e2.className = "ubtn" + (id === q[0] ? " on" : "");
        });
        var nb = S.buckets.length;
        S.hi = nb - 1;
        if (!q[1]) { S.lo = 0; }
        else {
          var d = new Date(); d.setDate(d.getDate() - q[1]);
          var cut = d.toISOString().slice(0, 10), j;
          S.lo = 0;
          for (j = 0; j < nb; j++) if (S.buckets[j].key >= cut) { S.lo = j; break; }
        }
        refreshRange(); draw(); summary();
      };
    });
    var btn = document.getElementById("lytbtn");
    if (btn) btn.addEventListener("click", function () { setTimeout(function () { draw(); }, 0); });
  }

  function boot() {
    fetch("battles.csv", { cache: "no-store" }).then(function (r) { return r.text(); })
      .then(function (t) {
        S.all = parseCSV(t).filter(function (r) { return r.battle_time_jst; })
          .sort(function (x, y) { return x.battle_time_jst < y.battle_time_jst ? -1 : 1; });
        return fetch("cards.json", { cache: "no-store" }).then(function (r) { return r.json(); })
          .catch(function () { return { cards: {} }; });
      })
      .then(function (c) { S.icons = (c && c.cards) || {}; bind(); rebuild(false); })
      .catch(function (e) {
        document.getElementById("chart").innerHTML =
          '<p class="empty">データを読み込めなかった。' + esc(e) + "</p>";
      });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
"""

RANK_JS = """(function () {
  var MODE = "__MODE__";
  var PAGE = "__PAGE__";          // deck / enemy
  var RELIABLE_N = 20, MIN_CARD_N = 5, TOP_CARDS = 10;
  var S = { rows: [], days: [], lo: 0, hi: 0, icons: {} };

  function narrow() {
    return document.documentElement.getAttribute("data-layout") === "narrow";
  }
  function esc(t) {
    return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function parseCSV(text) {
    var rows = [], row = [], cell = "", q = false, i, c;
    for (i = 0; i < text.length; i++) {
      c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else { q = false; } }
        else { cell += c; }
      } else if (c === '"') { q = true; }
      else if (c === ",") { row.push(cell); cell = ""; }
      else if (c === "\\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
      else if (c !== "\\r") { cell += c; }
    }
    if (cell.length || row.length) { row.push(cell); rows.push(row); }
    if (!rows.length) return [];
    var head = rows.shift().map(function (h) { return h.replace(/^\\uFEFF/, "").trim(); });
    return rows.filter(function (r) { return r.length === head.length; }).map(function (r) {
      var o = {}, k;
      for (k = 0; k < head.length; k++) o[head[k]] = r[k];
      return o;
    });
  }
  function classify(r) {
    var t = (r.battle_type || "").toLowerCase();
    if (t.indexOf("pathoflegend") >= 0) return "pol";
    return "etc";
  }
  function wilson(w, n) {
    if (!n) return [0, 0, 0];
    var z = 1.96, p = w / n, d = 1 + z * z / n;
    var c = (p + z * z / (2 * n)) / d;
    var m = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
    return [p, Math.max(0, c - m), Math.min(1, c + m)];
  }
  function tone(p, base, n) {
    if (n < RELIABLE_N) return "na";
    return p > base ? "up" : p < base ? "down" : "na";
  }
  function icon(c, x, y, w, h) {
    var u = S.icons[c];
    if (!u) return '<rect class="noicon" x="' + x.toFixed(1) + '" y="' + y.toFixed(1) +
      '" width="' + w + '" height="' + h + '" rx="2"/>';
    return '<image href="' + esc(u) + '" x="' + x.toFixed(1) + '" y="' + y.toFixed(1) +
      '" width="' + w + '" height="' + h + '" preserveAspectRatio="xMidYMid meet"><title>' +
      esc(c) + "</title></image>";
  }

  /* ---------- 図 ---------- */
  function wideRows(items, base, mode, blab) {
    var rh = mode === "none" ? 42 : mode === "deck" ? 46 : 54;
    var top = 36, W = 720, H = top + rh * items.length + 4;
    var x0 = mode === "deck" ? 216 : 210, x1 = 520, sp = x1 - x0;
    var px = function (v) { return x0 + sp * v; };
    var o = ['<svg viewBox="0 0 ' + W + ' ' + H + '" class="chart">'];
    [0, 0.25, 0.5, 0.75, 1].forEach(function (g) {
      var gx = px(g);
      o.push('<line class="gridv" x1="' + gx.toFixed(1) + '" y1="' + (top - 10) + '" x2="' +
        gx.toFixed(1) + '" y2="' + (H - 4) + '"/>');
      o.push('<text class="gtick" x="' + gx.toFixed(1) + '" y="' + (top - 14) +
        '" text-anchor="middle">' + (g * 100) + "</text>");
    });
    var bx = px(base);
    o.push('<line class="base" x1="' + bx.toFixed(1) + '" y1="' + (top - 10) + '" x2="' +
      bx.toFixed(1) + '" y2="' + (H - 4) + '"/>');
    o.push('<text class="baselab" x="' + bx.toFixed(1) + '" y="' + (top - 26) +
      '" text-anchor="middle">' + esc(blab) + "</text>");
    items.forEach(function (it, i) {
      var y = top + rh * i + rh / 2, r = wilson(it.w, it.n), cls = tone(r[0], base, it.n);
      o.push('<line class="hair" x1="0" y1="' + (y + rh / 2).toFixed(1) + '" x2="' + W +
        '" y2="' + (y + rh / 2).toFixed(1) + '"/>');
      if (mode === "deck") {
        it.cards.slice(0, 8).forEach(function (c, j) { o.push(icon(c, j * 25, y - 14, 22, 27)); });
      } else if (mode === "single") {
        o.push(icon(it.cards[0], 0, y - 19, 32, 38));
        o.push('<text class="lab" x="40" y="' + (y + 5).toFixed(1) + '">' + esc(it.label) + "</text>");
      } else {
        o.push('<text class="lab" x="0" y="' + (y + 5).toFixed(1) + '">' + esc(it.label) + "</text>");
      }
      o.push('<rect class="band ' + cls + '" x="' + px(r[1]).toFixed(1) + '" y="' + (y - 4).toFixed(1) +
        '" width="' + Math.max(10, px(r[2]) - px(r[1])).toFixed(1) + '" height="8" rx="4"/>');
      o.push('<circle class="mark ' + cls + '" cx="' + px(r[0]).toFixed(1) + '" cy="' +
        y.toFixed(1) + '" r="5.5"/>');
      o.push('<text class="val ' + cls + '" x="600" y="' + (y + 7).toFixed(1) +
        '" text-anchor="end">' + (r[0] * 100).toFixed(1) + '<tspan class="unit">%</tspan></text>');
      o.push('<text class="n" x="' + W + '" y="' + (y + 5).toFixed(1) + '" text-anchor="end">' +
        it.w + "勝" + (it.n - it.w) + "敗</text>");
    });
    o.push("</svg>");
    return o.join("");
  }

  function narrowRows(items, base, mode, blab) {
    var W = 380;
    var rh = mode === "deck" ? 106 : mode === "single" ? 90 : 64;
    var top = mode === "deck" ? 34 : 44, H = top + rh * items.length + 6;
    var x0 = mode === "deck" ? 162 : 24, x1 = mode === "deck" ? 372 : 286, sp = x1 - x0;
    var px = function (v) { return x0 + sp * v; };
    var o = ['<svg viewBox="0 0 ' + W + ' ' + H + '" class="chart">'];
    [0, 0.25, 0.5, 0.75, 1].forEach(function (g) {
      var gx = px(g);
      o.push('<line class="gridv" x1="' + gx.toFixed(1) + '" y1="' + (top - 12) + '" x2="' +
        gx.toFixed(1) + '" y2="' + (H - 6) + '"/>');
      o.push('<text class="gtick" x="' + gx.toFixed(1) + '" y="' + (top - 16) +
        '" text-anchor="middle">' + (g * 100) + "</text>");
    });
    o.push('<line class="base" x1="' + px(base).toFixed(1) + '" y1="' + (top - 12) + '" x2="' +
      px(base).toFixed(1) + '" y2="' + (H - 6) + '"/>');
    o.push('<text class="baselab" x="' + px(base).toFixed(1) + '" y="' + (top - 28) +
      '" text-anchor="middle">' + esc(blab) + "</text>");
    items.forEach(function (it, i) {
      var by0 = top + rh * i + 4, r = wilson(it.w, it.n), cls = tone(r[0], base, it.n), by;
      var rec = it.w + "勝" + (it.n - it.w) + "敗";
      if (mode === "deck") {
        var iw = 34, ih = 41, g = 3;
        it.cards.slice(0, 8).forEach(function (c, j) {
          o.push(icon(c, (j % 4) * (iw + g), by0 + Math.floor(j / 4) * (ih + g), iw, ih));
        });
        o.push('<text class="val ' + cls + '" x="' + W + '" y="' + (by0 + 26) +
          '" text-anchor="end">' + (r[0] * 100).toFixed(1) + '<tspan class="unit">%</tspan></text>');
        o.push('<text class="n" x="' + W + '" y="' + (by0 + 44) + '" text-anchor="end">' + rec + "</text>");
        by = by0 + 70;
      } else {
        o.push('<text class="n" x="' + W + '" y="' + (by0 + 13) + '" text-anchor="end">' + rec + "</text>");
        if (mode === "single") {
          o.push(icon(it.cards[0], 0, by0, 38, 46));
          o.push('<text class="lab" x="46" y="' + (by0 + 28) + '">' + esc(it.label) + "</text>");
          by = by0 + 64;
        } else {
          o.push('<text class="lab" x="0" y="' + (by0 + 13) + '">' + esc(it.label) + "</text>");
          by = by0 + 38;
        }
        o.push('<text class="val ' + cls + '" x="' + W + '" y="' + (by + 7) +
          '" text-anchor="end">' + (r[0] * 100).toFixed(1) + '<tspan class="unit">%</tspan></text>');
      }
      o.push('<rect class="band ' + cls + '" x="' + px(r[1]).toFixed(1) + '" y="' + (by - 4) +
        '" width="' + Math.max(8, px(r[2]) - px(r[1])).toFixed(1) + '" height="8" rx="4"/>');
      o.push('<circle class="mark ' + cls + '" cx="' + px(r[0]).toFixed(1) + '" cy="' +
        by + '" r="5.5"/>');
      o.push('<line class="hair" x1="0" y1="' + (by0 + rh - 14) + '" x2="' + W +
        '" y2="' + (by0 + rh - 14) + '"/>');
    });
    o.push("</svg>");
    return o.join("");
  }

  function rows(items, base, mode, blab) {
    if (!items.length) return '<p class="empty">該当するデータがない。</p>';
    return '<div class="wideonly">' + wideRows(items, base, mode, blab) + "</div>" +
      '<div class="narrowonly">' + narrowRows(items, base, mode, blab) + "</div>";
  }

  /* ---------- 集計と描画 ---------- */
  function render() {
    var from = S.days[S.lo], to = S.days[S.hi];
    var rs = S.rows.filter(function (r) {
      var d = r.battle_time_jst.slice(0, 10);
      return d >= from && d <= to;
    });
    var wins = 0, dec = 0;
    rs.forEach(function (r) { if (r.result !== "draw") { dec++; if (r.result === "win") wins++; } });
    var base = dec ? wins / dec : 0.5;
    var blab = "平均 " + (base * 100).toFixed(0) + "%";
    document.getElementById("rlab").textContent = from + " 〜 " + to +
      "（" + rs.length + "試合・勝率 " + (base * 100).toFixed(1) + "%）";

    if (PAGE === "deck") {
      var decks = {}, faces = {}, mine = {};
      rs.forEach(function (r) {
        if (r.result === "draw") return;
        var cs = (r.my_deck || "").split("|").filter(Boolean);
        var k = cs.slice().sort().join("|");
        if (!decks[k]) { decks[k] = [0, 0]; faces[k] = cs.slice(0, 8); }
        decks[k][1]++; if (r.result === "win") decks[k][0]++;
        var seen = {};
        cs.forEach(function (c) {
          if (seen[c]) return; seen[c] = 1;
          if (!mine[c]) mine[c] = [0, 0];
          mine[c][1]++; if (r.result === "win") mine[c][0]++;
        });
      });
      var dl = Object.keys(decks).map(function (k) {
        return { label: "", cards: faces[k], w: decks[k][0], n: decks[k][1] };
      }).sort(function (a, b) { return b.n - a.n; }).slice(0, 8);
      var vary = Object.keys(mine).filter(function (c) { return mine[c][1] < dec; });
      var ml = vary.map(function (c) {
        return { label: c, cards: [c], w: mine[c][0], n: mine[c][1] };
      }).sort(function (a, b) { return b.n - a.n; }).slice(0, TOP_CARDS);
      document.getElementById("s1").innerHTML = rows(dl, base, "deck", blab);
      document.getElementById("s2").innerHTML = rows(ml, base, "single", blab);
      document.getElementById("n1").textContent =
        "使用したデッキ構成は" + Object.keys(decks).length + "種類。試合数の多い順に上位8件。";
      document.getElementById("n2").textContent =
        "全試合に含まれる固定枠" + (Object.keys(mine).length - vary.length) + "枚は除外している。";
    } else {
      var opp = {};
      rs.forEach(function (r) {
        if (r.result === "draw") return;
        var seen = {};
        (r.opp_deck || "").split("|").filter(Boolean).forEach(function (c) {
          if (seen[c]) return; seen[c] = 1;
          if (!opp[c]) opp[c] = [0, 0];
          opp[c][1]++; if (r.result === "win") opp[c][0]++;
        });
      });
      var ok = Object.keys(opp).filter(function (c) { return opp[c][1] >= MIN_CARD_N; })
        .sort(function (a, b) { return opp[a][0] / opp[a][1] - opp[b][0] / opp[b][1]; });
      var mk = function (c) { return { label: c, cards: [c], w: opp[c][0], n: opp[c][1] }; };
      document.getElementById("s1").innerHTML = rows(ok.slice(0, TOP_CARDS).map(mk), base, "single", blab);
      document.getElementById("s2").innerHTML =
        rows(ok.slice().reverse().slice(0, TOP_CARDS).map(mk), base, "single", blab);
      document.getElementById("n1").textContent = MIN_CARD_N + "試合以上対戦したカードのみ（全" +
        Object.keys(opp).length + "種類のうち" + ok.length + "種類）。";
    }
  }

  function refresh() {
    var a = document.getElementById("r1"), z = document.getElementById("r2");
    a.max = z.max = Math.max(0, S.days.length - 1);
    a.value = S.lo; z.value = S.hi;
    if (window.crFill) crFill();
    render();
  }

  function bind() {
    var a = document.getElementById("r1"), z = document.getElementById("r2");
    a.oninput = function () {
      S.lo = Math.min(+a.value, +z.value); S.hi = Math.max(+a.value, +z.value);
      refresh();
    };
    z.oninput = a.oninput;
    [["p-all", 0], ["p-90", 90], ["p-30", 30], ["p-7", 7]].forEach(function (q) {
      var el = document.getElementById(q[0]);
      if (!el) return;
      el.onclick = function () {
        ["p-all", "p-90", "p-30", "p-7"].forEach(function (id) {
          var e2 = document.getElementById(id);
          if (e2) e2.className = "ubtn" + (id === q[0] ? " on" : "");
        });
        S.hi = S.days.length - 1;
        if (!q[1]) { S.lo = 0; }
        else {
          var d = new Date(); d.setDate(d.getDate() - q[1]);
          var cut = d.toISOString().slice(0, 10), j;
          S.lo = 0;
          for (j = 0; j < S.days.length; j++) if (S.days[j] >= cut) { S.lo = j; break; }
        }
        refresh();
      };
    });
    var btn = document.getElementById("lytbtn");
    if (btn) btn.addEventListener("click", function () { setTimeout(render, 0); });
  }

  function boot() {
    fetch("battles.csv", { cache: "no-store" }).then(function (r) { return r.text(); })
      .then(function (t) {
        S.rows = parseCSV(t).filter(function (r) { return r.battle_time_jst; })
          .filter(function (r) { return MODE === "all" || classify(r) === MODE; })
          .sort(function (x, y) { return x.battle_time_jst < y.battle_time_jst ? -1 : 1; });
        var seen = {};
        S.rows.forEach(function (r) {
          var d = r.battle_time_jst.slice(0, 10);
          if (!seen[d]) { seen[d] = 1; S.days.push(d); }
        });
        S.days.sort();
        S.lo = 0; S.hi = Math.max(0, S.days.length - 1);
        return fetch("cards.json", { cache: "no-store" }).then(function (r) { return r.json(); })
          .catch(function () { return { cards: {} }; });
      })
      .then(function (c) { S.icons = (c && c.cards) || {}; bind(); refresh(); })
      .catch(function (e) {
        document.getElementById("s1").innerHTML =
          '<p class="empty">データを読み込めなかった。' + esc(e) + "</p>";
      });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
"""

SCRIPT = """
function crLayout(m){
  document.documentElement.setAttribute('data-layout', m);
  try{ localStorage.setItem('crLayout', m); }catch(e){}
  var b = document.getElementById('lytbtn');
  if(b) b.textContent = (m === 'narrow') ? 'スマホ表示' : 'PC表示';
}
function crToggle(){
  crLayout(document.documentElement.getAttribute('data-layout') === 'narrow' ? 'wide' : 'narrow');
}
(function(){
  var saved = null;
  try{ saved = localStorage.getItem('crLayout'); }catch(e){}
  var ua = navigator.userAgent || '';
  var mob = /Android|iPhone|iPod|iPad|Mobile|Silk|Kindle/i.test(ua)
         || (/Mac/.test(navigator.platform) && navigator.maxTouchPoints > 1);
  document.documentElement.setAttribute('data-layout', saved || (mob ? 'narrow' : 'wide'));
})();
document.addEventListener('DOMContentLoaded', function(){
  crLayout(document.documentElement.getAttribute('data-layout'));
  var tabs = document.querySelector('.tabs'), on = tabs && tabs.querySelector('a.on');
  if(on && on.offsetLeft + on.offsetWidth > tabs.clientWidth) tabs.scrollLeft = on.offsetLeft - 24;
});
function crFill(){
  var a = document.getElementById('r1'), z = document.getElementById('r2'),
      f = document.getElementById('rfill');
  if(!a || !z || !f) return;
  var m = +a.max || 0, lo = Math.min(+a.value, +z.value), hi = Math.max(+a.value, +z.value);
  var p = function(v){ return m ? v / m : 0; };
  f.style.left = 'calc(8px + (100% - 16px) * ' + p(lo) + ')';
  f.style.width = 'calc((100% - 16px) * ' + Math.max(0, p(hi) - p(lo)) + ')';
}
document.addEventListener('input', function(e){
  var t = e.target;
  if(t && (t.id === 'r1' || t.id === 'r2')){
    crFill();
    var g = document.querySelectorAll('[id^="p-"]');
    for(var i = 0; i < g.length; i++) g[i].classList.remove('on');
  }
});
(function(){
  var tip = null, cur = null, hair = null;
  function hide(){
    if(tip) tip.style.opacity = 0;
    if(hair) hair.style.opacity = 0;
    cur = null; hair = null;
  }
  function show(el, x, y){
    if(!tip){ tip = document.createElement('div'); tip.id = 'crtip'; document.body.appendChild(tip); }
    if(cur !== el){
      tip.textContent = el.getAttribute('data-tip');
      if(hair) hair.style.opacity = 0;
      var svg = el.ownerSVGElement, cx = el.getAttribute('data-cx');
      hair = svg ? svg.querySelector('.xhair') : null;
      if(hair && cx){ hair.setAttribute('x1', cx); hair.setAttribute('x2', cx); hair.style.opacity = .4; }
      cur = el;
    }
    var w = tip.offsetWidth, h = tip.offsetHeight, vw = window.innerWidth;
    var left = x + 16; if(left + w > vw - 8) left = x - w - 16; if(left < 8) left = 8;
    var top = y - h - 14; if(top < 8) top = y + 18;
    tip.style.left = left + 'px'; tip.style.top = top + 'px'; tip.style.opacity = 1;
  }
  function move(e){
    var el = e.target && e.target.closest ? e.target.closest('[data-tip]') : null;
    if(el) show(el, e.clientX, e.clientY); else if(cur) hide();
  }
  document.addEventListener('pointermove', move);
  document.addEventListener('pointerdown', move);
  document.addEventListener('pointerleave', hide);
  window.addEventListener('scroll', hide, {passive: true});
})();
"""

CSS = """
:root{
  color-scheme:light;
  --page:#FFFFFF;--sunk:#F3F4F6;--ink:#1C2126;--ink2:#545C66;--ink3:#868E97;
  --rule:#E6E8EC;--rule2:#CDD2D8;
  --accent:#BF0000;--up:#C8102E;--down:#0B57A4;--na:#98A0A9;
  --upbg:#FBECEE;--downbg:#E9F0F9;--nabg:#EFF1F3;
  --upband:#F3C9D0;--downband:#C6D8EE;--naband:#DEE2E6;
  --ult:#6E3BB8;--link:#0B57A4;
  --line:var(--rule);--label:var(--ink2);--labelbg:var(--sunk);--panel:var(--page);
  --font:"IBM Plex Sans JP","Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic UI",
    "Yu Gothic","Meiryo",sans-serif;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--page);color:var(--ink);font-family:var(--font);
  font-size:14px;line-height:1.7;-webkit-font-smoothing:antialiased;
  font-variant-numeric:tabular-nums}
button{font-family:inherit}
a{color:var(--link)}
:focus-visible{outline:2px solid var(--down);outline-offset:2px;border-radius:4px}

/* ---------- 上部の帯 ---------- */
.top{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.94);
  -webkit-backdrop-filter:saturate(1.4) blur(8px);backdrop-filter:saturate(1.4) blur(8px);
  border-bottom:1px solid var(--rule)}
.bar{max-width:960px;margin:0 auto;padding:12px 24px 2px;display:flex;align-items:center;gap:20px}
.brand{display:flex;align-items:center;gap:9px;color:var(--ink);text-decoration:none;
  font-size:16px;font-weight:700;letter-spacing:.01em;white-space:nowrap}
.brand i{display:block;width:4px;height:18px;border-radius:1px;background:var(--accent)}
.lyt{margin-left:auto;font-size:12px;color:var(--ink2);background:none;border:1px solid var(--rule2);
  border-radius:6px;padding:4px 10px;cursor:pointer;white-space:nowrap}
.lyt:hover{color:var(--ink);border-color:var(--ink3)}
.tabs{max-width:960px;margin:0 auto;padding:0 24px;display:flex;gap:2px;overflow-x:auto;
  scrollbar-width:none;font-feature-settings:"palt"}
.tabs::-webkit-scrollbar{display:none}
.tabs a{display:block;padding:10px 12px 9px;color:var(--ink2);text-decoration:none;font-size:14px;
  border-bottom:2px solid transparent;white-space:nowrap;letter-spacing:.02em}
.tabs a:first-child{margin-left:-12px}
.tabs a:hover{color:var(--ink)}
.tabs a.on{color:var(--ink);font-weight:700;border-bottom-color:var(--accent)}

/* ---------- 切り替えボタン（つながった一組） ---------- */
.seg{display:inline-flex;align-items:center;background:var(--sunk);border-radius:8px;padding:3px;gap:2px}
.seg a,.seg .ubtn{display:block;border:0;background:none;color:var(--ink2);font-size:12.5px;
  line-height:1.5;padding:4px 12px;border-radius:6px;text-decoration:none;cursor:pointer;
  white-space:nowrap}
.seg a:hover,.seg .ubtn:hover{color:var(--ink)}
.seg a.on,.seg .ubtn.on{background:#fff;color:var(--ink);font-weight:700;
  box-shadow:0 1px 2px rgba(28,33,38,.14),0 0 0 1px rgba(28,33,38,.04)}
.modes a.on{color:var(--accent)}
.toolbar{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;
  gap:10px 24px;margin:0 0 16px}
.tgroup{display:flex;align-items:center;gap:10px}
.tl{font-size:12px;color:var(--ink3)}
.navlab{font-size:12px;color:var(--ink3)}

/* ---------- 本文 ---------- */
.wrap{max-width:960px;margin:0 auto;padding:32px 24px 72px}
.head{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;
  gap:6px 20px;margin:0 0 36px}
.head h1{margin:0;font-size:26px;line-height:1.3;font-weight:700;letter-spacing:.01em;
  font-feature-settings:"palt"}
.head p{margin:0;font-size:12px;color:var(--ink3)}
.panel{margin:0 0 56px}
.panel h2{position:relative;margin:0 0 16px;padding:0 0 10px;font-size:17px;font-weight:700;
  line-height:1.4;letter-spacing:.02em;border-bottom:2px solid var(--rule);
  font-feature-settings:"palt"}
.panel h2::after{content:"";position:absolute;left:0;bottom:-2px;width:48px;height:2px;
  background:var(--accent)}
.lead{margin:-4px 0 18px;max-width:46em;color:var(--ink2);font-size:13px}
.sub2{margin:28px 0 8px;font-size:14px;font-weight:700}
.note{position:relative;margin:14px 0 0;padding-left:1.3em;max-width:52em;color:var(--ink3);
  font-size:12px;line-height:1.75}
.note::before{content:"※";position:absolute;left:0}
.note:empty{display:none}
.empty{margin:4px 0;color:var(--ink3);font-size:13px}
.sname,.sub{display:block;font-size:11.5px;font-weight:400;color:var(--ink3);line-height:1.5}

/* ---------- 数値の表 ---------- */
table.kv{width:100%;border-collapse:collapse;border-top:1px solid var(--rule2)}
table.kv th{width:34%;padding:13px 16px 13px 0;border-bottom:1px solid var(--rule);
  color:var(--ink2);font-size:13px;font-weight:400;text-align:left;vertical-align:top}
table.kv td{padding:13px 0;border-bottom:1px solid var(--rule);text-align:right;
  font-size:15px;font-weight:500;vertical-align:top}
table.kv td.up{color:var(--up)}
table.kv td.down{color:var(--down)}
.big{font-size:30px;font-weight:700;line-height:1.15;letter-spacing:-.01em}
.big .u{margin-left:2px;font-size:13px;font-weight:400;color:var(--ink3)}
.up-t{color:var(--up)}.down-t{color:var(--down)}.na-t{color:var(--na)}
.stxt{display:flex;flex-direction:column;align-items:flex-end;line-height:1.35}
.stxt .big{font-size:28px}
.lgname{font-size:13px;font-weight:700;letter-spacing:.01em}
.lgname.big2{font-size:18px}
.mdeck{display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.mdeck .deck{grid-template-columns:repeat(8,1fr);gap:3px;width:100%;max-width:320px}

/* ---------- 横並びの勝率図 ---------- */
.chart{display:block;width:100%;height:auto;overflow:visible}
.hair{stroke:var(--rule);stroke-width:1}
.gridv{stroke:var(--rule);stroke-width:1}
.gtick{font-size:10px;fill:var(--ink3)}
.base{stroke:var(--ink3);stroke-width:1;stroke-dasharray:2 3}
.baselab{font-size:10.5px;font-weight:500;fill:var(--ink2)}
.lab{font-size:13px;fill:var(--ink)}
.lab.small{font-size:12px}
.noicon{fill:var(--sunk);stroke:var(--rule)}
.band.up{fill:var(--upband)}.band.down{fill:var(--downband)}.band.na{fill:var(--naband)}
.mark{stroke:#fff;stroke-width:2}
.mark.up{fill:var(--up)}.mark.down{fill:var(--down)}.mark.na{fill:var(--na)}
.val{font-size:17px;font-weight:700}
.val.up{fill:var(--up)}.val.down{fill:var(--down)}.val.na{fill:var(--na)}
.unit{font-size:11px;font-weight:400;fill:var(--ink3)}
.n{font-size:12px;fill:var(--ink2)}
.keys{display:flex;flex-wrap:wrap;gap:8px 22px;font-size:12.5px;color:var(--ink2)}
.keys span{display:inline-flex;align-items:center;gap:8px}
.sw{position:relative;display:inline-block;width:30px;height:12px}
.sw::before{content:"";position:absolute;left:0;right:0;top:4px;height:5px;border-radius:3px;
  background:var(--b)}
.sw::after{content:"";position:absolute;left:10px;top:1px;width:10px;height:10px;border-radius:50%;
  background:var(--c);box-shadow:0 0 0 1.5px #fff}
.sw-up{--b:var(--upband);--c:var(--up)}
.sw-down{--b:var(--downband);--c:var(--down)}
.sw-na{--b:var(--naband);--c:var(--na)}

/* ---------- 時系列の図 ---------- */
.plot{fill:none;stroke:none}
.grid{stroke:var(--rule);stroke-width:1}
.axis{stroke:var(--rule2);stroke-width:1}
.monthsep{stroke:var(--rule2);stroke-width:1;stroke-dasharray:2 3}
.seasonsep{stroke:var(--ink3);stroke-width:1;stroke-dasharray:3 3}
.seasonlab{font-size:11px;font-weight:700;fill:var(--ink2)}
.fifty{stroke:var(--ink3);stroke-width:1;stroke-dasharray:3 3}
.tick{font-size:10.5px;fill:var(--ink3)}
.tick.mon{fill:var(--ink2);font-weight:500}
.tick.vlab{font-size:11px;fill:var(--ink2)}
.ciband{fill:#7E8892;opacity:.12}
.cistick{stroke:#7E8892;stroke-width:6;opacity:.22;stroke-linecap:round}
.rate{fill:none;stroke:var(--ink);stroke-width:1.25;stroke-linejoin:round}
.pt{fill:var(--ink);stroke:#fff;stroke-width:1.5}
.pt.last{fill:var(--up)}
.ma{fill:none;stroke:var(--up);stroke-width:2.25;stroke-linejoin:round;stroke-linecap:round}
.patch{stroke:var(--down);stroke-width:1;stroke-dasharray:3 3}
.volbar{fill:#B3BECA}
.volfaint{fill:#8796A8;opacity:.2}
.ultband{fill:var(--ult);opacity:.075}
.ultlab{font-size:10.5px;font-weight:500;fill:var(--ult)}
.xhair{stroke:var(--ink);stroke-width:1;opacity:0;pointer-events:none}
.hit{fill:transparent;cursor:crosshair}
#crtip{position:fixed;z-index:60;max-width:270px;padding:9px 12px;border-radius:8px;
  background:#1C2126;color:#fff;font-size:12px;line-height:1.6;white-space:pre-line;
  pointer-events:none;opacity:0;transition:opacity .08s;
  box-shadow:0 6px 18px rgba(28,33,38,.22)}
.legend2{display:flex;flex-wrap:wrap;gap:6px 22px;margin:14px 0 0;font-size:12px;color:var(--ink2)}
.legend2 span{display:inline-flex;align-items:center;gap:8px}
.lgline{display:inline-block;width:22px;height:0;border-top-width:2px;border-top-style:solid}
.lgbox{display:inline-block;width:14px;height:12px;border-radius:3px}

/* ---------- 期間のつまみ ---------- */
.rng{margin:18px 0 0}
.rlab{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  margin:0 0 4px;font-size:12px;color:var(--ink3)}
.rlab b{color:var(--ink);font-weight:500}
.dual{position:relative;height:24px}
.dual::before{content:"";position:absolute;left:8px;right:8px;top:10px;height:4px;
  border-radius:2px;background:var(--rule)}
.dual-fill{position:absolute;top:10px;height:4px;border-radius:2px;background:var(--ink);
  left:8px;width:calc(100% - 16px)}
.dual input{position:absolute;left:0;top:0;width:100%;height:24px;margin:0;padding:0;
  background:none;pointer-events:none;-webkit-appearance:none;appearance:none}
.dual input::-webkit-slider-runnable-track{height:24px;background:none}
.dual input::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;pointer-events:auto;
  width:16px;height:16px;margin-top:4px;border-radius:50%;background:#fff;
  border:2px solid var(--ink);box-shadow:0 1px 3px rgba(28,33,38,.2);cursor:ew-resize}
.dual input::-moz-range-track{height:24px;background:none}
.dual input::-moz-range-thumb{pointer-events:auto;width:12px;height:12px;border-radius:50%;
  background:#fff;border:2px solid var(--ink);box-shadow:0 1px 3px rgba(28,33,38,.2);cursor:ew-resize}
.dual input:focus-visible{outline:none}
.dual input:focus-visible::-webkit-slider-thumb{box-shadow:0 0 0 3px rgba(11,87,164,.35)}

/* ---------- 目立つところ（推移ページ下） ---------- */
.hl-grid{display:grid;grid-template-columns:repeat(3,1fr);margin-top:24px;
  border-top:1px solid var(--rule2);border-bottom:1px solid var(--rule)}
.hl{display:flex;flex-direction:column;gap:8px;padding:16px 18px 18px;border-left:1px solid var(--rule)}
.hl:first-child{padding-left:0;border-left:0}
.hl-lab{font-size:12px;color:var(--ink2)}
.hl-val{font-size:26px;font-weight:700;line-height:1.1}
.hl-u{margin-left:1px;font-size:12px;font-weight:400;color:var(--ink3)}
.hl-sub{margin-top:-4px;font-size:11.5px;color:var(--ink3)}
.hl-card{display:flex;align-items:center;gap:10px;min-height:42px}
.hl-card img,.hl-card .noimg{display:block;width:34px;aspect-ratio:5/6;border-radius:4px}
.hl-card .noimg{background:var(--sunk);border:1px solid var(--rule)}
.hl-card b{font-size:13.5px;font-weight:700}
.hl-card b.wide{font-size:14px}
.hl .deck{grid-template-columns:repeat(4,1fr);gap:3px;max-width:156px}

/* ---------- カード画像 ---------- */
.deck{display:grid;grid-template-columns:repeat(4,1fr);gap:3px}
.deck img,.deck .noimg{display:block;width:100%;aspect-ratio:5/6;border-radius:4px}
.deck .noimg{background:var(--sunk);border:1px solid var(--rule)}

/* ---------- 対戦記録 ---------- */
.log{position:relative;padding:16px 0 18px 16px;border-bottom:1px solid var(--rule)}
.log:first-child{border-top:1px solid var(--rule2)}
.log::before{content:"";position:absolute;left:0;top:16px;bottom:18px;width:3px;border-radius:2px;
  background:var(--na)}
.log.win::before{background:var(--up)}
.log.lose::before{background:var(--down)}
.log header{display:flex;align-items:baseline;gap:14px;margin:0 0 4px;font-size:12px;color:var(--ink3)}
.log header .when{color:var(--ink2);font-weight:500}
.log header .mode{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.log header .tro{font-weight:700}
.oppinfo{display:flex;flex-wrap:wrap;align-items:center;gap:2px 14px;margin:0 0 12px;
  font-size:12px;color:var(--ink2)}
.oppinfo b{color:var(--ink);font-weight:700}
.rivaltag{display:inline-block;padding:0 7px;border-radius:4px;background:var(--upbg);
  color:var(--up);font-size:11px;font-weight:700;line-height:1.7}
.duel{display:grid;grid-template-columns:1fr auto 1fr;gap:18px;align-items:center}
html[data-layout="wide"] .log .deck{grid-template-columns:repeat(8,1fr);gap:2px}
.hp{margin:6px 0 0;font-size:11px;color:var(--ink3);text-align:center}
.mid{min-width:72px;text-align:center}
.badge{display:inline-flex;align-items:center;justify-content:center;width:44px;height:30px;
  border-radius:7px;background:var(--nabg);color:var(--na);font-size:15px;font-weight:700}
.badge.win{background:var(--upbg);color:var(--up)}
.badge.lose{background:var(--downbg);color:var(--down)}
.crowns{display:block;margin-top:6px;font-size:16px;font-weight:700;letter-spacing:.04em}

/* ---------- 強敵 ---------- */
.rivalwrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.rivals{width:100%;border-collapse:collapse;font-size:13px}
table.rivals th{padding:0 10px 9px;border-bottom:1px solid var(--rule2);color:var(--ink2);
  font-size:11.5px;font-weight:500;line-height:1.4;text-align:right;vertical-align:bottom;
  white-space:nowrap}
table.rivals th.l{text-align:left}
table.rivals td{padding:12px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
table.rivals tbody tr:hover td{background:#FAFBFC}
table.rivals .rk{width:30px;padding-left:0;color:var(--ink3);font-size:12px}
table.rivals .who{min-width:150px}
table.rivals .who b{font-weight:700}
table.rivals .num{text-align:right;white-space:nowrap;color:var(--ink2)}
table.rivals .num.key{color:var(--ink);font-weight:700}
table.rivals .topc b{display:block;color:var(--ink);font-size:15px;font-weight:700}
table.rivals .topc .sub{white-space:nowrap}
table.rivals .dt{font-size:12px;white-space:nowrap;color:var(--ink2)}

/* ---------- 表示の切り替え ---------- */
.narrowonly{display:none}
html[data-layout="narrow"] .wideonly{display:none}
html[data-layout="narrow"] .narrowonly{display:block}
.basenote{margin:0 0 6px;font-size:11px;color:var(--ink3)}

footer{max-width:960px;margin:0 auto;padding:18px 24px 48px;border-top:1px solid var(--rule);
  color:var(--ink3);font-size:11.5px;line-height:1.8}

html[data-layout="narrow"] .bar{padding:10px 14px 0;gap:10px}
html[data-layout="narrow"] .brand{font-size:15px}
html[data-layout="narrow"] .seg.modes a{padding:4px 9px;font-size:12px}
html[data-layout="narrow"] .lyt{font-size:11px;padding:4px 8px}
html[data-layout="narrow"] .brand span{display:none}
html[data-layout="narrow"] .tabs{padding:0 14px}
html[data-layout="narrow"] .tabs a{padding:10px 10px 9px;font-size:13.5px}
html[data-layout="narrow"] .tabs a:first-child{margin-left:-10px}
html[data-layout="narrow"] .wrap{padding:24px 14px 56px}
html[data-layout="narrow"] .head{margin-bottom:28px}
html[data-layout="narrow"] .head h1{font-size:22px}
html[data-layout="narrow"] .panel{margin-bottom:44px}
html[data-layout="narrow"] table.kv th{width:40%}
html[data-layout="narrow"] .hl-grid{grid-template-columns:1fr 1fr}
html[data-layout="narrow"] .hl{padding:14px 12px 16px}
html[data-layout="narrow"] .hl:nth-child(odd){padding-left:0;border-left:0}
html[data-layout="narrow"] .hl:nth-child(n+3){border-top:1px solid var(--rule)}
html[data-layout="narrow"] .duel{gap:10px}
html[data-layout="narrow"] .mid{min-width:52px}
html[data-layout="narrow"] .badge{width:38px;height:26px;font-size:14px}
html[data-layout="narrow"] .crowns{font-size:14px}
html[data-layout="narrow"] .hp{font-size:9.5px}
html[data-layout="narrow"] footer{padding:16px 14px 40px}
@media(max-width:560px){
  .bar{padding:10px 14px 0;gap:10px}.tabs{padding:0 14px}.wrap{padding:24px 14px 56px}
  .brand span{display:none}footer{padding:16px 14px 40px}}
@media print{.top{position:static}.rng,.toolbar,.lyt{display:none}}
@media(prefers-reduced-motion:reduce){#crtip{transition:none}}
"""

LEAGUE_JS = "{" + ",".join(f'"{k}":"{v[0]}"' for k, v in sorted(LEAGUES.items())) + "}"


RATE_JS = """(function () {
  var MODE = "__MODE__";
  var LG = __LEAGUES__;
  var ULT = __ULT__;
  var WR_WIN = 30;                 // 勝率の移動平均に使う試合数
  var SEASONS = __SEASONS__;       // [{f: このシーズンの最初の時刻, n: 番号}] 古い順
  var S = { prof: [], wr: [], vol: {}, days: [], lo: 0, hi: 0 };

  function narrow() {
    return document.documentElement.getAttribute("data-layout") === "narrow";
  }
  function esc(t) {
    return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function parseCSV(text) {
    var rows = [], row = [], cell = "", q = false, i, c;
    for (i = 0; i < text.length; i++) {
      c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else { q = false; } }
        else { cell += c; }
      } else if (c === '"') { q = true; }
      else if (c === ",") { row.push(cell); cell = ""; }
      else if (c === "\\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
      else if (c !== "\\r") { cell += c; }
    }
    if (cell.length || row.length) { row.push(cell); rows.push(row); }
    if (!rows.length) return [];
    var head = rows.shift().map(function (h) { return h.replace(/^\\uFEFF/, "").trim(); });
    /* profile.csv は見出しに無い列（生JSON）が付くため、過不足は切り捨てて読む */
    return rows.filter(function (r) { return r.length >= head.length; }).map(function (r) {
      var o = {}, k;
      for (k = 0; k < head.length; k++) o[head[k]] = r[k];
      return o;
    });
  }
  function classify(r) {
    var t = (r.battle_type || "").toLowerCase();
    if (t.indexOf("pathoflegend") >= 0) return "pol";
    return "etc";
  }
  function num(v) {
    var n = parseFloat(v);
    return isFinite(n) ? Math.round(n) : null;
  }
  function lname(n) { return LG[n] || ("League " + n); }
  function fmtn(n) { return String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ","); }
  function ms(s) {
    s = String(s || "").trim();
    if (s.length < 10) return null;
    var d = new Date(s.slice(0, 10) + "T" + (s.length >= 19 ? s.slice(11, 19) : "00:00:00"));
    var v = d.getTime();
    return isNaN(v) ? null : v;
  }
  function keyOf(d) {
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) +
      "-" + ("0" + d.getDate()).slice(-2);
  }
  function shift(key, n) {
    var d = new Date(key + "T00:00:00");
    d.setDate(d.getDate() + n);
    return keyOf(d);
  }
  function mn(a) { var v = a[0], i; for (i = 1; i < a.length; i++) if (a[i] < v) v = a[i]; return v; }
  function mx(a) { var v = a[0], i; for (i = 1; i < a.length; i++) if (a[i] > v) v = a[i]; return v; }

  /* ---------- 描画 ---------- */
  function draw() {
    var box = document.getElementById("rchart");
    if (!box) return;
    var days = S.days, total = days.length;
    if (!total) { box.innerHTML = '<p class="empty">記録がまだない。</p>'; return; }

    var lo = Math.max(0, Math.min(S.lo, total - 1));
    var hi = Math.max(lo, Math.min(S.hi, total - 1));
    var nd = hi - lo + 1;
    var dS = new Date(days[lo] + "T00:00:00").getTime();
    var dE = new Date(shift(days[hi], 1) + "T00:00:00").getTime();

    var nw = narrow();
    var W = nw ? 380 : 720;
    var RH = nw ? 128 : 168, WH = nw ? 92 : 120, GAP = 34;
    var padL = 8, padR = nw ? 84 : 104, padT = 40;
    var H = padT + RH + GAP + WH + 22;
    var pw = W - padL - padR;
    var ry0 = padT, ry1 = padT + RH;
    var wy0 = ry1 + GAP, wy1 = wy0 + WH;
    var bw = pw / nd;
    var xs = function (t) { return padL + pw * (t - dS) / (dE - dS); };
    var xd = function (i) { return padL + (i - lo + 0.5) * bw; };
    var i, k, o = [];

    o.push('<svg viewBox="0 0 ' + W + ' ' + H + '" class="chart">');
    o.push('<defs><clipPath id="rcA"><rect x="' + padL + '" y="' + ry0 + '" width="' + pw +
      '" height="' + RH + '"/></clipPath><clipPath id="rcB"><rect x="' + padL + '" y="' + wy0 +
      '" width="' + pw + '" height="' + WH + '"/></clipPath></defs>');

    /* ===== 上：レート ===== */
    o.push('<rect class="plot" x="' + padL + '" y="' + ry0 + '" width="' + pw + '" height="' + RH + '"/>');

    var Pr = S.prof, vis = [];
    for (i = 0; i < Pr.length; i++) if (Pr[i].t >= dS && Pr[i].t <= dE) vis.push(i);

    var ticks = [], yof = null, ultTop = null, ultBot = null;
    if (vis.length) {
      var ults = [], stgs = [];
      for (k = 0; k < vis.length; k++) {
        if (Pr[vis[k]].u) ults.push(Pr[vis[k]].tr); else stgs.push(Pr[vis[k]].lg);
      }
      if (!stgs.length) {
        var a1 = mn(ults), b1 = mx(ults);
        if (b1 === a1) { a1 -= 1; b1 += 1; }
        yof = function (p) { return ry0 + RH * (1 - (p.tr - a1) / (b1 - a1)); };
        for (k = 0; k < 5; k++)
          ticks.push([ry0 + RH * (1 - k / 4), fmtn(Math.round(a1 + (b1 - a1) * k / 4))]);
        ultTop = ry0; ultBot = ry1;
      } else if (!ults.length) {
        var a2 = mn(stgs), b2 = mx(stgs);
        if (b2 === a2) { a2 -= 1; b2 += 1; }
        yof = function (p) { return ry0 + RH * (1 - (p.lg - a2) / (b2 - a2)); };
        for (k = 0; k < 5; k++)
          ticks.push([ry0 + RH * (1 - k / 4), lname(Math.round(a2 + (b2 - a2) * k / 4))]);
      } else {
        var slo = mn(stgs), shi = Math.max(mx(stgs), ULT);
        if (shi === slo) slo = shi - 1;
        var sh = Math.min(RH * 0.5, Math.max(38, 16 * (shi - slo)));
        var sep = ry1 - sh;
        var rlo = mn(ults), rhi = mx(ults);
        if (rhi === rlo) { rlo -= 1; rhi += 1; }
        yof = function (p) {
          return p.u ? sep - (RH - sh) * (p.tr - rlo) / (rhi - rlo)
                     : ry1 - sh * (p.lg - slo) / (shi - slo);
        };
        for (k = slo; k < shi; k++) ticks.push([ry1 - sh * (k - slo) / (shi - slo), lname(k)]);
        for (k = 0; k < 5; k++)
          ticks.push([sep - (RH - sh) * k / 4, fmtn(Math.round(rlo + (rhi - rlo) * k / 4))]);
        ultTop = ry0; ultBot = sep;
      }
    }

    if (ultTop !== null && ultBot - ultTop > 2) {
      o.push('<rect class="ultband" x="' + padL + '" y="' + ultTop.toFixed(1) + '" width="' + pw +
        '" height="' + (ultBot - ultTop).toFixed(1) + '"/>');
      o.push('<text class="ultlab" x="' + (padL + 6) + '" y="' + (ultTop + 12).toFixed(1) +
        '">Ultimate Champion</text>');
    }
    for (k = 0; k < ticks.length; k++) {
      if (ticks[k][0] > ry0 + 1 && ticks[k][0] < ry1 - 1) {
        o.push('<line class="grid" x1="' + padL + '" y1="' + ticks[k][0].toFixed(1) +
          '" x2="' + (padL + pw) + '" y2="' + ticks[k][0].toFixed(1) + '"/>');
      }
      o.push('<text class="tick" x="' + (padL + pw + 5) + '" y="' + (ticks[k][0] + 3.5).toFixed(1) +
        '">' + esc(ticks[k][1]) + "</text>");
    }

    if (vis.length) {
      var seg = [];
      for (k = 0; k < vis.length; k++) {
        seg.push(xs(Pr[vis[k]].t).toFixed(1) + "," + yof(Pr[vis[k]]).toFixed(1));
      }
      o.push('<g clip-path="url(#rcA)">');
      if (seg.length > 1) o.push('<polyline class="ma" points="' + seg.join(" ") + '"/>');
      // 印は表示範囲の最後の記録だけ（途中の値はなぞると出る）
      var pl = Pr[vis[vis.length - 1]];
      o.push('<circle class="pt last" cx="' + xs(pl.t).toFixed(1) + '" cy="' + yof(pl).toFixed(1) +
        '" r="3.5"/>');
      o.push("</g>");
    } else {
      o.push('<text class="tick" x="' + (padL + pw / 2).toFixed(1) + '" y="' +
        (ry0 + RH / 2).toFixed(1) + '" text-anchor="middle">この期間はレートの記録がない</text>');
    }
    o.push('<line class="axis" x1="' + padL + '" y1="' + ry1 + '" x2="' + (padL + pw) + '" y2="' + ry1 + '"/>');
    o.push('<text class="tick vlab" x="' + padL + '" y="' + (ry0 - 6) + '">レート</text>');

    /* ===== シーズンの区切りと上の帯 ===== */
    var sst = [];
    for (k = 0; k < SEASONS.length; k++) {
      var sf = SEASONS[k].f ? ms(SEASONS[k].f) : -Infinity;
      var se = k + 1 < SEASONS.length ? ms(SEASONS[k + 1].f) : Infinity;
      if (se <= dS || sf >= dE) continue;
      sst.push({ a: Math.max(sf, dS), b: Math.min(se, dE), n: SEASONS[k].n, cut: sf > dS });
    }
    for (k = 0; k < sst.length; k++) {
      var sx0 = xs(sst[k].a), sx1 = xs(sst[k].b), sw = sx1 - sx0;
      if (sst[k].cut) o.push('<line class="seasonsep" x1="' + sx0.toFixed(1) + '" y1="' + (ry0 - 34) +
        '" x2="' + sx0.toFixed(1) + '" y2="' + wy1 + '"/>');
      if (sw >= 26) o.push('<text class="seasonlab" x="' + ((sx0 + sx1) / 2).toFixed(1) + '" y="' + (ry0 - 22) +
        '" text-anchor="middle">' + (sw >= 72 ? "シーズン" : "S") + sst[k].n + "</text>");
    }

    /* ===== 下：勝率＋出来高 ===== */
    o.push('<rect class="plot" x="' + padL + '" y="' + wy0 + '" width="' + pw + '" height="' + WH + '"/>');
    var maxv = 0;
    for (i = lo; i <= hi; i++) if ((S.vol[days[i]] || 0) > maxv) maxv = S.vol[days[i]];
    if (maxv > 0) {
      for (i = lo; i <= hi; i++) {
        var g = S.vol[days[i]] || 0;
        if (!g) continue;
        var bh = (WH - 2) * (g / maxv);
        o.push('<rect class="volfaint" x="' + (padL + (i - lo) * bw + bw * 0.14).toFixed(1) +
          '" y="' + (wy1 - bh).toFixed(1) + '" width="' + Math.max(0.8, bw * 0.72).toFixed(1) +
          '" height="' + bh.toFixed(1) + '" rx="' + Math.min(2, bw * 0.2).toFixed(1) + '"/>');
      }
    }
    [0, 0.25, 0.5, 0.75, 1].forEach(function (v) {
      var yy = wy1 - WH * v;
      if (v !== 0.5) o.push('<line class="' + (v === 0 ? "axis" : "grid") + '" x1="' + padL + '" y1="' +
        yy.toFixed(1) + '" x2="' + (padL + pw) + '" y2="' + yy.toFixed(1) + '"/>');
      o.push('<text class="tick" x="' + (padL + pw + 5) + '" y="' + (yy + 3.5).toFixed(1) + '">' +
        (v * 100) + (v === 1 ? "%" : "") + "</text>");
    });
    o.push('<line class="fifty" x1="' + padL + '" y1="' + (wy1 - WH * 0.5).toFixed(1) +
      '" x2="' + (padL + pw) + '" y2="' + (wy1 - WH * 0.5).toFixed(1) + '"/>');
    var wp = [];
    for (k = 0; k < S.wr.length; k++) {
      if (S.wr[k].t < dS || S.wr[k].t > dE) continue;
      wp.push(xs(S.wr[k].t).toFixed(1) + "," + (wy1 - WH * S.wr[k].p).toFixed(1));
    }
    if (wp.length > 1) {
      o.push('<g clip-path="url(#rcB)"><polyline class="rate" points="' + wp.join(" ") + '"/></g>');
    } else {
      o.push('<text class="tick" x="' + (padL + pw / 2).toFixed(1) + '" y="' +
        (wy0 + WH / 2).toFixed(1) + '" text-anchor="middle">移動平均には' + WR_WIN +
        '試合の蓄積が要る</text>');
    }
    o.push('<text class="tick vlab" x="' + padL + '" y="' + (wy0 - 6) +
      '">勝率（' + WR_WIN + '試合の移動平均）・薄い棒は試合数</text>');

    /* ===== 横軸 ===== */
    var used = [], yl = wy1 + 14, gap = nw ? 40 : 34;
    function room(x) {
      var j;
      for (j = 0; j < used.length; j++) if (Math.abs(x - used[j]) < gap) return false;
      used.push(x); return true;
    }
    var everyN = Math.max(1, Math.ceil(nd / (nw ? 4 : 9)));
    for (i = lo; i <= hi; i += everyN) {
      var dlx = xd(i);
      if (!room(dlx)) continue;
      o.push('<text class="tick" x="' + dlx.toFixed(1) + '" y="' + yl +
        '" text-anchor="middle">' + esc(days[i].slice(5).replace("-", "/")) + "</text>");
    }
    o.push('<line class="xhair" x1="0" y1="' + ry0 + '" x2="0" y2="' + wy1 + '"/>');
    var pi = -1, wi = -1;
    for (i = lo; i <= hi; i++) {
      var dEnd = new Date(shift(days[i], 1) + "T00:00:00").getTime();
      while (pi + 1 < Pr.length && Pr[pi + 1].t < dEnd) pi++;
      while (wi + 1 < S.wr.length && S.wr[wi + 1].t < dEnd) wi++;
      var dsn = null;
      for (k = 0; k < SEASONS.length; k++) if (!SEASONS[k].f || ms(SEASONS[k].f) < dEnd) dsn = SEASONS[k].n;
      var tl = [days[i].replace(/-/g, "/") + (dsn !== null ? "（シーズン" + dsn + "）" : "")];
      if (pi >= 0) {
        var pp = Pr[pi];
        tl.push(pp.u ? "レート " + fmtn(pp.tr) + "（" + lname(pp.lg) + "）" : "ステージ " + lname(pp.lg));
      }
      if (wi >= 0) tl.push("勝率 " + (S.wr[wi].p * 100).toFixed(1) + "%（直近" + WR_WIN + "試合）");
      tl.push("この日の試合 " + (S.vol[days[i]] || 0));
      o.push('<rect class="hit" x="' + (padL + (i - lo) * bw).toFixed(1) + '" y="' + ry0 +
        '" width="' + bw.toFixed(2) + '" height="' + (wy1 - ry0) + '" data-cx="' + xd(i).toFixed(1) +
        '" data-tip="' + esc(tl.join("\\n")) + '"/>');
    }
    o.push("</svg>");
    box.innerHTML = o.join("");
  }

  function refreshRange() {
    var a = document.getElementById("r1"), z = document.getElementById("r2");
    if (!a || !z) return;
    var n = S.days.length;
    a.max = z.max = Math.max(0, n - 1);
    a.value = S.lo; z.value = S.hi;
    document.getElementById("rlab").textContent =
      n ? S.days[S.lo] + " 〜 " + S.days[S.hi] : "-";
    if (window.crFill) crFill();
  }

  function bind() {
    var a = document.getElementById("r1"), z = document.getElementById("r2");
    if (a && z) {
      a.oninput = function () {
        S.lo = Math.min(+a.value, +z.value); S.hi = Math.max(+a.value, +z.value);
        refreshRange(); draw();
      };
      z.oninput = a.oninput;
    }
    [["p-all", 0], ["p-90", 90], ["p-30", 30], ["p-7", 7]].forEach(function (q) {
      var el = document.getElementById(q[0]);
      if (!el) return;
      el.onclick = function () {
        var n = S.days.length, j;
        S.hi = n - 1;
        if (!q[1]) { S.lo = 0; }
        else {
          var cut = shift(S.days[n - 1], -(q[1] - 1));
          S.lo = 0;
          for (j = 0; j < n; j++) if (S.days[j] >= cut) { S.lo = j; break; }
        }
        ["p-all", "p-90", "p-30", "p-7"].forEach(function (id) {
          var e2 = document.getElementById(id);
          if (e2) e2.className = "ubtn" + (id === q[0] ? " on" : "");
        });
        refreshRange(); draw();
      };
    });
    var btn = document.getElementById("lytbtn");
    if (btn) btn.addEventListener("click", function () { setTimeout(draw, 0); });
  }

  function boot() {
    if (!document.getElementById("rchart")) return;
    var prof = [], games = [];
    fetch("profile.csv", { cache: "no-store" }).then(function (r) { return r.text(); })
      .then(function (t) {
        parseCSV(t).forEach(function (r) {
          var lg = num(r.pol_current_league), tr = num(r.pol_current_trophies);
          var v = ms(r.checked_jst);
          if (lg === null || v === null) return;
          prof.push({ t: v, at: (r.checked_jst || "").slice(0, 16), lg: lg, tr: tr,
                      u: !!(lg >= ULT && tr) });
        });
        prof.sort(function (x, y) { return x.t - y.t; });
        return fetch("battles.csv", { cache: "no-store" }).then(function (r) { return r.text(); });
      })
      .then(function (t) {
        parseCSV(t).forEach(function (r) {
          if (MODE !== "all" && classify(r) !== MODE) return;
          var v = ms(r.battle_time_jst);
          if (v === null) return;
          games.push({ t: v, d: (r.battle_time_jst || "").slice(0, 10), win: r.result === "win",
                       dec: r.result !== "draw" });
        });
        games.sort(function (x, y) { return x.t - y.t; });

        S.prof = prof;
        S.vol = {};
        games.forEach(function (g) { S.vol[g.d] = (S.vol[g.d] || 0) + 1; });

        var dec = games.filter(function (g) { return g.dec; }), w = 0, i;
        S.wr = [];
        for (i = 0; i < dec.length; i++) {
          if (dec[i].win) w++;
          if (i >= WR_WIN && dec[i - WR_WIN].win) w--;
          if (i >= WR_WIN - 1) S.wr.push({ t: dec[i].t, p: w / WR_WIN });
        }

        var first = null, last = null;
        if (prof.length) { first = prof[0].at.slice(0, 10); last = prof[prof.length - 1].at.slice(0, 10); }
        if (games.length) {
          if (!first || games[0].d < first) first = games[0].d;
          if (!last || games[games.length - 1].d > last) last = games[games.length - 1].d;
        }
        S.days = [];
        if (first && last) {
          var cur = first, guard = 0;
          while (cur <= last && guard < 4000) { S.days.push(cur); cur = shift(cur, 1); guard++; }
        }
        S.lo = 0; S.hi = Math.max(0, S.days.length - 1);
        bind(); refreshRange(); draw();
      })
      .catch(function (e) {
        var box = document.getElementById("rchart");
        if (box) box.innerHTML = '<p class="empty">データを読み込めなかった。' + esc(e) + "</p>";
      });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
"""


MODES = [
    ("pol", "", "ランク戦"),
    ("etc", "etc-", "その他"),
    ("all", "all-", "すべて"),
]

AVAILABLE = []          # 実際に生成するモード（試合が1件以上あるもの）
WRITTEN = set()         # この実行で書き出したHTML


def classify(row):
    """クラン戦もその他に含める。"""
    t = (row.get("battle_type") or "").lower()
    if "pathoflegend" in t:
        return "pol"
    return "etc"


def nav(prefix, base):
    modes = "".join(
        f'<a href="{pre}{base}"{" class=\'on\'" if pre == prefix else ""}>{esc(lab)}</a>'
        for key, pre, lab in MODES if key in AVAILABLE
    )
    pages = "".join(
        f'<a href="{prefix}{f}"{" class=\'on\'" if f == base else ""}>{esc(l)}</a>'
        for f, l in PAGES
    )
    return ('<header class="top"><div class="bar">'
            f'<a class="brand" href="{prefix}chart.html"><i></i>Clash Log<span></span></a>'
            f'<nav class="seg modes" aria-label="モード">{modes}</nav>'
            '<button id="lytbtn" class="lyt" onclick="crToggle()"></button></div>'
            f'<nav class="tabs" aria-label="表示">{pages}</nav></header>')


def page(prefix, base, label, title, subtitle, body):
    doc = ("<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{esc(title)}｜{esc(label)}</title>"
           "<link rel='preconnect' href='https://fonts.googleapis.com'>"
           "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
           "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
           "family=IBM+Plex+Sans+JP:wght@400;500;700&display=swap'>"
           f"<style>{CSS}</style><script>{SCRIPT}</script></head>"
           "<body>"
           + nav(prefix, base)
           + "<main class='wrap'>"
           + f"<div class='head'><h1>{esc(title)}</h1><p>{esc(label)}　{esc(subtitle)}</p></div>"
           + body
           + "</main><footer>battles.csv より自動生成<br>"
             "カード画像の出典は Supercell 公式API。本ページは非公式のファン制作物であり、"
             "Supercell は内容に関与していない。</footer></body></html>")
    name = prefix + base
    WRITTEN.add(name)
    with open(os.path.join(SCRIPT_DIR, name), "w", encoding="utf-8") as f:
        f.write(doc)


def range_ui():
    return """
    <div class="toolbar"><div class="tgroup"><span class="tl">期間</span><div class="seg"><button id="p-7" class="ubtn">7日</button><button id="p-30" class="ubtn">30日</button><button id="p-90" class="ubtn">90日</button><button id="p-all" class="ubtn on">全期間</button></div></div></div>
    <div class="rng" style="margin-top:0">
      <div class="rlab"><b id="rlab">-</b></div>
      <div class="dual"><div class="dual-fill" id="rfill"></div><input id="r1" type="range" min="0" max="0" value="0" aria-label="表示範囲の始まり"><input id="r2" type="range" min="0" max="0" value="0" aria-label="表示範囲の終わり"></div>
    </div>"""


def legend_panel(extra=""):
    keys = ('<div class="keys">'
            '<span><i class="sw sw-up"></i>基準を上回る</span>'
            '<span><i class="sw sw-down"></i>基準を下回る</span>'
            f'<span><i class="sw sw-na"></i>判定不可（{RELIABLE_N}試合未満）</span>'
            "</div>")
    note = ("点が推定値、帯が95%信頼区間。帯が長いほど推定の幅が大きい。"
            "帯どうしが重なる範囲では、差があるとは言えない。" + extra)
    return panel("凡例と注意", keys, "", note)


def deck_grid(cards):
    """カード8枚を横4×縦2で並べる。"""
    cells = "".join(
        f'<img src="{esc(ICONS[c])}" alt="{esc(c)}" title="{esc(c)}">' if ICONS.get(c)
        else f'<span class="noimg" title="{esc(c)}"></span>'
        for c in cards[:8]
    )
    return f'<div class="deck">{cells}</div>'


def hp_text(king, princess):
    """残HPを短く。0や欠損は陥落扱い。"""
    k = str(king or "0")
    king_txt = "王 陥落" if k in ("0", "") else f"王 {int(float(k)):,}"
    towers = [f"{int(float(t)):,}" for t in str(princess or "").split("|") if t]
    towers += ["陥落"] * (2 - len(towers))
    return f"{king_txt}　姫 {towers[0]}/{towers[1]}"


def opp_line(r):
    """対戦記録に添える相手の情報。"""
    tag = (r.get("opp_tag") or "").strip()
    o = opp_ranks(tag)
    name, pol, gt, best, ladder = o["name"], o["pol"], o["gt"], o["best"], o["ladder"]
    name = name or (r.get("opp_name") or "")
    bits = []
    if name:
        bits.append(f"<b>{esc(name)}</b>")
    if tag:
        bits.append(esc(tag))
    if best is not None:
        bits.append(f"最高レート {best:,}")
    if pol is not None:
        bits.append(f"レート戦 最高 {pol:,} 位")
    if gt is not None:
        bits.append(f"グローバルトーナメント 最高 {gt:,} 位")
    if ladder is not None:
        season = o["ladder_season"]
        bits.append(f"Top Ladder 最高 {ladder:,} 位" + (f"（{esc(season)}）" if season else ""))
    if o["rt"]:
        bits.append(f"グローバルトーナメント Top1000 {o['rt']}回")
    if o["battles"] is not None:
        bits.append(f"通算 {o['battles']:,} 戦")
    if is_rival(pol, gt, ladder, o["rt"]):
        bits.append('<span class="rivaltag">強敵</span>')
    return "".join(f"<span>{b}</span>" for b in bits)


def battle_log(rows, limit=100):
    """直近の対戦を1件1ブロックで並べる。"""
    recent = rows[-limit:][::-1]
    blocks = []
    for r in recent:
        won = r["result"] == "win"
        cls = "win" if won else "lose" if r["result"] == "loss" else "draw"
        badge = "勝" if won else "敗" if r["result"] == "loss" else "分"
        change = r.get("trophy_change") or ""
        try:
            ch = int(float(change))
            chtxt = f'<span class="{"up-t" if ch > 0 else "down-t" if ch < 0 else ""}">{ch:+d}</span>'
        except (TypeError, ValueError):
            chtxt = ""
        mine = [c for c in r["my_deck"].split("|") if c]
        opp = [c for c in r["opp_deck"].split("|") if c]
        blocks.append(f"""<article class="log {cls}">
  <header>
    <span class="when">{esc(r["battle_time_jst"][5:16])}</span>
    <span class="mode">{esc(r.get("game_mode") or r.get("battle_type") or "")}</span>
    <span class="tro">{chtxt}</span>
  </header>
  <p class="oppinfo">{opp_line(r)}</p>
  <div class="duel">
    <div class="side">
      {deck_grid(mine)}
      <p class="hp">{esc(hp_text(r.get("my_king_hp"), r.get("my_princess_hp")))}</p>
    </div>
    <div class="mid">
      <span class="badge {cls}">{badge}</span>
      <span class="crowns">{esc(r.get("my_crowns", ""))} - {esc(r.get("opp_crowns", ""))}</span>
    </div>
    <div class="side">
      {deck_grid(opp)}
      <p class="hp">{esc(hp_text(r.get("opp_king_hp"), r.get("opp_princess_hp")))}</p>
    </div>
  </div>
</article>""")
    return "".join(blocks)


def hl_box(label, inner, wins, total, baseline):
    p, _, _ = wilson(wins, total)
    tone = "up-t" if p > baseline else "down-t" if p < baseline else ""
    return (f'<div class="hl"><span class="hl-lab">{esc(label)}</span>{inner}'
            f'<span class="hl-val {tone}">{p*100:.1f}<span class="hl-u">%</span></span>'
            f'<span class="hl-sub">{wins}勝{total-wins}敗</span></div>')


def hl_card(name):
    img = (f'<img src="{esc(ICONS[name])}" alt="{esc(name)}">' if ICONS.get(name)
           else '<span class="noimg"></span>')
    return f'<div class="hl-card">{img}<b>{esc(name)}</b></div>'


def hl_text(text):
    return f'<div class="hl-card"><b class="wide">{esc(text)}</b></div>'


def coverage_strip(rows):
    per_day = defaultdict(int)
    for r in rows:
        per_day[r["_dt"].date()] += 1
    start, end = min(per_day), max(per_day)
    days = []
    d = start
    while d <= end:
        days.append((d, per_day.get(d, 0)))
        d += datetime.timedelta(days=1)
    days = days[-30:]

    W, H = 720, 96          # 描画枠は常に固定（日数が変わっても文字の大きさが変わらない）
    peak = max(c for _, c in days) or 1
    cell = min(56, W / max(1, len(days)))
    offset = (W - cell * len(days)) / 2

    out = [f'<svg viewBox="0 0 {W} {H}" class="cov">']
    for i, (day, count) in enumerate(days):
        x = offset + cell * i
        h = 4 + 48 * (count / peak)
        cls = "zero" if count == 0 else "some"
        out.append(f'<rect class="covbar {cls}" x="{x+2:.1f}" y="{60-h:.1f}" '
                   f'width="{cell-4:.1f}" height="{h:.1f}" rx="1"/>')
        if count:
            out.append(f'<text class="covn" x="{x+cell/2:.1f}" y="{55-h:.1f}" text-anchor="middle">{count}</text>')
        out.append(f'<text class="covd" x="{x+cell/2:.1f}" y="76" text-anchor="middle">{day.month}/{day.day}</text>')
        out.append(f'<text class="covw" x="{x+cell/2:.1f}" y="90" text-anchor="middle">{WEEKDAY_JA[day.weekday()]}</text>')
    out.append("</svg>")
    return "".join(out), len(days), sum(1 for _, c in days if c == 0)


# ---------------- 本体 ----------------

def rivals_body(rows):
    """勝った相手のうち、上位実績を持つ者を最上位の順位順に並べる。"""
    items = []
    for r in rows:
        if r.get("result") != "win":
            continue
        tag = (r.get("opp_tag") or "").strip()
        o = opp_ranks(tag)
        name, pol, gt, best, ladder, rt = (o["name"], o["pol"], o["gt"], o["best"],
                                           o["ladder"], o["rt"])
        if not is_rival(pol, gt, ladder, rt):
            continue
        top, basis = best_rank(pol, gt, ladder, rt)
        items.append({
            "date": r["battle_time_jst"][:16],
            "name": name or r.get("opp_name") or "-",
            "tag": tag,
            "mode": r.get("game_mode") or r.get("battle_type") or "",
            "pol": pol, "gt": gt, "best": best, "ladder": ladder, "rt": rt,
            "top": top, "basis": basis,
            "battles": o["battles"],
        })
    big = 10 ** 9
    items.sort(key=lambda x: (x["top"] if x["top"] is not None else big,
                              x["pol"] if x["pol"] is not None else big,
                              x["ladder"] if x["ladder"] is not None else big,
                              x["date"]))

    crit = (f"レート戦の過去最高順位{RIVAL_POL_RANK:,}位以内、"
            f"グローバルトーナメント{RIVAL_RT_RANK:,}位以内、"
            f"または Top Ladder {RIVAL_LADDER_RANK:,}位以内の相手が対象。")

    if not OPPONENTS:
        return panel("強敵", '<p class="empty">相手の情報がまだ集まっていない。'
                     "収集が回ると順に貯まる。</p>",
                     "対戦相手のプレイヤー情報を別途取得して判定している。")
    if not items:
        return panel("強敵", '<p class="empty">条件を満たす相手にまだ勝っていない。</p>', "", crit)

    # 値が1件も無い列は出さない
    has_gt = any(x["gt"] is not None for x in items)
    has_rt = any(x["rt"] for x in items)

    def num_cell(v, suffix="", key=False):
        cls = "num key" if key else "num"
        return f'<td class="{cls}">{"-" if v is None else f"{v:,}{suffix}"}</td>'

    def rt_cell(x):
        if not x["rt"]:
            return '<td class="num">-</td>'
        key = " key" if x["basis"] == "GT Top1000" else ""
        return f'<td class="num{key}">{x["rt"]} 回</td>'

    body = "".join(
        f'<tr><td class="rk">{i}</td>'
        f'<td class="who"><b>{esc(x["name"])}</b><span class="sub">{esc(x["tag"])}</span></td>'
        + num_cell(x["best"])
        + num_cell(x["pol"], " 位", x["basis"] == "レート戦")
        + (num_cell(x["gt"], " 位", x["basis"] == "グローバルトーナメント") if has_gt else "")
        + (rt_cell(x) if has_rt else "")
        + num_cell(x["ladder"], " 位", x["basis"] == "Top Ladder")
        + num_cell(x["battles"])
        + f'<td class="dt">{esc(x["date"])}<span class="sub">{esc(x["mode"])}</span></td></tr>'
        for i, x in enumerate(items, 1))

    table_html = (
        '<div class="rivalwrap"><table class="rivals">'
        '<thead><tr><th class="rk">#</th><th class="l">相手</th>'
        "<th>最高<br>レート</th><th>レート戦<br>最高順位</th>"
        + ("<th>グローバル<br>トーナメント<br>最高順位</th>" if has_gt else "")
        + ("<th>グローバル<br>トーナメント<br>Top1000</th>" if has_rt else "")
        + "<th>Top Ladder<br>最高順位</th><th>通算<br>試合数</th>"
        '<th class="l">撃破した試合</th></tr></thead>'
        f"<tbody>{body}</tbody></table></div>")

    return panel(f"勝利した強敵 {len(items)} 件", table_html,
                 "それぞれの相手が持つ順位のうち、最も良いものが高い順。"
                 "同じ相手に複数回勝っていれば、その回数だけ並ぶ。",
                 crit + "グローバルトーナメントはAPIから「1,000位以内に入った回数」しか取れないため、"
                 "回数を表示し、並べ替えでは1,000位として扱う。太字が並べ替えの基準にした順位。")


def build(mode_key, prefix, label, rows, total_records):
    """1モード分の5ページを書き出す。"""
    wins = sum(1 for r in rows if r["result"] == "win")
    decided = sum(1 for r in rows if r["result"] != "draw")
    if decided == 0:
        return
    p, lo, hi = wilson(wins, decided)
    first, last = rows[0]["_dt"], rows[-1]["_dt"]
    sessions = len({r["_session"] for r in rows})
    stamp = (f"対象期間 {first:%Y/%m/%d} 〜 {last:%Y/%m/%d}"
             f"　更新 {now_jst():%Y/%m/%d %H:%M} JST")

    by_hour = tally(rows, lambda r: r["_hour"])
    hour_items = [(f"{h}時台", w, t) for h, (w, t) in sorted(by_hour.items())]
    by_pos = tally(rows, lambda r: "6戦目以降" if r["_pos"] >= 6 else f"{r['_pos']}戦目")
    pos_items = [(k, *by_pos[k]) for k in
                 ["1戦目", "2戦目", "3戦目", "4戦目", "5戦目", "6戦目以降"] if k in by_pos]

    def streak_key(r):
        s = r["_prev_streak"]
        return ("2連敗後" if s <= -2 else "1敗後" if s == -1 else
                "セッション初戦" if s == 0 else "1勝後" if s == 1 else "2連勝後")

    by_streak = tally(rows, streak_key)
    streak_items = [(k, *by_streak[k]) for k in
                    ["2連敗後", "1敗後", "セッション初戦", "1勝後", "2連勝後"] if k in by_streak]
    by_wd = tally(rows, lambda r: r["_wd"])
    wd_items = [(WEEKDAY_JA[k] + "曜", w, t) for k, (w, t) in sorted(by_wd.items())]

    page(prefix, "chosi.html", label, "調子の分析", stamp, f"""
  {panel("直前の結果別の勝率", rate_rows(streak_items), "点が左にあるほど勝率が低い。")}
  {panel("連続対戦数と勝率", rate_rows(pos_items), "",
      f"前の試合から{SESSION_GAP_MINUTES}分以上の間隔があいた場合、別セッションとして数える。")}
  {panel("時間帯別の勝率", rate_rows(hour_items))}
  {panel("曜日別の勝率", rate_rows(wd_items))}
  {legend_panel()}
""")

    # 使用デッキ
    def deck_key(r):
        cards = [c for c in r["my_deck"].split("|") if c]
        return "|".join(sorted(cards)) if cards else None

    by_deck = tally(rows, deck_key)
    deck_face = {}
    for r in rows:
        k = deck_key(r)
        if k and k not in deck_face:
            deck_face[k] = [c for c in r["my_deck"].split("|") if c][:8]
    deck_rank = sorted(by_deck.items(), key=lambda kv: -kv[1][1])
    deck_items = [("", w, t, deck_face.get(k, [])) for k, (w, t) in deck_rank[:8]]

    my_cards = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["result"] == "draw":
            continue
        for c in set(x for x in r["my_deck"].split("|") if x):
            my_cards[c][1] += 1
            if r["result"] == "win":
                my_cards[c][0] += 1
    varying = {c: v for c, v in my_cards.items() if v[1] < decided}
    my_items = [(c, w, t, [c]) for c, (w, t) in
                sorted(varying.items(), key=lambda kv: -kv[1][1])[:TOP_CARDS]]
    fixed_n = len(my_cards) - len(varying)

    page(prefix, "mydeck.html", label, "使用デッキ別の勝率", stamp, """
  <section class="panel">""" + range_ui() + """</section>
  <section class="panel"><h2>デッキ構成別の勝率</h2>
    <p class="lead">左に並ぶ8枚がその構成。基準線は指定期間の平均。</p>
    <div id="s1"></div><p class="note" id="n1"></p></section>
  <section class="panel"><h2>入れ替えのあったカード</h2>
    <p class="lead">全期間の全試合に含まれる固定枠は差が生じないため除外している。</p>
    <div id="s2"></div><p class="note" id="n2"></p></section>
  """ + legend_panel() + """
  <script>""" + RANK_JS.replace("__MODE__", mode_key).replace("__PAGE__", "deck") + """</script>
""")

    # 対戦相手
    page(prefix, "enemy.html", label, "対戦相手のカード別の勝率", stamp, """
  <section class="panel">""" + range_ui() + """</section>
  <section class="panel"><h2>勝率の低いカード</h2>
    <p class="lead">相手の編成に当該カードが含まれていた試合における、自分の勝率。</p>
    <div id="s1"></div><p class="note" id="n1"></p></section>
  <section class="panel"><h2>勝率の高いカード</h2>
    <div id="s2"></div></section>
  """ + legend_panel("　カードの種類が多いため、偶然により極端な値が生じやすい。") + """
  <script>""" + RANK_JS.replace("__MODE__", mode_key).replace("__PAGE__", "enemy") + """</script>
""")

    # 推移
    page(prefix, "chart.html", label, "勝率の推移", stamp, """
  <section class="panel"><h2>勝率の推移</h2>
    <div class="toolbar">
      <div class="tgroup"><span class="tl">粒度</span><div class="seg">
        <button id="u-day" class="ubtn">日</button>
        <button id="u-week" class="ubtn on">週</button>
        <button id="u-month" class="ubtn">月</button></div></div>
      <div class="tgroup"><span class="tl">期間</span><div class="seg"><button id="p-7" class="ubtn">7日</button><button id="p-30" class="ubtn">30日</button><button id="p-90" class="ubtn">90日</button><button id="p-all" class="ubtn on">全期間</button></div></div>
    </div>
    <div id="chart"></div>
    <div class="rng">
      <div class="rlab"><span>表示範囲</span><b id="rlab">-</b></div>
      <div class="dual"><div class="dual-fill" id="rfill"></div><input id="r1" type="range" min="0" max="0" value="0" aria-label="表示範囲の始まり"><input id="r2" type="range" min="0" max="0" value="0" aria-label="表示範囲の終わり"></div>
    </div>
    <div class="legend2">
      <span><i class="lgline" style="border-color:#1C2126;border-top-width:1.5px"></i>実測</span>
      <span><i class="lgline" style="border-color:#C8102E;border-top-width:2.5px"></i>移動平均（4期間）</span>
      <span><i class="lgbox" style="background:#E5E7EA"></i>95%信頼区間</span>
      <span><i class="lgbox" style="background:#B3BECA"></i>プレイ回数</span>
      <span><i class="lgline" style="border-color:#868E97;border-top-width:1.5px;border-top-style:dashed"></i>シーズンの区切り</span>
    </div>
    <p class="note">試合数が少ない期間ほど信頼区間は広くなる。灰色の帯が広い区間の上下動は、
      実力の変化ではなく偶然の可能性が高い。</p>
  </section>
  <section class="panel"><h2>選んだ期間の成績</h2>
    <p class="lead">上のつまみやボタンで期間を絞ると、ここが連動して変わる。</p>
    <div id="sum"></div>
  </section>
  <script>""" + CHART_JS.replace("__MODE__", mode_key).replace("__SEASONS__", SEASONS_JS) + """</script>
""")

    # レート
    page(prefix, "rate.html", label, "レート", stamp,
         rate_page_body(PROFILE) + season_deck_panel(rows)
         + "<script>" + RATE_JS.replace("__MODE__", mode_key).replace("__SEASONS__", SEASONS_JS)
                               .replace("__LEAGUES__", LEAGUE_JS)
                               .replace("__ULT__", str(ULTIMATE)) + "</script>")

    # 強敵
    page(prefix, "rivals.html", label, "強敵", stamp, rivals_body(rows))

    # 対戦記録
    page(prefix, "log.html", label, "対戦記録", stamp, f"""
  {panel("直近100試合", battle_log(rows, 100),
      "左が自分、右が相手の編成。数字は残ったタワーのHP。",
      "画像にマウスを乗せるとカード名が出る。")}
""")




# ================= 新しい1ページ型のサイト =================
# 見た目と計算はブラウザ側（APP_HTML の中のJS）で行い、ここではデータを詰めて渡すだけ。

APP_HTML = r'''<title>Clash Log</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+JP:wght@400;500;700&display=swap">
<style>
/* レイアウト：上にシーズンの帯（横軸）、カーソルで各シーズンのページ一覧が縦に開く。本文は白地に罫線で区切る */
:root{
  --bg:#FFFFFF;--sunk:#F3F4F6;--cell:#EEF0F3;--ink:#1C2126;--ink2:#545C66;--ink3:#868E97;
  --rule:#E6E8EC;--rule2:#CDD2D8;--accent:#BF0000;
  --up:#C8102E;--down:#0B57A4;--na:#98A0A9;
  --upbg:#FBECEE;--downbg:#E9F0F9;--nabg:#EFF1F3;
  --upband:#F3C9D0;--downband:#C6D8EE;--naband:#DEE2E6;
  --ult:#6E3BB8;--ultbg:#F2ECFA;--vol:#B3BECA;
  --tipbg:#1C2126;--tipfg:#FFFFFF;--shadow:rgba(28,33,38,.14);
  --font:"IBM Plex Sans JP","Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic UI","Yu Gothic","Meiryo",sans-serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#121518;--sunk:#1B1F24;--cell:#20252B;--ink:#E8EBEE;--ink2:#A9B1BA;--ink3:#7D8690;
  --rule:#262B31;--rule2:#363D45;--accent:#E5323F;
  --up:#F0566A;--down:#5B9BE8;--na:#6F7882;
  --upbg:#3A1C22;--downbg:#172A42;--nabg:#23282E;
  --upband:#5A2630;--downband:#1E3A5E;--naband:#2C3238;
  --ult:#A57BE8;--ultbg:#231C33;--vol:#46505C;
  --tipbg:#E8EBEE;--tipfg:#121518;--shadow:rgba(0,0,0,.5);color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#121518;--sunk:#1B1F24;--cell:#20252B;--ink:#E8EBEE;--ink2:#A9B1BA;--ink3:#7D8690;
  --rule:#262B31;--rule2:#363D45;--accent:#E5323F;
  --up:#F0566A;--down:#5B9BE8;--na:#6F7882;
  --upbg:#3A1C22;--downbg:#172A42;--nabg:#23282E;
  --upband:#5A2630;--downband:#1E3A5E;--naband:#2C3238;
  --ult:#A57BE8;--ultbg:#231C33;--vol:#46505C;
  --tipbg:#E8EBEE;--tipfg:#121518;--shadow:rgba(0,0,0,.5);color-scheme:dark}

*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);font-size:14px;line-height:1.7;
  -webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
button{font-family:inherit;color:inherit}
:focus-visible{outline:2px solid var(--down);outline-offset:2px;border-radius:4px}

/* ---------- 上部 ---------- */
.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:30;background:color-mix(in oklab,var(--bg) 94%,transparent);
  -webkit-backdrop-filter:saturate(1.4) blur(8px);backdrop-filter:saturate(1.4) blur(8px);border-bottom:1px solid var(--rule)}
.in{max-width:1040px;margin:0 auto;padding-inline:24px}
.bar{display:flex;align-items:center;gap:20px;padding-block:12px 8px}
.brand{display:flex;align-items:center;gap:9px;font-size:16px;font-weight:700;letter-spacing:.01em;white-space:nowrap}
.brand i{display:block;width:4px;height:18px;border-radius:1px;background:var(--accent)}
.meta{margin-left:auto;font-size:12px;color:var(--ink3);white-space:nowrap}
.seg{display:inline-flex;background:var(--sunk);border-radius:8px;padding:3px;gap:2px}
.seg button{border:0;background:none;color:var(--ink2);font-size:12.5px;line-height:1.5;padding:4px 12px;border-radius:6px;cursor:pointer;white-space:nowrap}
.seg button:hover{color:var(--ink)}
.seg button.on{background:var(--bg);color:var(--ink);font-weight:700;box-shadow:0 1px 2px var(--shadow),0 0 0 1px color-mix(in oklab,var(--ink) 6%,transparent)}
.seg.modes button.on{color:var(--accent)}

/* シーズンの帯 */
.seasons{display:flex;gap:0;overflow-x:auto;scrollbar-width:none;border-top:1px solid var(--rule)}
.seasons::-webkit-scrollbar{display:none}
.sn{position:relative;flex:1 0 auto;min-width:118px;display:flex;flex-direction:column;align-items:flex-start;gap:0;
  padding:9px 14px 10px;border:0;border-left:1px solid var(--rule);background:none;text-align:left;cursor:pointer}
.sn:first-child{border-left:0;padding-left:0;min-width:96px}
.sn b{font-size:13.5px;font-weight:700;color:var(--ink2);line-height:1.4}
.sn span{font-size:11px;color:var(--ink3);line-height:1.45}
.sn em{font-style:normal;font-size:11px;color:var(--ink3);line-height:1.45}
.sn em .up-t,.sn em .down-t{font-weight:700}
.sn:hover b,.sn.open b{color:var(--ink)}
.sn.on b{color:var(--ink)}
.sn.on::after{content:"";position:absolute;left:14px;right:14px;bottom:-1px;height:2px;background:var(--accent)}
.sn:first-child.on::after{left:0}
.sn .now{display:inline-block;margin-left:6px;padding:0 5px;border-radius:3px;background:var(--upbg);color:var(--up);font-size:10px;font-weight:700;vertical-align:1px}

/* ページのタブ */
.tabs{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;border-top:1px solid var(--rule)}
.tabs::-webkit-scrollbar{display:none}
.tabs button{border:0;background:none;padding:9px 12px 8px;color:var(--ink2);font-size:14px;cursor:pointer;
  border-bottom:2px solid transparent;white-space:nowrap;letter-spacing:.02em}
.tabs button:first-child{margin-left:-12px}
.tabs button:hover{color:var(--ink)}
.tabs button.on{color:var(--ink);font-weight:700;border-bottom-color:var(--accent)}

/* シーズンから開く一覧 */
.menu{position:fixed;z-index:40;width:300px;max-width:calc(100vw - 32px);background:var(--bg);border:1px solid var(--rule2);
  border-radius:10px;box-shadow:0 12px 32px var(--shadow);padding:6px;animation:drop .12s ease-out}
@keyframes drop{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.menu h4{margin:6px 10px 6px;font-size:12px;font-weight:500;color:var(--ink3)}
.menu button{display:grid;grid-template-columns:76px 1fr;gap:10px;align-items:baseline;width:100%;border:0;background:none;
  text-align:left;padding:8px 10px;border-radius:6px;cursor:pointer}
.menu button:hover,.menu button:focus-visible{background:var(--sunk)}
.menu button b{font-size:13.5px;font-weight:700}
.menu button span{font-size:12px;color:var(--ink2);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.menu button.cur b{color:var(--accent)}

/* ---------- 本文 ---------- */
.wrap{max-width:1040px;margin:0 auto;padding:28px 24px 64px}
.head{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:4px 20px;margin:0 0 28px}
.head h1{margin:0;font-size:26px;line-height:1.3;font-weight:700;letter-spacing:.01em;text-wrap:balance}
.head p{margin:0;font-size:12.5px;color:var(--ink3)}
.sec{margin:0 0 48px;min-width:0}
.sec>h2{position:relative;margin:0 0 14px;padding:0 0 9px;font-size:16px;font-weight:700;line-height:1.4;
  letter-spacing:.02em;border-bottom:2px solid var(--rule);display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.sec>h2::after{content:"";position:absolute;left:0;bottom:-2px;width:48px;height:2px;background:var(--accent)}
.sec>h2 small{font-size:12px;font-weight:400;color:var(--ink3)}
.lead{margin:-4px 0 14px;max-width:46em;color:var(--ink2);font-size:13px}
.note{position:relative;margin:12px 0 0;padding-left:1.3em;max-width:56em;color:var(--ink3);font-size:12px;line-height:1.75}
.note::before{content:"※";position:absolute;left:0}
.empty{color:var(--ink3);font-size:13px;margin:6px 0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:28px 40px}
.grid2>*{min-width:0}
.up-t{color:var(--up)}.down-t{color:var(--down)}.na-t{color:var(--na)}
.sub{display:block;font-size:11.5px;font-weight:400;color:var(--ink3);line-height:1.5}

/* 要約の数字 */
.kpi{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--rule2);border-bottom:1px solid var(--rule);margin:0 0 36px}
.kpi>div{padding:14px 18px 16px;border-left:1px solid var(--rule);min-width:0}
.kpi>div:first-child{border-left:0;padding-left:0}
.kpi .k{font-size:12px;color:var(--ink2)}
.kpi .v{display:block;margin-top:4px;font-size:30px;font-weight:700;line-height:1.1;letter-spacing:-.01em}
.kpi .v small{font-size:13px;font-weight:400;color:var(--ink3);margin-left:2px}
.kpi .s{display:block;margin-top:5px;font-size:11.5px;color:var(--ink3)}
.kpi.sm{margin:0 0 28px;grid-template-columns:repeat(4,minmax(0,1fr)) minmax(0,1.1fr)}.kpi .dn{display:flex;align-items:center;gap:10px}.kpi.sm>div:first-child{padding-left:0}.kpi.sm>div{padding:10px 16px 12px}.kpi.sm .v{font-size:22px}.kpi.sm .v small{font-size:12px}

/* 操作 */
.toolbar{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px 24px;margin:0 0 12px}
.tg{display:flex;align-items:center;gap:10px}.tl{font-size:12px;color:var(--ink3)}
.rng{margin:16px 0 0}
.rlab{display:flex;justify-content:space-between;gap:12px;margin:0 0 4px;font-size:12px;color:var(--ink3)}
.rlab b{color:var(--ink);font-weight:500}
.dual{position:relative;height:24px}
.dual::before{content:"";position:absolute;left:8px;right:8px;top:10px;height:4px;border-radius:2px;background:var(--rule)}
.dual .fill{position:absolute;top:10px;height:4px;border-radius:2px;background:var(--ink)}
.dual input{position:absolute;left:0;top:0;width:100%;height:24px;margin:0;background:none;pointer-events:none;-webkit-appearance:none;appearance:none}
.dual input::-webkit-slider-runnable-track{height:24px;background:none}
.dual input::-webkit-slider-thumb{-webkit-appearance:none;pointer-events:auto;width:16px;height:16px;margin-top:4px;border-radius:50%;
  background:var(--bg);border:2px solid var(--ink);box-shadow:0 1px 3px var(--shadow);cursor:ew-resize}
.dual input::-moz-range-track{height:24px;background:none}
.dual input::-moz-range-thumb{pointer-events:auto;width:12px;height:12px;border-radius:50%;background:var(--bg);border:2px solid var(--ink);cursor:ew-resize}
.legend{display:flex;flex-wrap:wrap;gap:6px 20px;margin:12px 0 0;font-size:12px;color:var(--ink2)}
.legend span{display:inline-flex;align-items:center;gap:8px}
.lgl{display:inline-block;width:20px;border-top:2px solid var(--ink)}
.lgb{display:inline-block;width:14px;height:12px;border-radius:3px}

/* グラフ共通 */
svg{display:block;overflow:visible}
.ax{stroke:var(--rule2);stroke-width:1}.gr{stroke:var(--rule);stroke-width:1}
.ref{stroke:var(--ink3);stroke-width:1;stroke-dasharray:3 3}
.ssep{stroke:var(--ink3);stroke-width:1;stroke-dasharray:3 3;opacity:.8}
.tk{font-size:10.5px;fill:var(--ink3);font-family:var(--font)}
.tk.b{fill:var(--ink2);font-weight:700;font-size:11px}
.tk.v{fill:var(--ink2);font-size:11px}
.band{fill:var(--ink3);opacity:.12}
.raw{fill:none;stroke:var(--ink);stroke-width:1.25;stroke-linejoin:round}
.ma{fill:none;stroke:var(--up);stroke-width:2.25;stroke-linejoin:round;stroke-linecap:round}
.vol{fill:var(--vol)}.volf{fill:var(--vol);opacity:.55}
.pt{fill:var(--ink);stroke:var(--bg);stroke-width:1.5}
.ptl{fill:var(--up);stroke:var(--bg);stroke-width:1.5}
.ultb{fill:var(--ult);opacity:.08}.ultl{font-size:10.5px;fill:var(--ult);font-weight:500;font-family:var(--font)}
.hit{fill:transparent;cursor:crosshair}
.xh{stroke:var(--ink);stroke-width:1;opacity:0;pointer-events:none}

/* 点と帯の表（勝率） */
.dt{display:grid;grid-template-columns:var(--cols);align-items:center;column-gap:0}
.dt>.h,.dt>.c{padding-right:16px}
.dt>.z{padding-right:0}
.dt>.h{padding:0 0 6px;font-size:11px;color:var(--ink3);border-bottom:1px solid var(--rule2);white-space:nowrap}
.dt>.h.r{text-align:right}
.dt>.c{padding:7px 0;border-bottom:1px solid var(--rule);min-width:0}
.dt .lab{display:flex;align-items:center;gap:8px;font-size:13px;min-width:0}
.dt .lab .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cg{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));border-top:1px solid var(--rule2)}
.cg>div{min-width:0;padding:10px 12px 12px;border-bottom:1px solid var(--rule);border-right:1px solid var(--rule)}
.cg .ctop{display:flex;align-items:center;gap:8px;min-width:0}
.cg .cnm{display:flex;flex-direction:column;min-width:0;line-height:1.35}
.cg .cnm b{font-size:12.5px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cg .cnm small{font-size:11px;color:var(--ink3)}
.cg .cmid{display:flex;justify-content:space-between;align-items:baseline;margin:8px 0 6px;font-size:11.5px;color:var(--ink2)}
.cg .pv{font-size:18px;font-weight:700}.cg .pv small{font-size:11px;font-weight:400;color:var(--ink3)}
.cg .dp{margin:0}
.dt .pv{text-align:right;font-size:16px;font-weight:700;white-space:nowrap}
.dt .pv small{font-size:10.5px;font-weight:400;color:var(--ink3)}
.dt .rc{text-align:right;font-size:12px;color:var(--ink2);white-space:nowrap}
.dt.tight>.c{padding:4px 0}
.dt.tight .pv{font-size:14px}
.dp{position:relative;height:16px;margin:0 6px}
.dp .g{position:absolute;inset:0;background:linear-gradient(90deg,var(--rule) 1px,transparent 1px) 0 0/25% 100%;
  border-right:1px solid var(--rule)}
.dp .bl{position:absolute;top:-6px;bottom:-6px;width:0;border-left:1px dashed var(--ink3)}
.dp .ci{position:absolute;top:5px;height:6px;border-radius:3px}
.dp .d{position:absolute;top:2px;width:12px;height:12px;margin-left:-6px;border-radius:50%;border:2px solid var(--bg)}
.ci.up{background:var(--upband)}.ci.down{background:var(--downband)}.ci.na{background:var(--naband)}
.d.up{background:var(--up)}.d.down{background:var(--down)}.d.na{background:var(--na)}
.dax{position:relative;height:14px;margin:0 6px;font-size:10px;color:var(--ink3)}
.dax span{position:absolute;transform:translateX(-50%)}
.dax span:first-child{transform:none}.dax span:last-child{transform:translateX(-100%)}
.use{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--ink2);white-space:nowrap}
.use i{display:block;height:6px;border-radius:3px;background:var(--ink2);opacity:.55}

/* 狭い画面の勝率の表（1件2段） */
.dtm-h{display:grid;grid-template-columns:minmax(0,1fr) 92px;column-gap:14px;padding:0 0 6px;border-bottom:1px solid var(--rule2);font-size:11px;color:var(--ink3)}
.dtm-h .r{text-align:right}
.dtm-r{display:grid;grid-template-columns:minmax(0,1fr) 92px;column-gap:14px;row-gap:8px;align-items:center;padding:10px 0 12px;border-bottom:1px solid var(--rule)}
.dtm-r .lab{display:flex;align-items:center;gap:8px;font-size:13px;min-width:0;overflow:hidden}
.dtm-r .lab .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dtm-r .pv{text-align:right;font-size:17px;font-weight:700;white-space:nowrap}
.dtm-r .pv small{font-size:10.5px;font-weight:400;color:var(--ink3)}
.dtm-r .dpw{padding:0;min-width:0}
.dtm-r .rc{text-align:right;font-size:12px;color:var(--ink2);white-space:nowrap;line-height:1.35}
.dtm-r .rc small{display:block;font-size:10.5px;color:var(--ink3)}
.dt .lab{overflow:hidden}

/* カード */
.cd{position:relative;display:inline-grid;place-items:center;width:var(--w,26px);aspect-ratio:5/6;border-radius:4px;overflow:hidden;
  flex:none;background:color-mix(in oklab,hsl(var(--h) 55% 50%) 22%,var(--cell));color:var(--ink2);
  font-size:calc(var(--w,26px)*.36);font-weight:700;letter-spacing:-.02em;line-height:1}
.cd img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.cd i{font-style:normal}
.deck8{display:flex;gap:3px;flex-wrap:nowrap}
.deck8.d42{display:inline-grid;grid-template-columns:repeat(4,max-content);gap:3px}

/* 対戦記録 */
.lg{display:grid;grid-template-columns:96px 64px auto auto 1fr;align-items:center;gap:6px 14px;padding:10px 0;border-bottom:1px solid var(--rule)}
.lg:first-of-type{border-top:1px solid var(--rule2)}
.lg .when{font-size:12px;color:var(--ink2);line-height:1.4}
.lg .when small{display:block;font-size:10.5px;color:var(--ink3)}
.res{display:inline-flex;flex-direction:column;align-items:center;gap:2px}
.pill{display:inline-grid;place-items:center;width:34px;height:22px;border-radius:5px;font-size:12.5px;font-weight:700}
.pill.w{background:var(--upbg);color:var(--up)}.pill.l{background:var(--downbg);color:var(--down)}.pill.d{background:var(--nabg);color:var(--na)}
.res b{font-size:12px;letter-spacing:.04em}
.lg .vs{display:flex;flex-direction:column;gap:3px}
.lg .hp{font-size:10.5px;color:var(--ink3)}
.lg .who{font-size:12px;color:var(--ink2);min-width:0;line-height:1.55;overflow-wrap:anywhere}
.lg .who b{color:var(--ink)}
.tag2{display:inline-block;padding:0 6px;border-radius:4px;background:var(--upbg);color:var(--up);font-size:10.5px;font-weight:700;line-height:1.7;margin-left:4px}
.more{display:block;margin:16px auto 0;border:1px solid var(--rule2);background:none;border-radius:8px;padding:8px 18px;font-size:13px;cursor:pointer}
.more:hover{border-color:var(--ink3)}

/* 表 */
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.t{width:100%;border-collapse:collapse;font-size:13px}
table.t th{padding:0 10px 8px;border-bottom:1px solid var(--rule2);color:var(--ink2);font-size:11.5px;font-weight:500;line-height:1.4;
  text-align:right;vertical-align:bottom;white-space:nowrap}
table.t th.l,table.t td.l{text-align:left}
table.t td{padding:10px;border-bottom:1px solid var(--rule);text-align:right;vertical-align:top;white-space:nowrap;color:var(--ink2)}
table.t td:first-child,table.t th:first-child{padding-left:0}
table.t td.key{color:var(--ink);font-weight:700}
table.t td b{color:var(--ink)}
table.t td.l b{white-space:normal;overflow-wrap:anywhere}
table.t tr.sel td{background:color-mix(in oklab,var(--accent) 5%,transparent)}
table.t .big{font-size:16px;font-weight:700;color:var(--ink)}

/* レートの見出し */
.hero{display:grid;grid-template-columns:1.2fr 1fr 1fr;border-top:1px solid var(--rule2);border-bottom:1px solid var(--rule);margin:0 0 36px}
.hero>div{padding:16px 18px 18px;border-left:1px solid var(--rule);min-width:0}
.hero>div:first-child{border-left:0;padding-left:0}
.hero .k{font-size:12px;color:var(--ink2)}
.hero .v{display:block;margin-top:2px;font-size:38px;font-weight:700;line-height:1.1;letter-spacing:-.02em}
.hero .v.st{font-size:26px}
.hero .s{display:block;margin-top:6px;font-size:12px;color:var(--ink3)}
.lgn{font-weight:700}

/* カレンダー */
.cal{display:grid;grid-template-columns:34px repeat(7,minmax(0,1fr));gap:3px}
.cal .ch{font-size:11px;color:var(--ink3);text-align:left;padding:0 0 2px 6px}
.cal .ch.we{color:var(--ink2)}
.cal .cw{font-size:11px;color:var(--ink3);display:flex;align-items:flex-start;padding-top:6px}
.cal .cc{position:relative;min-height:54px;border-radius:5px;background:var(--cell);padding:5px 7px;display:flex;flex-direction:column;justify-content:space-between;min-width:0}
.cal .cc.o{background:transparent}
.cal .cd1{font-size:10.5px;color:var(--ink2);line-height:1}
.cal .cc b{font-size:16px;line-height:1.1;text-align:right;color:var(--ink)}
.cal .cc b small{font-size:10px;font-weight:400;color:var(--ink3)}
.cal .cn{position:absolute;left:7px;bottom:5px;font-size:10px;color:var(--ink2);line-height:1}

/* 戦績（RoyaleAPI のプロフィール／OP.GG のランク欄／Baseball Savant の選手ページにならう） */
.bio{display:flex;flex-wrap:wrap;gap:4px 0;margin:-16px 0 30px;font-size:12.5px;color:var(--ink2);line-height:1.6}
.bio span+span::before{content:"｜";margin:0 8px;color:var(--rule2)}
.bio b{color:var(--ink);font-weight:700}
.hero.h4{grid-template-columns:repeat(4,minmax(0,1fr))}
.hero .rk{display:block;margin-top:2px;font-size:12px;color:var(--ink2)}
table.t tr.tot td{border-top:2px solid var(--rule2);border-bottom:0;color:var(--ink)}
table.t .ci{display:block;font-size:11px;color:var(--ink3);font-weight:400}
.jump{display:flex;flex-wrap:wrap;gap:6px;margin:-12px 0 30px}
.jump button{border:1px solid var(--rule2);background:var(--bg);border-radius:999px;padding:4px 12px;font-size:12px;color:var(--ink2);cursor:pointer}
.jump button:hover{border-color:var(--ink3);color:var(--ink)}

/* 対戦相手の中での位置（パーセンタイル） */
.pr{display:grid;grid-template-columns:minmax(0,170px) minmax(0,1fr) 96px;align-items:center;column-gap:18px;row-gap:0}
.pr>div{padding:10px 0;border-bottom:1px solid var(--rule);min-width:0}
.pr .ph{padding:0 0 6px;border-bottom:1px solid var(--rule2);font-size:11px;color:var(--ink3)}
.pr .ph.sc{display:flex;justify-content:space-between}
.pr .lb{font-size:13px}
.pr .lb small{display:block;font-size:11px;color:var(--ink3)}
.pr .vl{text-align:right;font-size:15px;font-weight:700}
.pr .vl small{display:block;font-size:10.5px;font-weight:400;color:var(--ink3)}
.trk{position:relative;height:30px}
.trk::before{content:"";position:absolute;left:0;right:0;top:13px;height:4px;border-radius:2px;
  background:linear-gradient(90deg,color-mix(in oklab,var(--down) 45%,var(--cell)),var(--cell) 50%,color-mix(in oklab,var(--up) 45%,var(--cell)))}
.trk .md{position:absolute;top:7px;height:16px;border-left:1px dashed var(--ink3)}
.trk .bb{position:absolute;top:1px;min-width:28px;height:28px;padding:0 9px;transform:translateX(-50%);white-space:nowrap;border-radius:14px;display:grid;place-items:center;
  color:#fff;font-size:12px;font-weight:700;border:2px solid var(--bg);box-shadow:0 1px 3px var(--shadow)}
.seasons-past{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;margin:-22px 0 36px;font-size:12px;color:var(--ink3)}
.seasons-past span.ch{display:inline-flex;align-items:baseline;gap:6px;padding:3px 10px;border-radius:999px;background:var(--sunk);color:var(--ink2)}
.seasons-past span.ch b{color:var(--ink);font-size:12.5px}

/* 直近20試合のまとめ */

/* 調子：時間帯×曜日 */
.hm{display:grid;grid-template-columns:28px 1fr 104px;gap:0 10px;align-items:stretch}
.hm .rows{display:grid;gap:3px}
.hm .rl{font-size:11.5px;color:var(--ink2);display:flex;align-items:center;height:var(--ch)}
.hm .cells{display:grid;gap:3px;min-width:0}
.hm .row{display:grid;grid-template-columns:repeat(var(--nh),1fr);gap:3px}
.hm .cell{height:var(--ch);border-radius:3px;background:var(--cell);display:grid;place-items:center;font-size:10px;color:var(--ink);cursor:default}
.hm .cell.e{background:transparent;box-shadow:inset 0 0 0 1px var(--rule)}
.hm .mg{display:grid;gap:3px}
.hm .mr{height:var(--ch);display:flex;align-items:center;justify-content:flex-end;gap:6px;font-size:12px;white-space:nowrap}
.hm .mr b{font-size:13px}
.hm .mr small{font-size:10.5px;color:var(--ink3)}
.hm .foot{grid-column:2;display:grid;grid-template-columns:repeat(var(--nh),1fr);gap:3px;margin-top:6px}
.hm .foot div{display:flex;flex-direction:column;align-items:center;gap:2px}
.hm .foot i{display:block;width:70%;border-radius:2px 2px 0 0;background:var(--vol)}
.hm .foot span{font-size:10px;color:var(--ink3)}
.hm .bars{height:34px;display:flex;align-items:flex-end;justify-content:center;width:100%}
.scale{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--ink3);margin-top:10px;flex-wrap:wrap}
.scale .sw{display:flex;gap:2px}.scale .sw i{display:block;width:16px;height:10px;border-radius:2px}

/* セッションの流れ */
.strip{overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:4px}

footer{max-width:1040px;margin:0 auto;padding:18px 24px 48px;border-top:1px solid var(--rule);color:var(--ink3);font-size:11.5px;line-height:1.8}
#tip{position:fixed;z-index:60;max-width:280px;padding:9px 12px;border-radius:8px;background:var(--tipbg);color:var(--tipfg);
  font-size:12px;line-height:1.6;white-space:pre-line;pointer-events:none;opacity:0;transition:opacity .08s;box-shadow:0 6px 18px var(--shadow)}

@media (max-width:760px){
  .cal .cc{min-height:44px;padding:4px 5px}.cal .cc b{font-size:13px}.cal .cn{display:none}.cal{grid-template-columns:26px repeat(7,minmax(0,1fr))}
  .in{padding-inline:16px}.wrap{padding:22px 16px 56px}footer{padding:16px 16px 40px}
  .meta{display:none}
  .head h1{font-size:22px}
  .kpi,.hero,.hero.h4{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
  .hero .v{font-size:28px}.hero .v.st{font-size:20px}.hero>div{padding:14px 12px 16px}
  .kpi>div:nth-child(3),.hero>div:nth-child(3){border-left:0;padding-left:0}
  .kpi.sm{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.kpi.sm>div:nth-child(5){grid-column:1/-1;border-left:0;padding-left:0}.kpi.sm>div:nth-child(3){padding-left:0}
  .kpi>div:nth-child(n+3),.hero>div:nth-child(n+3){border-top:1px solid var(--rule)}
  .hero>div:first-child{grid-column:1/-1;border-bottom:1px solid var(--rule)}
  .hero>div:nth-child(2){border-left:0;padding-left:0}
  .hero>div:nth-child(3){border-left:1px solid var(--rule);padding-left:18px;border-top:0}
  .hero.h4>div:first-child{grid-column:auto;border-bottom:0}
  .hero.h4>div:nth-child(2){border-left:1px solid var(--rule);padding-left:12px}
  .hero.h4>div:nth-child(3){border-left:0;padding-left:0;border-top:1px solid var(--rule)}
  .hero.h4>div:nth-child(4){border-top:1px solid var(--rule)}
  .bio{flex-direction:column;margin-top:-18px}.bio span+span::before{display:none}
  table.t .opt{display:none}table.t td.l b{white-space:nowrap}
  .ledger table.t td,.ledger table.t th{padding-left:6px;padding-right:6px}.ledger table.t .big{font-size:14px;white-space:normal}
  .grid2{grid-template-columns:1fr}
  .kpi .v{font-size:26px}
  .lg{grid-template-columns:1fr auto;grid-template-areas:"when res" "my my" "op op" "who who"}
  .lg .when{grid-area:when}.lg .res{grid-area:res;flex-direction:row}.lg .my{grid-area:my}.lg .op{grid-area:op}.lg .who{grid-area:who}
  .hm{grid-template-columns:24px 1fr 76px}
  .pr{grid-template-columns:minmax(0,1fr) 84px;grid-auto-flow:row dense}.pr .tr{grid-column:1/-1;padding-top:0}.pr .lb{border-bottom:0;padding-bottom:2px}.pr .vl{border-bottom:0;padding-bottom:2px}
  .pr .ph.lab2,.pr .ph.v2{display:none}.pr .ph.sc{grid-column:1/-1}
}
html{scroll-padding-top:180px}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.menu{animation:none}#tip{transition:none}}
</style>

<header class="top">
  <div class="in">
    <div class="bar">
      <div class="brand"><i></i>Clash Log</div>
      <div class="seg modes" id="modes" role="group" aria-label="モード"></div>
      <div class="meta" id="meta"></div>
    </div>
    <nav class="seasons" id="seasons" aria-label="シーズン"></nav>
    <nav class="tabs" id="tabs" aria-label="ページ"></nav>
  </div>
</header>
<div class="menu" id="menu" hidden></div>
<main class="wrap">
  <div class="head"><h1 id="title"></h1><p id="sub"></p></div>
  <div id="page"></div>
</main>
<footer>
  battles.csv・profile.csv・opponents.csv より自動生成<br>
  カード画像の出典は Supercell 公式API。本ページは非公式のファン制作物であり、Supercell は内容に関与していない。
</footer>
<div id="tip" role="tooltip"></div>

<script type="application/json" id="data">/*DATA*/</script>
<script>
(function () {
"use strict";
var D = JSON.parse(document.getElementById("data").textContent);
var IMG = D.img !== false;
var RELIABLE_N = 20, MIN_CARD_N = 5, WR_WIN = 30, MA_WIN = 4;
var PAGES = [["profile", "戦績"], ["trend", "推移"], ["deck", "使用デッキ"], ["enemy", "対戦相手"], ["rivals", "強敵"], ["log", "対戦記録"]];
var ALIAS = { home: "profile", form: "trend", rate: "trend", chart: "trend" };   // 旧ページの名前
var MODES = [["pol", "ランク戦"], ["etc", "その他"], ["all", "すべて"]];
var WD = ["月", "火", "水", "木", "金", "土", "日"];
var SEAS = D.seasons;

/* ---------- 下ごしらえ ---------- */
function esc(t) { return String(t == null ? "" : t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
function ms(t) { return new Date(t.slice(0, 10) + "T" + (t.length >= 19 ? t.slice(11, 19) : "00:00:00")).getTime(); }
function seasonOf(t) { var n = null; for (var j = 0; j < SEAS.length; j++) if (SEAS[j].f <= t) n = SEAS[j].n; return n; }
function dayKey(d) { return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
function addDays(k, n) { var d = new Date(k + "T00:00:00"); d.setDate(d.getDate() + n); return dayKey(d); }
function md(k) { return (+k.slice(5, 7)) + "/" + (+k.slice(8, 10)); }
function fmtn(n) { return n == null ? "-" : Number(n).toLocaleString("ja-JP"); }
function wilson(w, n) {
  if (!n) return [0, 0, 0];
  var z = 1.96, p = w / n, d = 1 + z * z / n, c = (p + z * z / (2 * n)) / d;
  var m = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return [p, Math.max(0, c - m), Math.min(1, c + m)];
}
function tone(p, base, n) { if (n < RELIABLE_N) return "na"; return p > base ? "up" : p < base ? "down" : "na"; }
function pc(p, d) { return (p * 100).toFixed(d == null ? 1 : d); }
function rec(w, n) { return w + "勝" + (n - w) + "敗"; }
function lname(n) { return D.leagues[n] || ("League " + n); }
function hash(s) { var h = 0; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }
function abbr(s) {
  var w = s.replace(/[^A-Za-z ]/g, " ").split(/\s+/).filter(Boolean);
  if (w.length >= 2) return (w[0][0] + w[1][0]).toUpperCase();
  return w.length ? w[0].slice(0, 2) : s.slice(0, 2);
}

var B = D.battles.map(function (a) {
  var d = a[0].slice(0, 10);
  return { t: a[0], d: d, h: +a[0].slice(11, 13), wd: (new Date(d + "T00:00:00").getDay() + 6) % 7,
    mode: a[1], r: a[2], mc: a[3], oc: a[4], my: a[5], op: a[6], tag: a[7], name: a[8],
    mk: a[9], mp: a[10], ok: a[11], opp: a[12], tc: a[13], gm: a[14], ses: a[15], s: seasonOf(a[0]) };
});
B.sort(function (x, y) { return x.t < y.t ? -1 : 1; });
(function () {   // 直前の連勝・連敗と、セッション内で何戦目か（セッションが変われば数え直す）
  var st = 0, ls = null, pos = 0;
  B.forEach(function (g) {
    if (g.ses !== ls) { st = 0; pos = 0; ls = g.ses; }
    pos++; g.pos = pos; g.prev = st;
    st = g.r === "w" ? (st > 0 ? st + 1 : 1) : g.r === "l" ? (st < 0 ? st - 1 : -1) : 0;
  });
})();
var P = D.prof.map(function (a) { return { t: a[0], v: ms(a[0]), lg: a[1], tr: a[2], u: a[1] >= D.ult && a[2] > 0, s: seasonOf(a[0]) }; });

var SINFO = SEAS.map(function (s, i) {
  var g = B.filter(function (x) { return x.s === s.n; });
  var p = P.filter(function (x) { return x.s === s.n; });
  var from = g.length ? g[0].d : (p.length ? p[0].t.slice(0, 10) : "");
  var to = g.length ? g[g.length - 1].d : from;
  return { n: s.n, f: s.f, from: from, to: to, last: i === SEAS.length - 1 };
});

/* ---------- 状態 ---------- */
var DAYS = [];
var S = { mode: "pol", season: "all", page: "profile", unit: null, lo: null, hi: null, logN: 50 };
try {
  var sv = JSON.parse(localStorage.getItem("clashlog.v2") || "{}");
  if (sv.mode) S.mode = sv.mode; if (sv.season != null) S.season = sv.season;
} catch (e) {}
// アドレスの # でページとモードを指定できる（例：#deck、#etc-deck）
var h0 = /^#(?:(pol|etc|all)-)?([a-z]+)$/.exec(location.hash || "");
if (h0) {
  var pg0 = ALIAS[h0[2]] || h0[2];
  if (PAGES.some(function (p) { return p[0] === pg0; })) { S.page = pg0; if (h0[1]) S.mode = h0[1]; }
}
function save() { try { localStorage.setItem("clashlog.v2", JSON.stringify({ mode: S.mode, season: S.season })); } catch (e) {} }

function games(season, mode) {
  season = season == null ? S.season : season; mode = mode || S.mode;
  return B.filter(function (g) { return (mode === "all" || g.mode === mode) && (season === "all" || g.s === season); });
}
function dec(gs) { var w = 0, n = 0; gs.forEach(function (g) { if (g.r !== "d") { n++; if (g.r === "w") w++; } }); return { w: w, n: n }; }
function sinfo(n) { for (var i = 0; i < SINFO.length; i++) if (SINFO[i].n === n) return SINFO[i]; return null; }
function seasonLabel(s) {
  if (s === "all") return "全シーズン";
  var i = sinfo(s); return "シーズン" + s + (i ? "（" + md(i.from) + "〜" + (i.last ? "" : md(i.to)) + "）" : "");
}

/* ---------- 部品 ---------- */
function card(i, w) {
  var nm = D.cards[i] || "?", url = D.icons[i];
  return '<span class="cd" style="--h:' + (hash(nm) % 360) + (w ? ";--w:" + w + "px" : "") + '" data-tip="' + esc(nm) + '">' +
    (IMG && url ? '<img src="' + esc(url) + '" alt="" loading="lazy" onerror="this.remove()">' : "") +
    "<i>" + esc(abbr(nm)) + "</i></span>";
}
function deck8(ids, w) { return '<span class="deck8">' + ids.slice(0, 8).map(function (c) { return card(c, w); }).join("") + "</span>"; }
function dotplot(w, n, base) {
  var r = wilson(w, n), t = tone(r[0], base, n);
  return '<div class="dp"><div class="g"></div><div class="bl" style="left:' + pc(base, 2) + '%"></div>' +
    '<div class="ci ' + t + '" style="left:' + pc(r[1], 2) + "%;width:" + Math.max(1.5, (r[2] - r[1]) * 100).toFixed(2) + '%"></div>' +
    '<div class="d ' + t + '" style="left:' + pc(r[0], 2) + '%"></div></div>';
}
function dax(base, lab) {
  return '<div class="dax"><span style="left:0">0</span><span style="left:25%">25</span><span style="left:50%">50</span>' +
    '<span style="left:75%">75</span><span style="left:100%">100</span></div>';
}
/* 勝率の表。items: {lab, w, n, use?} */
function dtable(items, base, o) {
  o = o || {};
  if (!items.length) return '<p class="empty">該当する試合がない。</p>';
  var useCol = o.total != null;
  if (pageW() < 760) return dtableNarrow(items, base, o, useCol);
  var cols = (o.labW || "minmax(0,1.3fr)") + (useCol ? " 96px" : "") + " minmax(120px,1.4fr) 62px " + (o.recW || "72px");
  var maxU = 0; items.forEach(function (it) { if (it.n > maxU) maxU = it.n; });
  var h = '<div class="dt' + (o.tight ? " tight" : "") + '" style="--cols:' + cols + '">' +
    '<div class="h">' + esc(o.head || "") + "</div>" + (useCol ? '<div class="h">使用率</div>' : "") +
    '<div class="h">' + dax(base) + '</div><div class="h r">勝率</div><div class="h r z">勝敗</div>';
  items.forEach(function (it) {
    var r = wilson(it.w, it.n), t = tone(r[0], base, it.n);
    var tip = (it.tip || "") + (it.tip ? "\n" : "") + "勝率 " + pc(r[0]) + "%（" + rec(it.w, it.n) + "）\n95%信頼区間 " + pc(r[1]) + "〜" + pc(r[2]) + "%" +
      (it.n < RELIABLE_N ? "\n" + RELIABLE_N + "試合未満のため判定不可" : "");
    h += '<div class="c lab">' + it.lab + "</div>" +
      (useCol ? '<div class="c use"><i style="width:' + Math.max(2, 46 * it.n / o.total).toFixed(1) + 'px;max-width:46px"></i>' + pc(it.n / o.total, 0) + "%</div>" : "") +
      '<div class="c" data-tip="' + esc(tip) + '">' + dotplot(it.w, it.n, base) + "</div>" +
      '<div class="c pv ' + t + '-t">' + pc(r[0]) + "<small>%</small></div>" +
      '<div class="c rc z">' + rec(it.w, it.n) + "</div>";
  });
  return h + "</div>";
}
function tiles(items, base) {
  if (!items.length) return '<p class="empty">該当する試合がない。</p>';
  return '<div class="cg">' + items.map(function (it) {
    var r = wilson(it.w, it.n), t = tone(r[0], base, it.n);
    var tip = D.cards[it.c] + "\n" + it.sub + "（" + it.n + "試合）\n勝率 " + pc(r[0]) + "%（" + rec(it.w, it.n) + "）\n95%信頼区間 " + pc(r[1]) + "〜" + pc(r[2]) + "%" +
      (it.n < RELIABLE_N ? "\n" + RELIABLE_N + "試合未満のため判定不可" : "");
    return '<div data-tip="' + esc(tip) + '"><div class="ctop">' + card(+it.c, 34) + '<span class="cnm"><b>' + esc(D.cards[it.c]) + "</b><small>" + it.sub + "</small></span></div>" +
      '<div class="cmid"><span class="pv ' + t + '-t">' + pc(r[0]) + "<small>%</small></span><span>" + rec(it.w, it.n) + "</span></div>" + dotplot(it.w, it.n, base) + "</div>";
  }).join("") + "</div>";
}
function dtableNarrow(items, base, o, useCol) {
  var h = '<div class="dtm"><div class="dtm-h"><div>' + dax(base) + '</div><div class="r">勝率・勝敗</div></div>';
  items.forEach(function (it) {
    var r = wilson(it.w, it.n), t = tone(r[0], base, it.n);
    var tip = (it.tip || "") + (it.tip ? "\n" : "") + "勝率 " + pc(r[0]) + "%（" + rec(it.w, it.n) + "）\n95%信頼区間 " + pc(r[1]) + "〜" + pc(r[2]) + "%" +
      (it.n < RELIABLE_N ? "\n" + RELIABLE_N + "試合未満のため判定不可" : "");
    h += '<div class="dtm-r"><div class="lab">' + (o.narrowLab ? o.narrowLab(it) : it.lab) + "</div>" +
      '<div class="pv ' + t + '-t">' + pc(r[0]) + "<small>%</small></div>" +
      '<div class="dpw" data-tip="' + esc(tip) + '">' + dotplot(it.w, it.n, base) + "</div>" +
      '<div class="rc">' + rec(it.w, it.n) + (useCol ? "<small>使用率 " + pc(it.n / o.total, 0) + "%</small>" : "") + "</div></div>";
  });
  return h + "</div>";
}
function sec(title, small, inner, lead, note) {
  return '<section class="sec"><h2>' + esc(title) + (small ? "<small>" + esc(small) + "</small>" : "") + "</h2>" +
    (lead ? '<p class="lead">' + esc(lead) + "</p>" : "") + inner + (note ? '<p class="note">' + esc(note) + "</p>" : "") + "</section>";
}
function pageW() { return Math.max(300, document.getElementById("page").clientWidth); }
function niceSep(lo, hi, xOf, y0, y1, labY) {   // シーズンの区切り線と名前（期間内のみ）
  var o = "";
  SINFO.forEach(function (si, i) {
    var a = si.f ? ms(si.f) : -Infinity, b = i + 1 < SINFO.length ? ms(SINFO[i + 1].f) : Infinity;
    var x0 = xOf(Math.max(a, lo)), x1 = xOf(Math.min(b, hi));
    if (b <= lo || a >= hi) return;
    if (a > lo) o += '<line class="ssep" x1="' + x0.toFixed(1) + '" y1="' + (labY - 12) + '" x2="' + x0.toFixed(1) + '" y2="' + y1 + '"/>';
    var w = x1 - x0;
    if (w >= 30) o += '<text class="tk b" x="' + ((x0 + x1) / 2).toFixed(1) + '" y="' + labY + '" text-anchor="middle">' + (w >= 80 ? "シーズン" : "S") + si.n + "</text>";
  });
  return o;
}

/* ---------- 表紙（まとめ） ---------- */
function rankedOf(season) {
  var g = B.filter(function (x) { return x.s === season && x.mode === "pol"; }), dd = dec(g);
  var peak = null; P.forEach(function (x) { if (x.s === season && x.u && (peak == null || x.tr > peak)) peak = x.tr; });
  return { n: g.length, dd: dd, r: wilson(dd.w, dd.n), peak: peak };
}
function profilePage() {
  var me = D.me, cur = SINFO[SINFO.length - 1], lastP = P[P.length - 1];
  var fk = Object.keys(D.finals).map(Number).sort(function (a, b) { return b - a; }), pn = fk[0], pf = D.finals[pn];
  var c = rankedOf(cur.n), pv = pn != null ? rankedOf(pn) : null;
  var wl = function (x) { return x.dd.n ? rec(x.dd.w, x.dd.n) + "・勝率 " + pc(x.r[0]) + "%" : "試合なし"; };
  var rateCell = function (lg, tr) {
    var isRate = lg >= D.ult && tr;
    return '<span class="v' + (isRate ? "" : " st") + '">' + stageOrRate(lg, tr) + "</span>" +
      '<span class="rk' + (isRate ? ' lgn" style="color:var(--ult)' : "") + '">' + (isRate ? lname(Math.min(lg, D.ult)) : "ステージ") + "</span>";
  };
  var days = {}; B.forEach(function (g) { days[g.d] = 1; });
  var bio = '<p class="bio"><span><b>' + esc(me.tag) + "</b></span><span>記録開始 " + md(B[0].d) + "（" + Object.keys(days).length + "日・" + fmtn(B.length) + "試合）</span>" +
    "<span>2時間ごとに自動更新</span></p>";
  var tot = me.wins + me.losses;
  var hero = '<div class="hero h4">' +
    '<div><span class="k">自己ベスト</span>' + rateCell(me.best_lg, me.best_tr) +
      '<span class="s">世界 ' + fmtn(me.best_rank) + "位・" + esc(me.best_when) + "に達成</span></div>" +
    '<div><span class="k">今シーズン（シーズン' + cur.n + (cur.last ? "・開催中" : "") + "）</span>" + rateCell(lastP.lg, lastP.tr) +
      '<span class="s">' + (c.peak != null ? "シーズン最高 " + fmtn(c.peak) + "<br>" : "") + wl(c) + "</span></div>" +
    (pf ? '<div><span class="k">前シーズン（シーズン' + pn + "）</span>" + rateCell(pf.lg, pf.tr) +
      '<span class="s">' + (pf.rank ? "世界 " + fmtn(pf.rank) + "位<br>" : "") + (pv.peak != null ? "シーズン最高 " + fmtn(pv.peak) + "<br>" : "") + wl(pv) + "</span></div>" : "<div></div>") +
    '<div><span class="k">通算（全モード）</span><span class="v">' + pc(me.wins / tot) + '<small style="font-size:14px;color:var(--ink3);font-weight:400">%</small></span>' +
      '<span class="rk">勝率</span><span class="s">' + fmtn(me.wins) + "勝 " + fmtn(me.losses) + "敗<br>トロフィー " + fmtn(me.trophies) + "</span></div>" +
    "</div>";
  return bio +
    sec("ランク戦の成績", "", hero, "", "自己ベストと通算は、公式APIがアカウントに記録している値（記録開始より前を含む）。シーズンの勝敗は、このサイトが記録したランク戦の試合から数えたもの。") +
    sec("シーズン別の成績", "", seasonLedger(), "",
      "最終成績は、シーズンが替わった時点でAPIが返す前シーズンの確定値。Ultimate到達は記録上で初めてレートが出た日。勝率の下の数字は95%信頼区間で、" + RELIABLE_N + "試合未満は灰色。") +
    sec("対戦した相手の中での位置", "", pctPanel(), "これまで対戦した相手の中で、上から何%の位置にいるか。右へ行くほど上位で赤、左ほど下位で青。点線が真ん中。",
      "マッチングで当たった相手との比較なので、プレイヤー全体の中での順位ではない。レート戦の自己ベストは、レートの数字が出る段階まで届いていない相手も下位として数に入れている。相手の値は最後に情報を取得した時点のもの。");
}

/* ---------- 推移 ---------- */
function streaks(gs) {
  var bw = 0, bl = 0, cw = 0, cl = 0;
  gs.forEach(function (g) {
    if (g.r === "w") { cw++; cl = 0; } else if (g.r === "l") { cl++; cw = 0; } else { cw = 0; cl = 0; }
    if (cw > bw) bw = cw; if (cl > bl) bl = cl;
  });
  return [bw, bl];
}
function trendPage() {
  var all = games(); if (!all.length) return '<p class="empty">このシーズンの試合がまだない。</p>';
  return anchor("rate", sec("レートと勝率の推移", S.season === "all" ? "全シーズン" : "シーズン" + S.season, rateChart(),
      "", "上はランク戦のレート（Ultimate Champion 到達前はステージ）。下は表示中のモードの勝率（直近" + WR_WIN + "試合の移動平均）と、1日の試合数。紫の帯がUltimate Championの範囲。")) +
    anchor("cal", sec("日ごとの成績", "", calendar(all), "", "色は勝率。50%より上は赤、下は青で、濃いほど差が大きい。試合が少ない日ほど、偶然で極端な値になりやすい。"));
}
function weekStart(k) { var d = new Date(k + "T00:00:00"); d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); return dayKey(d); }

function calendar(gs) {
  var by = {}; gs.forEach(function (g) { var c = by[g.d] || (by[g.d] = { w: 0, n: 0, g: 0 }); c.g++; if (g.r !== "d") { c.n++; if (g.r === "w") c.w++; } });
  var first = weekStart(gs[0].d), d0 = gs[0].d, last = gs[gs.length - 1].d, h = '<div class="cal"><div class="cw"></div>' +
    WD.map(function (d, i) { return '<div class="ch' + (i >= 5 ? " we" : "") + '">' + d + "</div>"; }).join("");
  for (var wk = first; wk <= last; wk = addDays(wk, 7)) {
    var m = addDays(wk, 6);
    var ml = ""; for (var q = 0; q < 7; q++) { var dq = addDays(wk, q); if (dq.slice(8) === "01") ml = (+dq.slice(5, 7)) + "月"; }
    if (wk === first) ml = (+d0.slice(5, 7)) + "月";
    h += '<div class="cw">' + ml + "</div>";
    for (var r = 0; r < 7; r++) {
      var d = addDays(wk, r), v = by[d], out = d < d0 || d > last;
      if (out) { h += '<div class="cc o"></div>'; continue; }
      var day = '<span class="cd1">' + (+d.slice(8)) + "</span>";
      if (!v) { h += '<div class="cc" data-tip="' + d + "（" + WD[r] + '）\n試合なし">' + day + "</div>"; continue; }
      var p = v.n ? v.w / v.n : .5, diff = Math.max(-.3, Math.min(.3, p - .5)), k2 = Math.abs(diff) / .3;
      var bg = "color-mix(in oklab," + (diff >= 0 ? "var(--up)" : "var(--down)") + " " + Math.round(10 + 55 * k2) + "%,var(--cell))";
      var tn = v.n < 5 ? "na" : p > .5 ? "up" : p < .5 ? "down" : "na";
      h += '<div class="cc f" style="background:' + bg + '" data-tip="' + esc(d + "（" + WD[r] + "）\n" + v.g + "試合　" + rec(v.w, v.n) + "\n勝率 " + pc(p) + "%") + '">' + day +
        '<b>' + pc(p, 0) + '<small>%</small></b><span class="cn">' + v.g + "戦</span></div>";
    }
  }
  h += "</div>";
  h += '<div class="scale">負け越し<span class="sw">' + [1, .66, .33].map(function (k) { return '<i style="background:color-mix(in oklab,var(--down) ' + Math.round(10 + 55 * k) + '%,var(--cell))"></i>'; }).join("") +
    '<i style="background:var(--cell)"></i>' + [.33, .66, 1].map(function (k) { return '<i style="background:color-mix(in oklab,var(--up) ' + Math.round(10 + 55 * k) + '%,var(--cell))"></i>'; }).join("") + "</span>勝ち越し</div>";
  return h;
}

/* ---------- 使用デッキ ---------- */
function deckPage() {
  var gs = games(), dd = dec(gs); if (!dd.n) return '<p class="empty">このシーズンの試合がまだない。</p>';
  var base = dd.w / dd.n, decks = {}, face = {}, mine = {};
  gs.forEach(function (g) {
    if (g.r === "d" || !g.my.length) return;
    var k = g.my.slice().sort(function (a, b) { return a - b; }).join(",");
    if (!decks[k]) { decks[k] = { w: 0, n: 0 }; face[k] = g.my; }
    decks[k].n++; if (g.r === "w") decks[k].w++;
    var seen = {}; g.my.forEach(function (c) { if (seen[c]) return; seen[c] = 1; var m = mine[c] || (mine[c] = { w: 0, n: 0 }); m.n++; if (g.r === "w") m.w++; });
  });
  var narrow = pageW() < 760, cw8 = narrow ? 26 : 24;
  var items = Object.keys(decks).sort(function (a, b) { return decks[b].n - decks[a].n; }).slice(0, 8).map(function (k) {
    return { lab: narrow ? deck8(face[k], cw8).replace('class="deck8"', 'class="deck8 d42"') : deck8(face[k], cw8), w: decks[k].w, n: decks[k].n, tip: face[k].map(function (c) { return D.cards[c]; }).join(" / ") };
  });
  var vary = Object.keys(mine).filter(function (c) { return mine[c].n < dd.n; }).sort(function (a, b) { return mine[b].n - mine[a].n; }).slice(0, 12);
  var ciHtml = tiles(vary.map(function (c) { return { c: c, w: mine[c].w, n: mine[c].n, sub: "使用率 " + pc(mine[c].n / dd.n, 0) + "%" }; }), base);
  var labW = "232px";
  return anchor("mydeck", sec("デッキ構成別の勝率", "基準線は期間平均 " + pc(base, 0) + "%", dtable(items, base, { head: "構成（8枚）", total: dd.n, labW: labW }),
      "", "使用したデッキ構成は" + Object.keys(decks).length + "種類。試合数の多い順に上位8件。")) +
    '<div id="sec-mycard"></div>' + sec("入れ替えのあったカード", "使用率の高い順", ciHtml,
      "全試合に入っている固定枠は差が出ないため除外している。", "点が推定値、帯が95%信頼区間。帯どうしが重なる範囲では、差があるとは言えない。" + RELIABLE_N + "試合未満は灰色。");
}

/* ---------- 対戦相手 ---------- */
function oppStats(gs) {
  var opp = {};
  gs.forEach(function (g) {
    if (g.r === "d") return; var seen = {};
    g.op.forEach(function (c) { if (seen[c]) return; seen[c] = 1; var m = opp[c] || (opp[c] = { w: 0, n: 0 }); m.n++; if (g.r === "w") m.w++; });
  });
  return opp;
}
function enemyPage() {
  var gs = games(), dd = dec(gs); if (!dd.n) return '<p class="empty">このシーズンの試合がまだない。</p>';
  var base = dd.w / dd.n, opp = oppStats(gs);
  var ok = Object.keys(opp).filter(function (c) { return opp[c].n >= MIN_CARD_N; });
  var byWr = ok.slice().sort(function (a, b) { return opp[a].w / opp[a].n - opp[b].w / opp[b].n; });
  var mk = function (c) { return { c: c, w: opp[c].w, n: opp[c].n, sub: "遭遇 " + opp[c].n + "試合" }; };
  return '<div id="sec-map"></div>' + sec("対戦カードの地図", "横＝よく当たる、縦＝勝てている", scatter(ok, opp, dd.n, base),
      "", "右下ほど「よく当たるのに勝てていない」カード。点の大きさは遭遇した試合数。" + MIN_CARD_N + "試合以上当たったカードのみ（全" + Object.keys(opp).length + "種類のうち" + ok.length + "種類）。") +
    '<div id="sec-oppcard"></div>' +
    sec("勝率の低いカード", "低い順に12枚", tiles(byWr.slice(0, 12).map(mk), base)) +
    sec("勝率の高いカード", "高い順に12枚", tiles(byWr.slice().reverse().slice(0, 12).map(mk), base),
      "", "点が推定値、帯が95%信頼区間、点線が期間平均。" + RELIABLE_N + "試合未満は灰色。");
}
function scatter(keys, opp, total, base) {
  var W = pageW(), narrow = W < 560, H = narrow ? 300 : 380, padL = 34, padR = 12, padT = 12, padB = 30;
  var pw = W - padL - padR, ph = H - padT - padB;
  var mx = 0; keys.forEach(function (c) { var f = opp[c].n / total; if (f > mx) mx = f; });
  mx = Math.min(1, Math.ceil(mx * 10 + .5) / 10);
  var X = function (f) { return padL + pw * f / mx; }, Y = function (p) { return padT + ph * (1 - p); };
  var o = ['<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="対戦カードの遭遇率と勝率">'];
  o.push('<rect x="' + X(mx * .5) + '" y="' + Y(base) + '" width="' + (X(mx) - X(mx * .5)) + '" height="' + (Y(0) - Y(base)) + '" style="fill:var(--downbg);opacity:.6"/>');
  [0, .25, .5, .75, 1].forEach(function (v) {
    o.push('<line class="' + (v ? "gr" : "ax") + '" x1="' + padL + '" x2="' + (padL + pw) + '" y1="' + Y(v) + '" y2="' + Y(v) + '"/>');
    o.push('<text class="tk" x="' + (padL - 6) + '" y="' + (Y(v) + 3.5) + '" text-anchor="end">' + v * 100 + (v === 1 ? "%" : "") + "</text>");
  });
  for (var f = 0; f <= mx + 1e-9; f += mx <= .3 ? .05 : .1) {
    o.push('<text class="tk" x="' + X(f) + '" y="' + (H - 10) + '" text-anchor="middle">' + Math.round(f * 100) + "%</text>");
    if (f > 0) o.push('<line class="gr" x1="' + X(f) + '" x2="' + X(f) + '" y1="' + padT + '" y2="' + (padT + ph) + '"/>');
  }
  o.push('<line class="ref" x1="' + padL + '" x2="' + (padL + pw) + '" y1="' + Y(base) + '" y2="' + Y(base) + '"/>');
  o.push('<text class="tk v" x="' + (padL + pw) + '" y="' + (Y(base) - 6) + '" text-anchor="end">期間平均 ' + pc(base, 0) + "%</text>");
  o.push('<text class="tk v" x="' + (padL + pw - 6) + '" y="' + (Y(0) - 8) + '" text-anchor="end">よく当たるのに勝てていない</text>');
  var pts = keys.map(function (c) { var m = opp[c], r = wilson(m.w, m.n); return { c: c, x: X(m.n / total), y: Y(r[0]), r: 3 + Math.sqrt(m.n) * .55, t: tone(r[0], base, m.n), m: m, ci: r }; });
  pts.sort(function (a, b) { return b.r - a.r; });
  pts.forEach(function (p) {
    var col = p.t === "up" ? "var(--up)" : p.t === "down" ? "var(--down)" : "var(--na)";
    o.push('<circle cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="' + p.r.toFixed(1) + '" style="fill:' + col + ';fill-opacity:' + (p.t === "na" ? .45 : .8) + ';stroke:var(--bg);stroke-width:1.5" data-tip="' +
      esc(D.cards[p.c] + "\n" + p.m.n + "試合で遭遇（" + pc(p.m.n / total) + "%）\n勝率 " + pc(p.ci[0]) + "%（" + rec(p.m.w, p.m.n) + "）\n95%信頼区間 " + pc(p.ci[1]) + "〜" + pc(p.ci[2]) + "%") + '"/>');
  });
  var boxes = [], lab = pts.slice().sort(function (a, b) { return b.m.n - a.m.n; }).slice(0, narrow ? 8 : 16);
  lab.forEach(function (p) {
    var t = D.cards[p.c], tw = t.length * 6.2, lx = p.x + p.r + 4, ly = p.y + 3.5;
    if (lx + tw > padL + pw) lx = p.x - p.r - 4 - tw;
    var bx = [lx, ly - 9, lx + tw, ly + 2];
    if (boxes.some(function (q) { return !(bx[2] < q[0] || bx[0] > q[2] || bx[3] < q[1] || bx[1] > q[3]); })) return;
    boxes.push(bx);
    o.push('<text class="tk v" x="' + lx.toFixed(1) + '" y="' + ly.toFixed(1) + '" style="pointer-events:none">' + esc(t) + "</text>");
  });
  o.push('<text class="tk" x="' + padL + '" y="' + (H - 10) + '" style="display:none"></text></svg>');
  return '<div class="tw">' + o.join("") + "</div>";
}

/* ---------- 調子 ---------- */
function formPage() {
  var gs = games(), dd = dec(gs); if (!dd.n) return '<p class="empty">このシーズンの試合がまだない。</p>';
  var base = dd.w / dd.n;
  function tally(fn, keys) {
    var m = {}; gs.forEach(function (g) { if (g.r === "d") return; var k = fn(g); if (k == null) return; var c = m[k] || (m[k] = { w: 0, n: 0 }); c.n++; if (g.r === "w") c.w++; });
    return keys.filter(function (k) { return m[k]; }).map(function (k) { return { lab: '<span class="nm">' + esc(k) + "</span>", w: m[k].w, n: m[k].n, tip: k }; });
  }
  var prev = tally(function (g) { var s = g.prev; return s <= -2 ? "2連敗後" : s === -1 ? "1敗後" : s === 0 ? "セッション初戦" : s === 1 ? "1勝後" : "2連勝後"; },
    ["2連敗後", "1敗後", "セッション初戦", "1勝後", "2連勝後"]);
  var pos = tally(function (g) { return g.pos >= 6 ? "6戦目以降" : g.pos + "戦目"; }, ["1戦目", "2戦目", "3戦目", "4戦目", "5戦目", "6戦目以降"]);
  return anchor("hm", sec("時間帯と曜日", "色は期間平均 " + pc(base, 0) + "% との差", heatmap(gs, base), "",
      "マスの数字は試合数（触れると勝率が出る）。" + RELIABLE_N + "試合未満のマスは淡く表示している（判定不可）。右の列は曜日ごとの勝率、下の棒は時間帯ごとの試合数。")) +
    '<div class="grid2" id="sec-streak">' +
    sec("直前の結果別", "", dtable(prev, base, { head: "直前", tight: true, recW: "64px", labW: "minmax(0,96px)" })) +
    sec("連続対戦数別", "", dtable(pos, base, { head: "何戦目", tight: true, recW: "64px", labW: "minmax(0,96px)" })) +
    "</div>" +
    anchor("ses", sec("プレイごとの勝ち負け", "1列が1回のプレイ", sessions(gs), "",
      "前の試合から30分以上あいたら別のプレイとして区切っている。上から順に1戦目、2戦目…。赤が勝ち、青が負け。"));
}
function heatmap(gs, base) {
  var hs = {}, cell = {}, rowT = [], colT = {};
  gs.forEach(function (g) {
    if (g.r === "d") return; hs[g.h] = 1;
    var k = g.wd + "-" + g.h, c = cell[k] || (cell[k] = { w: 0, n: 0 }); c.n++; if (g.r === "w") c.w++;
    var r = rowT[g.wd] || (rowT[g.wd] = { w: 0, n: 0 }); r.n++; if (g.r === "w") r.w++;
    var q = colT[g.h] || (colT[g.h] = { w: 0, n: 0 }); q.n++; if (g.r === "w") q.w++;
  });
  var hl = Object.keys(hs).map(Number), h0 = Math.min.apply(null, hl), h1 = Math.max.apply(null, hl), hours = [];
  for (var h = h0; h <= h1; h++) hours.push(h);
  var narrow = pageW() < 560, ch = narrow ? 24 : 28, mc = 0;
  hours.forEach(function (h) { if (colT[h] && colT[h].n > mc) mc = colT[h].n; });
  function fill(w, n) {
    var p = w / n, diff = Math.max(-.25, Math.min(.25, p - base)), k = Math.abs(diff) / .25;
    var c = "color-mix(in oklab," + (diff >= 0 ? "var(--up)" : "var(--down)") + " " + Math.round(12 + 70 * k) + "%,var(--cell))";
    return "background:" + c + ";opacity:" + (n >= RELIABLE_N ? 1 : .35 + .65 * n / RELIABLE_N).toFixed(2);
  }
  var o = '<div class="tw"><div class="hm" style="--nh:' + hours.length + ";--ch:" + ch + "px;min-width:" + (hours.length * (narrow ? 15 : 22) + (narrow ? 110 : 150)) + 'px">';
  o += '<div class="rows">' + WD.map(function (d) { return '<div class="rl">' + d + "</div>"; }).join("") + "</div>";
  o += '<div class="cells">';
  for (var r = 0; r < 7; r++) {
    o += '<div class="row">';
    hours.forEach(function (h) {
      var c = cell[r + "-" + h];
      if (!c) { o += '<div class="cell e" data-tip="' + WD[r] + "曜 " + h + '時台\n試合なし"></div>'; return; }
      var ci = wilson(c.w, c.n);
      o += '<div class="cell" style="' + fill(c.w, c.n) + '" data-tip="' + esc(WD[r] + "曜 " + h + "時台\n勝率 " + pc(ci[0]) + "%（" + rec(c.w, c.n) + "）\n95%信頼区間 " + pc(ci[1]) + "〜" + pc(ci[2]) + "%" + (c.n < RELIABLE_N ? "\n判定不可（" + RELIABLE_N + "試合未満）" : "")) + '">' + (narrow ? "" : c.n) + "</div>";
    });
    o += "</div>";
  }
  o += "</div>";
  o += '<div class="mg">' + WD.map(function (d, i) {
    var t = rowT[i]; if (!t) return '<div class="mr"><small>-</small></div>';
    var ci = wilson(t.w, t.n), tn = tone(ci[0], base, t.n);
    return '<div class="mr" data-tip="' + esc(d + "曜\n勝率 " + pc(ci[0]) + "%（" + rec(t.w, t.n) + "）\n95%信頼区間 " + pc(ci[1]) + "〜" + pc(ci[2]) + "%") + '"><b class="' + tn + '-t">' + pc(ci[0], 0) + "%</b><small>" + t.n + "戦</small></div>";
  }).join("") + "</div>";
  o += '<div class="foot">' + hours.map(function (h) {
    var t = colT[h], n = t ? t.n : 0, ci = t ? wilson(t.w, t.n) : null;
    return '<div data-tip="' + esc(h + "時台\n" + (t ? "勝率 " + pc(ci[0]) + "%（" + rec(t.w, t.n) + "）" : "試合なし")) + '"><div class="bars"><i style="height:' + (mc ? Math.max(n ? 2 : 0, 34 * n / mc) : 0).toFixed(1) + 'px"></i></div><span>' + (narrow && h % 2 ? "" : h) + "</span></div>";
  }).join("") + "</div>";
  o += "</div></div>";
  o += '<div class="scale">期間平均より低い<span class="sw">' + [1, .6, .25].map(function (k) { return '<i style="background:color-mix(in oklab,var(--down) ' + Math.round(12 + 70 * k) + '%,var(--cell))"></i>'; }).join("") +
    '<i style="background:var(--cell)"></i>' + [.25, .6, 1].map(function (k) { return '<i style="background:color-mix(in oklab,var(--up) ' + Math.round(12 + 70 * k) + '%,var(--cell))"></i>'; }).join("") + "</span>高い</div>";
  return o;
}
function sessions(gs) {
  var ss = [], cur = null;
  gs.forEach(function (g) { if (!cur || cur.id !== g.ses) { cur = { id: g.ses, g: [] }; ss.push(cur); } cur.g.push(g); });
  var W = pageW(), cw = 10, gap = 4, maxN = 0;
  var fit = Math.floor((W - 4) / (cw + gap));
  var show = ss.slice(-Math.max(fit, 20));
  show.forEach(function (s) { if (s.g.length > maxN) maxN = s.g.length; });
  maxN = Math.min(maxN, 24);
  var Wn = show.length * (cw + gap), H = maxN * (cw + 2) + 22, o = [];
  o.push('<div class="strip"><svg width="' + Wn + '" height="' + H + '" viewBox="0 0 ' + Wn + " " + H + '" role="img" aria-label="プレイごとの勝敗">');
  var lastLab = -99, lastD = "";
  show.forEach(function (s, i) {
    var x0 = i * (cw + gap);
    s.g.slice(0, maxN).forEach(function (g, j) {
      var col = g.r === "w" ? "var(--up)" : g.r === "l" ? "var(--down)" : "var(--na)";
      var nm = (D.opps[g.tag] && D.opps[g.tag].name) || g.name;
      o.push('<rect x="' + x0 + '" y="' + j * (cw + 2) + '" width="' + cw + '" height="' + cw + '" rx="2" style="fill:' + col + '" data-tip="' +
        esc(g.t.slice(5, 16).replace("-", "/") + "　" + (j + 1) + "戦目\n" + (g.r === "w" ? "勝ち" : g.r === "l" ? "負け" : "引き分け") + " " + g.mc + "-" + g.oc + (nm ? "\n相手 " + nm : "")) + '"/>');
    });
    var d = s.g[0].d;
    if (d !== lastD && i - lastLab >= 6) { o.push('<text class="tk" x="' + x0 + '" y="' + (H - 4) + '">' + md(d) + "</text>"); lastLab = i; }
    lastD = d;
  });
  o.push("</svg></div>");
  if (ss.length > show.length) o.push('<p class="note">直近の' + show.length + "回を表示（このシーズンは全" + ss.length + "回）。</p>");
  return o.join("");
}

/* ---------- レート ---------- */
function stageOrRate(lg, tr) { return lg >= D.ult && tr ? fmtn(tr) : lname(lg); }
function seasonLedger() {
  var row = function (cls, c1, c2, fin, finSub, peak, reach, gs) {
    var dd = dec(gs), r = wilson(dd.w, dd.n);
    return '<tr class="' + cls + '"><td class="l">' + c1 + '</td><td class="l opt">' + c2 + "</td>" +
      '<td><span class="big">' + fin + "</span>" + finSub + "</td><td>" + peak + '</td><td class="opt">' + reach + "</td>" +
      '<td class="opt">' + gs.length + '</td><td class="opt">' + (dd.n ? rec(dd.w, dd.n) : "-") + "</td>" +
      '<td class="' + tone(r[0], .5, dd.n) + '-t"><b style="color:inherit">' + (dd.n ? pc(r[0]) + "%" : "-") + "</b>" +
      (dd.n ? '<span class="ci">' + pc(r[1]) + "〜" + pc(r[2]) + "</span>" : "") + "</td></tr>";
  };
  var allPeak = null;
  var rows = SINFO.slice().reverse().map(function (si) {
    var p = P.filter(function (x) { return x.s === si.n; });
    var g = B.filter(function (x) { return x.s === si.n && x.mode === "pol"; });
    var peak = null; p.forEach(function (x) { if (x.u && (peak == null || x.tr > peak)) peak = x.tr; });
    if (peak != null && (allPeak == null || peak > allPeak)) allPeak = peak;
    var reach = null; for (var i = 0; i < p.length; i++) if (p[i].u) { reach = p[i]; break; }
    var fin = D.finals[si.n], cur = !fin && p.length ? p[p.length - 1] : null;
    var days = reach && si.from ? Math.round((ms(reach.t.slice(0, 10)) - ms(si.from)) / 864e5) + 1 : null;
    return row(S.season === si.n ? "sel" : "", "<b>シーズン" + si.n + "</b>" + (si.last ? '<span class="sub">開催中</span>' : ""),
      si.from ? md(si.from) + "〜" + (si.last ? "" : md(si.to)) : "-",
      fin ? stageOrRate(fin.lg, fin.tr) : cur ? stageOrRate(cur.lg, cur.tr) : "-",
      fin ? '<span class="sub">確定' + (fin.rank ? "・世界" + fmtn(fin.rank) + "位" : "") + "</span>" : cur ? '<span class="sub">現在</span>' : "",
      peak != null ? fmtn(peak) : "-",
      reach ? md(reach.t.slice(0, 10)) + '<span class="sub">開幕から' + days + "日目</span>" : "-", g);
  }).join("");
  rows += row("tot", "<b>記録全体</b>", md(B[0].d) + "〜", "-", "", allPeak != null ? fmtn(allPeak) : "-", "-",
    B.filter(function (x) { return x.mode === "pol"; }));
  return '<div class="tw ledger"><table class="t"><thead><tr><th class="l">シーズン</th><th class="l opt">期間</th><th>最終成績</th><th>シーズン最高<br>レート</th><th class="opt">Ultimate<br>到達</th><th class="opt">ランク戦<br>試合数</th><th class="opt">勝敗</th><th>勝率</th></tr></thead><tbody>' + rows + "</tbody></table></div>";
}
function pctColor(p) {
  return p >= 50 ? "color-mix(in oklab,var(--up) " + Math.round(35 + 65 * (p - 50) / 50) + "%,var(--na))"
                 : "color-mix(in oklab,var(--down) " + Math.round(35 + 65 * (50 - p) / 50) + "%,var(--na))";
}
function pctPanel() {
  if (!D.pct || !D.pct.length) return "";
  var n = D.pct[0].n;
  var h = '<div class="pr"><div class="ph lab2">指標</div><div class="ph sc"><span>下位</span><span>真ん中</span><span>上位</span></div><div class="ph v2" style="text-align:right">自分の値</div>';
  D.pct.forEach(function (m) {
    var v = m.fmt === "pct" ? pc(m.v) + "%" : fmtn(Math.round(m.v)), md2 = m.fmt === "pct" ? pc(m.med) + "%" : m.med < 0 ? "レートなし" : fmtn(Math.round(m.med));
    var top = m.top < 1 ? "1%未満" : Math.round(m.top) + "%";
    h += '<div class="lb">' + esc(m.lab) + "<small>" + m.n + "人と比較</small></div>" +
      '<div class="tr" data-tip="' + esc(m.lab + "\n対戦した相手" + m.n + "人の中で上位" + top + "\n自分 " + v + "／相手の真ん中 " + md2) + '"><div class="trk">' +
      '<span class="md" style="left:50%"></span><span class="bb" style="left:clamp(34px,' + m.p + "%,calc(100% - 34px));background:" + pctColor(m.p) + '">上位' + top + "</span></div></div>" +
      '<div class="vl">' + v + "<small>相手の真ん中 " + md2 + "</small></div>";
  });
  return h + "</div>";
}
function pastSeasons() {
  var ks = Object.keys(D.finals).map(Number).sort(function (a, b) { return b - a; });
  if (!ks.length) return "";
  return '<div class="seasons-past">過去のシーズン' + ks.map(function (k) {
    var f = D.finals[k]; return '<span class="ch">S' + k + "<b>" + stageOrRate(f.lg, f.tr) + "</b></span>";
  }).join("") + "</div>";
}
function jump(list) {
  return '<div class="jump">' + list.map(function (x) { return '<button data-jump="' + x[0] + '">' + x[1] + "</button>"; }).join("") + "</div>";
}
function anchor(id, html) { return '<div id="sec-' + id + '">' + html + "</div>"; }
function timePage() {
  return jump([["rate", "レートと勝率"], ["cal", "日ごと"], ["hm", "時間帯と曜日"], ["streak", "直前の結果・連戦"], ["ses", "プレイごと"]]) +
    trendPage(true) +
    formPage(true);
}
function rateChart() {
  var all = games("all"), gs = games();
  var lo, hi;
  if (S.season === "all") { lo = ms((all.length ? all[0].d : P[0].t.slice(0, 10)) + " 00:00:00"); hi = Math.max(P[P.length - 1].v, all.length ? ms(all[all.length - 1].t) : 0); }
  else {
    var si = sinfo(S.season), i0 = SINFO.indexOf(si);
    lo = si.f ? ms(si.f) : ms(si.from + " 00:00:00");
    hi = i0 + 1 < SINFO.length ? ms(SINFO[i0 + 1].f) : Math.max(P[P.length - 1].v, gs.length ? ms(gs[gs.length - 1].t) : lo + 864e5);
  }
  hi += 36e5;
  var W = pageW(), narrow = W < 560, padR = narrow ? 92 : 112, padT = S.season === "all" ? 34 : 18;
  var RH = narrow ? 150 : 200, WH = narrow ? 96 : 120, GAP = 30, pw = W - padR;
  var ry0 = padT, ry1 = ry0 + RH, wy0 = ry1 + GAP, wy1 = wy0 + WH, H = wy1 + 24;
  var X = function (t) { return pw * (t - lo) / (hi - lo); };
  var o = ['<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="レートと勝率の推移">'];
  // 範囲内の記録点（直前の1点を左端に足して線をつなぐ）
  var vis = [], before = null;
  P.forEach(function (p) { if (p.v < lo) before = p; else if (p.v <= hi) vis.push(p); });
  if (before && S.season === "all") vis.unshift({ t: before.t, v: lo, lg: before.lg, tr: before.tr, u: before.u });
  var ticks = [], yof = null, uT = null, uB = null;
  if (vis.length) {
    var ults = vis.filter(function (p) { return p.u; }).map(function (p) { return p.tr; });
    var stg = vis.filter(function (p) { return !p.u; }).map(function (p) { return p.lg; });
    var mn = function (a) { return Math.min.apply(null, a); }, mxf = function (a) { return Math.max.apply(null, a); };
    if (!stg.length) {
      var a1 = mn(ults), b1 = mxf(ults); if (a1 === b1) { a1 -= 10; b1 += 10; }
      yof = function (p) { return ry0 + RH * (1 - (p.tr - a1) / (b1 - a1)); };
      for (var k = 0; k < 5; k++) ticks.push([ry0 + RH * (1 - k / 4), fmtn(Math.round(a1 + (b1 - a1) * k / 4))]);
      uT = ry0; uB = ry1;
    } else if (!ults.length) {
      var a2 = mn(stg), b2 = Math.max(mxf(stg), a2 + 1);
      yof = function (p) { return ry0 + RH * (1 - (p.lg - a2) / (b2 - a2)); };
      for (k = a2; k <= b2; k++) ticks.push([ry0 + RH * (1 - (k - a2) / (b2 - a2)), lname(k)]);
    } else {
      var slo = mn(stg), shi = Math.max(mxf(stg), D.ult); if (shi === slo) slo = shi - 1;
      var sh = Math.min(RH * .5, Math.max(40, 16 * (shi - slo))), sep = ry1 - sh;
      var rlo = mn(ults), rhi = mxf(ults); if (rhi === rlo) { rlo -= 10; rhi += 10; }
      yof = function (p) { return p.u ? sep - (RH - sh) * (p.tr - rlo) / (rhi - rlo) : ry1 - sh * (p.lg - slo) / (shi - slo); };
      for (k = slo; k < shi; k++) ticks.push([ry1 - sh * (k - slo) / (shi - slo), lname(k)]);
      for (k = 0; k < 5; k++) ticks.push([sep - (RH - sh) * k / 4, fmtn(Math.round(rlo + (rhi - rlo) * k / 4))]);
      uT = ry0; uB = sep;
    }
  }
  if (uT != null && uB - uT > 2) {
    o.push('<rect class="ultb" x="0" y="' + uT + '" width="' + pw + '" height="' + (uB - uT) + '"/>');
    o.push('<text class="ultl" x="6" y="' + (uT + 13) + '">Ultimate Champion</text>');
  }
  ticks.forEach(function (t) {
    if (t[0] > ry0 + 1 && t[0] < ry1 - 1) o.push('<line class="gr" x1="0" x2="' + pw + '" y1="' + t[0].toFixed(1) + '" y2="' + t[0].toFixed(1) + '"/>');
    o.push('<text class="tk" x="' + (pw + 6) + '" y="' + (t[0] + 3.5).toFixed(1) + '">' + esc(t[1]) + "</text>");
  });
  o.push('<line class="ax" x1="0" x2="' + pw + '" y1="' + ry1 + '" y2="' + ry1 + '"/>');
  if (vis.length > 1) {
    var pts = []; vis.forEach(function (p, i) {   // 段差で描く（記録の間は値が変わっていない）
      if (i) pts.push(X(p.v).toFixed(1) + "," + yof(vis[i - 1]).toFixed(1));
      pts.push(X(p.v).toFixed(1) + "," + yof(p).toFixed(1));
    });
    var lp = vis[vis.length - 1];
    pts.push(Math.min(pw, X(Math.min(hi, Date.now()))).toFixed(1) + "," + yof(lp).toFixed(1));
    o.push('<polyline class="ma" points="' + pts.join(" ") + '"/>');
    o.push('<circle class="ptl" cx="' + Math.min(pw, X(Math.min(hi, Date.now()))).toFixed(1) + '" cy="' + yof(lp).toFixed(1) + '" r="4"/>');
  } else if (!vis.length) o.push('<text class="tk" x="' + pw / 2 + '" y="' + (ry0 + RH / 2) + '" text-anchor="middle">この期間はレートの記録がない</text>');
  o.push('<text class="tk v" x="0" y="' + (ry0 - 7) + '">レート</text>');
  // 勝率と試合数
  var mode = all.filter(function (g) { return g.r !== "d"; }), wr = [], w = 0;
  mode.forEach(function (g, i) { if (g.r === "w") w++; if (i >= WR_WIN && mode[i - WR_WIN].r === "w") w--; if (i >= WR_WIN - 1) wr.push({ v: ms(g.t), p: w / WR_WIN }); });
  var vol = {}; all.forEach(function (g) { vol[g.d] = (vol[g.d] || 0) + 1; });
  var dk = [], d0 = dayKey(new Date(lo)), d1 = dayKey(new Date(hi - 36e5));
  for (var dd = d0; dd <= d1; dd = addDays(dd, 1)) dk.push(dd);
  var mv = 0; dk.forEach(function (d) { if ((vol[d] || 0) > mv) mv = vol[d]; });
  dk.forEach(function (d) {
    var n = vol[d] || 0; if (!n) return;
    var x0 = Math.max(0, X(ms(d + " 00:00:00"))), x1 = Math.min(pw, X(ms(addDays(d, 1) + " 00:00:00"))), bw = x1 - x0, bh = (WH - 2) * n / mv;
    o.push('<rect class="volf" x="' + (x0 + bw * .14).toFixed(1) + '" y="' + (wy1 - bh).toFixed(1) + '" width="' + Math.max(.8, bw * .72).toFixed(1) + '" height="' + bh.toFixed(1) + '" rx="' + Math.min(2, bw * .2).toFixed(1) + '"/>');
  });
  [0, .25, .5, .75, 1].forEach(function (v) {
    var yy = wy1 - WH * v;
    if (v !== .5) o.push('<line class="' + (v ? "gr" : "ax") + '" x1="0" x2="' + pw + '" y1="' + yy + '" y2="' + yy + '"/>');
    o.push('<text class="tk" x="' + (pw + 6) + '" y="' + (yy + 3.5) + '">' + v * 100 + (v === 1 ? "%" : "") + "</text>");
  });
  o.push('<line class="ref" x1="0" x2="' + pw + '" y1="' + (wy1 - WH * .5) + '" y2="' + (wy1 - WH * .5) + '"/>');
  var wp = wr.filter(function (q) { return q.v >= lo && q.v <= hi; }).map(function (q) { return X(q.v).toFixed(1) + "," + (wy1 - WH * q.p).toFixed(1); });
  if (wp.length > 1) o.push('<polyline class="raw" points="' + wp.join(" ") + '"/>');
  else o.push('<text class="tk" x="' + pw / 2 + '" y="' + (wy0 + WH / 2) + '" text-anchor="middle">移動平均には' + WR_WIN + "試合の蓄積が要る</text>");
  o.push('<text class="tk v" x="0" y="' + (wy0 - 7) + '">勝率（' + WR_WIN + "試合の移動平均）・薄い棒は1日の試合数</text>");
  if (S.season === "all") o.push(niceSep(lo, hi, X, ry0, wy1, ry0 - 20));
  var used = [], ev = Math.max(1, Math.ceil(dk.length / (narrow ? 4 : 9)));
  for (var i = 0; i < dk.length; i += ev) {
    var xx = X(ms(dk[i] + " 12:00:00")); if (xx < 10 || xx > pw - 10 || used.some(function (u) { return Math.abs(u - xx) < 38; })) continue; used.push(xx);
    o.push('<text class="tk" x="' + xx.toFixed(1) + '" y="' + (wy1 + 16) + '" text-anchor="middle">' + md(dk[i]) + "</text>");
  }
  o.push('<line class="xh" id="xh" x1="0" x2="0" y1="' + ry0 + '" y2="' + wy1 + '"/>');
  var pi = -1, wi = -1, sorted = P;
  dk.forEach(function (d) {
    var de = ms(addDays(d, 1) + " 00:00:00"), x0 = Math.max(0, X(ms(d + " 00:00:00"))), x1 = Math.min(pw, X(de));
    while (pi + 1 < sorted.length && sorted[pi + 1].v < de) pi++;
    while (wi + 1 < wr.length && wr[wi + 1].v < de) wi++;
    var sn = seasonOf(d + " 23:59:59"), tl = [d.replace(/-/g, "/") + (sn ? "（シーズン" + sn + "）" : "")];
    if (pi >= 0) { var pp = sorted[pi]; tl.push(pp.u ? "レート " + fmtn(pp.tr) + "（" + lname(pp.lg) + "）" : "ステージ " + lname(pp.lg)); }
    if (wi >= 0) tl.push("勝率 " + pc(wr[wi].p) + "%（直近" + WR_WIN + "試合）");
    tl.push("この日の試合 " + (vol[d] || 0));
    o.push('<rect class="hit" x="' + x0.toFixed(1) + '" y="' + ry0 + '" width="' + Math.max(0, x1 - x0).toFixed(2) + '" height="' + (wy1 - ry0) + '" data-cx="' + ((x0 + x1) / 2).toFixed(1) + '" data-tip="' + esc(tl.join("\n")) + '"/>');
  });
  o.push("</svg>");
  return '<div class="tw">' + o.join("") + "</div>" +
    '<div class="legend"><span><i class="lgl" style="border-color:var(--up);border-top-width:2.5px"></i>レート・ステージ</span><span><i class="lgl" style="border-top-width:1.5px"></i>勝率（' + WR_WIN + '試合の移動平均）</span>' +
    '<span><i class="lgb" style="background:var(--ultbg);box-shadow:inset 0 0 0 1px color-mix(in oklab,var(--ult) 30%,transparent)"></i>Ultimate Champion</span><span><i class="lgb" style="background:var(--vol);opacity:.7"></i>試合数</span>' +
    (S.season === "all" ? '<span><i class="lgl" style="border-top:1.5px dashed var(--ink3)"></i>シーズンの区切り</span>' : "") + "</div>";
}

/* ---------- 強敵 ---------- */
function rivalOf(o) {
  return o && ((o.pol != null && o.pol <= D.rival.pol) || (o.gt != null && o.gt <= 1000) || (o.ladder != null && o.ladder <= D.rival.ladder) || !!o.rt);
}
function bestRank(o) {
  var c = [];
  if (o.pol != null) c.push([o.pol, "レート戦"]); if (o.gt != null) c.push([o.gt, "GT"]);
  if (o.ladder != null) c.push([o.ladder, "Top Ladder"]); if (o.rt) c.push([D.rival.rt, "GT Top1000"]);
  c.sort(function (a, b) { return a[0] - b[0]; }); return c[0] || [null, ""];
}
function rivalsPage() {
  var gs = games().filter(function (g) { return g.r === "w" && rivalOf(D.opps[g.tag]); });
  if (!gs.length) return sec("勝利した強敵", "", '<p class="empty">このシーズンは、条件を満たす相手にまだ勝っていない。</p>');
  var it = gs.map(function (g) { var o = D.opps[g.tag], b = bestRank(o); return { g: g, o: o, top: b[0], basis: b[1] }; });
  it.sort(function (a, b) { return (a.top || 1e9) - (b.top || 1e9) || (a.o.pol || 1e9) - (b.o.pol || 1e9) || (a.g.t < b.g.t ? 1 : -1); });
  var cnt = {}; it.forEach(function (x) { cnt[x.g.tag] = (cnt[x.g.tag] || 0) + 1; });
  var c = function (v, s, key) { return '<td class="' + (key ? "key" : "") + '">' + (v == null ? "-" : fmtn(v) + (s || "")) + "</td>"; };
  var rows = it.map(function (x, i) {
    return '<tr><td class="l" style="color:var(--ink3)">' + (i + 1) + '</td><td class="l"><b>' + esc(x.o.name || x.g.name) + '</b><span class="sub">' + esc(x.g.tag) + (cnt[x.g.tag] > 1 ? "・" + cnt[x.g.tag] + "回撃破" : "") + "</span></td>" +
      c(x.o.best) + c(x.o.pol, " 位", x.basis === "レート戦") +
      '<td class="' + (x.basis === "GT Top1000" ? "key" : "") + '">' + (x.o.rt ? x.o.rt + " 回" : "-") + "</td>" +
      c(x.o.ladder, " 位", x.basis === "Top Ladder") + c(x.o.battles) +
      '<td class="l">' + x.g.t.slice(5, 16).replace("-", "/") + '<span class="sub">' + deck8(x.g.op, 14) + "</span></td></tr>";
  }).join("");
  return sec("勝利した強敵", it.length + "件", '<div class="tw"><table class="t"><thead><tr><th class="l">#</th><th class="l">相手</th><th>最高<br>レート</th><th>レート戦<br>最高順位</th><th>グローバル<br>トーナメント<br>Top1000</th><th>Top Ladder<br>最高順位</th><th>通算<br>試合数</th><th class="l">撃破した試合・相手のデッキ</th></tr></thead><tbody>' + rows + "</tbody></table></div>",
    "それぞれの相手が持つ順位のうち、最も良いものが高い順。太字が並べ替えの基準にした順位。",
    "レート戦の過去最高順位" + fmtn(D.rival.pol) + "位以内、グローバルトーナメント1,000位以内、または Top Ladder " + fmtn(D.rival.ladder) + "位以内の相手が対象。グローバルトーナメントはAPIから回数しか取れないため、並べ替えでは1,000位として扱う。");
}

/* ---------- 対戦記録 ---------- */
function gmLabel(g) {
  var m = g.gm || "";
  if (/^Ranked/i.test(m)) return "ランク戦";
  if (/^CW_|riverrace|clanwar/i.test(m)) return "クラン戦";
  return m.replace(/_/g, " ");
}
function hpTxt(k, p) {
  var kk = String(k || "0"), king = (kk === "0" || kk === "") ? "王 陥落" : "王 " + fmtn(Math.round(+kk));
  var t = String(p || "").split("|").filter(Boolean).map(function (v) { return fmtn(Math.round(+v)); });
  while (t.length < 2) t.push("陥落");
  return king + "　姫 " + t[0] + "/" + t[1];
}
function donut(w, l, d) {
  var n = w + l + d, R = 30, C = 2 * Math.PI * R, fw = n ? w / n : 0, fl = n ? l / n : 0;
  return '<svg width="76" height="76" viewBox="0 0 76 76" role="img" aria-label="勝敗の割合"><circle cx="38" cy="38" r="' + R + '" style="fill:none;stroke:var(--cell);stroke-width:9"/>' +
    '<circle cx="38" cy="38" r="' + R + '" transform="rotate(-90 38 38)" style="fill:none;stroke:var(--up);stroke-width:9" stroke-dasharray="' + (C * fw).toFixed(1) + " " + C.toFixed(1) + '"/>' +
    '<circle cx="38" cy="38" r="' + R + '" transform="rotate(' + (-90 + 360 * fw).toFixed(1) + ' 38 38)" style="fill:none;stroke:var(--down);stroke-width:9" stroke-dasharray="' + (C * fl).toFixed(1) + " " + C.toFixed(1) + '"/>' +
    '<text x="38" y="43" text-anchor="middle" style="font-size:15px;font-weight:700;fill:var(--ink);font-family:var(--font)">' + (n ? Math.round(100 * w / (w + l || 1)) : 0) + "%</text></svg>";
}
function kpiBox(gs) {
  var dd = dec(gs), r = wilson(dd.w, dd.n), t = tone(r[0], 0.5, dd.n), sk = streaks(gs);
  var nd = 0, seen = {}; gs.forEach(function (g) { if (!seen[g.d]) { seen[g.d] = 1; nd++; } });
  var dLo = gs[0].d, dHi = gs[gs.length - 1].d, span = Math.round((ms(dHi) - ms(dLo)) / 864e5) + 1;
  var kpi = '<div class="kpi sm">' +
    '<div><span class="k">勝率（' + (S.season === "all" ? "全シーズン" : "シーズン" + S.season) + '全体）</span><span class="v ' + t + '-t">' + pc(r[0]) + "<small>%</small></span>" +
    '<span class="s">95%信頼区間 ' + pc(r[1]) + "〜" + pc(r[2]) + "%</span></div>" +
    '<div><span class="k">試合</span><span class="v">' + gs.length + '<small>戦</small></span><span class="s">' +
    '<span class="up-t">' + dd.w + '勝</span> <span class="down-t">' + (dd.n - dd.w) + "敗</span>" + (gs.length - dd.n ? " " + (gs.length - dd.n) + "分" : "") + "</span></div>" +
    '<div><span class="k">最長の連勝・連敗</span><span class="v"><span class="up-t">' + sk[0] + '</span><small>連勝</small> <span class="down-t">' + sk[1] + "</span><small>連敗</small></span>" +
    '<span class="s">日をまたいでも続けて数える</span></div>' +
    '<div><span class="k">1日あたり</span><span class="v">' + (gs.length / nd).toFixed(1) + '<small>戦</small></span><span class="s">' + span + "日間のうち " + nd + "日プレイ</span></div></div>";;
  var rc = gs.slice(-20), rw = 0, rl = 0, rd = 0; rc.forEach(function (g) { if (g.r === "w") rw++; else if (g.r === "l") rl++; else rd++; });
  kpi = kpi.replace(/<\/div>$/, '<div class="dn">' + donut(rw, rl, rd).replace('width="76" height="76"', 'width="54" height="54"') +
    '<div><span class="k">直近' + rc.length + '試合</span><span class="v"><span class="up-t">' + rw + '</span><small>勝</small> <span class="down-t">' + rl + "</span><small>敗</small></span></div></div></div>");
  return kpi;
}
function logPage() {
  var gs = games().slice().reverse(); if (!gs.length) return '<p class="empty">このシーズンの試合がまだない。</p>';
  var narrow = pageW() < 640, cw = narrow ? 26 : 22;
  var rows = gs.slice(0, S.logN).map(function (g) {
    var o = D.opps[g.tag] || {}, nm = o.name || g.name, bits = [];
    if (o.best) bits.push("最高レート " + fmtn(o.best));
    if (o.pol != null) bits.push("レート戦 " + fmtn(o.pol) + "位");
    if (o.ladder != null) bits.push("Top Ladder " + fmtn(o.ladder) + "位");
    if (o.rt) bits.push("GT Top1000 " + o.rt + "回");
    if (o.battles != null) bits.push("通算 " + fmtn(o.battles) + "戦");
    return '<div class="lg"><div class="when">' + g.t.slice(5, 16).replace("-", "/") + "<small>" + esc(gmLabel(g)) + (g.tc != null ? '　<span class="' + (g.tc > 0 ? "up-t" : g.tc < 0 ? "down-t" : "") + '">' + (g.tc > 0 ? "+" : "") + g.tc + "</span>" : "") + "</small></div>" +
      '<div class="res"><span class="pill ' + g.r + '">' + (g.r === "w" ? "勝" : g.r === "l" ? "敗" : "分") + "</span><b>" + g.mc + " - " + g.oc + "</b></div>" +
      '<div class="vs my">' + deck8(g.my, cw) + '<span class="hp">自分　' + hpTxt(g.mk, g.mp) + "</span></div>" +
      '<div class="vs op">' + deck8(g.op, cw) + '<span class="hp">相手　' + hpTxt(g.ok, g.opp) + "</span></div>" +
      '<div class="who"><b>' + esc(nm) + "</b>" + (rivalOf(o) ? '<span class="tag2">強敵</span>' : "") + '<br><span style="color:var(--ink3)">' + esc(g.tag) + "</span>" + (bits.length ? "<br>" + bits.join("・") : "") + "</div></div>";
  }).join("");
  return kpiBox(gs.slice().reverse()) + sec("試合の一覧", "新しい順", rows + (gs.length > S.logN ? '<button class="more" id="more">さらに50試合を表示（残り' + (gs.length - S.logN) + "試合）</button>" : ""),
    "1行が1試合。左が自分、右が相手のデッキ。HPは残ったタワーの体力。");
}

/* ---------- シーズンから開く一覧 ---------- */
var menuCache = {};
function summary(season) {
  var key = S.mode + ":" + season; if (menuCache[key]) return menuCache[key];
  var gs = games(season), dd = dec(gs), r = wilson(dd.w, dd.n), base = dd.n ? dd.w / dd.n : .5, out = {};
  out.trend = dd.n ? "勝率 " + pc(r[0]) + "%・" + gs.length + "戦" : "試合なし";
  var decks = {}, face = {}; gs.forEach(function (g) { if (g.r === "d" || !g.my.length) return; var k = g.my.slice().sort().join(","); var d = decks[k] || (decks[k] = { w: 0, n: 0 }); d.n++; if (g.r === "w") d.w++; });
  var top = Object.keys(decks).sort(function (a, b) { return decks[b].n - decks[a].n; })[0];
  out.deck = top ? "主力デッキ " + pc(decks[top].w / decks[top].n) + "%（" + decks[top].n + "戦）" : "-";
  var opp = oppStats(gs), ok = Object.keys(opp).filter(function (c) { return opp[c].n >= 10; }).sort(function (a, b) { return opp[a].w / opp[a].n - opp[b].w / opp[b].n; });
  out.enemy = ok.length ? "苦手 " + D.cards[ok[0]] + " " + pc(opp[ok[0]].w / opp[ok[0]].n, 0) + "%" : "-";
  var hh = {}; gs.forEach(function (g) { if (g.r === "d") return; var c = hh[g.h] || (hh[g.h] = { w: 0, n: 0 }); c.n++; if (g.r === "w") c.w++; });
  var hk = Object.keys(hh).filter(function (h) { return hh[h].n >= RELIABLE_N; }).sort(function (a, b) { return hh[b].w / hh[b].n - hh[a].w / hh[a].n; });
  out.form = hk.length ? "好調 " + hk[0] + "時台 " + pc(hh[hk[0]].w / hh[hk[0]].n, 0) + "%" : "判定できる時間帯なし";
  var pp = P.filter(function (x) { return season === "all" || x.s === season; }), fin = season !== "all" ? D.finals[season] : null;
  var lp = pp.length ? pp[pp.length - 1] : P[P.length - 1];
  out.rate = fin ? "最終 " + stageOrRate(fin.lg, fin.tr) : "現在 " + stageOrRate(lp.lg, lp.tr);
  out.trend = out.rate + "・" + out.trend;
  var rv = gs.filter(function (g) { return g.r === "w" && rivalOf(D.opps[g.tag]); }).length;
  out.profile = "自己ベスト " + fmtn(D.me.best_tr);
  out.rivals = "撃破 " + rv + "件";
  out.log = gs.length + "試合";
  menuCache[key] = out; return out;
}
var menuEl = document.getElementById("menu"), menuFor = null, menuTimer = null;
function openMenu(btn) {
  var s = btn.getAttribute("data-s"); s = s === "all" ? "all" : +s;
  var sm = summary(s);
  menuEl.innerHTML = "<h4>" + esc(seasonLabel(s)) + "</h4>" + PAGES.map(function (p) {
    return '<button data-go="' + p[0] + '" class="' + (S.season === s && S.page === p[0] ? "cur" : "") + '"><b>' + p[1] + "</b><span>" + esc(sm[p[0]]) + "</span></button>";
  }).join("");
  var r = btn.getBoundingClientRect();
  menuEl.hidden = false;
  var left = Math.min(r.left, window.innerWidth - menuEl.offsetWidth - 16);
  menuEl.style.left = Math.max(16, left) + "px"; menuEl.style.top = (r.bottom + 4) + "px";
  menuFor = s;
  document.querySelectorAll(".sn").forEach(function (b) { b.classList.toggle("open", b === btn); });
}
function closeMenu() { menuEl.hidden = true; menuFor = null; document.querySelectorAll(".sn.open").forEach(function (b) { b.classList.remove("open"); }); }
var hoverable = window.matchMedia("(hover:hover)").matches;

/* ---------- 描画 ---------- */
function renderChrome() {
  document.getElementById("modes").innerHTML = MODES.map(function (m) { return '<button data-m="' + m[0] + '" class="' + (S.mode === m[0] ? "on" : "") + '">' + m[1] + "</button>"; }).join("");
  document.getElementById("meta").textContent = D.me.tag + "　更新 " + D.updated.replace(/-/g, "/");
  var items = [{ s: "all", b: "全シーズン", sp: md(SINFO[0].from) + "〜" }].concat(SINFO.slice().reverse().map(function (si) {
    return { s: si.n, b: "シーズン" + si.n, sp: si.from ? md(si.from) + "〜" + (si.last ? "" : md(si.to)) : "記録なし", now: si.last };
  }));
  document.getElementById("seasons").innerHTML = items.map(function (it) {
    var gs = games(it.s), dd = dec(gs), r = wilson(dd.w, dd.n), t = tone(r[0], .5, dd.n);
    return '<button class="sn' + (S.season === it.s ? " on" : "") + '" data-s="' + it.s + '" aria-haspopup="true"><b>' + it.b + (it.now ? '<span class="now">開催中</span>' : "") + "</b><span>" + it.sp + "</span>" +
      "<em>" + (dd.n ? gs.length + "戦　<span class=\"" + t + '-t">' + pc(r[0]) + "%</span>" : "試合なし") + "</em></button>";
  }).join("");
  document.getElementById("tabs").innerHTML = PAGES.map(function (p) { return '<button data-p="' + p[0] + '" class="' + (S.page === p[0] ? "on" : "") + '">' + p[1] + "</button>"; }).join("");
}
var lastW = 0;
function render() {
  renderChrome();
  var name = PAGES.filter(function (p) { return p[0] === S.page; })[0][1];
  document.getElementById("title").textContent = name;
  document.getElementById("sub").textContent = seasonLabel(S.season) + "・" + MODES.filter(function (m) { return m[0] === S.mode; })[0][1];
  document.title = name + "｜Clash Log";
  var f = { profile: profilePage, trend: timePage, deck: deckPage, enemy: enemyPage, rivals: rivalsPage, log: logPage }[S.page];
  document.getElementById("page").innerHTML = f();
  lastW = pageW();
  fillRange();
}
function fillRange() {
  var a = document.getElementById("r1"), z = document.getElementById("r2"), f = document.getElementById("rfill");
  if (!a || !z || !f) return;
  var m = +a.max || 1, lo = Math.min(+a.value, +z.value) / m, hi = Math.max(+a.value, +z.value) / m;
  f.style.left = "calc(8px + (100% - 16px) * " + lo + ")"; f.style.width = "calc((100% - 16px) * " + (hi - lo) + ")";
}
function go(o) {
  var reset = ("season" in o && o.season !== S.season) || ("mode" in o && o.mode !== S.mode);
  Object.keys(o).forEach(function (k) { S[k] = o[k]; });
  if (reset) { S.lo = null; S.hi = null; S.logN = 50; S.unit = null; }
  if ("page" in o || "mode" in o) {
    var hs = "#" + (S.mode !== "pol" ? S.mode + "-" : "") + S.page;
    try { history.replaceState(null, "", hs); } catch (e) { location.hash = hs; }
  }
  if ("page" in o) S.logN = 50;
  save(); closeMenu(); render();
  if ("page" in o || "season" in o) window.scrollTo({ top: 0 });
}

/* ---------- 操作 ---------- */
document.addEventListener("click", function (e) {
  var t = e.target.closest ? e.target : null; if (!t) return;
  var m = t.closest("[data-m]"); if (m) return go({ mode: m.getAttribute("data-m") });
  var sn = t.closest(".sn");
  if (sn) {
    var s = sn.getAttribute("data-s"); s = s === "all" ? "all" : +s;
    if (!hoverable && menuFor !== s) { openMenu(sn); return; }   // スマホは1回目のタップで一覧を開く
    return go({ season: s });
  }
  var g2 = t.closest("[data-go]"); if (g2) return go({ season: menuFor, page: g2.getAttribute("data-go") });
  var p = t.closest("[data-p]"); if (p) return go({ page: p.getAttribute("data-p") });
  var u = t.closest("[data-u]"); if (u) { S.unit = u.getAttribute("data-u"); return render(); }
  var jp = t.closest("[data-jump]");
  if (jp) {
    var el = document.getElementById("sec-" + jp.getAttribute("data-jump"));
    if (el) { var top = el.getBoundingClientRect().top + window.scrollY - document.querySelector(".top").offsetHeight - 12; window.scrollTo({ top: top, behavior: "smooth" }); }
    return;
  }
  if (t.closest("#more")) { S.logN += 50; return render(); }
  if (!t.closest("#menu")) closeMenu();
});
document.getElementById("seasons").addEventListener("mouseover", function (e) {
  if (!hoverable) return; var sn = e.target.closest(".sn"); if (!sn) return;
  clearTimeout(menuTimer); menuTimer = setTimeout(function () { openMenu(sn); }, 90);
});
document.getElementById("seasons").addEventListener("focusin", function (e) { var sn = e.target.closest(".sn"); if (sn) openMenu(sn); });
function maybeClose(e) {
  if (!hoverable) return; var to = e.relatedTarget;
  if (to && (to.closest && (to.closest("#menu") || to.closest(".sn")))) return;
  clearTimeout(menuTimer); menuTimer = setTimeout(closeMenu, 160);
}
document.getElementById("seasons").addEventListener("mouseout", maybeClose);
menuEl.addEventListener("mouseout", maybeClose);
menuEl.addEventListener("mouseover", function () { clearTimeout(menuTimer); });
document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeMenu(); });
window.addEventListener("scroll", function () { if (!menuEl.hidden && hoverable) closeMenu(); hideTip(); }, { passive: true });
document.addEventListener("input", function (e) {   // つまみを動かしている間は帯と日付だけ動かす
  if (e.target.id !== "r1" && e.target.id !== "r2") return;
  var a = document.getElementById("r1"), z = document.getElementById("r2");
  S.lo = Math.min(+a.value, +z.value); S.hi = Math.max(+a.value, +z.value);
  fillRange();
  var lab = document.getElementById("rlabv"); if (lab && DAYS.length) lab.textContent = DAYS[S.lo] + " 〜 " + DAYS[S.hi];
});
document.addEventListener("change", function (e) {  // 離したら集計を描き直す
  if (e.target.id !== "r1" && e.target.id !== "r2") return;
  var y = window.scrollY, id = e.target.id; render(); window.scrollTo(0, y);
  var a2 = document.getElementById(id); if (a2) a2.focus({ preventScroll: true });
});
var rt = null;
window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(function () { if (Math.abs(pageW() - lastW) > 16) render(); }, 120); });

/* 吹き出し */
var tip = document.getElementById("tip"), cur = null;
function hideTip() { tip.style.opacity = 0; var x = document.getElementById("xh"); if (x) x.style.opacity = 0; cur = null; }
function moveTip(e) {
  var el = e.target.closest ? e.target.closest("[data-tip]") : null;
  if (!el) { if (cur) hideTip(); return; }
  if (cur !== el) {
    tip.textContent = el.getAttribute("data-tip"); cur = el;
    var xh = document.getElementById("xh"), cx = el.getAttribute("data-cx");
    if (xh) { if (cx && el.ownerSVGElement && el.ownerSVGElement.contains(xh)) { xh.setAttribute("x1", cx); xh.setAttribute("x2", cx); xh.style.opacity = .35; } else xh.style.opacity = 0; }
  }
  var w = tip.offsetWidth, h = tip.offsetHeight, vw = window.innerWidth;
  var l = e.clientX + 14; if (l + w > vw - 8) l = e.clientX - w - 14; if (l < 8) l = 8;
  var tp = e.clientY - h - 12; if (tp < 8) tp = e.clientY + 16;
  tip.style.left = l + "px"; tip.style.top = tp + "px"; tip.style.opacity = 1;
}
document.addEventListener("pointermove", moveTip);
document.addEventListener("pointerdown", moveTip);

if (S.season !== "all" && !sinfo(S.season)) S.season = "all";
render();
})();
</script>
'''

PLAYER_TAG = "#LQQQQPUL0"     # 表示用（収集側の collect_battles.py と同じタグ）

# 旧ページのアドレス → 新サイトの「#モード-ページ」（ブックマークが切れないように転送する）
OLD_PAGES = [("chart.html", "trend"), ("mydeck.html", "deck"), ("enemy.html", "enemy"),
             ("chosi.html", "form"), ("rate.html", "rate"), ("rivals.html", "rivals"),
             ("log.html", "log")]
OLD_PREFIX = [("", "pol"), ("etc-", "etc"), ("all-", "all")]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_app_data(rows):
    """ブラウザ側に渡すデータ。カード名は番号に置き換えて小さくする。"""
    cards, cidx = [], {}

    def ci(name):
        if name not in cidx:
            cidx[name] = len(cards)
            cards.append(name)
        return cidx[name]

    def deck(text):
        return [ci(c) for c in (text or "").split("|") if c]

    res = {"win": "w", "loss": "l"}
    battles, tags = [], set()
    for r in rows:
        tag = (r.get("opp_tag") or "").strip()
        tags.add(tag)
        battles.append([
            r["battle_time_jst"][:19], classify(r), res.get(r["result"], "d"),
            _num(r.get("my_crowns")) or 0, _num(r.get("opp_crowns")) or 0,
            deck(r.get("my_deck")), deck(r.get("opp_deck")), tag, r.get("opp_name") or "",
            r.get("my_king_hp") or "", r.get("my_princess_hp") or "",
            r.get("opp_king_hp") or "", r.get("opp_princess_hp") or "",
            _num(r.get("trophy_change")), r.get("game_mode") or r.get("battle_type") or "",
            r["_session"],
        ])

    opps = {}
    for tag in tags:
        if not tag:
            continue
        o = opp_ranks(tag)
        if all(o.get(k) is None for k in ("pol", "gt", "best", "ladder", "battles")) and not o.get("rt"):
            continue
        opps[tag] = {k: o.get(k) for k in ("name", "pol", "gt", "best", "ladder",
                                            "ladder_season", "rt", "battles")}

    prof, prev = [], None
    for r in PROFILE:
        t = (r.get("checked_jst") or "").strip()[:19]
        lg, tr = _num(r.get("pol_current_league")), _num(r.get("pol_current_trophies"))
        if not t or lg is None:
            continue
        if (lg, tr) != prev:
            prof.append([t, lg, tr or 0])
            prev = (lg, tr)
    last = PROFILE[-1] if PROFILE else {}
    lt = (last.get("checked_jst") or "")[:19]
    if prof and lt and prof[-1][0] != lt:
        prof.append([lt, prof[-1][1], prof[-1][2]])

    # 各シーズンの確定成績（前シーズンの成績欄が更新された時点の値）
    finals, seen = {}, None
    for r in PROFILE:
        key = (r.get("pol_last_league"), r.get("pol_last_trophies"), r.get("pol_last_rank"))
        if key == seen or _num(key[0]) is None:
            continue
        seen = key
        sn = season_of((r.get("checked_jst") or "").strip())
        if sn:
            finals[sn - 1] = {"lg": _num(key[0]), "tr": _num(key[1]), "rank": _num(key[2])}

    # 対戦した相手の中での位置（Baseball Savant のパーセンタイル表示にならう）
    pop = {"wr": [], "best": [], "bc": []}
    for o in OPPONENTS.values():
        w, l = _f(o.get("wins")), _f(o.get("losses"))
        if w is not None and l is not None and w + l > 0:
            pop["wr"].append(w / (w + l))
        b = _f(o.get("pol_best_trophies"))
        pop["best"].append(b if b and b > 0 else -1)   # レートが出ていない相手も下位として数える
        c = _f(o.get("battle_count"))
        if c:
            pop["bc"].append(c)
    mw, ml = _f(last.get("wins")), _f(last.get("losses"))
    mine = {"wr": mw / (mw + ml) if mw is not None and ml else None,
            "best": _f(last.get("pol_best_trophies")), "bc": _f(last.get("battle_count"))}
    pct = []
    for key, lab, fmt in (("wr", "通算勝率", "pct"), ("best", "レート戦の自己ベスト", "int"),
                          ("bc", "通算試合数", "int")):
        arr = sorted(pop[key])
        if mine[key] is None or not arr:
            continue
        lo = sum(1 for x in arr if x < mine[key])
        hi = sum(1 for x in arr if x > mine[key])
        eq = sum(1 for x in arr if x == mine[key])
        n = len(arr)
        med = arr[n // 2] if n % 2 else (arr[n // 2 - 1] + arr[n // 2]) / 2
        pct.append({"k": key, "lab": lab, "fmt": fmt, "v": mine[key],
                    "p": round((lo + eq / 2) / n * 100), "top": round((hi + eq / 2) / n * 100, 1),
                    "med": med, "n": n})

    return {
        "img": True,
        "updated": now_jst().strftime("%Y-%m-%d %H:%M"),
        "seasons": [{"f": f, "n": n} for f, n in SEASONS],
        "anchor": list(SEASON_ANCHOR),
        "leagues": {k: v[0] for k, v in LEAGUES.items()},
        "ult": ULTIMATE,
        "cards": cards,
        "icons": [ICONS.get(c, "") for c in cards],
        "battles": battles,
        "opps": opps,
        "prof": prof,
        "finals": finals,
        "me": {
            "tag": PLAYER_TAG,
            "best_lg": _num(last.get("pol_best_league")),
            "best_tr": _num(last.get("pol_best_trophies")),
            "best_rank": _num(last.get("pol_best_rank")),
            "best_when": BEST_ACHIEVED_BEFORE,
            "wins": _num(last.get("wins")), "losses": _num(last.get("losses")),
            "trophies": _num(last.get("trophies")),
        },
        "pct": pct,
        "rival": {"pol": RIVAL_POL_RANK, "ladder": RIVAL_LADDER_RANK, "rt": RIVAL_RT_RANK},
    }


def _write(name, text):
    WRITTEN.add(name)
    with open(os.path.join(SCRIPT_DIR, name), "w", encoding="utf-8") as f:
        f.write(text)


def write_app(rows):
    data = json.dumps(build_app_data(rows), ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/")
    head, body = APP_HTML.split("</style>", 1)
    doc = ("<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
           + head + "</style></head><body>" + body.replace("/*DATA*/", data) + "</body></html>")
    _write("index.html", doc)
    for prefix, mode in OLD_PREFIX:
        for name, pg in OLD_PAGES:
            to = "index.html#" + ("" if mode == "pol" else mode + "-") + pg
            _write(prefix + name,
                   "<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'>"
                   f"<meta http-equiv='refresh' content='0; url={to}'>"
                   "<title>Clash Log</title></head>"
                   f"<body><p><a href='{to}'>新しいページへ移動</a></p></body></html>")
    return len(doc)


def main():
    global ICONS, AVAILABLE, PROFILE, OPPONENTS, GT_RANKS
    ICONS = load_icons()
    PROFILE = load_profile()
    OPPONENTS = load_opponents()
    GT_RANKS = load_gt()
    all_rows = add_sessions(load_rows())
    prev_state(all_rows)

    global SEASONS, SEASONS_JS
    SEASONS = detect_seasons(all_rows, PROFILE)
    SEASONS_JS = json.dumps([{"f": f, "n": n} for f, n in SEASONS])

    groups = defaultdict(list)
    for r in all_rows:
        groups[classify(r)].append(r)

    AVAILABLE = [k for k, _, _ in MODES
                 if (k == "all" and all_rows) or groups.get(k)]

    if NEW_UI:
        size = write_app(all_rows)
        print(f"新しいサイトを出力しました（index.html {size:,} 字）")
    else:
        for key, prefix, label in MODES:
            if key not in AVAILABLE:
                continue
            rows = all_rows if key == "all" else groups[key]
            build(key, prefix, label, rows, len(all_rows))

        # 入口。概要ページを廃止したため、トップは推移へ送る
        WRITTEN.add("index.html")
        with open(os.path.join(SCRIPT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'>"
                    "<meta http-equiv='refresh' content='0; url=chart.html'>"
                    "<title>対戦記録レポート</title></head>"
                    "<body><p><a href='chart.html'>推移のページへ</a></p></body></html>")

    # 今回書き出さなかった古いHTMLを片づける
    removed = 0
    for name in sorted(os.listdir(SCRIPT_DIR)):
        if name.endswith(".html") and name not in WRITTEN:
            try:
                os.remove(os.path.join(SCRIPT_DIR, name))
                removed += 1
            except OSError:
                pass

    counts = " / ".join(f"{lab} {len(all_rows) if k == 'all' else len(groups.get(k, []))}"
                        for k, _, lab in MODES if k in AVAILABLE)
    print(f"モード別に出力しました（{counts}）"
          + (f" 古いHTMLを{removed}件削除" if removed else ""))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"エラー: {error}")
        raise
