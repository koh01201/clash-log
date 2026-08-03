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


# ---------------- 描画 ----------------

def esc(text):
    return html.escape(str(text))


def verdict(total):
    return "まだわからん" if total < RELIABLE_N else "そこそこ言える"


def rate_rows(items, caption=""):
    """items: [(ラベル, 勝ち, 全体)] を「帯＋玉」で描く。帯＝ありうる範囲、玉＝いまの見積り。"""
    if not items:
        return ""

    row_h = 46
    top = 30
    height = top + row_h * len(items) + 10
    x0, x1 = 132, 500
    span = x1 - x0

    def px(p):
        return x0 + span * p

    out = [f'<svg viewBox="0 0 700 {height}" class="chart">']
    out.append(
        f'<line class="half" x1="{px(0.5):.1f}" y1="{top - 16}" x2="{px(0.5):.1f}" y2="{height - 8}"/>'
    )
    out.append(f'<text class="halflab" x="{px(0.5):.1f}" y="{top - 20}" text-anchor="middle">五分五分</text>')

    for i, (label, wins, total) in enumerate(items):
        y = top + row_h * i + row_h / 2
        p, lo, hi = wilson(wins, total)
        weak = total < RELIABLE_N
        cls = "weak" if weak else "sure"
        w = max(14.0, px(hi) - px(lo))

        out.append(f'<text class="lab" x="0" y="{y + 6:.1f}">{esc(label)}</text>')
        out.append(
            f'<rect class="band {cls}" x="{px(lo):.1f}" y="{y - 11:.1f}" '
            f'width="{w:.1f}" height="22" rx="11"/>'
        )
        out.append(f'<circle class="ball {cls}" cx="{px(p):.1f}" cy="{y:.1f}" r="9"/>')
        out.append(f'<text class="pct {cls}" x="518" y="{y + 8:.1f}">{p * 100:.0f}<tspan class="pctu">%</tspan></text>')
        out.append(f'<text class="score" x="700" y="{y + 5:.1f}" text-anchor="end">{wins}勝{total - wins}敗</text>')

    out.append("</svg>")
    cap = f'<p class="cap">{esc(caption)}</p>' if caption else ""
    return "".join(out), cap


def card(title, lead, items, caption=""):
    chart, cap = rate_rows(items, caption) if items else ("", "")
    return f"""<section class="card">
  <h2>{esc(title)}</h2>
  <p class="lead">{esc(lead)}</p>
  {chart}{cap}
</section>"""


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

    peak = max(c for _, c in days) or 1
    cell = min(64, max(30, int(660 / max(1, len(days)))))
    width = cell * len(days)
    height = 104

    out = [f'<svg viewBox="0 0 {width} {height}" class="cov">']
    for i, (day, count) in enumerate(days):
        x = cell * i
        h = 6 + 54 * (count / peak)
        cls = "zero" if count == 0 else "some"
        out.append(
            f'<rect class="covbar {cls}" x="{x + 4}" y="{66 - h:.1f}" '
            f'width="{cell - 8}" height="{h:.1f}" rx="{min(10, (cell - 8) / 2):.1f}"/>'
        )
        if count:
            out.append(f'<text class="covn" x="{x + cell / 2:.1f}" y="{60 - h:.1f}" text-anchor="middle">{count}</text>')
        out.append(f'<text class="covd" x="{x + cell / 2:.1f}" y="86" text-anchor="middle">{day.month}/{day.day}</text>')
        out.append(f'<text class="covw" x="{x + cell / 2:.1f}" y="100" text-anchor="middle">{WEEKDAY_JA[day.weekday()]}</text>')
    out.append("</svg>")
    return "".join(out), len(days), sum(1 for _, c in days if c == 0)


CSS = """
@import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;700;800&display=swap');
:root{
  --bg:#F3F1FE; --card:#FFFFFF; --ink:#241546; --sub:#7A6CA6;
  --line:#E7E2FB; --violet:#6C4BF4; --violet-soft:#D9D0FF;
  --gold:#FFB020; --gold-soft:#FFE6B8; --coral:#FF6B6B;
}
*{box-sizing:border-box}
body{
  margin:0; padding:28px 16px 72px; background:var(--bg); color:var(--ink);
  font-family:"M PLUS Rounded 1c","Hiragino Maru Gothic ProN","Yu Gothic UI","Noto Sans JP",sans-serif;
  line-height:1.75; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:760px;margin:0 auto}
.top{margin:0 0 22px}
.top h1{font-size:27px;font-weight:800;margin:0 0 2px;letter-spacing:.01em}
.top p{margin:0;color:var(--sub);font-size:13px}
.card{background:var(--card);border-radius:20px;padding:24px 26px 20px;margin-bottom:16px;
  box-shadow:0 2px 0 var(--line),0 10px 24px -18px rgba(60,30,140,.5)}
.card h2{font-size:19px;font-weight:800;margin:0 0 4px}
.lead{margin:0 0 16px;color:var(--sub);font-size:13.5px}
.cap{margin:12px 0 0;color:var(--sub);font-size:12.5px}
.hero{background:linear-gradient(135deg,#6C4BF4,#9B6BFF);color:#fff}
.hero h2{color:#fff;font-size:16px;opacity:.85;font-weight:700}
.answer{font-size:34px;font-weight:800;line-height:1.25;margin:2px 0 14px}
.gauge{background:rgba(255,255,255,.25);border-radius:999px;height:16px;overflow:hidden}
.gauge i{display:block;height:100%;background:var(--gold);border-radius:999px}
.gaugelab{display:flex;justify-content:space-between;font-size:12.5px;margin-top:8px;opacity:.9}
.chart,.cov{width:100%;height:auto;display:block;overflow:visible}
.half{stroke:#C9BEEF;stroke-width:2;stroke-dasharray:4 5}
.halflab{font-size:11px;fill:var(--sub)}
.lab{font-size:14px;font-weight:700;fill:var(--ink)}
.band.sure{fill:var(--violet-soft)}
.band.weak{fill:var(--gold-soft)}
.ball.sure{fill:var(--violet);stroke:#fff;stroke-width:3}
.ball.weak{fill:var(--gold);stroke:#fff;stroke-width:3}
.pct{font-size:21px;font-weight:800}
.pct.sure{fill:var(--violet)} .pct.weak{fill:#C98800}
.pctu{font-size:12px;font-weight:700}
.score{font-size:12px;fill:var(--sub)}
.covbar.some{fill:var(--violet);opacity:.85}
.covbar.zero{fill:#EDE9FB}
.covn{font-size:11px;fill:var(--sub);font-weight:700}
.covd{font-size:11.5px;fill:var(--ink);font-weight:700}
.covw{font-size:10.5px;fill:var(--sub)}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:4px 0 0;padding:0;list-style:none}
.stats li{background:var(--bg);border-radius:14px;padding:10px 16px;min-width:92px}
.stats b{display:block;font-size:22px;font-weight:800;line-height:1.3}
.stats span{font-size:11.5px;color:var(--sub)}
.keys{display:flex;flex-wrap:wrap;gap:16px;margin-top:6px;font-size:13px;color:var(--sub)}
.keys span{display:inline-flex;align-items:center;gap:7px}
.pill{width:26px;height:13px;border-radius:999px;display:inline-block}
.p-sure{background:var(--violet-soft)} .p-weak{background:var(--gold-soft)}
.dotmini{width:11px;height:11px;border-radius:50%;background:var(--violet);
  border:2px solid #fff;box-shadow:0 0 0 1px var(--violet-soft);display:inline-block}
footer{color:var(--sub);font-size:12px;text-align:center;margin-top:24px}
@media(max-width:600px){body{padding:20px 10px 56px}.card{padding:20px 16px 16px;border-radius:16px}
  .answer{font-size:27px}.top h1{font-size:23px}}
"""


def main():
    all_rows = add_sessions(load_rows())
    prev_state(all_rows)

    excluded = 0
    if RANKED_ONLY:
        rows = [r for r in all_rows if is_ranked(r)]
        excluded = len(all_rows) - len(rows)
    else:
        rows = all_rows
    if not rows:
        raise SystemExit("集計対象の試合がありません。")

    strip, day_count, empty_days = coverage_strip(all_rows)

    wins = sum(1 for r in rows if r["result"] == "win")
    decided = sum(1 for r in rows if r["result"] != "draw")
    p, lo, hi = wilson(wins, decided)
    first, last = all_rows[0]["_dt"], all_rows[-1]["_dt"]
    sessions = len({r["_session"] for r in rows})

    by_hour = tally(rows, lambda r: r["_hour"])
    hour_items = [(f"{h}時台", w, t) for h, (w, t) in sorted(by_hour.items())]

    def pos_key(r):
        return "6戦目以降" if r["_pos"] >= 6 else f"{r['_pos']}戦目"

    by_pos = tally(rows, pos_key)
    pos_items = [(k, *by_pos[k]) for k in
                 ["1戦目", "2戦目", "3戦目", "4戦目", "5戦目", "6戦目以降"] if k in by_pos]

    def streak_key(r):
        s = r["_prev_streak"]
        if s <= -2:
            return "2連敗のあと"
        if s == -1:
            return "1敗のあと"
        if s == 0:
            return "その日の1戦目"
        if s == 1:
            return "1勝のあと"
        return "2連勝のあと"

    by_streak = tally(rows, streak_key)
    streak_items = [(k, *by_streak[k]) for k in
                    ["2連敗のあと", "1敗のあと", "その日の1戦目", "1勝のあと", "2連勝のあと"]
                    if k in by_streak]

    by_wd = tally(rows, lambda r: r["_wd"])
    wd_items = [(WEEKDAY_JA[k] + "曜", w, t) for k, (w, t) in sorted(by_wd.items())]

    # 見出しの答え：負けたあと vs 勝ったあと
    after_loss = [0, 0]
    after_win = [0, 0]
    for r in rows:
        if r["result"] == "draw" or r["_prev_streak"] == 0:
            continue
        box = after_loss if r["_prev_streak"] < 0 else after_win
        box[1] += 1
        if r["result"] == "win":
            box[0] += 1
    pl, ll, hl = wilson(*after_loss)
    pw, lw, hw = wilson(*after_win)
    overlap = not (hl < lw or hw < ll)
    enough = min(after_loss[1], after_win[1]) >= RELIABLE_N

    if not enough or overlap:
        answer = "まだ わからない"
        answer_sub = "差があるとも、ないとも言えない段階。試合数が足りていない。"
    elif pl < pw:
        answer = "負けたあとは 弱いかも"
        answer_sub = f"負けたあと{pl*100:.0f}% / 勝ったあと{pw*100:.0f}%。連敗したら止めるのが良さそう。"
    else:
        answer = "負けたあとも 落ちてない"
        answer_sub = f"負けたあと{pl*100:.0f}% / 勝ったあと{pw*100:.0f}%。引きずってはいないみたい。"

    need = needed_n()
    goal = need * 2
    pctdone = min(100, decided / goal * 100)
    remain = max(0, goal - decided)

    body = f"""
<div class="wrap">
  <div class="top">
    <h1>今日のクラロワ、どうだった？</h1>
    <p>{first:%Y/%m/%d} 〜 {last:%Y/%m/%d} ／ {datetime.datetime.now():%m/%d %H:%M} 時点</p>
  </div>

  <section class="card hero">
    <h2>知りたいこと：連敗のあと、弱くなる？</h2>
    <div class="answer">{esc(answer)}</div>
    <div class="gauge"><i style="width:{pctdone:.1f}%"></i></div>
    <div class="gaugelab"><span>答え合わせゲージ {decided} / {goal} 試合</span><span>あと {remain} 試合</span></div>
    <p class="cap" style="color:rgba(255,255,255,.9);margin-top:14px">{esc(answer_sub)}</p>
  </section>

  <section class="card">
    <h2>ぜんぶまとめて</h2>
    <p class="lead">ランク戦だけを数えたもの。</p>
    <ul class="stats">
      <li><b>{p*100:.0f}%</b><span>勝率</span></li>
      <li><b>{wins}-{decided-wins}</b><span>勝敗</span></li>
      <li><b>{lo*100:.0f}〜{hi*100:.0f}%</b><span>ほんとうの実力はこの辺</span></li>
      <li><b>{sessions}</b><span>プレイした回数</span></li>
    </ul>
  </section>

  {card("連敗したあと、弱くなる？", "これが一番知りたいところ。玉が左にあるほど弱い。", streak_items,
        "帯が長いのは「まだ絞りきれてない」という意味。試合が増えると細くなる。")}
  {card("何戦目でバテる？", "続けて遊んだとき、何戦目から崩れるか。", pos_items,
        f"{SESSION_GAP_MINUTES}分あいたら別の回として数えている。")}
  {card("何時が強い？", "生活リズムとの相性。", hour_items)}
  {card("曜日でちがう？", "", wd_items)}

  <section class="card">
    <h2>どれくらい集まった？</h2>
    <p class="lead">棒がない日は、遊んでいないか取り逃した日。</p>
    {strip}
    <ul class="stats" style="margin-top:14px">
      <li><b>{len(rows)}</b><span>集計に使った試合</span></li>
      <li><b>{len(all_rows)}</b><span>記録した全試合</span></li>
      <li><b>{empty_days}</b><span>空っぽの日</span></li>
      <li><b>{excluded}</b><span>除いた試合</span></li>
    </ul>
    <p class="cap">クラン戦などルールが違う試合は混ぜていない。同じ土俵じゃないと比べられないため。</p>
  </section>

  <section class="card">
    <h2>この図の見かた</h2>
    <p class="lead">玉が「いまの見積り」、帯が「ほんとうはこのへん」。</p>
    <div class="keys">
      <span><i class="dotmini"></i>いまの見積り</span>
      <span><i class="pill p-sure"></i>{RELIABLE_N}試合以上ある（そこそこ言える）</span>
      <span><i class="pill p-weak"></i>{RELIABLE_N}試合未満（まだわからん）</span>
    </div>
    <p class="cap">
      帯どうしが重なっているうちは、差があるとは言えない。
      ちゃんと言い切るには、比べる2グループにそれぞれ約{need}試合ずつ必要。
      いまは全部で{decided}試合。
    </p>
  </section>

  <footer>battles.csv から自動生成</footer>
</div>
"""

    doc = ("<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           "<title>今日のクラロワ、どうだった？</title><style>" + CSS + "</style></head><body>"
           + body + "</body></html>")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(doc)

    print(f"report.html を書き出しました（対象 {len(rows)} 試合 / 除外 {excluded} 件）")
    print(f"全体勝率 {p*100:.1f}%  ありうる範囲 {lo*100:.0f}〜{hi*100:.0f}%")
    print(f"答え合わせゲージ {decided}/{goal}")


if __name__ == "__main__":
    main()
