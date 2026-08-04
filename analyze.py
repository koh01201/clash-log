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
    ("index.html", "概要"),
    ("chosi.html", "調子"),
    ("mydeck.html", "使用デッキ"),
    ("enemy.html", "対戦相手"),
    ("chart.html", "推移"),
    ("log.html", "対戦記録"),
]


CARDS_FILE = os.path.join(SCRIPT_DIR, "cards.json")


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
    top, W = 26, 720
    height = top + row_h * len(items) + 4
    x0 = {"none": 210, "single": 210, "deck": 216}[icon_mode]
    x1 = 520
    span = x1 - x0

    def px(v):
        return x0 + span * v

    out = [f'<svg viewBox="0 0 {W} {height}" class="chart">']
    bx = px(baseline)
    out.append(f'<line class="base" x1="{bx:.1f}" y1="{top-12}" x2="{bx:.1f}" y2="{height-4}"/>')
    out.append(f'<text class="baselab" x="{bx:.1f}" y="{top-16}" text-anchor="middle">{esc(baseline_label)}</text>')

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
    top, W = 34, 380
    height = top + row_h * len(items) + 6
    x0 = 72 if icon_mode == "deck" else 24
    x1 = 286
    span = x1 - x0

    def px(v):
        return x0 + span * v

    bx = px(baseline)
    out = [f'<svg viewBox="0 0 {W} {height}" class="chart">']
    if icon_mode != "deck":
        # カードを貫かない配置なので、基準線は通しで引く
        out.append(f'<line class="base" x1="{bx:.1f}" y1="{top-14}" x2="{bx:.1f}" y2="{height-6}"/>')
    out.append(f'<text class="baselab" x="{bx:.1f}" y="{top-18}" text-anchor="middle">{esc(baseline_label)}</text>')

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
    if (t.indexOf("riverrace") >= 0 || t.indexOf("clanwar") >= 0) return "cw";
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
    var b = S.buckets, nb = b.length;
    if (!nb) { document.getElementById("chart").innerHTML =
      '<p class="empty">この期間のデータがない。</p>'; return; }

    var nw = narrow();
    var W = nw ? 380 : 720, H = nw ? 210 : 250, VH = nw ? 56 : 74;
    var padL = 32, padR = 10, padT = 16, padB = 20;
    var pw = W - padL - padR, ph = H - padT - padB;
    var step = pw / nb;
    var x = function (i) { return padL + (i + 0.5) * step; };
    var y = function (v) { return padT + ph * (1 - v); };
    var o = [];

    o.push('<svg viewBox="0 0 ' + W + ' ' + H + '" class="chart">');

    // 月ごとの背景（シーズンの目安）
    var mstart = 0, mi = 0, k;
    for (k = 1; k <= nb; k++) {
      if (k === nb || b[k].key.slice(0, 7) !== b[mstart].key.slice(0, 7)) {
        if (mi % 2 === 1) {
          o.push('<rect class="season" x="' + (padL + mstart * step).toFixed(1) + '" y="' + padT +
            '" width="' + ((k - mstart) * step).toFixed(1) + '" height="' + ph + '"/>');
        }
        mstart = k; mi++;
      }
    }

    // 目盛り
    [0, 0.25, 0.5, 0.75, 1].forEach(function (v) {
      o.push('<line class="grid' + (v === 0.5 ? " half" : "") + '" x1="' + padL + '" y1="' +
        y(v).toFixed(1) + '" x2="' + (W - padR) + '" y2="' + y(v).toFixed(1) + '"/>');
      o.push('<text class="tick" x="' + (padL - 5) + '" y="' + (y(v) + 3.5).toFixed(1) +
        '" text-anchor="end">' + (v * 100) + '</text>');
    });

    // 信頼区間の帯
    var up = [], dn = [], i, r;
    for (i = 0; i < nb; i++) {
      r = wilson(b[i].w, b[i].n);
      up.push(x(i).toFixed(1) + "," + y(r[2]).toFixed(1));
      dn.unshift(x(i).toFixed(1) + "," + y(r[1]).toFixed(1));
    }
    if (nb > 1) o.push('<polygon class="ciband" points="' + up.concat(dn).join(" ") + '"/>');

    // 実測の折れ線と点
    var pts = b.map(function (d, j) {
      return x(j).toFixed(1) + "," + y(d.n ? d.w / d.n : 0).toFixed(1);
    });
    if (nb > 1) o.push('<polyline class="rate" points="' + pts.join(" ") + '"/>');

    // 移動平均
    var ma = movingAvg(b, MA_WIN);
    var mp = [];
    for (i = 0; i < nb; i++) if (ma[i] !== null) mp.push(x(i).toFixed(1) + "," + y(ma[i]).toFixed(1));
    if (mp.length > 1) o.push('<polyline class="ma" points="' + mp.join(" ") + '"/>');

    // 点と日付
    var base = S.overall;
    for (i = 0; i < nb; i++) {
      var p = b[i].n ? b[i].w / b[i].n : 0;
      o.push('<circle class="pt ' + tone(p, base, b[i].n) + '" cx="' + x(i).toFixed(1) +
        '" cy="' + y(p).toFixed(1) + '" r="' + (nw ? 3.2 : 4) + '"><title>' +
        esc(b[i].key) + " " + b[i].w + "勝" + (b[i].n - b[i].w) + "敗</title></circle>");
    }
    var everyN = Math.ceil(nb / (nw ? 5 : 10));
    for (i = 0; i < nb; i += everyN) {
      o.push('<text class="tick" x="' + x(i).toFixed(1) + '" y="' + (H - 5) +
        '" text-anchor="middle">' + esc(fmtDate(b[i].key, S.unit)) + "</text>");
    }

    // バランス調整日
    PATCHES.forEach(function (d) {
      for (i = 0; i < nb; i++) {
        if (b[i].key >= d) {
          o.push('<line class="patch" x1="' + (padL + i * step).toFixed(1) + '" y1="' + padT +
            '" x2="' + (padL + i * step).toFixed(1) + '" y2="' + (padT + ph) + '"/>');
          break;
        }
      }
    });

    // 範囲外を暗く
    if (S.lo > 0) o.push('<rect class="mask" x="' + padL + '" y="' + padT + '" width="' +
      (S.lo * step).toFixed(1) + '" height="' + ph + '"/>');
    if (S.hi < nb - 1) o.push('<rect class="mask" x="' + (padL + (S.hi + 1) * step).toFixed(1) +
      '" y="' + padT + '" width="' + ((nb - 1 - S.hi) * step).toFixed(1) + '" height="' + ph + '"/>');
    o.push("</svg>");

    // 出来高（プレイ回数）
    var maxg = Math.max.apply(null, b.map(function (d) { return d.games; })) || 1;
    o.push('<svg viewBox="0 0 ' + W + ' ' + VH + '" class="chart vol">');
    o.push('<text class="tick" x="' + (padL - 5) + '" y="12" text-anchor="end">' + maxg + "</text>");
    for (i = 0; i < nb; i++) {
      var bh = (VH - 18) * (b[i].games / maxg);
      var inr = i >= S.lo && i <= S.hi;
      o.push('<rect class="volbar' + (inr ? "" : " out") + '" x="' +
        (padL + i * step + step * 0.15).toFixed(1) + '" y="' + (VH - 14 - bh).toFixed(1) +
        '" width="' + (step * 0.7).toFixed(1) + '" height="' + bh.toFixed(1) + '" rx="1"><title>' +
        esc(b[i].key) + " " + b[i].games + "試合</title></rect>");
    }
    o.push('<line class="grid" x1="' + padL + '" y1="' + (VH - 14) + '" x2="' + (W - padR) +
      '" y2="' + (VH - 14) + '"/>');
    o.push('<text class="tick" x="' + padL + '" y="' + (VH - 3) + '">プレイ回数</text>');
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
    var full = document.getElementById("rfull");
    if (full) full.onclick = function () { S.lo = 0; S.hi = S.buckets.length - 1; refreshRange(); draw(); summary(); };
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
.note{margin:10px 0 0;color:var(--warnink);font-size:12px;background:var(--warnbg);
  border:1px solid var(--warnline);border-radius:3px;padding:8px 12px}
.empty{color:var(--label);font-size:13px;margin:4px 0}
.chart{width:100%;height:auto;display:block;overflow:visible}
.hair{stroke:var(--line);stroke-width:1}
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
html[data-layout="narrow"] .lead{display:none}
.basenote{margin:0 0 6px;font-size:11px;color:var(--label)}
.lyt{margin-left:auto;font-size:11.5px;color:var(--label);background:var(--panel);
  border:1px solid var(--line);border-radius:4px;padding:6px 12px;cursor:pointer;
  font-family:inherit}
.lyt:hover{border-color:var(--link);color:var(--link)}
@media print{.navwrap{display:none}}
.season{fill:#F4F6F8}
.grid{stroke:var(--line);stroke-width:1}
.grid.half{stroke:#B6BDC4;stroke-dasharray:3 3}
.tick{font-size:9.5px;fill:var(--label)}
.ciband{fill:#C8102E;opacity:.10}
.rate{fill:none;stroke:var(--up);stroke-width:1.6;stroke-linejoin:round}
.ma{fill:none;stroke:var(--down);stroke-width:2.4;stroke-linejoin:round;opacity:.85}
.pt{stroke:#fff;stroke-width:1.4}
.pt.up{fill:var(--up)}.pt.down{fill:var(--down)}.pt.na{fill:var(--na)}
.patch{stroke:#8A939C;stroke-width:1.4;stroke-dasharray:4 3}
.mask{fill:#fff;opacity:.62}
.vol{margin-top:2px}
.volbar{fill:#4E7CB8;opacity:.85}
.volbar.out{fill:#C7CDD4;opacity:.7}
.ubtn{font-size:12px;padding:5px 14px;border:1px solid var(--line);border-radius:4px;
  background:var(--panel);color:var(--ink);cursor:pointer;font-family:inherit;margin-right:5px}
.ubtn.on{background:var(--ink);color:#fff;border-color:var(--ink);font-weight:700}
.ctrl{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.rng{margin:8px 0 0}
.rng input{width:100%;margin:2px 0;accent-color:var(--accent)}
.rlab{font-size:12px;color:var(--label);display:flex;justify-content:space-between;
  align-items:center;gap:10px}
.legend2{display:flex;flex-wrap:wrap;gap:16px;font-size:12px;color:var(--label);margin-top:8px}
.legend2 i{display:inline-block;width:20px;height:0;border-top-width:3px;border-top-style:solid;
  vertical-align:middle;margin-right:6px}
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
    ("pol", "", "伝説の道"),
    ("cw", "cw-", "クラン戦"),
    ("etc", "etc-", "その他"),
    ("all", "all-", "すべて"),
]

AVAILABLE = []          # 実際に生成するモード（試合が1件以上あるもの）


def classify(row):
    t = (row.get("battle_type") or "").lower()
    if "pathoflegend" in t:
        return "pol"
    if "riverrace" in t or "clanwar" in t:
        return "cw"
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
    with open(os.path.join(SCRIPT_DIR, prefix + base), "w", encoding="utf-8") as f:
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

    aft_l, aft_w = [0, 0], [0, 0]
    for r in rows:
        if r["result"] == "draw" or r["_prev_streak"] == 0:
            continue
        box = aft_l if r["_prev_streak"] < 0 else aft_w
        box[1] += 1
        if r["result"] == "win":
            box[0] += 1
    pl, ll, hl_ = wilson(*aft_l)
    pw, lw, hw = wilson(*aft_w)
    conclusive = min(aft_l[1], aft_w[1]) >= RELIABLE_N and (hl_ < lw or hw < ll)
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
    strip, day_count, empty_days = coverage_strip(rows)

    page(prefix, "chosi.html", label, "調子の分析", stamp, f"""
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
      ("このモードの試合", f"{len(rows)} 試合"),
      ("記録総数（全モード）", f"{total_records} 試合"),
      ("取得のない日", f"{empty_days} 日"),
  ]), "棒のない日は、未プレイまたは取得漏れ。")}
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

    page(prefix, "mydeck.html", label, "使用デッキ別の勝率", stamp, f"""
  {panel("デッキ構成別の勝率", rate_rows(deck_items, p, f"平均 {p*100:.0f}%", "deck"),
      "左に並ぶ8枚がその構成。基準線は全体平均で、デッキ変更の効果はここに現れる。",
      f"使用したデッキ構成は{len(by_deck)}種類。試合数の多い順に上位8件を表示する。")}
  {panel("入れ替えのあったカード",
      rate_rows(my_items, p, f"平均 {p*100:.0f}%", "single") if my_items
      else '<p class="empty">入れ替えの記録がまだない。</p>',
      "全試合に含まれる固定枠は差が生じないため除外している。",
      f"常時採用のカード{fixed_n}枚を表から除外した。")}
  {legend_panel()}
""")

    # 対戦相手
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
    worst = [(c, w, t, [c]) for c, (w, t) in ranked[:TOP_CARDS]]
    best = [(c, w, t, [c]) for c, (w, t) in ranked[::-1][:TOP_CARDS]]

    page(prefix, "enemy.html", label, "対戦相手のカード別の勝率", stamp, f"""
  {panel("勝率の低いカード",
      rate_rows(worst, p, f"平均 {p*100:.0f}%", "single") if worst
      else '<p class="empty">判定できるカードがまだない。</p>',
      "相手の編成に当該カードが含まれていた試合における、自分の勝率。",
      f"{MIN_CARD_N}試合以上対戦したカードのみを対象とする"
      f"（全{len(opp_cards)}種類のうち{len(enough)}種類）。")}
  {panel("勝率の高いカード",
      rate_rows(best, p, f"平均 {p*100:.0f}%", "single") if best else "")}
  {legend_panel("　カードの種類が多いため、偶然により極端な値が生じやすい。")}
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
    <div class="rng">
      <div class="rlab"><span>期間 <b id="rlab">-</b></span>
        <button id="rfull" class="ubtn">全期間</button></div>
      <input id="r1" type="range" min="0" max="0" value="0">
      <input id="r2" type="range" min="0" max="0" value="0">
    </div>
    <div class="legend2">
      <span><i style="border-color:#C8102E"></i>実測</span>
      <span><i style="border-color:#0B57A4"></i>移動平均（4期間）</span>
      <span>薄い赤帯＝95%信頼区間</span>
      <span>灰色の背景＝月の区切り</span>
    </div>
    <p class="note">週や日の勝率は試合数が少ないと大きく上下する。帯の幅がその不確かさを表す。
      背景の色分けは暦月による目安で、実際のシーズン境界とは一致しないことがある。</p>
  </section>
  <section class="panel"><h2>選んだ期間の成績</h2>
    <p class="lead">上のつまみで期間を絞ると、ここが連動して変わる。</p>
    <div id="sum"></div>
  </section>
  <script>""" + CHART_JS.replace("__MODE__", mode_key) + """</script>
""")

    # 対戦記録
    page(prefix, "log.html", label, "対戦記録", stamp, f"""
  {panel("直近100試合", battle_log(rows, 100),
      "左が自分、右が相手の編成。数字は残ったタワーのHP。",
      "画像にマウスを乗せるとカード名が出る。")}
""")

    # 概要
    MIN_HL = 5
    boxes = []
    good_decks = [(k, w, t) for k, (w, t) in by_deck.items() if t >= MIN_HL]
    if good_decks:
        k, w, t = max(good_decks, key=lambda x: x[1] / x[2])
        boxes.append(hl_box("最も勝てているデッキ", deck_grid(deck_face.get(k, [])), w, t, p))
        if len(good_decks) > 1:
            k, w, t = min(good_decks, key=lambda x: x[1] / x[2])
            boxes.append(hl_box("苦戦しているデッキ", deck_grid(deck_face.get(k, [])), w, t, p))
    if ranked:
        c, (w, t) = ranked[0]
        boxes.append(hl_box("苦手な相手カード", hl_card(c), w, t, p))
        c, (w, t) = ranked[-1]
        boxes.append(hl_box("得意な相手カード", hl_card(c), w, t, p))
    good_hours = [(h, w, t) for h, (w, t) in by_hour.items() if t >= MIN_HL]
    if good_hours:
        h, w, t = max(good_hours, key=lambda x: x[1] / x[2])
        boxes.append(hl_box("勝てている時間帯", hl_text(f"{h}時台"), w, t, p))
        if len(good_hours) > 1:
            h, w, t = min(good_hours, key=lambda x: x[1] / x[2])
            boxes.append(hl_box("負けている時間帯", hl_text(f"{h}時台"), w, t, p))
    highlights = ('<div class="hl-grid">' + "".join(boxes) + "</div>") if boxes \
        else '<p class="empty">判定できるだけの試合数がまだない。</p>'

    page(prefix, "index.html", label, "対戦記録レポート", stamp, f"""
  {panel("現況", table([
      ("勝率", f'<span class="big">{p*100:.1f}<span class="u">%</span></span>',
       "up" if p > 0.5 else "down" if p < 0.5 else ""),
      ("95%信頼区間", f"{lo*100:.1f}% 〜 {hi*100:.1f}%"),
      ("勝敗", f'<span class="up-t">{wins}勝</span> / <span class="down-t">{decided-wins}敗</span>'),
      ("このモードの試合", f"{len(rows)} 試合"),
      ("記録総数（全モード）", f"{total_records} 試合"),
      ("プレイ回数", f"{sessions} 回"),
  ]))}
  {panel("いま目立つところ", highlights,
      f"{MIN_HL}試合以上あるものから選んでいる。基準はこのモードの平均 {p*100:.1f}%。",
      "件数の少ないものは偶然で極端な値になりやすい。詳細は上のタブから。")}
  {panel("検証課題：連敗後に勝率は低下するか", table([
      ("現時点の判定", f'<span class="big {judge_cls}">{judge}</span>'),
      ("敗戦後の勝率", f"{pl*100:.1f}%（{aft_l[0]}勝{aft_l[1]-aft_l[0]}敗）"),
      ("勝利後の勝率", f"{pw*100:.1f}%（{aft_w[0]}勝{aft_w[1]-aft_w[0]}敗）"),
  ]) + f'<div class="bar"><i style="width:{min(100, decided/goal*100):.1f}%"></i></div>'
     f'<div class="barlab"><span>必要試合数に対する進捗 {decided} / {goal}</span>'
     f'<span>残り {max(0, goal-decided)} 試合</span></div>')}
""")


def main():
    global ICONS, AVAILABLE
    ICONS = load_icons()
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

    counts = " / ".join(f"{lab} {len(all_rows) if k == 'all' else len(groups.get(k, []))}"
                        for k, _, lab in MODES if k in AVAILABLE)
    print(f"モード別に出力しました（{counts}）")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"エラー: {error}")
        raise
