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


def load_opponents():
    """opponents.csv をタグ引きの辞書にする。"""
    if not os.path.exists(OPPONENTS_FILE):
        return {}
    try:
        with open(OPPONENTS_FILE, encoding="utf-8-sig", newline="") as f:
            return {r["tag"]: r for r in csv.DictReader(f) if r.get("tag")}
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
        "battles": _num(o.get("battle_count")),
    }


def is_rival(pol, gt, ladder=None):
    return ((pol is not None and pol <= RIVAL_POL_RANK)
            or (gt is not None and gt <= RIVAL_GT_RANK)
            or (ladder is not None and ladder <= RIVAL_LADDER_RANK))


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


WR_WINDOW = 30          # 勝率の移動平均に使う試合数


def rolling_winrate(rows, window=WR_WINDOW):
    """直近 window 試合の勝率（Wilson法の95%区間つき）を時系列で返す。"""
    games = sorted((r for r in (rows or [])
                    if r.get("result") != "draw" and r.get("_dt")),
                   key=lambda r: r["_dt"])
    if len(games) < window:
        return []
    out, w = [], 0
    for i, r in enumerate(games):
        if r["result"] == "win":
            w += 1
        if i >= window and games[i - window]["result"] == "win":
            w -= 1
        if i >= window - 1:
            out.append((r["_dt"],) + wilson(w, window))
    return out


def rate_history_chart(prof, rows=None):
    """レート（未到達ならステージ）の推移。横軸は実時間。

    アルティメットチャンピオン到達後はレートの数値で描く。
    到達前と到達後が混ざる場合は、下段にステージ・上段にレートを置いた2段の軸にする。
    表示中のモードの勝率（移動平均）を同じ横軸に重ねる。
    """
    pts = []
    for r in prof:
        lg, tr = _num(r.get("pol_current_league")), _num(r.get("pol_current_trophies"))
        if lg is None:
            continue
        raw = (r.get("checked_jst") or "").strip()
        t = None
        for fmt, cut_to in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
            try:
                t = datetime.datetime.strptime(raw[:cut_to], fmt)
                break
            except ValueError:
                continue
        if t is None:
            continue
        pts.append((t, lg, tr))
    if len(pts) < 2:
        return ""
    pts.sort(key=lambda x: x[0])

    ult = [bool(p[1] >= ULTIMATE and p[2]) for p in pts]
    wr = rolling_winrate(rows)

    W, H = 720, 230
    padT, padB, padR = 14, 26, 46
    padL = 30 if wr else 8
    pw, ph = W - padL - padR, H - padT - padB

    t0 = min([pts[0][0]] + ([wr[0][0]] if wr else []))
    t1 = max([pts[-1][0]] + ([wr[-1][0]] if wr else []))
    span = (t1 - t0).total_seconds() or 1.0
    xs = lambda t: padL + pw * ((t - t0).total_seconds() / span)
    wy = lambda v: padT + ph * (1 - v)

    ticks = []          # (y, ラベル)
    sep_y = None        # アルティメット到達ラインの高さ

    if all(ult):
        # 全期間アルティメット：レートの数値だけで描く
        vals = [p[2] for p in pts]
        lo, hi = min(vals), max(vals)
        if hi == lo:
            lo, hi = lo - 1, hi + 1
        ys = [padT + ph * (1 - (v - lo) / (hi - lo)) for v in vals]
        for k in range(5):
            ticks.append((padT + ph * (1 - k / 4),
                          f"{int(round(lo + (hi - lo) * k / 4)):,}"))
        labels = [f"{v:,}" for v in vals]
        caption = "レートの推移。"
    elif not any(ult):
        # 未到達：ステージだけで描く
        vals = [p[1] for p in pts]
        lo, hi = min(vals), max(vals)
        if hi == lo:
            lo, hi = lo - 1, hi + 1
        ys = [padT + ph * (1 - (v - lo) / (hi - lo)) for v in vals]
        for k in range(5):
            ticks.append((padT + ph * (1 - k / 4),
                          league_name(int(round(lo + (hi - lo) * k / 4)))))
        labels = [league_name(v) for v in vals]
        caption = "ステージの推移。アルティメットチャンピオン到達後はレートで表示する。"
    else:
        # 混在：下段＝ステージ、上段＝レート
        st = [p[1] for p, u in zip(pts, ult) if not u]
        rt = [p[2] for p, u in zip(pts, ult) if u]
        slo, shi = min(st), max(max(st), ULTIMATE)
        if shi == slo:
            slo = shi - 1
        sh = min(ph * 0.5, max(40.0, 16.0 * (shi - slo)))       # 下段の高さ
        sep_y = padT + ph - sh
        rlo, rhi = min(rt), max(rt)
        if rhi == rlo:
            rlo, rhi = rlo - 1, rhi + 1
        ys = [(sep_y - (ph - sh) * (p[2] - rlo) / (rhi - rlo)) if u
              else (padT + ph - sh * (p[1] - slo) / (shi - slo))
              for p, u in zip(pts, ult)]
        for v in range(slo, shi):                                # 下段：リーグ名
            ticks.append((padT + ph - sh * (v - slo) / (shi - slo), league_name(v)))
        for k in range(5):                                       # 上段：レートの数値
            ticks.append((sep_y - (ph - sh) * k / 4,
                          f"{int(round(rlo + (rhi - rlo) * k / 4)):,}"))
        labels = [f"{p[2]:,}" if u else league_name(p[1]) for p, u in zip(pts, ult)]
        caption = ("下段はステージ、上段はアルティメットチャンピオン到達後のレート。"
                   "破線が到達ライン。")

    out = [f'<svg viewBox="0 0 {W} {H}" class="chart">']
    out.append(f'<rect class="plot" x="{padL}" y="{padT}" width="{pw}" height="{ph}"/>')
    for yy, lab in ticks:
        if padT + 1 < yy < padT + ph - 1:
            out.append(f'<line class="grid" x1="{padL}" y1="{yy:.1f}" x2="{padL+pw}" y2="{yy:.1f}"/>')
        out.append(f'<text class="tick" x="{padL+pw+5}" y="{yy+3.5:.1f}">{esc(lab)}</text>')
    if sep_y is not None:
        out.append(f'<line class="fifty" x1="{padL}" y1="{sep_y:.1f}" '
                   f'x2="{padL+pw}" y2="{sep_y:.1f}"/>')
        out.append(f'<text class="tick" x="{padL+4}" y="{sep_y-4:.1f}">'
                   "アルティメットチャンピオン到達</text>")

    if wr:
        # 勝率（左目盛り）。レートの線より下に敷く
        band = ([f"{xs(t):.1f},{wy(h):.1f}" for t, _p, _l, h in wr]
                + [f"{xs(t):.1f},{wy(l):.1f}" for t, _p, l, _h in reversed(wr)])
        out.append(f'<polygon class="ciband" points="{" ".join(band)}"/>')
        out.append(f'<line class="base" x1="{padL}" y1="{wy(0.5):.1f}" '
                   f'x2="{padL+pw}" y2="{wy(0.5):.1f}"/>')
        wline = " ".join(f"{xs(t):.1f},{wy(p):.1f}" for t, p, _l, _h in wr)
        out.append(f'<polyline class="rate" points="{wline}"/>')
        for k in range(5):
            v = k / 4
            out.append(f'<text class="tick" x="{padL-5}" y="{wy(v)+3.5:.1f}" '
                       f'text-anchor="end">{int(v*100)}{"%" if k == 4 else ""}</text>')

    line = " ".join(f"{xs(pts[i][0]):.1f},{yy:.1f}" for i, yy in enumerate(ys))
    out.append(f'<polyline class="ma" points="{line}"/>')
    for i, yy in enumerate(ys):
        # 値が動いていない点は打たない（記録点が多く、線が黒く潰れるため）
        if 0 < i < len(ys) - 1 and abs(yy - ys[i - 1]) < 0.05 and abs(yy - ys[i + 1]) < 0.05:
            continue
        out.append(f'<circle class="pt" cx="{xs(pts[i][0]):.1f}" cy="{yy:.1f}" r="2.6"><title>'
                   f'{esc(pts[i][0].strftime("%Y-%m-%d %H:%M"))} {esc(labels[i])}</title></circle>')
    for k in range(7):
        t = t0 + datetime.timedelta(seconds=span * k / 6)
        out.append(f'<text class="tick" x="{padL + pw * k / 6:.1f}" y="{H-8}" '
                   f'text-anchor="middle">{t:%m-%d}</text>')
    out.append("</svg>")

    if wr:
        caption += (f"細い黒線は勝率（直近{WR_WINDOW}試合の移動平均、左目盛り）。"
                    "灰色の帯は95%信頼区間、破線は五分。表示中のモードの試合だけを使う。")
        legend = ('<div class="legend2">'
                  '<span><i class="lgline" style="border-color:#C8102E;border-top-width:3px"></i>'
                  'レート</span>'
                  '<span><i class="lgline" style="border-color:#3A424B"></i>'
                  f'勝率（{WR_WINDOW}試合平均）</span>'
                  '<span><i class="lgbox" style="background:#D9DCDF"></i>95%信頼区間</span>'
                  "</div>")
    else:
        legend = ""
    return (f'<h3 class="sub2">推移</h3>{"".join(out)}{legend}'
            f'<p class="cap">{caption}</p>')


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


def rate_page_body(prof, rows=None):
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

    chart = rate_history_chart(prof, rows)
    return (panel("現在の成績", table(kv) + hist,
                  "アルティメットチャンピオンに到達するまでレートは表示されないため、"
                  "それまではステージを表示する。")
            + (panel("レートの推移", chart.replace('<h3 class="sub2">推移</h3>', ""))
               if chart else ""))


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
        out.append(f'<rect class="band {cls}" x="{px(lo):.1f}" y="{y-8:.1f}" width="{w:.1f}" height="16" rx="2"/>')
        out.append(f'<rect class="mark {cls}" x="{px(p)-1.5:.1f}" y="{y-13:.1f}" width="3" height="26"/>')
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
        out.append(f'<rect class="band {cls}" x="{px(lo):.1f}" y="{by-8:.1f}" width="{w:.1f}" height="16" rx="2"/>')
        out.append(f'<rect class="mark {cls}" x="{px(p)-1.5:.1f}" y="{by-12:.1f}" width="3" height="24"/>')
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
    var MH = nw ? 132 : 172, VH = nw ? 44 : 58, GAP = 12;
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
      if (v > 0 && v < 1) {
        o.push('<line class="grid" x1="' + padL + '" y1="' + y(v).toFixed(1) +
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
    for (i = lo; i <= hi; i++) {
      o.push('<circle class="pt" cx="' + x(i).toFixed(1) + '" cy="' +
        y(all[i].n ? all[i].w / all[i].n : 0).toFixed(1) + '" r="' + (nw ? 2 : 2.6) + '"><title>' +
        esc(all[i].key) + " " + all[i].w + "勝" + (all[i].n - all[i].w) + "敗</title></circle>");
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
      if (t > 0) o.push('<line class="grid" x1="' + padL + '" y1="' + yy.toFixed(1) +
        '" x2="' + (padL + pw) + '" y2="' + yy.toFixed(1) + '"/>');
      o.push('<text class="tick" x="' + (padL + pw + 5) + '" y="' + (yy + 3.5).toFixed(1) + '">' +
        Math.round(maxg * t) + "</text>");
    });
    for (i = lo; i <= hi; i++) {
      var bh = VH * (all[i].games / maxg);
      o.push('<rect class="volbar" x="' + (xe(i) + step * 0.18).toFixed(1) +
        '" y="' + (vy1 - bh).toFixed(1) + '" width="' + Math.max(1, step * 0.64).toFixed(1) +
        '" height="' + bh.toFixed(1) + '"><title>' + esc(all[i].key) + " " + all[i].games + "試合</title></rect>");
    }

    // 横軸ラベル（月の区切りを優先）
    var labeled = {}, yl = vy1 + 13;
    mb.forEach(function (i2) {
      labeled[i2] = 1;
      o.push('<text class="tick mon" x="' + x(i2).toFixed(1) + '" y="' + yl +
        '" text-anchor="middle">' + esc(all[i2].key.slice(0, 7).replace("-", "/")) + "</text>");
    });
    var everyN = Math.max(1, Math.ceil(nb / (nw ? 4 : 9)));
    for (i = lo; i <= hi; i += everyN) {
      if (labeled[i]) continue;
      o.push('<text class="tick" x="' + x(i).toFixed(1) + '" y="' + yl +
        '" text-anchor="middle">' + esc(fmtDate(all[i].key, S.unit)) + "</text>");
    }
    o.push('<text class="tick vlab" x="' + padL + '" y="' + (vy0 - 3) + '">プレイ回数</text>');
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
      o.push('<rect class="band ' + cls + '" x="' + px(r[1]).toFixed(1) + '" y="' + (y - 8).toFixed(1) +
        '" width="' + Math.max(10, px(r[2]) - px(r[1])).toFixed(1) + '" height="16" rx="2"/>');
      o.push('<rect class="mark ' + cls + '" x="' + (px(r[0]) - 1.5).toFixed(1) + '" y="' +
        (y - 13).toFixed(1) + '" width="3" height="26"/>');
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
      o.push('<rect class="band ' + cls + '" x="' + px(r[1]).toFixed(1) + '" y="' + (by - 8) +
        '" width="' + Math.max(8, px(r[2]) - px(r[1])).toFixed(1) + '" height="16" rx="2"/>');
      o.push('<rect class="mark ' + cls + '" x="' + (px(r[0]) - 1.5).toFixed(1) + '" y="' +
        (by - 12) + '" width="3" height="24"/>');
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
});
"""

CSS = """
:root{
  --bg:#F2F3F5;--panel:#FFFFFF;--line:#DCDFE3;--ink:#1F2328;--label:#5B646E;
  --labelbg:#F6F7F9;--up:#C8102E;--down:#0B57A4;--na:#8A939C;
  --accent:#BF0000;--link:#0B5FBF;--upbg:#FDF0F2;--downbg:#EFF4FA;
  --warnbg:#FFF4E5;--warnline:#F0C078;--warnink:#A85E00;
}
*{box-sizing:border-box}
body{margin:0;padding:20px 16px 64px;background:var(--bg);color:var(--ink);
  font-family:"Yu Gothic","Hiragino Kaku Gothic ProN","Noto Sans JP","Meiryo",sans-serif;
  font-size:14px;line-height:1.7;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto}
.navwrap{position:sticky;top:0;z-index:20;background:var(--bg);
  padding:8px 0 6px;margin:-8px 0 12px;box-shadow:0 6px 8px -8px rgba(0,0,0,.28)}
nav{display:flex;gap:5px;flex-wrap:wrap;align-items:center}
nav.modes{margin-bottom:5px;padding-bottom:5px;border-bottom:1px dashed var(--line)}
.navlab{font-size:10px;color:var(--label);width:34px;flex:none;letter-spacing:.08em}
nav.modes a{background:var(--labelbg);font-weight:700}
nav.modes a.on{background:var(--accent);color:#fff;border-color:var(--accent)}
nav a{text-decoration:none;background:var(--panel);color:var(--ink);font-size:13px;
  padding:6px 14px;border:1px solid var(--line);border-radius:4px}
nav a.on{background:var(--ink);color:#fff;border-color:var(--ink);font-weight:700}
nav a:not(.on):hover{border-color:var(--link);color:var(--link)}
.head{background:var(--panel);border:1px solid var(--line);border-radius:4px;
  padding:16px 20px;margin-bottom:12px;display:flex;justify-content:space-between;
  align-items:flex-end;flex-wrap:wrap;gap:8px}
.head{border-top:3px solid var(--accent)}
.head h1{font-size:20px;font-weight:700;margin:0;display:flex;align-items:center;gap:10px}
.mtag{font-size:11.5px;font-weight:700;color:#fff;background:var(--accent);
  border-radius:3px;padding:2px 9px}
.head p{margin:0;color:var(--label);font-size:12px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:4px;
  padding:18px 20px 16px;margin-bottom:12px}
.panel h2{font-size:15px;font-weight:700;margin:0 0 10px;padding-bottom:9px;
  border-bottom:3px solid var(--line);position:relative}
.panel h2::after{content:"";position:absolute;left:0;bottom:-3px;width:56px;height:3px;
  background:var(--accent)}
.lead{margin:-2px 0 12px;color:var(--label);font-size:12.5px}
.sub2{font-size:13px;font-weight:700;margin:16px 0 6px}
.stxt{display:flex;flex-direction:column;align-items:flex-end;line-height:1.35}
.stxt .big{font-size:26px}
.lgname{font-size:13px;font-weight:700;letter-spacing:.01em}
.lgname.big2{font-size:17px}
.sname{font-size:11.5px;color:var(--label);font-weight:400;display:block}
.mdeck{display:flex;flex-direction:column;align-items:flex-end;gap:6px}
.mdeck .deck{grid-template-columns:repeat(8,1fr);gap:3px;max-width:290px;width:100%}
@media(max-width:520px){.mdeck .deck{grid-template-columns:repeat(4,1fr);max-width:170px}}
.note{margin:10px 0 0;color:var(--warnink);font-size:12px;background:var(--warnbg);
  border:1px solid var(--warnline);border-radius:3px;padding:8px 12px}
.empty{color:var(--label);font-size:13px;margin:4px 0}
.chart{width:100%;height:auto;display:block;overflow:visible}
.hair{stroke:var(--line);stroke-width:1}
.gridv{stroke:#EDF0F2;stroke-width:1}
.gtick{font-size:9px;fill:#9AA4AE}
.base{stroke:#B6BDC4;stroke-width:1;stroke-dasharray:3 3}
.baselab{font-size:10px;fill:var(--label)}
.lab{font-size:12.5px;fill:var(--ink)}
.lab.small{font-size:11.5px}
.noicon{fill:#E7EAED;stroke:var(--line)}
.band.up{fill:#F7D9DE}.band.down{fill:#D6E3F3}.band.na{fill:#E7EAED}
.mark.up{fill:var(--up)}.mark.down{fill:var(--down)}.mark.na{fill:var(--na)}
.val{font-size:19px;font-weight:700}
.val.up{fill:var(--up)}.val.down{fill:var(--down)}.val.na{fill:var(--na)}
.unit{font-size:11px;font-weight:400}
.n{font-size:11.5px;fill:var(--label)}
table.kv{width:100%;border-collapse:collapse;margin:2px 0 0}
table.kv th{width:190px;background:var(--labelbg);color:var(--label);font-weight:400;
  text-align:left;padding:9px 14px;border:1px solid var(--line);font-size:12.5px}
table.kv td{padding:9px 14px;border:1px solid var(--line);text-align:right;
  font-size:15px;font-weight:700;background:#fff}
table.kv tr:nth-child(even) td{background:#FCFCFD}
table.kv td.up{background:var(--upbg);color:var(--up)}
table.kv td.down{background:var(--downbg);color:var(--down)}
.big{font-size:28px;font-weight:700;letter-spacing:-.01em}
.big .u{font-size:13px;font-weight:400;color:var(--label);margin-left:2px}
.up-t{color:var(--up)}.down-t{color:var(--down)}.na-t{color:var(--na)}
.bar{height:10px;background:#E7EAED;border-radius:2px;overflow:hidden;margin:10px 0 6px}
.bar i{display:block;height:100%;background:var(--accent)}
.barlab{display:flex;justify-content:space-between;font-size:12px;color:var(--label)}
.hl-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.hl{background:var(--labelbg);border:1px solid var(--line);border-radius:4px;
  padding:12px 14px 10px;display:flex;flex-direction:column;gap:6px}
.hl-lab{font-size:11.5px;color:var(--label)}
.hl-val{font-size:24px;font-weight:700;line-height:1.1}
.hl-u{font-size:12px;font-weight:400;color:var(--label);margin-left:1px}
.hl-sub{font-size:11px;color:var(--label);margin-top:-4px}
.hl-card{display:flex;align-items:center;gap:8px;min-height:38px}
.hl-card img,.hl-card .noimg{width:32px;aspect-ratio:5/6;border-radius:3px;display:block}
.hl-card .noimg{background:#E7EAED;border:1px solid var(--line)}
.hl-card b{font-size:13px;font-weight:700}
.hl-card b.wide{font-size:14px}
.hl .deck{grid-template-columns:repeat(4,1fr);gap:2px;max-width:150px}
.menu{display:grid;gap:10px}
.menu a{display:flex;justify-content:space-between;align-items:center;gap:16px;
  text-decoration:none;color:inherit;background:var(--panel);border:1px solid var(--line);
  border-radius:4px;padding:16px 20px}
.menu a:hover{border-color:var(--ink)}
.menu b{display:block;font-size:15px;font-weight:700}
.menu span{font-size:12.5px;color:var(--label)}
.menu em{font-style:normal;font-size:12px;color:var(--link);white-space:nowrap;font-weight:700}
.menu a:hover b{color:var(--link)}
.cov{width:100%;height:auto;display:block}
.covbar.some{fill:#4E7CB8}.covbar.zero{fill:#EDEFF2}
.covn{font-size:10px;fill:var(--label)}
.covd{font-size:10.5px;fill:var(--ink)}
.covw{font-size:9.5px;fill:var(--label)}
.keys{display:flex;flex-wrap:wrap;gap:18px;font-size:12.5px;color:var(--label);margin:2px 0 0}
.keys span{display:inline-flex;align-items:center;gap:6px}
.sw{width:22px;height:11px;border-radius:2px;display:inline-block}
.sw-up{background:#F7D9DE;border-left:3px solid var(--up)}
.sw-down{background:#D6E3F3;border-left:3px solid var(--down)}
.sw-na{background:#E7EAED;border-left:3px solid var(--na)}
.log{background:var(--panel);border:1px solid var(--line);border-radius:4px;
  margin-bottom:8px;padding:10px 14px 12px;border-left:4px solid var(--na)}
.log.win{border-left-color:var(--up)}
.log.lose{border-left-color:var(--down)}
.log header{display:flex;align-items:center;gap:12px;font-size:11.5px;color:var(--label);
  margin-bottom:8px}
.log header .mode{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.log header .tro{font-weight:700}
.duel{display:grid;grid-template-columns:1fr auto 1fr;gap:14px;align-items:center}
.deck{display:grid;grid-template-columns:repeat(4,1fr);gap:3px}
html[data-layout="wide"] .log .deck{grid-template-columns:repeat(8,1fr);gap:2px}
.deck img,.deck .noimg{width:100%;aspect-ratio:5/6;display:block;border-radius:3px}
.deck .noimg{background:#E7EAED;border:1px solid var(--line)}
.hp{margin:6px 0 0;font-size:10.5px;color:var(--label);text-align:center}
.mid{text-align:center;min-width:74px}
.badge{display:block;font-size:19px;font-weight:700;color:#fff;border-radius:3px;
  padding:2px 0;background:var(--na)}
.badge.win{background:var(--up)}.badge.lose{background:var(--down)}
.crowns{display:block;font-size:15px;font-weight:700;margin-top:4px}
.narrowonly{display:none}
html[data-layout="narrow"] .wideonly{display:none}
html[data-layout="narrow"] .narrowonly{display:block}
.basenote{margin:0 0 6px;font-size:11px;color:var(--label)}
.lyt{margin-left:auto;font-size:11.5px;color:var(--label);background:var(--panel);
  border:1px solid var(--line);border-radius:4px;padding:6px 12px;cursor:pointer;
  font-family:inherit}
.lyt:hover{border-color:var(--link);color:var(--link)}
@media print{.navwrap{display:none}}
.plot{fill:#FCFCFD;stroke:#C3CAD1;stroke-width:1}
.grid{stroke:#E9ECEF;stroke-width:1}
.monthsep{stroke:#C3CAD1;stroke-width:1}
.fifty{stroke:#E4A6AE;stroke-width:1;stroke-dasharray:4 3}
.tick{font-size:9.5px;fill:var(--label)}
.tick.mon{fill:var(--ink);font-weight:700}
.tick.vlab{font-size:9px}
.ciband{fill:#8A939C;opacity:.13}
.cistick{stroke:#8A939C;stroke-width:6;opacity:.28}
.rate{fill:none;stroke:#3A424B;stroke-width:1.1;stroke-linejoin:round}
.pt{fill:#3A424B}
.ma{fill:none;stroke:var(--up);stroke-width:2.2;stroke-linejoin:round}
.patch{stroke:#0B57A4;stroke-width:1.2;stroke-dasharray:3 3}
.mask{fill:#FFFFFF;opacity:.66}
.volbar{fill:#7B8FA8}
.ubtn{font-size:12px;padding:5px 14px;border:1px solid var(--line);border-radius:4px;
  background:var(--panel);color:var(--ink);cursor:pointer;font-family:inherit}
.ubtn.on{background:var(--ink);color:#fff;border-color:var(--ink);font-weight:700}
.ctrl{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.ctrl.foot{margin:10px 0 0;justify-content:center}
.rng{margin:10px 0 0;padding-top:10px;border-top:1px solid var(--line)}
.rng input{width:100%;margin:1px 0;accent-color:var(--ink)}
.rlab{font-size:12px;color:var(--label);margin-bottom:2px}
.rlab b{color:var(--ink)}
.legend2{display:flex;flex-wrap:wrap;gap:18px;font-size:12px;color:var(--label);
  margin-top:10px;padding-top:9px;border-top:1px solid var(--line)}
.legend2 span{display:inline-flex;align-items:center;gap:7px}
.lgline{display:inline-block;width:22px;height:0;border-top-width:2px;border-top-style:solid}
.lgbox{display:inline-block;width:20px;height:11px;border-radius:2px}
.oppinfo{margin:0 0 8px;font-size:11.5px;color:var(--label);
  display:flex;flex-wrap:wrap;gap:0 4px;align-items:center}
.oppinfo b{color:var(--ink)}
.rivaltag{background:var(--up);color:#fff;border-radius:3px;padding:1px 7px;
  font-size:10.5px;font-weight:700}
.rivalwrap{overflow-x:auto}
table.rivals{width:100%;border-collapse:collapse;font-size:13px}
table.rivals th{background:var(--labelbg);color:var(--label);font-weight:400;font-size:11.5px;
  padding:8px 10px;border:1px solid var(--line);text-align:left;white-space:nowrap}
table.rivals td{padding:8px 10px;border:1px solid var(--line);vertical-align:top}
table.rivals tr:nth-child(even) td{background:#FCFCFD}
table.rivals .rk{width:34px;color:var(--label);font-size:12px}
table.rivals .num{text-align:right;font-weight:700;white-space:nowrap}
table.rivals .dt{font-size:12px;white-space:nowrap}
footer{color:var(--label);font-size:11.5px;margin-top:18px;text-align:right}
@media(max-width:640px){body{padding:14px 8px 48px}.panel,.head{padding:14px 12px}
  nav a{font-size:12px;padding:6px 11px}
  .navlab{width:100%;margin-bottom:2px}
  table.kv th{width:130px}
  .hl-grid{grid-template-columns:1fr 1fr}
  .duel{grid-template-columns:1fr auto 1fr;gap:8px}
  .mid{min-width:52px}.badge{font-size:15px}.crowns{font-size:13px}
  .hp{font-size:9px}}
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
    return ('<div class="navwrap">'
            f'<nav class="modes"><span class="navlab">モード</span>{modes}</nav>'
            f'<nav class="pages"><span class="navlab">表示</span>{pages}'
            '<button id="lytbtn" class="lyt" onclick="crToggle()"></button></nav>'
            "</div>")


def page(prefix, base, label, title, subtitle, body):
    doc = ("<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{esc(title)}｜{esc(label)}</title>"
           f"<style>{CSS}</style><script>{SCRIPT}</script></head>"
           "<body><div class='wrap'>"
           + nav(prefix, base)
           + f"<div class='head'><h1>{esc(title)}<span class='mtag'>{esc(label)}</span></h1>"
             f"<p>{esc(subtitle)}</p></div>"
           + body
           + "<footer>battles.csv より自動生成<br>"
             "カード画像の出典は Supercell 公式API。本ページは非公式のファン制作物であり、"
             "Supercell は内容に関与していない。</footer></div></body></html>")
    name = prefix + base
    WRITTEN.add(name)
    with open(os.path.join(SCRIPT_DIR, name), "w", encoding="utf-8") as f:
        f.write(doc)


def range_ui():
    return """
    <div class="ctrl">
      <span class="navlab" style="width:auto">期間</span>
      <button id="p-7" class="ubtn">7日</button>
      <button id="p-30" class="ubtn">30日</button>
      <button id="p-90" class="ubtn">90日</button>
      <button id="p-all" class="ubtn on">全期間</button>
    </div>
    <div class="rng" style="border:0;padding-top:0;margin-top:0">
      <div class="rlab"><b id="rlab">-</b></div>
      <input id="r1" type="range" min="0" max="0" value="0">
      <input id="r2" type="range" min="0" max="0" value="0">
    </div>"""


def legend_panel(extra=""):
    keys = ('<div class="keys">'
            '<span><i class="sw sw-up"></i>基準を上回る</span>'
            '<span><i class="sw sw-down"></i>基準を下回る</span>'
            f'<span><i class="sw sw-na"></i>判定不可（{RELIABLE_N}試合未満）</span>'
            "</div>")
    note = ("縦線が推定値、帯が95%信頼区間。帯が長いほど推定の幅が大きい。"
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
    if o["battles"] is not None:
        bits.append(f"通算 {o['battles']:,} 戦")
    if is_rival(pol, gt, ladder):
        bits.append('<span class="rivaltag">強敵</span>')
    return "　".join(bits) if bits else ""


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
    """勝った相手のうち、上位実績を持つ者を順位順に並べる。"""
    items = []
    for r in rows:
        if r.get("result") != "win":
            continue
        tag = (r.get("opp_tag") or "").strip()
        o = opp_ranks(tag)
        name, pol, gt, best, ladder = o["name"], o["pol"], o["gt"], o["best"], o["ladder"]
        if not is_rival(pol, gt, ladder):
            continue
        items.append({
            "date": r["battle_time_jst"][:16],
            "name": name or r.get("opp_name") or "-",
            "tag": tag,
            "mode": r.get("game_mode") or r.get("battle_type") or "",
            "pol": pol, "gt": gt, "best": best, "ladder": ladder,
            "battles": o["battles"],
        })
    items.sort(key=lambda x: (x["pol"] if x["pol"] is not None else 10 ** 9,
                             x["gt"] if x["gt"] is not None else 10 ** 9,
                             x["ladder"] if x["ladder"] is not None else 10 ** 9))

    if not OPPONENTS:
        return panel("強敵", '<p class="empty">相手の情報がまだ集まっていない。'
                     "収集が回ると順に貯まる。</p>",
                     "対戦相手のプレイヤー情報を別途取得して判定している。")
    if not items:
        return panel("強敵", '<p class="empty">条件を満たす相手にまだ勝っていない。</p>',
                     f"レート戦の過去最高順位が{RIVAL_POL_RANK:,}位以内、"
                     f"グローバルトーナメント{RIVAL_GT_RANK:,}位以内、"
                 f"または Top Ladder {RIVAL_LADDER_RANK:,}位以内の相手が対象。")

    # 値が1件も無い列は出さない
    has_gt = any(x["gt"] is not None for x in items)

    def num_cell(v, suffix=""):
        return f'<td class="num">{"-" if v is None else f"{v:,}{suffix}"}</td>'

    body = "".join(
        f'<tr><td class="rk">{i}</td><td><b>{esc(x["name"])}</b>'
        f'<span class="sname">{esc(x["tag"])}</span></td>'
        + num_cell(x["best"])
        + num_cell(x["pol"], " 位")
        + (num_cell(x["gt"], " 位") if has_gt else "")
        + num_cell(x["ladder"], " 位")
        + num_cell(x["battles"])
        + f'<td class="dt">{esc(x["date"])}<span class="sname">{esc(x["mode"])}</span></td></tr>'
        for i, x in enumerate(items, 1))

    table_html = (
        '<div class="rivalwrap"><table class="rivals">'
        "<thead><tr><th>#</th><th>相手</th><th>最高<br>レート</th><th>レート戦<br>最高順位</th>"
        + ("<th>グローバル<br>トーナメント<br>最高順位</th>" if has_gt else "")
        + "<th>Top Ladder<br>最高順位</th><th>通算<br>試合数</th>"
        "<th>撃破した試合</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>")

    return panel(f"勝利した強敵 {len(items)} 件", table_html,
                 "レート戦の過去最高順位が高い順。同じ相手に複数回勝っていれば、その回数だけ並ぶ。",
                 f"対象はレート戦の過去最高順位{RIVAL_POL_RANK:,}位以内、"
                 + (f"グローバルトーナメント{RIVAL_GT_RANK:,}位以内、" if has_gt else "")
                 + f"または Top Ladder {RIVAL_LADDER_RANK:,}位以内の相手。")


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
  {panel("直前の結果別の勝率", rate_rows(streak_items), "縦線が左にあるほど勝率が低い。")}
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
  <section class="panel"><h2>期間の指定</h2>""" + range_ui() + """</section>
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
  <section class="panel"><h2>期間の指定</h2>""" + range_ui() + """</section>
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
    <div class="ctrl">
      <span class="navlab" style="width:auto">粒度</span>
      <button id="u-day" class="ubtn">日</button>
      <button id="u-week" class="ubtn on">週</button>
      <button id="u-month" class="ubtn">月</button>
    </div>
    <div id="chart"></div>
    <div class="ctrl foot">
      <button id="p-7" class="ubtn">7日</button>
      <button id="p-30" class="ubtn">30日</button>
      <button id="p-90" class="ubtn">90日</button>
      <button id="p-all" class="ubtn on">全期間</button>
    </div>
    <div class="rng">
      <div class="rlab">表示範囲 <b id="rlab">-</b></div>
      <input id="r1" type="range" min="0" max="0" value="0">
      <input id="r2" type="range" min="0" max="0" value="0">
    </div>
    <div class="legend2">
      <span><i class="lgline" style="border-color:#3A424B"></i>実測</span>
      <span><i class="lgline" style="border-color:#C8102E;border-top-width:3px"></i>移動平均（4期間）</span>
      <span><i class="lgbox" style="background:#D9DCDF"></i>95%信頼区間</span>
      <span><i class="lgbox" style="background:#7B8FA8"></i>プレイ回数</span>
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
         rate_page_body(PROFILE, rows) + monthly_deck_panel(rows))

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
