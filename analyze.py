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
    ("index.html", "概要"),
    ("chosi.html", "調子"),
    ("mydeck.html", "使用デッキ"),
    ("enemy.html", "対戦相手"),
]


def esc(text):
    return html.escape(str(text))


def rate_rows(items, baseline=0.5, baseline_label="50%"):
    """items: [(ラベル, 勝ち, 全体)]。基準より上は赤、下は青、試合数不足は灰。"""
    if not items:
        return '<p class="empty">該当するデータがない。</p>'

    row_h = 42
    top = 26
    height = top + row_h * len(items) + 4
    x0, x1 = 210, 520
    span = x1 - x0

    def px(p):
        return x0 + span * p

    out = [f'<svg viewBox="0 0 720 {height}" class="chart">']
    bx = px(baseline)
    out.append(f'<line class="base" x1="{bx:.1f}" y1="{top - 12}" x2="{bx:.1f}" y2="{height - 4}"/>')
    out.append(f'<text class="baselab" x="{bx:.1f}" y="{top - 16}" text-anchor="middle">{esc(baseline_label)}</text>')

    for i, (label, wins, total) in enumerate(items):
        y = top + row_h * i + row_h / 2
        p, lo, hi = wilson(wins, total)
        if total < RELIABLE_N:
            cls = "na"
        elif p > baseline:
            cls = "up"
        elif p < baseline:
            cls = "down"
        else:
            cls = "na"
        w = max(10.0, px(hi) - px(lo))

        out.append(f'<line class="hair" x1="0" y1="{y + row_h / 2:.1f}" x2="720" y2="{y + row_h / 2:.1f}"/>')
        out.append(f'<text class="lab" x="0" y="{y + 5:.1f}">{esc(label)}</text>')
        out.append(f'<rect class="band {cls}" x="{px(lo):.1f}" y="{y - 8:.1f}" width="{w:.1f}" height="16" rx="2"/>')
        out.append(f'<rect class="mark {cls}" x="{px(p) - 1.5:.1f}" y="{y - 13:.1f}" width="3" height="26"/>')
        out.append(f'<text class="val {cls}" x="600" y="{y + 7:.1f}" text-anchor="end">'
                   f'{p * 100:.1f}<tspan class="unit">%</tspan></text>')
        out.append(f'<text class="n" x="720" y="{y + 5:.1f}" text-anchor="end">{wins}勝{total - wins}敗</text>')
    out.append("</svg>")
    return "".join(out)


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
nav{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 16px}
nav a{text-decoration:none;background:var(--panel);color:var(--ink);font-size:13px;
  padding:7px 18px;border:1px solid var(--line);border-radius:4px}
nav a.on{background:var(--ink);color:#fff;border-color:var(--ink);font-weight:700}
nav a:not(.on):hover{border-color:var(--link);color:var(--link)}
.head{background:var(--panel);border:1px solid var(--line);border-radius:4px;
  padding:16px 20px;margin-bottom:12px;display:flex;justify-content:space-between;
  align-items:flex-end;flex-wrap:wrap;gap:8px}
.head{border-top:3px solid var(--accent)}
.head h1{font-size:20px;font-weight:700;margin:0}
.head p{margin:0;color:var(--label);font-size:12px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:4px;
  padding:18px 20px 16px;margin-bottom:12px}
.panel h2{font-size:15px;font-weight:700;margin:0 0 10px;padding-bottom:9px;
  border-bottom:3px solid var(--line);position:relative}
.panel h2::after{content:"";position:absolute;left:0;bottom:-3px;width:56px;height:3px;
  background:var(--accent)}
.lead{margin:-2px 0 12px;color:var(--label);font-size:12.5px}
.note{margin:10px 0 0;color:var(--warnink);font-size:12px;background:var(--warnbg);
  border:1px solid var(--warnline);border-radius:3px;padding:8px 12px}
.empty{color:var(--label);font-size:13px;margin:4px 0}
.chart{width:100%;height:auto;display:block;overflow:visible}
.hair{stroke:var(--line);stroke-width:1}
.base{stroke:#B6BDC4;stroke-width:1;stroke-dasharray:3 3}
.baselab{font-size:10px;fill:var(--label)}
.lab{font-size:12.5px;fill:var(--ink)}
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
footer{color:var(--label);font-size:11.5px;margin-top:18px;text-align:right}
@media(max-width:640px){body{padding:14px 8px 48px}.panel,.head{padding:14px 12px}
  table.kv th{width:130px}}
"""


def nav(current):
    return "<nav>" + "".join(
        f'<a href="{f}"{" class=\"on\"" if f == current else ""}>{esc(l)}</a>' for f, l in PAGES
    ) + "</nav>"


def page(fname, title, subtitle, body):
    doc = ("<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{esc(title)}｜対戦記録レポート</title><style>{CSS}</style></head><body><div class='wrap'>"
           + nav(fname)
           + f"<div class='head'><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>"
           + body + "<footer>battles.csv より自動生成</footer></div></body></html>")
    with open(os.path.join(SCRIPT_DIR, fname), "w", encoding="utf-8") as f:
        f.write(doc)


def legend_panel(extra=""):
    keys = ('<div class="keys">'
            '<span><i class="sw sw-up"></i>基準を上回る</span>'
            '<span><i class="sw sw-down"></i>基準を下回る</span>'
            f'<span><i class="sw sw-na"></i>判定不可（{RELIABLE_N}試合未満）</span>'
            "</div>")
    note = ("縦線が推定値、帯が95%信頼区間。帯が長いほど推定の幅が大きい。"
            "帯どうしが重なる範囲では、差があるとは言えない。" + extra)
    return panel("凡例と注意", keys, "", note)


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

def main():
    all_rows = add_sessions(load_rows())
    prev_state(all_rows)
    rows = [r for r in all_rows if is_ranked(r)] if RANKED_ONLY else list(all_rows)
    excluded = len(all_rows) - len(rows)
    if not rows:
        raise SystemExit("集計対象の試合がない。")

    wins = sum(1 for r in rows if r["result"] == "win")
    decided = sum(1 for r in rows if r["result"] != "draw")
    p, lo, hi = wilson(wins, decided)
    first, last = all_rows[0]["_dt"], all_rows[-1]["_dt"]
    sessions = len({r["_session"] for r in rows})
    stamp = f"対象期間 {first:%Y/%m/%d} 〜 {last:%Y/%m/%d}　更新 {now_jst():%Y/%m/%d %H:%M} JST"

    # ---- 概要 ----
    page("index.html", "対戦記録レポート", stamp, f"""
  {panel("現況", table([
      ("勝率", f'<span class="big">{p*100:.1f}<span class="u">%</span></span>',
       "up" if p > 0.5 else "down" if p < 0.5 else ""),
      ("95%信頼区間", f"{lo*100:.1f}% 〜 {hi*100:.1f}%"),
      ("勝敗", f'<span class="up-t">{wins}勝</span> / <span class="down-t">{decided-wins}敗</span>'),
      ("集計対象", f"{len(rows)} 試合"),
      ("記録総数", f"{len(all_rows)} 試合"),
      ("プレイ回数", f"{sessions} 回"),
  ]), "ランク戦のみを対象とする。")}
  <div class="menu">
    <a href="chosi.html"><span><b>調子の分析</b><span>連敗後の勝率、連続対戦数、時間帯、曜日</span></span><em>表示 &gt;</em></a>
    <a href="mydeck.html"><span><b>使用デッキ別</b><span>デッキ構成ごとの勝率と、入れ替えたカードの影響</span></span><em>表示 &gt;</em></a>
    <a href="enemy.html"><span><b>対戦相手カード別</b><span>相手の編成に含まれるカードと勝率の関係</span></span><em>表示 &gt;</em></a>
  </div>
""")

    # ---- 調子 ----
    by_hour = tally(rows, lambda r: r["_hour"])
    hour_items = [(f"{h}時台", w, t) for h, (w, t) in sorted(by_hour.items())]
    by_pos = tally(rows, lambda r: "6戦目以降" if r["_pos"] >= 6 else f"{r['_pos']}戦目")
    pos_items = [(k, *by_pos[k]) for k in ["1戦目", "2戦目", "3戦目", "4戦目", "5戦目", "6戦目以降"] if k in by_pos]

    def streak_key(r):
        s = r["_prev_streak"]
        return ("2連敗後" if s <= -2 else "1敗後" if s == -1 else
                "セッション初戦" if s == 0 else "1勝後" if s == 1 else "2連勝後")

    by_streak = tally(rows, streak_key)
    streak_items = [(k, *by_streak[k]) for k in
                    ["2連敗後", "1敗後", "セッション初戦", "1勝後", "2連勝後"] if k in by_streak]
    by_wd = tally(rows, lambda r: r["_wd"])
    wd_items = [(WEEKDAY_JA[k] + "曜", w, t) for k, (w, t) in sorted(by_wd.items())]

    aft_l, aft_w = [0, 0], [0, 0]
    for r in rows:
        if r["result"] == "draw" or r["_prev_streak"] == 0:
            continue
        box = aft_l if r["_prev_streak"] < 0 else aft_w
        box[1] += 1
        if r["result"] == "win":
            box[0] += 1
    pl, ll, hl = wilson(*aft_l)
    pw, lw, hw = wilson(*aft_w)
    conclusive = min(aft_l[1], aft_w[1]) >= RELIABLE_N and (hl < lw or hw < ll)
    if not conclusive:
        judge, judge_cls = "判定不可", "na-t"
        judge_note = "試合数が不足しており、差の有無を判断できない。"
    elif pl < pw:
        judge, judge_cls = "低下の傾向あり", "down-t"
        judge_note = f"敗戦後 {pl*100:.1f}% に対し勝利後 {pw*100:.1f}%。連敗時は中断が妥当と考えられる。"
    else:
        judge, judge_cls = "低下は認められない", "up-t"
        judge_note = f"敗戦後 {pl*100:.1f}% に対し勝利後 {pw*100:.1f}%。"

    need = needed_n()
    goal = need * 2
    strip, day_count, empty_days = coverage_strip(all_rows)

    page("chosi.html", "調子の分析", stamp, f"""
  {panel("検証課題：連敗後に勝率は低下するか",
      table([
          ("現時点の判定", f'<span class="big {judge_cls}">{judge}</span>'),
          ("敗戦後の勝率", f"{pl*100:.1f}%（{aft_l[0]}勝{aft_l[1]-aft_l[0]}敗）",
           "up" if aft_l[1] >= RELIABLE_N and pl > p else "down" if aft_l[1] >= RELIABLE_N and pl < p else ""),
          ("勝利後の勝率", f"{pw*100:.1f}%（{aft_w[0]}勝{aft_w[1]-aft_w[0]}敗）",
           "up" if aft_w[1] >= RELIABLE_N and pw > p else "down" if aft_w[1] >= RELIABLE_N and pw < p else ""),
      ])
      + f'<div class="bar"><i style="width:{min(100, decided/goal*100):.1f}%"></i></div>'
        f'<div class="barlab"><span>必要試合数に対する進捗 {decided} / {goal}</span>'
        f'<span>残り {max(0, goal-decided)} 試合</span></div>',
      "", judge_note + f" 勝率50%と60%の差を有意水準5%・検出力80%で検出するには、各群{need}試合を要する。")}
  {panel("直前の結果別の勝率", rate_rows(streak_items), "縦線が左にあるほど勝率が低い。")}
  {panel("連続対戦数と勝率", rate_rows(pos_items), "",
      f"前の試合から{SESSION_GAP_MINUTES}分以上の間隔があいた場合、別セッションとして数える。")}
  {panel("時間帯別の勝率", rate_rows(hour_items))}
  {panel("曜日別の勝率", rate_rows(wd_items))}
  {panel("データ取得状況", strip + table([
      ("集計対象", f"{len(rows)} 試合"),
      ("記録総数", f"{len(all_rows)} 試合"),
      ("取得のない日", f"{empty_days} 日"),
      ("除外した試合", f"{excluded} 試合"),
  ]), "棒のない日は、未プレイまたは取得漏れ。",
      "クラン戦など規則の異なる試合は集計から除外している。")}
  {legend_panel()}
""")

    # ---- 使用デッキ ----
    def deck_key(r):
        cards = [c for c in r["my_deck"].split("|") if c]
        return "|".join(sorted(cards)) if cards else None

    by_deck = tally(rows, deck_key)
    deck_face = {}
    for r in rows:
        k = deck_key(r)
        if k and k not in deck_face:
            deck_face[k] = "・".join([c for c in r["my_deck"].split("|") if c][:3])
    deck_rank = sorted(by_deck.items(), key=lambda kv: -kv[1][1])
    deck_items = [(f"{i}. {deck_face.get(k, '?')}…", w, t)
                  for i, (k, (w, t)) in enumerate(deck_rank[:8], 1)]

    my_cards = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["result"] == "draw":
            continue
        for c in set(x for x in r["my_deck"].split("|") if x):
            my_cards[c][1] += 1
            if r["result"] == "win":
                my_cards[c][0] += 1
    varying = {c: v for c, v in my_cards.items() if v[1] < decided}
    my_items = [(c, w, t) for c, (w, t) in
                sorted(varying.items(), key=lambda kv: -kv[1][1])[:TOP_CARDS]]
    fixed_n = len(my_cards) - len(varying)

    page("mydeck.html", "使用デッキ別の勝率", stamp, f"""
  {panel("デッキ構成別の勝率", rate_rows(deck_items, p, f"平均 {p*100:.0f}%"),
      "基準線は全体平均。デッキ変更の効果はここに現れる。",
      f"使用したデッキ構成は{len(by_deck)}種類。試合数の多い順に上位8件を表示する。")}
  {panel("入れ替えのあったカード", rate_rows(my_items, p, f"平均 {p*100:.0f}%") if my_items
         else '<p class="empty">入れ替えの記録がまだない。</p>',
      "全試合に含まれる固定枠は差が生じないため除外している。",
      f"常時採用のカード{fixed_n}枚を表から除外した。")}
  {legend_panel("　なお自分側のカードは、デッキを変更しない限り差が生じない構造にある。")}
""")

    # ---- 対戦相手 ----
    opp_cards = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["result"] == "draw":
            continue
        for c in set(x for x in r["opp_deck"].split("|") if x):
            opp_cards[c][1] += 1
            if r["result"] == "win":
                opp_cards[c][0] += 1
    enough = {c: v for c, v in opp_cards.items() if v[1] >= MIN_CARD_N}
    ranked = sorted(enough.items(), key=lambda kv: kv[1][0] / kv[1][1])
    worst = [(c, w, t) for c, (w, t) in ranked[:TOP_CARDS]]
    best = [(c, w, t) for c, (w, t) in ranked[::-1][:TOP_CARDS]]

    page("enemy.html", "対戦相手のカード別の勝率", stamp, f"""
  {panel("勝率の低いカード", rate_rows(worst, p, f"平均 {p*100:.0f}%") if worst
         else '<p class="empty">判定できるカードがまだない。</p>',
      "相手の編成に当該カードが含まれていた試合における、自分の勝率。",
      f"{MIN_CARD_N}試合以上対戦したカードのみを対象とする"
      f"（全{len(opp_cards)}種類のうち{len(enough)}種類）。")}
  {panel("勝率の高いカード", rate_rows(best, p, f"平均 {p*100:.0f}%") if best else "")}
  {legend_panel("　カードの種類が多いため、偶然により極端な値が生じやすい。"
                "個別のカードで判断せず、同種の役割を持つカードが揃って下振れしているかを確認するのが妥当。")}
""")

    print(f"4ページを出力（対象 {len(rows)} 試合 / 除外 {excluded} 件）")
    print(f"全体勝率 {p*100:.1f}%（95%CI {lo*100:.1f}〜{hi*100:.1f}%） / 相手カード判定可能 {len(enough)}種類")


if __name__ == "__main__":
    main()
