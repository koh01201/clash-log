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



def monthly_decks(rows):
    """暦月ごとの最多使用デッキと成績。シーズン区切りの目安として使う。"""
    by_month = defaultdict(lambda: {"w": 0, "n": 0, "decks": defaultdict(lambda: [0, 0]), "face": {}})
    for r in rows:
        if r["result"] == "draw":
            continue
        m = by_month[r["_dt"].strftime("%Y-%m")]
        m["n"] += 1
        if r["result"] == "win":
            m["w"] += 1
        cards = [c for c in r["my_deck"].split("|") if c]
        if not cards:
            continue
        k = "|".join(sorted(cards))
        m["decks"][k][1] += 1
        if r["result"] == "win":
            m["decks"][k][0] += 1
        m["face"].setdefault(k, cards[:8])

    out = []
    for month in sorted(by_month, reverse=True):
        m = by_month[month]
        if not m["decks"]:
            continue
        k = max(m["decks"], key=lambda x: m["decks"][x][1])
        dw, dn = m["decks"][k]
        out.append({
            "month": month, "n": m["n"], "w": m["w"],
            "cards": m["face"].get(k, []), "dw": dw, "dn": dn,
            "kinds": len(m["decks"]),
        })
    return out


def monthly_deck_panel(rows):
    data = monthly_decks(rows)
    if not data:
        return ""
    body = []
    for d in data:
        wr = d["w"] / d["n"] * 100 if d["n"] else 0
        dwr = d["dw"] / d["dn"] * 100 if d["dn"] else 0
        y, mo = d["month"].split("-")
        body.append(
            f'<tr><th>{y}年{int(mo)}月<span class="sname">{d["n"]}試合・勝率{wr:.1f}%</span></th>'
            f'<td><div class="mdeck">{deck_grid(d["cards"])}'
            f'<span class="sname">{d["dn"]}試合使用（{d["kinds"]}種類中）・このデッキの勝率 {dwr:.1f}%</span>'
            "</div></td></tr>")
    return panel("月ごとの最多使用デッキ", f'<table class="kv">{"".join(body)}</table>',
                 "シーズンの区切りはAPIから取得できないため、暦月で区切っている。",
                 "その月にいちばん多く使った構成を1つ表示している。")


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

    kv = [("今シーズン", stage_cell(cl, ct, cr))]
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
        seasons.append((r.get("checked_jst", "")[:10], _num(key[0]), _num(key[1]), _num(key[2])))

    if seasons:
        body = "".join(f"<tr><th>{esc(d)} 時点で確認</th><td>{stage_cell(lg, tr, rk, 32)}</td></tr>"
                       for d, lg, tr, rk in reversed(seasons))
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
  function bucketize(rows, unit) {
    var map = {}, order = [], i, k, r;
    for (i = 0; i < rows.length; i++) {
      r = rows[i];
      k = keyOf(r.battle_time_jst, unit);
      if (!map[k]) { map[k] = { key: k, w: 0, n: 0, games: 0 }; order.push(k); }
      map[k].games++;
      if (r.result === "draw") continue;
      map[k].n++;
      if (r.result === "win") map[k].w++;
    }
    order.sort();
    return order.map(function (k) { return map[k]; });
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
    var padL = 8, padR = nw ? 34 : 40, padT = 10;
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

    // 月の区切り（期間内のみ）
    var i, mb = [];
    for (i = lo + 1; i <= hi; i++) {
      if (all[i].key.slice(0, 7) !== all[i - 1].key.slice(0, 7)) mb.push(i);
    }
    mb.forEach(function (i2) {
      var mx = xe(i2).toFixed(1);
      o.push('<line class="monthsep" x1="' + mx + '" y1="' + padT + '" x2="' + mx + '" y2="' + vy1 + '"/>');
    });

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

    // 横軸ラベル（月の区切りを優先）
    var used = [], yl = vy1 + 15, gap = nw ? 44 : 40;
    function room(px0) {
      for (var j = 0; j < used.length; j++) if (Math.abs(px0 - used[j]) < gap) return false;
      used.push(px0); return true;
    }
    mb.forEach(function (i2) {
      if (!room(x(i2))) return;
      o.push('<text class="tick mon" x="' + x(i2).toFixed(1) + '" y="' + yl +
        '" text-anchor="middle">' + esc(all[i2].key.slice(0, 7).replace("-", "/")) + "</text>");
    });
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
      var lines = [(S.unit === "month" ? b0.key.slice(0, 7) : b0.key) + unitLab];
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
    var padL = 8, padR = nw ? 84 : 104, padT = 18;
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
    var mb = [];
    for (i = lo + 1; i <= hi; i++) {
      if (days[i].slice(0, 7) !== days[i - 1].slice(0, 7)) mb.push(i);
    }
    for (k = 0; k < mb.length; k++) {
      var mxx = (padL + (mb[k] - lo) * bw).toFixed(1);
      o.push('<line class="monthsep" x1="' + mxx + '" y1="' + ry0 + '" x2="' + mxx +
        '" y2="' + wy1 + '"/>');
    }
    var used = [], yl = wy1 + 14, gap = nw ? 40 : 34;
    function room(x) {
      var j;
      for (j = 0; j < used.length; j++) if (Math.abs(x - used[j]) < gap) return false;
      used.push(x); return true;
    }
    for (k = 0; k < mb.length; k++) {
      var mlx = xd(mb[k]);
      if (!room(mlx)) continue;
      o.push('<text class="tick mon" x="' + mlx.toFixed(1) + '" y="' + yl +
        '" text-anchor="middle">' + esc(days[mb[k]].slice(0, 7).replace("-", "/")) + "</text>");
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
      var tl = [days[i].replace(/-/g, "/")];
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
    </div>
    <p class="note">試合数が少ない期間ほど信頼区間は広くなる。灰色の帯が広い区間の上下動は、
      実力の変化ではなく偶然の可能性が高い。</p>
  </section>
  <section class="panel"><h2>選んだ期間の成績</h2>
    <p class="lead">上のつまみやボタンで期間を絞ると、ここが連動して変わる。</p>
    <div id="sum"></div>
  </section>
  <script>""" + CHART_JS.replace("__MODE__", mode_key) + """</script>
""")

    # レート
    page(prefix, "rate.html", label, "レート", stamp,
         rate_page_body(PROFILE) + monthly_deck_panel(rows)
         + "<script>" + RATE_JS.replace("__MODE__", mode_key)
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



def main():
    global ICONS, AVAILABLE, PROFILE, OPPONENTS, GT_RANKS
    ICONS = load_icons()
    PROFILE = load_profile()
    OPPONENTS = load_opponents()
    GT_RANKS = load_gt()
    all_rows = add_sessions(load_rows())
    prev_state(all_rows)

    groups = defaultdict(list)
    for r in all_rows:
        groups[classify(r)].append(r)

    AVAILABLE = [k for k, _, _ in MODES
                 if (k == "all" and all_rows) or groups.get(k)]

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
