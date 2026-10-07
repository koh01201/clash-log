/* 募集要項チェック表を作る： node yoko-status.js  → yoko-status.md を書き出す
   各イベントの chk（日程をどこから取ったか）を集計し、「公式2027」以外＝次に調べ直すものを一覧にする。
   大学ごとのメモ（要項の公開予定など）は下の NOTES に書く。 */
var fs = require("fs"), path = require("path");
var ROOT = __dirname;
global.window = {};
require(path.join(ROOT, "data-2027.js"));
require(path.join(ROOT, "data-2027-bun.js"));

var NOTES = {
  // 大学ID: "次に調べるときのメモ"（確認日つきで書く）
  tus: "2027年度要項は未公表（10/7時点）",
  kanagawa: "2027年度要項は未公表（10/7時点）",
  icu: "入学試験要項は10月下旬公開予定（公式、10/7時点）。日程は公式ページで確認済み",
  teu: "公式の日程ページが画像で文字が取れない。要項はPDFビューア内（https://secure.nanaop-web.com/teu/2027_ippansenbatsu/）。画像かPDFを目で確認する",
  kangaku: "試験日・出願締切は公式2027。出願開始・合格発表はベネッセ、手続締切は未掲載（10/7時点）",
  tokai: "Kei-Netの締切欄は11月以降掲載だが、公式要項PDFで確認済み",
  kansai: "公式サイト（kansai-u.ac.jp/nyusi/）が10/7時点でリダイレクトエラーで読めず。日程はKei-Netの大学からのお知らせ",
  chibatech: "公式サイトが10/7時点で接続できず。日程はベネッセ掲載の2027年度",
  twcu: "日程はKei-Netの大学からのお知らせ（2027年度）。公式サイトは未確認",
  ritsumei: "共通テスト併用方式の手続締切は要項の表記が「合格発表日の翌金融機関営業日〜3/24」で日付が1つに決まらない"
};
var TODO = [
  "東京女子大学：公式サイトの2027年度日程を確認していない（Kei-Netの大学からのお知らせのみ）。前期共通テスト併用 GCP Link型（個別試験2/11）・後期共通テスト併用型（個別試験3/10）は対象学科が未確認のため未掲載",
  "千葉工業大学：公式サイト（admission.chibatech.ac.jp）が10/7時点で接続できず未確認",
  "立命館：映像学部の理系型（学部個別 2/7）は対象範囲外として未掲載。同志社の心理・スポーツ健康科学の理系型も同様"
];

var LEGEND = [
  ["公式2027", "2027年度の大学公式（募集要項・入試ガイド・公式の日程ページ）で確認済み", "調べ直し不要"],
  ["公式2027一部", "2027年度の大学公式で確認したが、一部の項目が公式に未掲載", "未掲載の項目だけ再確認"],
  ["非公式2027", "2027年度の値だが、Kei-Net・ベネッセなど大学以外から", "公式で再確認"],
  ["前年度", "2026年度の値（公式要項またはパスナビ）", "2027年度の要項で再確認"],
  ["試験日のみ", "試験日（Kei-Net）しかない", "出願・発表・手続を要項で確認"]
];
var ORDER = LEGEND.map(function (l) { return l[0]; });

var tracks = [["理系", window.NYUSHI[2027]], ["文系", window.NYUSHI["2027-bun"]]];
var univ = {}, order = [];
tracks.forEach(function (t) {
  var Y = t[1];
  Y.univs.forEach(function (u) { if (!univ[u.id]) { univ[u.id] = { name: u.name, ev: [] }; order.push(u.id); } });
  Y.events.forEach(function (e) {
    if (!e.chk) throw new Error("chk がないイベント: " + e.u + " " + e.method);
    if (ORDER.indexOf(e.chk) < 0) throw new Error("chk の値が不正: " + e.chk);
    var miss = [];
    if (!e.apply) miss.push("出願"); if (!e.result) miss.push("発表"); if (!e.proc) miss.push("手続");
    univ[e.u].ev.push({ tr: t[0], m: e.method, chk: e.chk, miss: miss, srcs: e.src.map(function (s) { return typeof s === "string" ? Y.src[s] : s; }) });
  });
});

function mark(evs) {
  if (evs.every(function (e) { return e.chk === "公式2027"; })) return "○ 済";
  if (evs.every(function (e) { return /^公式2027/.test(e.chk); })) return "△ 一部未掲載";
  return "× 要再調査";
}
function count(evs, tr) {
  var c = {}; evs.filter(function (e) { return e.tr === tr; }).forEach(function (e) { c[e.chk] = (c[e.chk] || 0) + 1; });
  return ORDER.filter(function (k) { return c[k]; }).map(function (k) { return k + " " + c[k]; }).join("、") || "－";
}

var now = new Date(), ymd = now.getFullYear() + "-" + ("0" + (now.getMonth() + 1)).slice(-2) + "-" + ("0" + now.getDate()).slice(-2);
var L = [];
L.push("# 募集要項チェック表");
L.push("");
L.push("`node yoko-status.js` で自動生成（" + ymd + "）。手で書き換えず、データの `chk` か yoko-status.js の NOTES・TODO を直して作り直す。");
L.push("");
L.push("**次に調べに行くのは「× 要再調査」と「△ 一部未掲載」の大学だけ。「○ 済」は行かなくてよい。**");
L.push("");
L.push("## 凡例（chk の値）");
L.push("");
L.push("| chk | 意味 | 次にやること |");
L.push("|---|---|---|");
LEGEND.forEach(function (l) { L.push("| " + l.join(" | ") + " |"); });
L.push("");
L.push("## 大学ごとのまとめ");
L.push("");
L.push("| 大学 | 状態 | 理系 | 文系 | メモ |");
L.push("|---|---|---|---|---|");
var tot = { "○ 済": 0, "△ 一部未掲載": 0, "× 要再調査": 0 };
order.forEach(function (id) {
  var u = univ[id], m = mark(u.ev); tot[m]++;
  L.push("| " + u.name + " | " + m + " | " + count(u.ev, "理系") + " | " + count(u.ev, "文系") + " | " + (NOTES[id] || "") + " |");
});
L.push("");
L.push("合計：○ 済 " + tot["○ 済"] + "校／△ 一部未掲載 " + tot["△ 一部未掲載"] + "校／× 要再調査 " + tot["× 要再調査"] + "校");
L.push("");
L.push("## 調べ直しリスト（公式2027 以外の方式）");
L.push("");
order.forEach(function (id) {
  var u = univ[id], ev = u.ev.filter(function (e) { return e.chk !== "公式2027"; });
  if (!ev.length) return;
  L.push("### " + u.name);
  ev.forEach(function (e) {
    L.push("- [" + e.tr + "] " + e.m + " … **" + e.chk + "**" + (e.miss.length ? "（空欄：" + e.miss.join("・") + "）" : ""));
  });
  var seen = {}, s = [];
  u.ev.forEach(function (e) { e.srcs.forEach(function (x) { if (x && !seen[x.url]) { seen[x.url] = 1; s.push("[" + x.label + "](" + x.url + ")"); } }); });
  L.push("- いまの出典：" + s.join("、"));
  L.push("");
});
L.push("## まだ入っていない大学・確認（TODO）");
L.push("");
TODO.forEach(function (t) { L.push("- " + t); });
L.push("");
fs.writeFileSync(path.join(ROOT, "yoko-status.md"), L.join("\n"));
console.log("yoko-status.md を書き出しました", tot);
