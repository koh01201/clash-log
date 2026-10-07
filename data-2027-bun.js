/* 2027年度入試（文系）の日程データ ─ build/build_bun.py で生成（直接編集しない）
   試験日は2027年度（大学発表、または河合塾Kei-Net掲載）。
   出願・発表・手続は year=2027 なら2027年度の大学発表、year=2026 なら前年度（旺文社パスナビ等）。
   chk ＝ 日程をどこから取ったか（公式2027／公式2027一部／非公式2027／前年度／試験日のみ）。意味は data-2027.js の冒頭と yoko-status.md を参照 */
(function () {
var FIELDS = [
  { id: "law", name: "法・政治" },
  { id: "econ", name: "経済・経営・商" },
  { id: "lit", name: "文・人文" },
  { id: "intl", name: "外国語・国際" },
  { id: "soc", name: "社会・メディア" },
  { id: "edu", name: "教育・心理・福祉" },
  { id: "other", name: "総合・スポーツほか" }
];
var FIELD_RULES = [
  ["law", /法学|法律|法$|法・|政治|政経|ヒューマンライツ/],
  ["econ", /経済|政経|経営|商学|商$|商・|会計|マーケティング|ビジネス|ホスピタリティ/],
  ["lit", /文学|文化|文芸|史|哲|神学|人文|仏教|書道|芸術|映像|デザイン・アート|国文|英米文|日本文/],
  ["intl", /外国語|国際|グローバル|英語|多文化|異文化|地球社会|言語|アジア|共創/],
  ["soc", /社会|メディア|コミュニケーション|観光|コミュニティ|ジャーナリズム|新聞|マスコミ|イノベーション|情報/],
  ["edu", /教育|心理|人間|福祉|子ども|児童|発達|キャリア/],
  ["other", /政策|スポーツ|健康|環境|食|総合|学環|ウエルネス/]
];
function fieldOf(fac, depts) {
  var t = fac + " " + (depts || ""), out = [];
  if (fac === "文学部") out.push("lit");
  FIELD_RULES.forEach(function (r) { if (out.indexOf(r[0]) < 0 && r[1].test(t)) out.push(r[0]); });
  return out.length ? out : ["other"];
}
var UNIVS = [
 {
  "id": "waseda",
  "name": "早稲田大学",
  "short": "早稲田",
  "hue": 352
 },
 {
  "id": "keio",
  "name": "慶應義塾大学",
  "short": "慶應",
  "hue": 220
 },
 {
  "id": "sophia",
  "name": "上智大学",
  "short": "上智",
  "hue": 120
 },
 {
  "id": "tus",
  "name": "東京理科大学",
  "short": "東京理科",
  "hue": 28
 },
 {
  "id": "meiji",
  "name": "明治大学",
  "short": "明治",
  "hue": 268
 },
 {
  "id": "aoyama",
  "name": "青山学院大学",
  "short": "青学",
  "hue": 160
 },
 {
  "id": "rikkyo",
  "name": "立教大学",
  "short": "立教",
  "hue": 285
 },
 {
  "id": "chuo",
  "name": "中央大学",
  "short": "中央",
  "hue": 95
 },
 {
  "id": "hosei",
  "name": "法政大学",
  "short": "法政",
  "hue": 200
 },
 {
  "id": "nihon",
  "name": "日本大学",
  "short": "日大",
  "hue": 8
 },
 {
  "id": "toyo",
  "name": "東洋大学",
  "short": "東洋",
  "hue": 25
 },
 {
  "id": "komazawa",
  "name": "駒澤大学",
  "short": "駒澤",
  "hue": 340
 },
 {
  "id": "senshu",
  "name": "専修大学",
  "short": "専修",
  "hue": 175
 },
 {
  "id": "seikei",
  "name": "成蹊大学",
  "short": "成蹊",
  "hue": 230
 },
 {
  "id": "seijo",
  "name": "成城大学",
  "short": "成城",
  "hue": 50
 },
 {
  "id": "meigaku",
  "name": "明治学院大学",
  "short": "明学",
  "hue": 305
 },
 {
  "id": "daito",
  "name": "大東文化大学",
  "short": "大東文化",
  "hue": 15
 },
 {
  "id": "tokai",
  "name": "東海大学",
  "short": "東海",
  "hue": 205
 },
 {
  "id": "asia",
  "name": "亜細亜大学",
  "short": "亜細亜",
  "hue": 130
 },
 {
  "id": "teikyo",
  "name": "帝京大学",
  "short": "帝京",
  "hue": 355
 },
 {
  "id": "kokushikan",
  "name": "国士舘大学",
  "short": "国士舘",
  "hue": 80
 },
 {
  "id": "kansai",
  "name": "関西大学",
  "short": "関西",
  "hue": 265
 },
 {
  "id": "kangaku",
  "name": "関西学院大学",
  "short": "関学",
  "hue": 40
 },
 {
  "id": "doshisha",
  "name": "同志社大学",
  "short": "同志社",
  "hue": 245
 },
 {
  "id": "ritsumei",
  "name": "立命館大学",
  "short": "立命館",
  "hue": 330
 },
 {
  "id": "tsuda",
  "name": "津田塾大学",
  "short": "津田塾",
  "hue": 170
 },
 {
  "id": "twcu",
  "name": "東京女子大学",
  "short": "東京女子",
  "hue": 0
 },
 {
  "id": "jwu",
  "name": "日本女子大学",
  "short": "日本女子",
  "hue": 315
 },
 {
  "id": "kanagawa",
  "name": "神奈川大学",
  "short": "神奈川",
  "hue": 300
 },
 {
  "id": "icu",
  "name": "国際基督教大学",
  "short": "ICU",
  "hue": 75
 }
];
var GROUPS = [{"name": "早慶上理", "members": ["waseda", "keio", "sophia", "tus"], "missing": []}, {"name": "MARCH", "members": ["meiji", "aoyama", "rikkyo", "chuo", "hosei"], "missing": []}, {"name": "日東駒専", "members": ["nihon", "toyo", "komazawa", "senshu"], "missing": []}, {"name": "成成明学", "members": ["seikei", "seijo", "meigaku"], "missing": []}, {"name": "大東亜帝国", "members": ["daito", "tokai", "asia", "teikyo", "kokushikan"], "missing": []}, {"name": "関関同立", "members": ["kansai", "kangaku", "doshisha", "ritsumei"], "missing": []}, {"name": "女子大御三家", "members": ["tsuda", "twcu", "jwu"], "missing": []}, {"name": "その他", "members": ["kanagawa", "icu"], "missing": []}];
var SRC = {
 "waseda": {
  "label": "早稲田大学 2027年度一般選抜（入学センター）",
  "url": "https://www.waseda.jp/inst/admission/assets/uploads/2026/05/2027_ippan.pdf"
 },
 "keio": {
  "label": "慶應義塾大学 一般選抜（2027年度）",
  "url": "https://www.keio.ac.jp/ja/admissions/faculty/examinations/general-admissions/"
 },
 "sophia": {
  "label": "上智大学 2027年度一般選抜入学試験日程",
  "url": "https://adm.sophia.ac.jp/jpn/gakubu_ippan_ad/date/"
 },
 "meijiTop": {
  "label": "明治大学 入試総合サイト",
  "url": "https://www.meiji.ac.jp/exam/information/index.html"
 },
 "meijiPN": {
  "label": "旺文社パスナビ 明治大学（前年度）",
  "url": "https://passnavi.obunsha.co.jp/univ/3120/schedule/"
 },
 "aoyamaTop": {
  "label": "青山学院大学 入試情報",
  "url": "https://www.aoyama.ac.jp/admission/undergraduate/"
 },
 "aoyamaPN": {
  "label": "旺文社パスナビ 青山学院大学（前年度）",
  "url": "https://passnavi.obunsha.co.jp/univ/2260/schedule/"
 },
 "rikkyoTop": {
  "label": "立教大学 2027年度 学部入試の情報",
  "url": "https://www.rikkyo.ac.jp/admissions/undergraduate/"
 },
 "rikkyoTopic": {
  "label": "河合塾 Kei-Net 立教大学「一般選抜の特徴」（2027年度・大学からのお知らせ）",
  "url": "https://search.keinet.ne.jp/2290/topics/12"
 },
 "rikkyoPN": {
  "label": "旺文社パスナビ 立教大学（前年度）",
  "url": "https://passnavi.obunsha.co.jp/univ/3160/schedule/"
 },
 "chuoTop": {
  "label": "中央大学 一般選抜の概要（2027年度日程PDFあり）",
  "url": "https://www.chuo-u.ac.jp/connect/admission/exam/overview/"
 },
 "chuoPN": {
  "label": "旺文社パスナビ 中央大学（前年度）",
  "url": "https://passnavi.obunsha.co.jp/univ/2680/schedule/"
 },
 "hoseiTop": {
  "label": "法政大学 入試情報サイト",
  "url": "https://nyushi.hosei.ac.jp/"
 },
 "hoseiPN": {
  "label": "旺文社パスナビ 法政大学（前年度）",
  "url": "https://passnavi.obunsha.co.jp/univ/3050/schedule/"
 },
 "toyoTop": {
  "label": "東洋大学 入試情報サイト",
  "url": "https://www.toyo.ac.jp/nyushi/"
 },
 "toyoPN": {
  "label": "旺文社パスナビ 東洋大学（前年度）",
  "url": "https://passnavi.obunsha.co.jp/univ/2910/schedule/"
 },
 "komazawaTop": {
  "label": "駒澤大学 入試情報",
  "url": "https://www.komazawa-u.ac.jp/exam/"
 },
 "komazawaPN": {
  "label": "旺文社パスナビ 駒澤大学（前年度）",
  "url": "https://passnavi.obunsha.co.jp/univ/2430/schedule/"
 },
 "nihonN": {
  "label": "日本大学 N全学統一方式（2027年度）",
  "url": "https://www.nihon-u.ac.jp/admission_info/application/general_information/general/n_system/"
 },
 "nihonTop": {
  "label": "日本大学 入試ガイド",
  "url": "https://www.nihon-u.ac.jp/admission_info/"
 },
 "senshuTop": {
  "label": "専修大学 入試情報",
  "url": "https://www.senshu-u.ac.jp/admission/"
 },
 "seikeiTop": {
  "label": "成蹊大学 入試情報",
  "url": "https://www.seikei.ac.jp/university/admission/"
 },
 "seikeiPN": {
  "label": "旺文社パスナビ 成蹊大学（前年度）",
  "url": "https://passnavi.obunsha.co.jp/univ/2540/schedule/"
 },
 "seijoTop": {
  "label": "成城大学 入試情報",
  "url": "https://www.seijo.ac.jp/admissions/"
 },
 "meigakuTop": {
  "label": "明治学院大学 入試情報",
  "url": "https://nyushi.meijigakuin.ac.jp/"
 },
 "meigakuPN": {
  "label": "旺文社パスナビ 明治学院大学（前年度）",
  "url": "https://passnavi.obunsha.co.jp/univ/3130/schedule/"
 },
 "daitoTop": {
  "label": "大東文化大学 入試情報",
  "url": "https://www.daito.ac.jp/admission/"
 },
 "tokaiTop": {
  "label": "東海大学 2027年度入試情報",
  "url": "https://www.u-tokai.ac.jp/examination-admissions/exam/"
 },
 "tokaiYoko": {
  "label": "東海大学 2027年度 全学部統一／一般／大学入学共通テスト利用選抜 要項（医学部医学科を除く）",
  "url": "https://www.u-tokai.ac.jp/uploads/2021/02/3138531a9456e7e37c3281d7a941b022.pdf"
 },
 "asiaTop": {
  "label": "亜細亜大学 入試情報",
  "url": "https://www.asia-u.ac.jp/admissions/"
 },
 "teikyoTop": {
  "label": "帝京大学 入試情報",
  "url": "https://www.teikyo-u.ac.jp/applicants/"
 },
 "kokushikanTop": {
  "label": "国士舘大学 入試情報",
  "url": "https://www.kokushikan.ac.jp/admissions/"
 },
 "tus": {
  "label": "東京理科大学 2026年度 一般選抜 入学試験要項（前年度）",
  "url": "https://www.tus.ac.jp/today/archive/2025/GeneralExamGuidelines_2026.pdf"
 },
 "doshisha": {
  "label": "同志社大学 2027年度入学試験ガイド",
  "url": "https://www.doshisha.ac.jp/files/nyugk/page/nyushiguide2027.pdf"
 },
 "ritsumei": {
  "label": "立命館大学 2027年度一般選抜ガイド",
  "url": "https://admission.ritsumei.ac.jp/assets/file/2027/application/guide/04-19.pdf"
 },
 "kansaiTop": {
  "label": "関西大学 入試情報",
  "url": "https://www.kansai-u.ac.jp/nyusi/"
 },
 "kansaiKN": {
  "label": "河合塾 Kei-Net 関西大学「大学からのお知らせ」（2027年度）",
  "url": "https://search.keinet.ne.jp/2533/topics/12"
 },
 "kangakuTop": {
  "label": "関西学院大学 入試情報",
  "url": "https://www.kwansei.ac.jp/admissions/"
 },
 "kanagawa": {
  "label": "神奈川大学 2026年度一般選抜要項（2027年度は未公表）",
  "url": "https://www.kanagawa-u.ac.jp/admissions/faculty/about_application/general/file/general_yoko2026.pdf"
 },
 "jwu": {
  "label": "日本女子大学 2027年度 一般選抜募集要項",
  "url": "https://www.jwu.ac.jp/unv/admission/exam/ct6r0e0000007526-att/2027general.pdf"
 },
 "jwuWeb": {
  "label": "日本女子大学 一般選抜（個別選抜型）2027年度",
  "url": "https://www.jwu.ac.jp/unv/admission/exam/general.html"
 },
 "jwuEng": {
  "label": "日本女子大学 英語外部試験利用型 2027年度",
  "url": "https://www.jwu.ac.jp/unv/admission/exam/external_english_exam.html"
 },
 "icu": {
  "label": "国際基督教大学 一般選抜 2027年度（入学試験要項は10月下旬公開予定）",
  "url": "https://www.icu.ac.jp/admissions/undergraduate/exam/general/"
 },
 "tsuda": {
  "label": "津田塾大学 2027年度一般選抜 試験日程一覧",
  "url": "https://www.tsuda.ac.jp/admissions/ug-general/"
 },
 "twcuKN": {
  "label": "河合塾 Kei-Net 東京女子大学「一般選抜の特徴」（2027年度・大学からのお知らせ）",
  "url": "https://search.keinet.ne.jp/2254/topics/12"
 }
};
var EVENTS = [
 {
  "u": "waseda",
  "method": "一般選抜（共通テスト併用）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-20",
    "f": [
     [
      "政治経済学部",
      "政治・経済・国際政治経済"
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-02-28",
  "proc": "2027-03-08",
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "procNote": "1次手続の締切。Web入力・書類郵送 3/12、2次手続 3/24",
  "note": "大学入学共通テストの受験が必要です。個別試験は総合問題。",
  "chk": "公式2027"
 },
 {
  "u": "waseda",
  "method": "一般選抜",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-15",
    "f": [
     [
      "法学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-02-24",
  "proc": "2027-03-04",
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "procNote": "1次手続の締切。Web入力・書類郵送 3/12、2次手続 3/24",
  "chk": "公式2027"
 },
 {
  "u": "waseda",
  "method": "一般選抜（A〜D方式）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-19",
    "f": [
     [
      "教育学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-03-02",
  "proc": "2027-03-09",
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "procNote": "1次手続の締切。Web入力・書類郵送 3/12、2次手続 3/24",
  "note": "C方式・D方式は大学入学共通テストを併用します。",
  "chk": "公式2027"
 },
 {
  "u": "waseda",
  "method": "一般選抜（地歴・公民型／数学型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-21",
    "f": [
     [
      "商学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-03-01",
  "proc": "2027-03-08",
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "procNote": "1次手続の締切。Web入力・書類郵送 3/12、2次手続 3/24",
  "chk": "公式2027"
 },
 {
  "u": "waseda",
  "method": "一般選抜（共通テスト併用）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-22",
    "f": [
     [
      "社会科学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-03-03",
  "proc": "2027-03-10",
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "procNote": "1次手続の締切。Web入力・書類郵送 3/12、2次手続 3/24",
  "note": "総合問題型と数学型があります。大学入学共通テストの受験が必要です。",
  "chk": "公式2027"
 },
 {
  "u": "waseda",
  "method": "一般選抜（共通テスト併用）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-13",
    "f": [
     [
      "国際教養学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-03-04",
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "note": "大学入学共通テストの受験が必要です。",
  "chk": "公式2027一部"
 },
 {
  "u": "waseda",
  "method": "一般選抜（英語4技能テスト利用・共通テスト利用方式を含む）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-12",
    "f": [
     [
      "文化構想学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-02-20",
  "proc": "2027-03-04",
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "procNote": "1次手続の締切。Web入力・書類郵送 3/12、2次手続 3/24",
  "chk": "公式2027"
 },
 {
  "u": "waseda",
  "method": "一般選抜（英語4技能テスト利用・共通テスト利用方式を含む）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-17",
    "f": [
     [
      "文学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-02-26",
  "proc": "2027-03-05",
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "procNote": "1次手続の締切。Web入力・書類郵送 3/12、2次手続 3/24",
  "chk": "公式2027"
 },
 {
  "u": "waseda",
  "method": "数学選抜方式（共通テスト併用）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-08",
    "f": [
     [
      "人間科学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-02-22",
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "chk": "公式2027一部"
 },
 {
  "u": "waseda",
  "method": "国英型・数英型（共通テスト併用）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-18",
    "f": [
     [
      "人間科学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-02-27",
  "proc": "2027-03-05",
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "procNote": "1次手続の締切。Web入力・書類郵送 3/12、2次手続 3/24",
  "chk": "公式2027"
 },
 {
  "u": "waseda",
  "method": "一般選抜（共通テスト併用）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-23",
    "f": [
     [
      "スポーツ科学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "締切日消印有効"
  ],
  "result": "2027-03-03",
  "proc": "2027-03-10",
  "subjects": null,
  "eiken": null,
  "src": [
   "waseda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2293/general/schedule"
   }
  ],
  "procNote": "1次手続の締切。Web入力・書類郵送 3/12、2次手続 3/24",
  "note": "個別試験は総合問題。大学入学共通テストの受験が必要です。",
  "chk": "公式2027"
 },
 {
  "u": "keio",
  "method": "一般選抜",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-15",
    "f": [
     [
      "文学部",
      "人文社会"
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-24",
   "2027-01-18",
   "Web登録 1/18 17:00まで、書類は1/4〜1/18 消印有効"
  ],
  "result": "2027-02-24",
  "proc": "2027-03-12",
  "subjects": null,
  "eiken": null,
  "src": [
   "keio",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2210/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "keio",
  "method": "一般選抜（A方式・B方式）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-13",
    "f": [
     [
      "経済学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-24",
   "2027-01-18",
   "Web登録 1/18 17:00まで、書類は1/4〜1/18 消印有効"
  ],
  "result": "2027-02-25",
  "proc": "2027-03-12",
  "subjects": null,
  "eiken": null,
  "src": [
   "keio",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2210/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "keio",
  "method": "一般選抜",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-16",
    "f": [
     [
      "法学部",
      "法律・政治"
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-24",
   "2027-01-18",
   "Web登録 1/18 17:00まで、書類は1/4〜1/18 消印有効"
  ],
  "result": "2027-02-25",
  "proc": "2027-03-12",
  "subjects": null,
  "eiken": null,
  "src": [
   "keio",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2210/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "keio",
  "method": "一般選抜（A方式・B方式）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-14",
    "f": [
     [
      "商学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-24",
   "2027-01-18",
   "Web登録 1/18 17:00まで、書類は1/4〜1/18 消印有効"
  ],
  "result": "2027-02-24",
  "proc": "2027-03-12",
  "subjects": null,
  "eiken": null,
  "src": [
   "keio",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2210/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "keio",
  "method": "一般選抜",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-17",
    "f": [
     [
      "総合政策学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-24",
   "2027-01-18",
   "Web登録 1/18 17:00まで、書類は1/4〜1/18 消印有効"
  ],
  "result": "2027-02-25",
  "proc": "2027-03-12",
  "subjects": null,
  "eiken": null,
  "src": [
   "keio",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2210/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "keio",
  "method": "一般選抜",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-18",
    "f": [
     [
      "環境情報学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-24",
   "2027-01-18",
   "Web登録 1/18 17:00まで、書類は1/4〜1/18 消印有効"
  ],
  "result": "2027-02-25",
  "proc": "2027-03-12",
  "subjects": null,
  "eiken": null,
  "src": [
   "keio",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2210/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "sophia",
  "method": "TEAPスコア利用方式（全学統一日程）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-06",
    "f": [
     [
      "神学部",
      ""
     ],
     [
      "文学部",
      "哲・史・国文・英文・ドイツ文・フランス文・新聞"
     ],
     [
      "総合人間科学部",
      "教育・心理・社会・社会福祉・看護"
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "総合グローバル学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-21",
   "Web出願。書類は1/22（金）消印有効"
  ],
  "result": "2027-02-17",
  "proc": "2027-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "sophia",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2221/general/schedule"
   }
  ],
  "resultNote": "神学部と総合人間科学部の心理・看護学科は2/24（1次合格発表2/15、2次試験2/19）",
  "procNote": "入学金の支払期限。入学手続の締切は3/17（水）",
  "note": "試験は午前。経済学部の理系受験だけ午後です。英語はTEAPのスコアを使います。",
  "chk": "公式2027"
 },
 {
  "u": "sophia",
  "method": "学部学科試験・共通テスト併用方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "神学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-21",
   "Web出願。書類は1/22（金）消印有効"
  ],
  "result": "2027-02-24",
  "proc": "2027-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "sophia",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2221/general/schedule"
   }
  ],
  "procNote": "入学金の支払期限。入学手続の締切は3/17（水）",
  "note": "試験は午前。",
  "chk": "公式2027"
 },
 {
  "u": "sophia",
  "method": "学部学科試験・共通テスト併用方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "文学部",
      "史・英文・ドイツ文"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "史・英文・ドイツ文"
   },
   {
    "d": "2027-02-08",
    "f": [
     [
      "文学部",
      "哲・国文・フランス文・新聞"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "哲・国文・フランス文・新聞"
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-21",
   "Web出願。書類は1/22（金）消印有効"
  ],
  "result": null,
  "proc": "2027-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "sophia",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2221/general/schedule"
   }
  ],
  "procNote": "入学金の支払期限。入学手続の締切は3/17（水）",
  "note": "最終合格発表は学科により2/17または2/19です（どの学科がどちらかは要項で確認）。試験は午後。",
  "chk": "公式2027一部"
 },
 {
  "u": "sophia",
  "method": "学部学科試験・共通テスト併用方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "総合人間科学部",
      "教育・社会・社会福祉・看護"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "教育・社会・社会福祉・看護"
   },
   {
    "d": "2027-02-08",
    "f": [
     [
      "総合人間科学部",
      "心理"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "心理"
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-21",
   "Web出願。書類は1/22（金）消印有効"
  ],
  "result": "2027-02-17",
  "proc": "2027-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "sophia",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2221/general/schedule"
   }
  ],
  "resultNote": "心理・看護学科は2/24",
  "procNote": "入学金の支払期限。入学手続の締切は3/17（水）",
  "chk": "公式2027"
 },
 {
  "u": "sophia",
  "method": "学部学科試験・共通テスト併用方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "法学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-21",
   "Web出願。書類は1/22（金）消印有効"
  ],
  "result": "2027-02-19",
  "proc": "2027-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "sophia",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2221/general/schedule"
   }
  ],
  "procNote": "入学金の支払期限。入学手続の締切は3/17（水）",
  "note": "試験は午前。",
  "chk": "公式2027"
 },
 {
  "u": "sophia",
  "method": "学部学科試験・共通テスト併用方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "経済学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-21",
   "Web出願。書類は1/22（金）消印有効"
  ],
  "result": "2027-02-20",
  "proc": "2027-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "sophia",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2221/general/schedule"
   }
  ],
  "procNote": "入学金の支払期限。入学手続の締切は3/17（水）",
  "note": "試験は午後。",
  "chk": "公式2027"
 },
 {
  "u": "sophia",
  "method": "学部学科試験・共通テスト併用方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "経営学部",
      "数学選択"
     ]
    ],
    "tag": "選択科目で試験日が違う",
    "l2": "数学選択"
   },
   {
    "d": "2027-02-10",
    "f": [
     [
      "経営学部",
      "英語選択"
     ]
    ],
    "tag": "選択科目で試験日が違う",
    "l2": "英語選択"
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-21",
   "Web出願。書類は1/22（金）消印有効"
  ],
  "result": null,
  "proc": "2027-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "sophia",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2221/general/schedule"
   }
  ],
  "procNote": "入学金の支払期限。入学手続の締切は3/17（水）",
  "chk": "公式2027一部"
 },
 {
  "u": "sophia",
  "method": "学部学科試験・共通テスト併用方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-10",
    "f": [
     [
      "総合グローバル学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-21",
   "Web出願。書類は1/22（金）消印有効"
  ],
  "result": "2027-02-20",
  "proc": "2027-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "sophia",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2221/general/schedule"
   }
  ],
  "procNote": "入学金の支払期限。入学手続の締切は3/17（水）",
  "note": "試験は午前。",
  "chk": "公式2027"
 },
 {
  "u": "sophia",
  "method": "学部学科試験・共通テスト併用方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-10",
    "f": [
     [
      "外国語学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-21",
   "Web出願。書類は1/22（金）消印有効"
  ],
  "result": "2027-02-20",
  "proc": "2027-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "sophia",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2221/general/schedule"
   }
  ],
  "procNote": "入学金の支払期限。入学手続の締切は3/17（水）",
  "note": "試験は午後。",
  "chk": "公式2027"
 },
 {
  "u": "meiji",
  "method": "全学部統一入試（英語4技能試験活用方式を含む）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-05",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "政治経済学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "情報コミュニケーション学部",
      ""
     ],
     [
      "国際日本学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-16"
  ],
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "meijiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2286/general/schedule"
   },
   "meijiPN"
  ],
  "resultNote": "前年度の合格発表は学部ごとに違う：法 2/13、商 2/13、政治経済 2/14、文 2/12、経営 2/17、情コミ 2/15、国際日本 2/16",
  "procNote": "前年度の手続締切：法 3/3、商 3/4、政治経済 3/4、文 3/3、経営 3/5、情コミ 3/5、国際日本 3/2",
  "chk": "前年度"
 },
 {
  "u": "meiji",
  "method": "学部別入試",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-14",
    "f": [
     [
      "法学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-26"
  ],
  "result": "2026-02-21",
  "proc": "2026-03-03",
  "subjects": null,
  "eiken": null,
  "src": [
   "meijiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2286/general/schedule"
   },
   "meijiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "meiji",
  "method": "学部別入試（英語4技能試験利用方式を含む）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-16",
    "f": [
     [
      "商学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-26"
  ],
  "result": "2026-02-24",
  "proc": "2026-03-04",
  "subjects": null,
  "eiken": null,
  "src": [
   "meijiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2286/general/schedule"
   },
   "meijiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "meiji",
  "method": "学部別入試",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-11",
    "f": [
     [
      "政治経済学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-22"
  ],
  "result": "2026-02-18",
  "proc": "2026-03-04",
  "subjects": null,
  "eiken": null,
  "src": [
   "meijiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2286/general/schedule"
   },
   "meijiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "meiji",
  "method": "学部別入試",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-13",
    "f": [
     [
      "文学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-26"
  ],
  "result": "2026-02-20",
  "proc": "2026-03-03",
  "subjects": null,
  "eiken": null,
  "src": [
   "meijiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2286/general/schedule"
   },
   "meijiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "meiji",
  "method": "学部別入試（共通テスト併用）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-10",
    "f": [
     [
      "経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-22"
  ],
  "result": "2026-02-17",
  "proc": "2026-03-05",
  "subjects": null,
  "eiken": null,
  "src": [
   "meijiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2286/general/schedule"
   },
   "meijiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "meiji",
  "method": "学部別入試",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-08",
    "f": [
     [
      "情報コミュニケーション学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-22"
  ],
  "result": "2026-02-15",
  "proc": "2026-03-05",
  "subjects": null,
  "eiken": null,
  "src": [
   "meijiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2286/general/schedule"
   },
   "meijiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "meiji",
  "method": "学部別入試（英語4技能・共通テスト併用を含む）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "国際日本学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-22"
  ],
  "result": "2026-02-16",
  "proc": "2026-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "meijiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2286/general/schedule"
   },
   "meijiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "全学部日程",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "教育人間科学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "国際政治経済学部",
      ""
     ],
     [
      "総合文化政策学部",
      ""
     ],
     [
      "社会情報学部",
      ""
     ],
     [
      "地球社会共生学部",
      ""
     ],
     [
      "コミュニティ人間科学部",
      ""
     ],
     [
      "統計データサイエンス学環",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-19"
  ],
  "result": "2026-02-14",
  "proc": "2026-02-24",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "note": "統計データサイエンス学環は前年度の日程がないため、出願・発表・手続は要項で確認してください。",
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-13",
    "f": [
     [
      "文学部",
      "英米文（D方式・A方式）、フランス文・日本文（B方式）"
     ]
    ],
    "tag": "学科・方式ごとに試験日が違う",
    "l2": "英米文（D・A方式）、フランス文・日本文（B方式）"
   },
   {
    "d": "2027-02-14",
    "f": [
     [
      "文学部",
      "英米文（B方式・C方式）、フランス文・日本文（A方式）、史、比較芸術"
     ]
    ],
    "tag": "学科・方式ごとに試験日が違う",
    "l2": "英米文（B・C方式）、フランス文・日本文（A方式）、史、比較芸術"
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-24",
  "proc": "2026-03-03",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "note": "A方式と一部の方式は大学入学共通テストを併用します（共通テストの受験が必要）。",
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（共通テスト併用）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-13",
    "f": [
     [
      "教育人間科学部",
      "教育・心理"
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-24",
  "proc": "2026-03-03",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（共通テスト併用 A方式・B方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "総合文化政策学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-17",
  "proc": "2026-02-25",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "resultNote": "A方式。前年度はB方式だけ別日程で、発表2/24",
  "procNote": "A方式。B方式は3/3（前年度）",
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（共通テスト併用）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-18",
    "f": [
     [
      "地球社会共生学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-26",
  "proc": "2026-03-05",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（A方式・B方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-17",
    "f": [
     [
      "国際政治経済学部",
      "国際政治・国際経済・国際コミュニケーション"
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-26",
  "proc": "2026-03-05",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "note": "A方式は大学入学共通テストを併用します。",
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（共通テスト併用 A方式・B方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-18",
    "f": [
     [
      "法学部",
      "法・ヒューマンライツ"
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-26",
  "proc": "2026-03-05",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（A方式・B方式・C方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-19",
    "f": [
     [
      "経済学部",
      "経済・現代経済デザイン"
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-27",
  "proc": "2026-03-05",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（共通テスト併用 A方式・B方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-15",
    "f": [
     [
      "経営学部",
      "経営・マーケティング"
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-24",
  "proc": "2026-03-03",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（共通テスト併用）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-11",
    "f": [
     [
      "コミュニティ人間科学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-17",
  "proc": "2026-02-25",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（A〜D方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "社会情報学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-21"
  ],
  "result": "2026-02-17",
  "proc": "2026-02-25",
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "note": "A方式は大学入学共通テストを併用します。",
  "chk": "前年度"
 },
 {
  "u": "aoyama",
  "method": "個別学部日程（共通テスト併用）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-13",
    "f": [
     [
      "統計データサイエンス学環",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "aoyamaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2200/general/schedule"
   },
   "aoyamaPN"
  ],
  "note": "前年度の日程がないため、出願・発表・手続は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "rikkyo",
  "method": "一般入試（試験日自由選択）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-06",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "異文化コミュニケーション学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "観光学部",
      ""
     ],
     [
      "コミュニティ福祉学部",
      ""
     ],
     [
      "現代心理学部",
      ""
     ],
     [
      "スポーツウエルネス学部",
      ""
     ],
     [
      "環境学部",
      "文系型"
     ]
    ],
    "tag": "5日から選べる・複数日受験可",
    "pick": "2/6・2/8・2/9・2/12・2/13から選べる。1試験日につき1学科で、試験日が違えば同じ学科も受けられる（最大5回。文学部は2/11と合わせて最大6回）",
    "l2": "文・異文化コミュ・経済・経営・社会・法・観光・コミュ福祉・現代心理・スポーツウエルネス・環境（文系型）"
   },
   {
    "d": "2027-02-08",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "異文化コミュニケーション学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "観光学部",
      ""
     ],
     [
      "コミュニティ福祉学部",
      ""
     ],
     [
      "現代心理学部",
      ""
     ],
     [
      "スポーツウエルネス学部",
      ""
     ],
     [
      "環境学部",
      "文系型"
     ]
    ],
    "tag": "5日から選べる・複数日受験可",
    "pick": "2/6・2/8・2/9・2/12・2/13から選べる。1試験日につき1学科で、試験日が違えば同じ学科も受けられる（最大5回。文学部は2/11と合わせて最大6回）",
    "l2": "文・異文化コミュ・経済・経営・社会・法・観光・コミュ福祉・現代心理・スポーツウエルネス・環境（文系型）"
   },
   {
    "d": "2027-02-09",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "異文化コミュニケーション学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "観光学部",
      ""
     ],
     [
      "コミュニティ福祉学部",
      ""
     ],
     [
      "現代心理学部",
      ""
     ],
     [
      "スポーツウエルネス学部",
      ""
     ],
     [
      "環境学部",
      "文系型"
     ]
    ],
    "tag": "5日から選べる・複数日受験可",
    "pick": "2/6・2/8・2/9・2/12・2/13から選べる。1試験日につき1学科で、試験日が違えば同じ学科も受けられる（最大5回。文学部は2/11と合わせて最大6回）",
    "l2": "文・異文化コミュ・経済・経営・社会・法・観光・コミュ福祉・現代心理・スポーツウエルネス・環境（文系型）"
   },
   {
    "d": "2027-02-12",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "異文化コミュニケーション学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "観光学部",
      ""
     ],
     [
      "コミュニティ福祉学部",
      ""
     ],
     [
      "現代心理学部",
      ""
     ],
     [
      "スポーツウエルネス学部",
      ""
     ],
     [
      "環境学部",
      "文系型"
     ]
    ],
    "tag": "5日から選べる・複数日受験可",
    "pick": "2/6・2/8・2/9・2/12・2/13から選べる。1試験日につき1学科で、試験日が違えば同じ学科も受けられる（最大5回。文学部は2/11と合わせて最大6回）",
    "l2": "文・異文化コミュ・経済・経営・社会・法・観光・コミュ福祉・現代心理・スポーツウエルネス・環境（文系型）"
   },
   {
    "d": "2027-02-13",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "異文化コミュニケーション学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "観光学部",
      ""
     ],
     [
      "コミュニティ福祉学部",
      ""
     ],
     [
      "現代心理学部",
      ""
     ],
     [
      "スポーツウエルネス学部",
      ""
     ],
     [
      "環境学部",
      "文系型"
     ]
    ],
    "tag": "5日から選べる・複数日受験可",
    "pick": "2/6・2/8・2/9・2/12・2/13から選べる。1試験日につき1学科で、試験日が違えば同じ学科も受けられる（最大5回。文学部は2/11と合わせて最大6回）",
    "l2": "文・異文化コミュ・経済・経営・社会・法・観光・コミュ福祉・現代心理・スポーツウエルネス・環境（文系型）"
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-20"
  ],
  "result": "2026-02-21",
  "proc": "2026-02-27",
  "subjects": null,
  "eiken": "英語は、英語資格・検定試験のスコアか共通テストの英語の得点を使う（大学発表）",
  "src": [
   "rikkyoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2290/general/schedule"
   },
   "rikkyoTopic",
   "rikkyoPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "rikkyo",
  "method": "文学部独自日程",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-11",
    "f": [
     [
      "文学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "rikkyoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2290/general/schedule"
   },
   "rikkyoTopic",
   "rikkyoPN"
  ],
  "note": "文学部だけの試験日です。出願・発表・手続は要項で確認してください（前年度は一般入試全体で出願締切1/20、発表2/21、手続締切2/27）。",
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "5学部共通選抜",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "総合政策学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-24"
  ],
  "result": "2026-02-20",
  "proc": "2026-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "note": "1回の試験で複数の学部の合否判定を受けられます（大学発表）。",
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "学部別選抜（一般方式・共通テスト併用方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-12",
    "f": [
     [
      "法学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-24"
  ],
  "result": "2026-02-24",
  "proc": "2026-03-03",
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "学部別選抜（一般方式・英語外部試験利用方式・共通テスト併用方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-14",
    "f": [
     [
      "経済学部",
      "Ⅰ"
     ]
    ],
    "tag": "Ⅰ・Ⅱで試験日が違う",
    "l2": "一般方式Ⅰ・英語外部試験利用方式Ⅰ・共通テスト併用方式Ⅰ"
   },
   {
    "d": "2027-02-15",
    "f": [
     [
      "経済学部",
      "Ⅱ"
     ]
    ],
    "tag": "Ⅰ・Ⅱで試験日が違う",
    "l2": "一般方式Ⅱ・英語外部試験利用方式Ⅱ・共通テスト併用方式Ⅱ"
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-24"
  ],
  "result": "2026-02-25",
  "proc": "2026-03-04",
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "note": "ⅠとⅡで対象の学科が違います。どちらで受けるかは要項で確認してください。",
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "学部別選抜 A（一般方式・英語外部試験利用方式・共通テスト併用方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-11",
    "f": [
     [
      "商学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-24"
  ],
  "result": "2026-02-22",
  "proc": "2026-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "note": "AとBで対象の学科が違います。要項で確認してください。",
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "学部別選抜 B（一般方式・英語外部試験利用方式・共通テスト併用方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-13",
    "f": [
     [
      "商学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-24"
  ],
  "result": "2026-02-24",
  "proc": "2026-03-03",
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "note": "AとBで対象の学科が違います。要項で確認してください。",
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "学部別選抜（一般方式・英語外部試験利用方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-10",
    "f": [
     [
      "文学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-24"
  ],
  "result": "2026-02-21",
  "proc": "2026-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "学部別選抜（一般方式・英語外部試験利用方式・共通テスト併用方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-16",
    "f": [
     [
      "総合政策学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-24"
  ],
  "result": "2026-02-26",
  "proc": "2026-03-05",
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "学部別選抜（一般方式・英語外部試験利用方式・共通テスト併用方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-10",
    "f": [
     [
      "国際経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-24"
  ],
  "result": "2026-02-19",
  "proc": "2026-02-27",
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "学部別選抜（一般方式・英語外部試験利用方式・共通テスト併用方式）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-11",
    "f": [
     [
      "国際情報学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-24"
  ],
  "result": "2026-02-22",
  "proc": "2026-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "chuo",
  "method": "学部別選抜（一般方式・英語外部試験利用方式・共通テスト併用方式）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-08",
    "f": [
     [
      "スポーツ情報学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "chuoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2242/general/schedule"
   },
   "chuoPN"
  ],
  "note": "前年度の日程がないため、出願・発表・手続は要項で確認してください。",
  "chk": "公式2027一部"
 },
 {
  "u": "hosei",
  "method": "T日程・英語外部試験利用",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-05",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "国際文化学部",
      ""
     ],
     [
      "人間環境学部",
      ""
     ],
     [
      "現代福祉学部",
      ""
     ],
     [
      "キャリアデザイン学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-07",
   "2026-01-16"
  ],
  "result": "2026-02-17",
  "proc": "2026-02-20",
  "subjects": null,
  "eiken": null,
  "src": [
   "hoseiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2279/general/schedule"
   },
   "hoseiPN"
  ],
  "note": "T日程（統一日程）と英語外部試験利用入試は同じ日です。",
  "chk": "前年度"
 },
 {
  "u": "hosei",
  "method": "A方式（個別日程）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "文学部",
      "哲・日本文・史"
     ],
     [
      "経営学部",
      "経営"
     ],
     [
      "人間環境学部",
      ""
     ],
     [
      "グローバル教養学部",
      ""
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "文（哲・日本文・史）、経営（経営）、人間環境、グローバル教養"
   }
  ],
  "apply": [
   "2026-01-07",
   "2026-01-23"
  ],
  "result": "2026-02-18",
  "proc": "2026-02-24",
  "subjects": null,
  "eiken": null,
  "src": [
   "hoseiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2279/general/schedule"
   },
   "hoseiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "hosei",
  "method": "A方式（個別日程）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-08",
    "f": [
     [
      "法学部",
      "国際政治"
     ],
     [
      "文学部",
      "英文・地理・心理"
     ],
     [
      "経営学部",
      "経営戦略・市場経営"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "法（国際政治）、文（英文・地理・心理）、経営（経営戦略・市場経営）"
   }
  ],
  "apply": [
   "2026-01-07",
   "2026-01-23"
  ],
  "result": "2026-02-18",
  "proc": "2026-02-24",
  "subjects": null,
  "eiken": null,
  "src": [
   "hoseiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2279/general/schedule"
   },
   "hoseiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "hosei",
  "method": "A方式（個別日程）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "経済学部",
      "国際経済・現代ビジネス"
     ],
     [
      "社会学部",
      "社会政策科学・メディア社会"
     ],
     [
      "現代福祉学部",
      ""
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "経済（国際経済・現代ビジネス）、社会（社会政策科学・メディア社会）、現代福祉"
   }
  ],
  "apply": [
   "2026-01-07",
   "2026-01-23"
  ],
  "result": "2026-02-19",
  "proc": "2026-02-25",
  "subjects": null,
  "eiken": null,
  "src": [
   "hoseiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2279/general/schedule"
   },
   "hoseiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "hosei",
  "method": "A方式（個別日程）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-12",
    "f": [
     [
      "経済学部",
      "経済"
     ],
     [
      "社会学部",
      "社会"
     ],
     [
      "スポーツ健康学部",
      ""
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "経済（経済）、社会（社会）、スポーツ健康"
   }
  ],
  "apply": [
   "2026-01-07",
   "2026-01-28"
  ],
  "result": "2026-02-19",
  "proc": "2026-02-25",
  "subjects": null,
  "eiken": null,
  "src": [
   "hoseiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2279/general/schedule"
   },
   "hoseiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "hosei",
  "method": "A方式（個別日程）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-16",
    "f": [
     [
      "法学部",
      "法律・政治"
     ],
     [
      "国際文化学部",
      ""
     ],
     [
      "キャリアデザイン学部",
      ""
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "法（法律・政治）、国際文化、キャリアデザイン"
   }
  ],
  "apply": [
   "2026-01-07",
   "2026-02-02"
  ],
  "result": "2026-02-26",
  "proc": "2026-03-03",
  "subjects": null,
  "eiken": null,
  "src": [
   "hoseiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2279/general/schedule"
   },
   "hoseiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "toyo",
  "method": "一般選抜 前期日程",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-08",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際観光学部",
      ""
     ],
     [
      "福祉社会デザイン学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ],
    "tag": "2/8〜2/11・学科により日が違う",
    "pick": "前期は2/8〜2/11。受けられる日と方式（3教科・4教科・英語重視など）は学科ごとに違う。複数の日を受けられる学科も多い（要項で確認）",
    "l2": "文・社会・国際観光・福祉社会デザイン・国際・法・経済・経営"
   },
   {
    "d": "2027-02-09",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際観光学部",
      ""
     ],
     [
      "福祉社会デザイン学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ],
    "tag": "2/8〜2/11・学科により日が違う",
    "pick": "前期は2/8〜2/11。受けられる日と方式（3教科・4教科・英語重視など）は学科ごとに違う。複数の日を受けられる学科も多い（要項で確認）",
    "l2": "文・社会・国際観光・福祉社会デザイン・国際・法・経済・経営"
   },
   {
    "d": "2027-02-10",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際観光学部",
      ""
     ],
     [
      "福祉社会デザイン学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ],
    "tag": "2/8〜2/11・学科により日が違う",
    "pick": "前期は2/8〜2/11。受けられる日と方式（3教科・4教科・英語重視など）は学科ごとに違う。複数の日を受けられる学科も多い（要項で確認）",
    "l2": "文・社会・国際観光・福祉社会デザイン・国際・法・経済・経営"
   },
   {
    "d": "2027-02-11",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際観光学部",
      ""
     ],
     [
      "福祉社会デザイン学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ],
    "tag": "2/8〜2/11・学科により日が違う",
    "pick": "前期は2/8〜2/11。受けられる日と方式（3教科・4教科・英語重視など）は学科ごとに違う。複数の日を受けられる学科も多い（要項で確認）",
    "l2": "文・社会・国際観光・福祉社会デザイン・国際・法・経済・経営"
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-29"
  ],
  "result": "2026-02-21",
  "proc": "2026-02-27",
  "subjects": null,
  "eiken": null,
  "src": [
   "toyoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2265/general/schedule"
   },
   "toyoPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "toyo",
  "method": "一般選抜 後期日程",
  "year": 2026,
  "slots": [
   {
    "d": "2027-03-05",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際観光学部",
      ""
     ],
     [
      "福祉社会デザイン学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-02-26"
  ],
  "result": "2026-03-14",
  "proc": "2026-03-23",
  "subjects": null,
  "eiken": null,
  "src": [
   "toyoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2265/general/schedule"
   },
   "toyoPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "komazawa",
  "method": "全学部統一日程",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-04",
    "f": [
     [
      "仏教学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "グローバル・メディア・スタディーズ学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-23"
  ],
  "result": "2026-02-12",
  "proc": "2026-02-26",
  "subjects": null,
  "eiken": null,
  "src": [
   "komazawaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2216/general/schedule"
   },
   "komazawaPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "komazawa",
  "method": "T方式（2月）・S方式",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-05",
    "f": [
     [
      "仏教学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "グローバル・メディア・スタディーズ学部",
      ""
     ]
    ],
    "tag": "2/5〜2/8・学科により日が違う",
    "pick": "T方式（2月）は学科ごとに試験日が決まっている（2/5〜2/8）。S方式も学部により2/5〜2/8。どの日に受けるかは要項で確認",
    "l2": "仏教・文・経済・法・経営・GMS"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "仏教学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "グローバル・メディア・スタディーズ学部",
      ""
     ]
    ],
    "tag": "2/5〜2/8・学科により日が違う",
    "pick": "T方式（2月）は学科ごとに試験日が決まっている（2/5〜2/8）。S方式も学部により2/5〜2/8。どの日に受けるかは要項で確認",
    "l2": "仏教・文・経済・法・経営・GMS"
   },
   {
    "d": "2027-02-07",
    "f": [
     [
      "仏教学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "グローバル・メディア・スタディーズ学部",
      ""
     ]
    ],
    "tag": "2/5〜2/8・学科により日が違う",
    "pick": "T方式（2月）は学科ごとに試験日が決まっている（2/5〜2/8）。S方式も学部により2/5〜2/8。どの日に受けるかは要項で確認",
    "l2": "仏教・文・経済・法・経営・GMS"
   },
   {
    "d": "2027-02-08",
    "f": [
     [
      "仏教学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "グローバル・メディア・スタディーズ学部",
      ""
     ]
    ],
    "tag": "2/5〜2/8・学科により日が違う",
    "pick": "T方式（2月）は学科ごとに試験日が決まっている（2/5〜2/8）。S方式も学部により2/5〜2/8。どの日に受けるかは要項で確認",
    "l2": "仏教・文・経済・法・経営・GMS"
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-23"
  ],
  "result": null,
  "proc": "2026-02-26",
  "subjects": null,
  "eiken": null,
  "src": [
   "komazawaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2216/general/schedule"
   },
   "komazawaPN"
  ],
  "resultNote": "前年度は学科により2/15〜2/18",
  "chk": "前年度"
 },
 {
  "u": "komazawa",
  "method": "T方式（3月）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-03-07",
    "f": [
     [
      "仏教学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "グローバル・メディア・スタディーズ学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-02-08",
   "2026-02-20"
  ],
  "result": "2026-03-13",
  "proc": "2026-03-17",
  "subjects": null,
  "eiken": null,
  "src": [
   "komazawaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2216/general/schedule"
   },
   "komazawaPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "nihon",
  "method": "N全学統一方式 第1期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "文理学部",
      "人文・社会系"
     ],
     [
      "商学部",
      ""
     ],
     [
      "芸術学部",
      ""
     ],
     [
      "危機管理学部",
      ""
     ],
     [
      "スポーツ科学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   null,
   "2027-01-22",
   "郵送必着"
  ],
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "nihonN",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2267/general/schedule"
   }
  ],
  "resultNote": "学部ごとに違う：法・経済・国際関係 2/17、文理 2/12、商・芸術 2/15、危機管理・スポーツ科 2/10",
  "chk": "公式2027一部"
 },
 {
  "u": "nihon",
  "method": "N全学統一方式 第2期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-03-04",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "文理学部",
      "人文・社会系"
     ],
     [
      "経済学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "芸術学部",
      ""
     ],
     [
      "危機管理学部",
      ""
     ],
     [
      "スポーツ科学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   null,
   "2027-02-25",
   "郵送必着"
  ],
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "nihonN",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2267/general/schedule"
   }
  ],
  "resultNote": "学部ごとに違う：法 3/16、文理・経済・国際関係 3/12、商・芸術・危機管理・スポーツ科 3/15",
  "chk": "公式2027一部"
 },
 {
  "u": "nihon",
  "method": "AN共通方式 第1期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "危機管理学部",
      ""
     ],
     [
      "スポーツ科学部",
      ""
     ]
    ],
    "tag": "2/3〜2/5から選択",
    "pick": "2/3〜2/5の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "法・経済・商・国際関係・危機管理・スポーツ科学"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "危機管理学部",
      ""
     ],
     [
      "スポーツ科学部",
      ""
     ]
    ],
    "tag": "2/3〜2/5から選択",
    "pick": "2/3〜2/5の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "法・経済・商・国際関係・危機管理・スポーツ科学"
   },
   {
    "d": "2027-02-05",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "危機管理学部",
      ""
     ],
     [
      "スポーツ科学部",
      ""
     ]
    ],
    "tag": "2/3〜2/5から選択",
    "pick": "2/3〜2/5の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "法・経済・商・国際関係・危機管理・スポーツ科学"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "nihonTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2267/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "nihon",
  "method": "AN共通方式 第2期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-20",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "nihonTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2267/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "nihon",
  "method": "A個別方式（人文社会）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "文理学部",
      "人文・社会系"
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "nihonTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2267/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "nihon",
  "method": "A個別方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-03-06",
    "f": [
     [
      "国際関係学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "nihonTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2267/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "senshu",
  "method": "全国入試",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "国際コミュニケーション学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "ネットワーク情報学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ],
    "tag": "2/1・2/2から選択",
    "pick": "2/1・2/2の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・国際コミュ・法・経済・経営・商・ネットワーク情報・人間科学"
   },
   {
    "d": "2027-02-02",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "国際コミュニケーション学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "ネットワーク情報学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ],
    "tag": "2/1・2/2から選択",
    "pick": "2/1・2/2の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・国際コミュ・法・経済・経営・商・ネットワーク情報・人間科学"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "senshuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2233/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "senshu",
  "method": "全学部統一入試",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "国際コミュニケーション学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "ネットワーク情報学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ],
    "tag": "2/9・2/12から選択",
    "pick": "2/9・2/12の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・国際コミュ・法・経済・経営・商・ネットワーク情報・人間科学"
   },
   {
    "d": "2027-02-12",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "国際コミュニケーション学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "ネットワーク情報学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ],
    "tag": "2/9・2/12から選択",
    "pick": "2/9・2/12の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・国際コミュ・法・経済・経営・商・ネットワーク情報・人間科学"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "senshuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2233/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "senshu",
  "method": "前期入試（A〜F方式）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-10",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "国際コミュニケーション学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "ネットワーク情報学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ],
    "tag": "学科・方式ごとに試験日が違う",
    "pick": "前期は学科と方式（3教科・選択重視・英語重視・国語重視など）ごとに2/10か2/13のどちらかに決まっている（要項で確認）",
    "l2": "文・国際コミュ・法・経済・経営・商・ネットワーク情報・人間科学"
   },
   {
    "d": "2027-02-13",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "国際コミュニケーション学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "ネットワーク情報学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ],
    "tag": "学科・方式ごとに試験日が違う",
    "pick": "前期は学科と方式（3教科・選択重視・英語重視・国語重視など）ごとに2/10か2/13のどちらかに決まっている（要項で確認）",
    "l2": "文・国際コミュ・法・経済・経営・商・ネットワーク情報・人間科学"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "senshuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2233/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "senshu",
  "method": "後期入試",
  "year": 2027,
  "slots": [
   {
    "d": "2027-03-03",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "国際コミュニケーション学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "ネットワーク情報学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "senshuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2233/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "seikei",
  "method": "E方式（2教科全学部統一）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "国際共創学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-20"
  ],
  "result": "2026-02-09",
  "proc": "2026-02-26",
  "subjects": null,
  "eiken": null,
  "src": [
   "seikeiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2228/general/schedule"
   },
   "seikeiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "seikei",
  "method": "A方式（3教科学部個別）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-12",
    "f": [
     [
      "文学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-26"
  ],
  "result": "2026-02-19",
  "proc": "2026-02-27",
  "subjects": null,
  "eiken": null,
  "src": [
   "seikeiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2228/general/schedule"
   },
   "seikeiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "seikei",
  "method": "A方式（3教科学部個別）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-13",
    "f": [
     [
      "国際共創学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-26"
  ],
  "result": "2026-02-20",
  "proc": "2026-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "seikeiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2228/general/schedule"
   },
   "seikeiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "seikei",
  "method": "A方式（3教科学部個別）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-14",
    "f": [
     [
      "法学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-26"
  ],
  "result": "2026-02-20",
  "proc": "2026-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "seikeiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2228/general/schedule"
   },
   "seikeiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "seikei",
  "method": "A方式（3教科学部個別）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-13",
    "f": [
     [
      "経済学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-26"
  ],
  "result": "2026-02-20",
  "proc": "2026-03-02",
  "subjects": null,
  "eiken": null,
  "src": [
   "seikeiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2228/general/schedule"
   },
   "seikeiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "seikei",
  "method": "A方式（3教科学部個別）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-11",
    "f": [
     [
      "経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-05",
   "2026-01-26"
  ],
  "result": "2026-02-19",
  "proc": "2026-02-27",
  "subjects": null,
  "eiken": null,
  "src": [
   "seikeiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2228/general/schedule"
   },
   "seikeiPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "seijo",
  "method": "全学部統一選抜",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-02",
    "f": [
     [
      "文芸学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "社会イノベーション学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "seijoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2229/general/schedule"
   }
  ],
  "note": "経済学部は英語外部検定試験を使う方式もあります。出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "seijo",
  "method": "学部別選抜（3教科型・2教科型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "文芸学部",
      ""
     ]
    ],
    "tag": "2/3〜2/6・学科により日が違う",
    "pick": "3教科型は英文・芸術・文化史・マスコミュニケーション・ヨーロッパ文化が2/3〜2/6から選べる、国文は2/5。2教科型は2/5"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "文芸学部",
      ""
     ]
    ],
    "tag": "2/3〜2/6・学科により日が違う",
    "pick": "3教科型は英文・芸術・文化史・マスコミュニケーション・ヨーロッパ文化が2/3〜2/6から選べる、国文は2/5。2教科型は2/5"
   },
   {
    "d": "2027-02-05",
    "f": [
     [
      "文芸学部",
      ""
     ]
    ],
    "tag": "2/3〜2/6・学科により日が違う",
    "pick": "3教科型は英文・芸術・文化史・マスコミュニケーション・ヨーロッパ文化が2/3〜2/6から選べる、国文は2/5。2教科型は2/5"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "文芸学部",
      ""
     ]
    ],
    "tag": "2/3〜2/6・学科により日が違う",
    "pick": "3教科型は英文・芸術・文化史・マスコミュニケーション・ヨーロッパ文化が2/3〜2/6から選べる、国文は2/5。2教科型は2/5"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "seijoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2229/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "seijo",
  "method": "学部別選抜（3教科型・2教科型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "社会イノベーション学部",
      ""
     ]
    ],
    "tag": "2/3・2/4から選択",
    "pick": "3教科型は2/3・2/4から選べる。2教科型は2/4"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "社会イノベーション学部",
      ""
     ]
    ],
    "tag": "2/3・2/4から選択",
    "pick": "3教科型は2/3・2/4から選べる。2教科型は2/4"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "seijoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2229/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "seijo",
  "method": "学部別選抜（3教科型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "法学部",
      ""
     ]
    ],
    "tag": "2/3〜2/6から選択",
    "pick": "2/3〜2/6の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "法学部",
      ""
     ]
    ],
    "tag": "2/3〜2/6から選択",
    "pick": "2/3〜2/6の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認"
   },
   {
    "d": "2027-02-05",
    "f": [
     [
      "法学部",
      ""
     ]
    ],
    "tag": "2/3〜2/6から選択",
    "pick": "2/3〜2/6の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "法学部",
      ""
     ]
    ],
    "tag": "2/3〜2/6から選択",
    "pick": "2/3〜2/6の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "seijoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2229/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "seijo",
  "method": "学部別選抜（3教科型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "経済学部",
      ""
     ]
    ],
    "tag": "2/3・2/4・2/6から選択",
    "pick": "2/3・2/4・2/6の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "経済学部",
      ""
     ]
    ],
    "tag": "2/3・2/4・2/6から選択",
    "pick": "2/3・2/4・2/6の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "経済学部",
      ""
     ]
    ],
    "tag": "2/3・2/4・2/6から選択",
    "pick": "2/3・2/4・2/6の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "seijoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2229/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "meigaku",
  "method": "全学部日程（3教科型・英語外部検定試験利用型）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "文学部",
      "英文・フランス文"
     ],
     [
      "心理学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-20"
  ],
  "result": "2026-02-17",
  "proc": "2026-02-26",
  "subjects": null,
  "eiken": null,
  "src": [
   "meigakuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2287/general/schedule"
   },
   "meigakuPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "meigaku",
  "method": "A日程（3教科型）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "心理学部",
      "教育発達"
     ],
     [
      "社会学部",
      "社会"
     ],
     [
      "国際学部",
      "国際キャリア"
     ],
     [
      "法学部",
      "法律"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "心理（教育発達）、社会（社会）、国際（国際キャリア）、法（法律）"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "文学部",
      "英文"
     ],
     [
      "社会学部",
      "社会福祉"
     ],
     [
      "法学部",
      "消費情報環境法"
     ],
     [
      "経済学部",
      "国際経営"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "文（英文）、社会（社会福祉）、法（消費情報環境法）、経済（国際経営）"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "文学部",
      "芸術"
     ],
     [
      "国際学部",
      "国際"
     ],
     [
      "法学部",
      "政治"
     ],
     [
      "経済学部",
      "経済"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "文（芸術）、国際（国際）、法（政治）、経済（経済）"
   },
   {
    "d": "2027-02-07",
    "f": [
     [
      "文学部",
      "フランス文"
     ],
     [
      "心理学部",
      "心理"
     ],
     [
      "法学部",
      "グローバル法"
     ],
     [
      "経済学部",
      "経営"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "文（フランス文）、心理（心理）、法（グローバル法）、経済（経営）"
   }
  ],
  "apply": [
   "2026-01-06",
   "2026-01-20"
  ],
  "result": null,
  "proc": "2026-02-26",
  "subjects": null,
  "eiken": null,
  "src": [
   "meigakuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2287/general/schedule"
   },
   "meigakuPN"
  ],
  "resultNote": "前年度は学科により2/18または2/19",
  "chk": "前年度"
 },
 {
  "u": "meigaku",
  "method": "B日程",
  "year": 2026,
  "slots": [
   {
    "d": "2027-03-02",
    "f": [
     [
      "社会学部",
      "社会福祉"
     ],
     [
      "法学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-02-09",
   "2026-02-19"
  ],
  "result": "2026-03-14",
  "proc": "2026-03-18",
  "subjects": null,
  "eiken": null,
  "src": [
   "meigakuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2287/general/schedule"
   },
   "meigakuPN"
  ],
  "chk": "前年度"
 },
 {
  "u": "daito",
  "method": "全学部統一前期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "スポーツ・健康科学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "daitoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2235/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "daito",
  "method": "一般選抜（3教科）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-05",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "スポーツ・健康科学部",
      ""
     ]
    ],
    "tag": "2/5〜2/8から選択",
    "pick": "2/5〜2/8の試験日自由選択（Kei-Net表記。書道学科は2/5・2/6）。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・国際関係・法・経済・経営・スポーツ健康"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "スポーツ・健康科学部",
      ""
     ]
    ],
    "tag": "2/5〜2/8から選択",
    "pick": "2/5〜2/8の試験日自由選択（Kei-Net表記。書道学科は2/5・2/6）。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・国際関係・法・経済・経営・スポーツ健康"
   },
   {
    "d": "2027-02-07",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "スポーツ・健康科学部",
      ""
     ]
    ],
    "tag": "2/5〜2/8から選択",
    "pick": "2/5〜2/8の試験日自由選択（Kei-Net表記。書道学科は2/5・2/6）。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・国際関係・法・経済・経営・スポーツ健康"
   },
   {
    "d": "2027-02-08",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "スポーツ・健康科学部",
      ""
     ]
    ],
    "tag": "2/5〜2/8から選択",
    "pick": "2/5〜2/8の試験日自由選択（Kei-Net表記。書道学科は2/5・2/6）。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・国際関係・法・経済・経営・スポーツ健康"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "daitoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2235/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "daito",
  "method": "全学部統一後期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-27",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "スポーツ・健康科学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "daitoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2235/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "tokai",
  "method": "文系学部統一選抜（前期）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-02",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "文化社会学部",
      ""
     ],
     [
      "政治経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "観光学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-04",
   "2027-01-20",
   "Web登録 1/20 23:59まで、書類は1/22必着"
  ],
  "result": "2027-02-09",
  "proc": "2027-02-18",
  "subjects": null,
  "eiken": "英検などを英語のみなし得点に換算でき、大学の英語の得点と高いほうを採用（当日の英語は受験が必要）。換算点は要項で確認",
  "src": [
   "tokaiYoko",
   "tokaiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2245/general/schedule"
   }
  ],
  "chk": "公式2027",
  "procNote": "2/18 17:00まで（特待生に選ばれた人は2/27まで）"
 },
 {
  "u": "tokai",
  "method": "一般選抜（3教科型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "文化社会学部",
      ""
     ],
     [
      "政治経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "観光学部",
      ""
     ],
     [
      "児童教育学部",
      ""
     ]
    ],
    "tag": "2/7〜2/10・試験日自由選択",
    "pick": "2/7〜2/10の試験日自由選択（公式要項）。同じ学科を複数日受けたときは、3科目の合計が最も高い日の結果で判定",
    "l2": "文・文化社会・政治経済・法・国際・観光・児童教育"
   },
   {
    "d": "2027-02-08",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "文化社会学部",
      ""
     ],
     [
      "政治経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "観光学部",
      ""
     ],
     [
      "児童教育学部",
      ""
     ]
    ],
    "tag": "2/7〜2/10・試験日自由選択",
    "pick": "2/7〜2/10の試験日自由選択（公式要項）。同じ学科を複数日受けたときは、3科目の合計が最も高い日の結果で判定",
    "l2": "文・文化社会・政治経済・法・国際・観光・児童教育"
   },
   {
    "d": "2027-02-09",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "文化社会学部",
      ""
     ],
     [
      "政治経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "観光学部",
      ""
     ],
     [
      "児童教育学部",
      ""
     ]
    ],
    "tag": "2/7〜2/10・試験日自由選択",
    "pick": "2/7〜2/10の試験日自由選択（公式要項）。同じ学科を複数日受けたときは、3科目の合計が最も高い日の結果で判定",
    "l2": "文・文化社会・政治経済・法・国際・観光・児童教育"
   },
   {
    "d": "2027-02-10",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "文化社会学部",
      ""
     ],
     [
      "政治経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "観光学部",
      ""
     ],
     [
      "児童教育学部",
      ""
     ]
    ],
    "tag": "2/7〜2/10・試験日自由選択",
    "pick": "2/7〜2/10の試験日自由選択（公式要項）。同じ学科を複数日受けたときは、3科目の合計が最も高い日の結果で判定",
    "l2": "文・文化社会・政治経済・法・国際・観光・児童教育"
   }
  ],
  "apply": [
   "2027-01-04",
   "2027-01-22",
   "Web登録 1/22 23:59まで、書類は1/25必着"
  ],
  "result": "2027-02-18",
  "proc": "2027-02-27",
  "subjects": null,
  "eiken": "英検などを英語のみなし得点に換算でき、大学の英語の得点と高いほうを採用（当日の英語は受験が必要）。換算点は要項で確認",
  "src": [
   "tokaiYoko",
   "tokaiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2245/general/schedule"
   }
  ],
  "chk": "公式2027",
  "procNote": "2/27 17:00まで"
 },
 {
  "u": "tokai",
  "method": "文系学部統一選抜（後期）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-28",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "文化社会学部",
      ""
     ],
     [
      "政治経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "観光学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-02-01",
   "2027-02-14",
   "Web登録 2/14 23:59まで、書類は2/16必着"
  ],
  "result": "2027-03-06",
  "proc": "2027-03-10",
  "subjects": null,
  "eiken": "英検などを英語のみなし得点に換算でき、大学の英語の得点と高いほうを採用（当日の英語は受験が必要）。換算点は要項で確認",
  "src": [
   "tokaiYoko",
   "tokaiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2245/general/schedule"
   }
  ],
  "chk": "公式2027",
  "procNote": "3/10 17:00まで"
 },
 {
  "u": "asia",
  "method": "全学統一前期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-02",
    "f": [
     [
      "経営学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "健康スポーツ科学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "asiaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2199/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "asia",
  "method": "一般選抜（3教科型・2教科型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "社会学部",
      "現代社会"
     ],
     [
      "経営学部",
      "ホスピタリティ・データサイエンス"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "社会（現代社会）、経営（ホスピタリティ・データサイエンス）"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "国際関係学部",
      "国際関係"
     ],
     [
      "法学部",
      "法律"
     ],
     [
      "経営学部",
      "経営"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "国際関係（国際関係）、法（法律）、経営（経営）"
   },
   {
    "d": "2027-02-05",
    "f": [
     [
      "国際関係学部",
      "多文化コミュニケーション"
     ],
     [
      "経済学部",
      "経済"
     ],
     [
      "健康スポーツ科学部",
      ""
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "国際関係（多文化）、経済、健康スポーツ科学"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "asiaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2199/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "asia",
  "method": "全学統一中期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-18",
    "f": [
     [
      "経営学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "健康スポーツ科学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "asiaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2199/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "asia",
  "method": "全学統一後期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-28",
    "f": [
     [
      "経営学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "健康スポーツ科学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "asiaTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2199/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "teikyo",
  "method": "一般選抜 Ⅰ期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-01-30",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "教育学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ]
    ],
    "tag": "1/30〜2/1から選択",
    "pick": "1/30〜2/1の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・教育・外国語・法・経済"
   },
   {
    "d": "2027-01-31",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "教育学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ]
    ],
    "tag": "1/30〜2/1から選択",
    "pick": "1/30〜2/1の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・教育・外国語・法・経済"
   },
   {
    "d": "2027-02-01",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "教育学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ]
    ],
    "tag": "1/30〜2/1から選択",
    "pick": "1/30〜2/1の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・教育・外国語・法・経済"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "teikyoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2244/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "teikyo",
  "method": "一般選抜 Ⅱ期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-20",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "教育学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ]
    ],
    "tag": "2/20・2/21から選択",
    "pick": "2/20・2/21の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・教育・外国語・法・経済"
   },
   {
    "d": "2027-02-21",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "教育学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ]
    ],
    "tag": "2/20・2/21から選択",
    "pick": "2/20・2/21の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・教育・外国語・法・経済"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "teikyoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2244/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "teikyo",
  "method": "一般選抜 Ⅲ期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-03-07",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "教育学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "teikyoTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2244/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "kokushikan",
  "method": "一般選抜 前期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "21世紀アジア学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政経学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ],
    "tag": "2/1・2/2から選択",
    "pick": "2/1・2/2の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・21世紀アジア・法・政経・経営"
   },
   {
    "d": "2027-02-02",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "21世紀アジア学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政経学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ],
    "tag": "2/1・2/2から選択",
    "pick": "2/1・2/2の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・21世紀アジア・法・政経・経営"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "kokushikanTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2215/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "kokushikan",
  "method": "デリバリー選抜",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "21世紀アジア学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政経学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "kokushikanTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2215/general/schedule"
   }
  ],
  "note": "方式の名前はKei-Netの表記です。内容は要項で確認してください。出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "kokushikan",
  "method": "一般選抜 中期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-20",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "21世紀アジア学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政経学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "kokushikanTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2215/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "kokushikan",
  "method": "一般選抜 後期",
  "year": 2027,
  "slots": [
   {
    "d": "2027-03-02",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "21世紀アジア学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政経学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "kokushikanTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2215/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "tus",
  "method": "B方式",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-02",
    "f": [
     [
      "経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-07",
   "2026-01-22"
  ],
  "result": "2026-02-19",
  "proc": "2026-02-25",
  "subjects": null,
  "eiken": null,
  "src": [
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2262/general/schedule"
   },
   "tus"
  ],
  "procNote": "1次手続の期間は2/19〜2/25（前年度）",
  "chk": "前年度"
 },
 {
  "u": "doshisha",
  "method": "全学部日程（文系）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-05",
    "f": [
     [
      "神学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "政策学部",
      ""
     ],
     [
      "文化情報学部",
      ""
     ],
     [
      "スポーツ健康科学部",
      ""
     ],
     [
      "心理学部",
      ""
     ],
     [
      "グローバル・コミュニケーション学部",
      "中国語コース"
     ],
     [
      "グローバル地域文化学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-21",
   "2027-01-07",
   "締切日消印有効"
  ],
  "result": "2027-02-15",
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "doshisha",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2498/general/schedule"
   }
  ],
  "chk": "公式2027一部"
 },
 {
  "u": "doshisha",
  "method": "学部個別日程",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-06",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "経済学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-21",
   "2027-01-07",
   "締切日消印有効"
  ],
  "result": "2027-02-15",
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "doshisha",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2498/general/schedule"
   }
  ],
  "chk": "公式2027一部"
 },
 {
  "u": "doshisha",
  "method": "学部個別日程",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "政策学部",
      ""
     ],
     [
      "文化情報学部",
      "文系型"
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-21",
   "2027-01-07",
   "締切日消印有効"
  ],
  "result": "2027-02-16",
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "doshisha",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2498/general/schedule"
   }
  ],
  "chk": "公式2027一部"
 },
 {
  "u": "doshisha",
  "method": "学部個別日程",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-08",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "グローバル・コミュニケーション学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-21",
   "2027-01-07",
   "締切日消印有効"
  ],
  "result": "2027-02-17",
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "doshisha",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2498/general/schedule"
   }
  ],
  "chk": "公式2027一部"
 },
 {
  "u": "doshisha",
  "method": "学部個別日程",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "神学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "心理学部",
      ""
     ],
     [
      "グローバル地域文化学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-21",
   "2027-01-07",
   "締切日消印有効"
  ],
  "result": "2027-02-18",
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "doshisha",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2498/general/schedule"
   }
  ],
  "chk": "公式2027一部"
 },
 {
  "u": "doshisha",
  "method": "学部個別日程",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-10",
    "f": [
     [
      "社会学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-21",
   "2027-01-07",
   "締切日消印有効"
  ],
  "result": "2027-02-19",
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "doshisha",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2498/general/schedule"
   }
  ],
  "chk": "公式2027一部"
 },
 {
  "u": "doshisha",
  "method": "学部個別日程（文系型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "スポーツ健康科学部",
      "文系型"
     ]
    ]
   }
  ],
  "apply": [
   "2026-12-21",
   "2027-01-07",
   "締切日消印有効"
  ],
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "doshisha",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2498/general/schedule"
   }
  ],
  "note": "合格発表日は要項で確認してください。",
  "chk": "公式2027一部"
 },
 {
  "u": "ritsumei",
  "method": "全学統一方式（文系）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "産業社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "デザイン・アート学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "政策科学部",
      ""
     ],
     [
      "総合心理学部",
      ""
     ],
     [
      "映像学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "スポーツ健康科学部",
      ""
     ],
     [
      "食マネジメント学部",
      ""
     ]
    ],
    "tag": "2/1〜2/4から選択",
    "pick": "2/1〜2/4の試験日自由選択。何日受けられるかは要項で確認",
    "l2": "法・産社・国関・文・デザインアート・経営・政策・心理・映像・経済・スポ健・食マネ"
   },
   {
    "d": "2027-02-02",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "産業社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "デザイン・アート学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "政策科学部",
      ""
     ],
     [
      "総合心理学部",
      ""
     ],
     [
      "映像学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "スポーツ健康科学部",
      ""
     ],
     [
      "食マネジメント学部",
      ""
     ]
    ],
    "tag": "2/1〜2/4から選択",
    "pick": "2/1〜2/4の試験日自由選択。何日受けられるかは要項で確認",
    "l2": "法・産社・国関・文・デザインアート・経営・政策・心理・映像・経済・スポ健・食マネ"
   },
   {
    "d": "2027-02-03",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "産業社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "デザイン・アート学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "政策科学部",
      ""
     ],
     [
      "総合心理学部",
      ""
     ],
     [
      "映像学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "スポーツ健康科学部",
      ""
     ],
     [
      "食マネジメント学部",
      ""
     ]
    ],
    "tag": "2/1〜2/4から選択",
    "pick": "2/1〜2/4の試験日自由選択。何日受けられるかは要項で確認",
    "l2": "法・産社・国関・文・デザインアート・経営・政策・心理・映像・経済・スポ健・食マネ"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "産業社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "文学部",
      ""
     ],
     [
      "デザイン・アート学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "政策科学部",
      ""
     ],
     [
      "総合心理学部",
      ""
     ],
     [
      "映像学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "スポーツ健康科学部",
      ""
     ],
     [
      "食マネジメント学部",
      ""
     ]
    ],
    "tag": "2/1〜2/4から選択",
    "pick": "2/1〜2/4の試験日自由選択。何日受けられるかは要項で確認",
    "l2": "法・産社・国関・文・デザインアート・経営・政策・心理・映像・経済・スポ健・食マネ"
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-22",
   "1/22 23:00まで"
  ],
  "result": "2027-02-16",
  "proc": "2027-03-01",
  "subjects": null,
  "eiken": null,
  "src": [
   "ritsumei",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2504/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "ritsumei",
  "method": "学部個別配点方式（文系）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "総合心理学部",
      ""
     ],
     [
      "産業社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政策科学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "食マネジメント学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-26",
   "1/26 23:00まで"
  ],
  "result": "2027-02-17",
  "proc": "2027-03-01",
  "subjects": null,
  "eiken": null,
  "src": [
   "ritsumei",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2504/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "ritsumei",
  "method": "共通テスト併用方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-08",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "総合心理学部",
      ""
     ],
     [
      "産業社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政策科学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "食マネジメント学部",
      ""
     ]
    ],
    "tag": "2/8・2/9から選択",
    "pick": "2/8・2/9の試験日自由選択（Kei-Net表記）。大学入学共通テストの受験が必要。何日受けられるかは要項で確認",
    "l2": "文・心理・産社・国関・法・政策・経済・経営・食マネ"
   },
   {
    "d": "2027-02-09",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "総合心理学部",
      ""
     ],
     [
      "産業社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政策科学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "食マネジメント学部",
      ""
     ]
    ],
    "tag": "2/8・2/9から選択",
    "pick": "2/8・2/9の試験日自由選択（Kei-Net表記）。大学入学共通テストの受験が必要。何日受けられるかは要項で確認",
    "l2": "文・心理・産社・国関・法・政策・経済・経営・食マネ"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "ritsumei",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2504/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "公式2027一部"
 },
 {
  "u": "ritsumei",
  "method": "IR方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-09",
    "f": [
     [
      "国際関係学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "ritsumei",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2504/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "公式2027一部"
 },
 {
  "u": "ritsumei",
  "method": "後期分割方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-03-07",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "総合心理学部",
      ""
     ],
     [
      "産業社会学部",
      ""
     ],
     [
      "国際関係学部",
      ""
     ],
     [
      "政策科学部",
      ""
     ],
     [
      "経営学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2027-02-12",
   "2027-02-26",
   "2/26 23:00まで"
  ],
  "result": "2027-03-17",
  "proc": "2027-03-24",
  "subjects": null,
  "eiken": null,
  "src": [
   "ritsumei",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2504/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "kansai",
  "method": "全学日程（3教科型・2教科型・英語外部試験利用など）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "社会安全学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政策創造学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "人間健康学部",
      ""
     ]
    ],
    "tag": "2/1〜2/7・方式で選べる日が違う",
    "pick": "3教科型は2/1〜2/3と2/5〜2/7から選べる（試験日自由選択）。英語外部試験利用は2/1〜2/3、同一配点方式は2/5〜2/7。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・社会安全・法・政策創造・経済・商・人間健康"
   },
   {
    "d": "2027-02-02",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "社会安全学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政策創造学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "人間健康学部",
      ""
     ]
    ],
    "tag": "2/1〜2/7・方式で選べる日が違う",
    "pick": "3教科型は2/1〜2/3と2/5〜2/7から選べる（試験日自由選択）。英語外部試験利用は2/1〜2/3、同一配点方式は2/5〜2/7。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・社会安全・法・政策創造・経済・商・人間健康"
   },
   {
    "d": "2027-02-03",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "社会安全学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政策創造学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "人間健康学部",
      ""
     ]
    ],
    "tag": "2/1〜2/7・方式で選べる日が違う",
    "pick": "3教科型は2/1〜2/3と2/5〜2/7から選べる（試験日自由選択）。英語外部試験利用は2/1〜2/3、同一配点方式は2/5〜2/7。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・社会安全・法・政策創造・経済・商・人間健康"
   },
   {
    "d": "2027-02-05",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "社会安全学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政策創造学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "人間健康学部",
      ""
     ]
    ],
    "tag": "2/1〜2/7・方式で選べる日が違う",
    "pick": "3教科型は2/1〜2/3と2/5〜2/7から選べる（試験日自由選択）。英語外部試験利用は2/1〜2/3、同一配点方式は2/5〜2/7。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・社会安全・法・政策創造・経済・商・人間健康"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "社会安全学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政策創造学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "人間健康学部",
      ""
     ]
    ],
    "tag": "2/1〜2/7・方式で選べる日が違う",
    "pick": "3教科型は2/1〜2/3と2/5〜2/7から選べる（試験日自由選択）。英語外部試験利用は2/1〜2/3、同一配点方式は2/5〜2/7。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・社会安全・法・政策創造・経済・商・人間健康"
   },
   {
    "d": "2027-02-07",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "社会安全学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "政策創造学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ],
     [
      "人間健康学部",
      ""
     ]
    ],
    "tag": "2/1〜2/7・方式で選べる日が違う",
    "pick": "3教科型は2/1〜2/3と2/5〜2/7から選べる（試験日自由選択）。英語外部試験利用は2/1〜2/3、同一配点方式は2/5〜2/7。何日受けられるかは要項で確認",
    "l2": "文・外国語・社会・社会安全・法・政策創造・経済・商・人間健康"
   }
  ],
  "apply": [
   "2027-01-07",
   "2027-01-19",
   "Web登録 1/19 23:00まで"
  ],
  "result": "2027-02-16",
  "proc": "2027-02-24",
  "subjects": null,
  "eiken": null,
  "src": [
   "kansaiKN",
   "kansaiTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2533/general/schedule"
   }
  ],
  "procNote": "入学金 2/24 13:00まで、授業料等 3/24 13:00まで",
  "chk": "非公式2027"
 },
 {
  "u": "kangaku",
  "method": "全学部日程",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "教育学部",
      ""
     ],
     [
      "神学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "人間福祉学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "総合政策学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ]
    ],
    "tag": "2/1・2/2から選択",
    "pick": "2/1・2/2の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・教育・神・社会・人間福祉・国際・法・総合政策・経済・商"
   },
   {
    "d": "2027-02-02",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "教育学部",
      ""
     ],
     [
      "神学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "人間福祉学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "総合政策学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ]
    ],
    "tag": "2/1・2/2から選択",
    "pick": "2/1・2/2の試験日自由選択（Kei-Net表記）。何日受けられるかは要項で確認",
    "l2": "文・教育・神・社会・人間福祉・国際・法・総合政策・経済・商"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "kangakuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2558/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "kangaku",
  "method": "学部個別日程（傾斜配点型・均等配点型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "神学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "人間福祉学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "総合政策学部",
      ""
     ],
     [
      "商学部",
      ""
     ]
    ],
    "tag": "学部・配点型で日が違う",
    "l2": "傾斜配点型：文・神・社会・人間福祉・法・総合政策・商"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "教育学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "国際学部",
      ""
     ]
    ],
    "tag": "学部・配点型で日が違う",
    "l2": "傾斜配点型：教育・経済・国際"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "文学部",
      ""
     ],
     [
      "人間福祉学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "総合政策学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ]
    ],
    "tag": "学部・配点型で日が違う",
    "l2": "均等配点型：文・人間福祉・法・総合政策・経済・商"
   },
   {
    "d": "2027-02-07",
    "f": [
     [
      "教育学部",
      ""
     ],
     [
      "神学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "国際学部",
      ""
     ]
    ],
    "tag": "学部・配点型で日が違う",
    "l2": "均等配点型：教育・神・社会・国際"
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "kangakuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2558/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "kangaku",
  "method": "英数日程",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-05",
    "f": [
     [
      "教育学部",
      ""
     ],
     [
      "社会学部",
      ""
     ],
     [
      "人間福祉学部",
      ""
     ],
     [
      "国際学部",
      ""
     ],
     [
      "法学部",
      ""
     ],
     [
      "総合政策学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "商学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   "kangakuTop",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2558/general/schedule"
   }
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "kanagawa",
  "method": "全学統一型（文系）",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-04",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "国際日本学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-01-07",
   "2026-01-16",
   "消印有効"
  ],
  "result": "2026-02-18",
  "proc": "2026-03-06",
  "subjects": null,
  "eiken": null,
  "src": [
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2306/general/schedule"
   },
   "kanagawa"
  ],
  "chk": "前年度"
 },
 {
  "u": "kanagawa",
  "method": "前期 3科目型",
  "year": 2026,
  "slots": [
   {
    "d": "2027-02-06",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "国際日本学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ],
    "tag": "2/6〜2/8・受け方は要項で確認",
    "pick": "3日間の3科目型はまとめて合否を判定（2026年度要項）。何日受けられるかは要項で確認",
    "l2": "法・経済・経営・外国語・国際日本・人間科学"
   },
   {
    "d": "2027-02-07",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "国際日本学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ],
    "tag": "2/6〜2/8・受け方は要項で確認",
    "pick": "3日間の3科目型はまとめて合否を判定（2026年度要項）。何日受けられるかは要項で確認",
    "l2": "法・経済・経営・外国語・国際日本・人間科学"
   },
   {
    "d": "2027-02-08",
    "f": [
     [
      "法学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "経営学部",
      ""
     ],
     [
      "外国語学部",
      ""
     ],
     [
      "国際日本学部",
      ""
     ],
     [
      "人間科学部",
      ""
     ]
    ],
    "tag": "2/6〜2/8・受け方は要項で確認",
    "pick": "3日間の3科目型はまとめて合否を判定（2026年度要項）。何日受けられるかは要項で確認",
    "l2": "法・経済・経営・外国語・国際日本・人間科学"
   }
  ],
  "apply": [
   "2026-01-07",
   "2026-01-16",
   "消印有効"
  ],
  "result": "2026-02-18",
  "proc": "2026-03-06",
  "subjects": null,
  "eiken": null,
  "src": [
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2306/general/schedule"
   },
   "kanagawa"
  ],
  "chk": "前年度"
 },
 {
  "u": "kanagawa",
  "method": "得意科目型",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-07",
    "f": [
     [
      "法学部",
      ""
     ]
    ]
   }
  ],
  "apply": null,
  "result": null,
  "proc": null,
  "subjects": null,
  "eiken": null,
  "src": [
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2306/general/schedule"
   },
   "kanagawa"
  ],
  "note": "出願期間・合格発表・手続締切は要項で確認してください。",
  "chk": "試験日のみ"
 },
 {
  "u": "kanagawa",
  "method": "後期 2科目型",
  "year": 2026,
  "slots": [
   {
    "d": "2027-03-04",
    "f": [
     [
      "法学部",
      ""
     ]
    ]
   }
  ],
  "apply": [
   "2026-02-13",
   "2026-02-20",
   "消印有効"
  ],
  "result": "2026-03-12",
  "proc": "2026-03-18",
  "subjects": null,
  "eiken": null,
  "src": [
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2306/general/schedule"
   },
   "kanagawa"
  ],
  "note": "前年度の後期の日付です。2027年度に後期を行う学部はKei-Net上では法学部です。",
  "chk": "前年度"
 },
 {
  "u": "jwu",
  "method": "個別選抜型（3科目型・2科目型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "文学部",
      "日本語日本文・英文・歴史文化"
     ],
     [
      "国際文化学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "人間社会学部",
      "現代社会・社会福祉・教育・心理"
     ],
     [
      "家政学部",
      "児童・被服"
     ]
    ],
    "tag": "2/1〜2/3・複数日受験可",
    "pick": "文系の学部は2/1〜2/3から選べる（複数日受験可・公式）",
    "l2": "文・国際文化・経済・人間社会・家政"
   },
   {
    "d": "2027-02-02",
    "f": [
     [
      "文学部",
      "日本語日本文・英文・歴史文化"
     ],
     [
      "国際文化学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "人間社会学部",
      "現代社会・社会福祉・教育・心理"
     ],
     [
      "家政学部",
      "児童・被服"
     ]
    ],
    "tag": "2/1〜2/3・複数日受験可",
    "pick": "文系の学部は2/1〜2/3から選べる（複数日受験可・公式）",
    "l2": "文・国際文化・経済・人間社会・家政"
   },
   {
    "d": "2027-02-03",
    "f": [
     [
      "文学部",
      "日本語日本文・英文・歴史文化"
     ],
     [
      "国際文化学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "人間社会学部",
      "現代社会・社会福祉・教育・心理"
     ],
     [
      "家政学部",
      "児童・被服"
     ]
    ],
    "tag": "2/1〜2/3・複数日受験可",
    "pick": "文系の学部は2/1〜2/3から選べる（複数日受験可・公式）",
    "l2": "文・国際文化・経済・人間社会・家政"
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-15"
  ],
  "result": "2027-02-15",
  "proc": "2027-02-25",
  "subjects": "文・人間社会・国際文化は3科目型のみ（外国語・国語＋地理歴史か数学など）。経済・家政は2科目型もある。詳しくは要項で確認",
  "eiken": "英検などは「英語外部試験利用型」で利用（別の方式）",
  "src": [
   "jwu",
   "jwuWeb",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2272/general/schedule"
   }
  ],
  "chk": "公式2027",
  "procNote": "手続期間 2/15〜2/25",
  "note": "経済学部は2027年4月新設（要項の記載）。"
 },
 {
  "u": "jwu",
  "method": "英語外部試験利用型",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-01",
    "f": [
     [
      "文学部",
      "日本語日本文・英文・歴史文化"
     ],
     [
      "国際文化学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "人間社会学部",
      "現代社会・社会福祉・教育・心理"
     ],
     [
      "家政学部",
      "児童・被服"
     ]
    ],
    "tag": "2/1〜2/3・複数日受験可",
    "pick": "文系の学部は2/1〜2/3から選べる（複数日受験可・公式）",
    "l2": "文・国際文化・経済・人間社会・家政"
   },
   {
    "d": "2027-02-02",
    "f": [
     [
      "文学部",
      "日本語日本文・英文・歴史文化"
     ],
     [
      "国際文化学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "人間社会学部",
      "現代社会・社会福祉・教育・心理"
     ],
     [
      "家政学部",
      "児童・被服"
     ]
    ],
    "tag": "2/1〜2/3・複数日受験可",
    "pick": "文系の学部は2/1〜2/3から選べる（複数日受験可・公式）",
    "l2": "文・国際文化・経済・人間社会・家政"
   },
   {
    "d": "2027-02-03",
    "f": [
     [
      "文学部",
      "日本語日本文・英文・歴史文化"
     ],
     [
      "国際文化学部",
      ""
     ],
     [
      "経済学部",
      ""
     ],
     [
      "人間社会学部",
      "現代社会・社会福祉・教育・心理"
     ],
     [
      "家政学部",
      "児童・被服"
     ]
    ],
    "tag": "2/1〜2/3・複数日受験可",
    "pick": "文系の学部は2/1〜2/3から選べる（複数日受験可・公式）",
    "l2": "文・国際文化・経済・人間社会・家政"
   }
  ],
  "apply": [
   "2027-01-05",
   "2027-01-15"
  ],
  "result": "2027-02-15",
  "proc": "2027-02-25",
  "subjects": "英語以外の2科目",
  "eiken": "英検2級以上を受けてCSE1950以上なら出願でき、英語以外の2科目で受験。CSE2100以上・2300以上で加点。2025年1月15日以降の受験が対象（従来型は二次試験も受験が必要）",
  "src": [
   "jwu",
   "jwuEng",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2272/general/schedule"
   }
  ],
  "chk": "公式2027",
  "procNote": "手続期間 2/15〜2/25"
 },
 {
  "u": "icu",
  "method": "一般選抜（人文・社会科学選択）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-06",
    "f": [
     [
      "教養学部",
      "アーツ・サイエンス学科",
      [
       "lit",
       "intl",
       "soc",
       "law",
       "econ",
       "edu",
       "other"
      ]
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "Web 1/19 23:59まで、書類は1/20消印有効"
  ],
  "result": "2027-02-12",
  "proc": "2027-02-22",
  "subjects": "人文・社会科学、総合教養（ATLAS）、英語",
  "eiken": "この方式では利用なし",
  "src": [
   "icu",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2214/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "icu",
  "method": "日英バイリンガル面接利用",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-06",
    "f": [
     [
      "教養学部",
      "アーツ・サイエンス学科",
      [
       "lit",
       "intl",
       "soc",
       "law",
       "econ",
       "edu",
       "other"
      ]
     ]
    ],
    "tag": "1次 2/6・2次 2/20"
   },
   {
    "d": "2027-02-20",
    "f": [
     [
      "教養学部",
      "アーツ・サイエンス学科",
      [
       "lit",
       "intl",
       "soc",
       "law",
       "econ",
       "edu",
       "other"
      ]
     ]
    ],
    "tag": "2次（オンライン面接）"
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "Web 1/19 23:59まで、書類は1/20消印有効"
  ],
  "result": "2027-02-26",
  "proc": "2027-03-08",
  "subjects": "1次：総合教養（ATLAS）・英語／2次：オンライン個人面接（日本語・英語）",
  "eiken": null,
  "src": [
   "icu",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2214/general/schedule"
   }
  ],
  "chk": "公式2027",
  "resultNote": "1次の結果通知は2/12"
 },
 {
  "u": "icu",
  "method": "英語外部試験利用",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-06",
    "f": [
     [
      "教養学部",
      "アーツ・サイエンス学科",
      [
       "lit",
       "intl",
       "soc",
       "law",
       "econ",
       "edu",
       "other"
      ]
     ]
    ],
    "tag": "1次 2/6・2次 2/20"
   },
   {
    "d": "2027-02-20",
    "f": [
     [
      "教養学部",
      "アーツ・サイエンス学科",
      [
       "lit",
       "intl",
       "soc",
       "law",
       "econ",
       "edu",
       "other"
      ]
     ]
    ],
    "tag": "2次（オンライン面接）"
   }
  ],
  "apply": [
   "2027-01-06",
   "2027-01-19",
   "Web 1/19 23:59まで、書類は1/20消印有効"
  ],
  "result": "2027-02-26",
  "proc": "2027-03-08",
  "subjects": "1次：総合教養（ATLAS）＋英語外部試験の成績／2次：オンライン面接（日本語）",
  "eiken": "対象はIELTS・TOEFL iBT・ケンブリッジ英検・GTEC CBT（2025年2月1日以降の受験）。英検は対象の一覧にない",
  "src": [
   "icu",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2214/general/schedule"
   }
  ],
  "chk": "公式2027",
  "resultNote": "1次の結果通知は2/12"
 },
 {
  "u": "tsuda",
  "method": "A方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-05",
    "f": [
     [
      "学芸学部",
      "英語英文・多文化・国際協力"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "学芸（英語英文・多文化・国際協力）"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "学芸学部",
      "国際関係"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "学芸（国際関係）"
   },
   {
    "d": "2027-02-07",
    "f": [
     [
      "総合政策学部",
      ""
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "総合政策"
   }
  ],
  "apply": [
   "2027-01-04",
   "2027-01-22"
  ],
  "result": "2027-02-16",
  "proc": "2027-02-22",
  "subjects": null,
  "eiken": "英検などは「A方式（英語外部試験利用型）」で利用（別の方式）",
  "src": [
   "tsuda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2243/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "tsuda",
  "method": "A方式（英語外部試験利用型）",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-05",
    "f": [
     [
      "学芸学部",
      "英語英文・多文化・国際協力"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "学芸（英語英文・多文化・国際協力）"
   },
   {
    "d": "2027-02-06",
    "f": [
     [
      "学芸学部",
      "国際関係"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "学芸（国際関係）"
   },
   {
    "d": "2027-02-07",
    "f": [
     [
      "総合政策学部",
      ""
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "総合政策"
   }
  ],
  "apply": [
   "2027-01-04",
   "2027-01-22"
  ],
  "result": "2027-02-16",
  "proc": "2027-02-22",
  "subjects": null,
  "eiken": "英語外部試験の成績を利用。対象の試験と基準は要項で確認",
  "src": [
   "tsuda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2243/general/schedule"
   }
  ],
  "chk": "公式2027"
 },
 {
  "u": "tsuda",
  "method": "B方式",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-28",
    "f": [
     [
      "学芸学部",
      "英語英文・多文化・国際協力"
     ]
    ]
   }
  ],
  "apply": [
   "2027-01-04",
   "2027-02-18"
  ],
  "result": "2027-03-08",
  "proc": "2027-03-15",
  "subjects": null,
  "eiken": null,
  "src": [
   "tsuda",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2243/general/schedule"
   }
  ],
  "chk": "公式2027",
  "note": "Kei-Netでは共通テストを使う方式に分類されています。内容は要項で確認してください。"
 },
 {
  "u": "twcu",
  "method": "個別学力試験型",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "現代教養学部",
      "人文（英語圏文化・歴史文化）"
     ],
     [
      "現代教養学部",
      "経済経営"
     ],
     [
      "現代教養学部",
      "心理"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "英語圏文化・歴史文化・経済経営・心理"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "現代教養学部",
      "人文（哲学・日本文学文化）"
     ],
     [
      "現代教養学部",
      "国際社会"
     ],
     [
      "現代教養学部",
      "社会コミュニケーション"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "哲学・日本文学文化・国際社会・社会コミュニケーション"
   }
  ],
  "apply": [
   "2027-01-04",
   "2027-01-18",
   "Web登録 1/18 23:00まで"
  ],
  "result": "2027-02-12",
  "proc": "2027-02-18",
  "subjects": null,
  "eiken": "英検などは「英語外部検定試験利用型」で利用（別の方式）",
  "src": [
   "twcuKN",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2254/general/schedule"
   }
  ],
  "note": "試験日の違う学科（専攻）は併願できます（Kei-Net 大学からのお知らせ）。",
  "chk": "非公式2027"
 },
 {
  "u": "twcu",
  "method": "英語外部検定試験利用型",
  "year": 2027,
  "slots": [
   {
    "d": "2027-02-03",
    "f": [
     [
      "現代教養学部",
      "人文（英語圏文化・歴史文化）"
     ],
     [
      "現代教養学部",
      "経済経営"
     ],
     [
      "現代教養学部",
      "心理"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "英語圏文化・歴史文化・経済経営・心理"
   },
   {
    "d": "2027-02-04",
    "f": [
     [
      "現代教養学部",
      "人文（哲学・日本文学文化）"
     ],
     [
      "現代教養学部",
      "国際社会"
     ],
     [
      "現代教養学部",
      "社会コミュニケーション"
     ]
    ],
    "tag": "学科ごとに試験日が違う",
    "l2": "哲学・日本文学文化・国際社会・社会コミュニケーション"
   }
  ],
  "apply": [
   "2027-01-04",
   "2027-01-18",
   "Web登録 1/18 23:00まで"
  ],
  "result": "2027-02-12",
  "proc": "2027-03-01",
  "subjects": null,
  "eiken": "対象は英検（従来型・S-CBT・S-Interview）・TEAP（4技能パターン）・GTEC（検定版・CBT）。基準は要項で確認",
  "src": [
   "twcuKN",
   {
    "label": "河合塾 Kei-Net（2027年度 試験日）",
    "url": "https://search.keinet.ne.jp/2254/general/schedule"
   }
  ],
  "chk": "非公式2027"
 }
];
window.NYUSHI = window.NYUSHI || {};
window.NYUSHI["2027-bun"] = {
  y: 2027, track: "bun", asof: "2026年10月7日", exam: "2027年1〜3月", enroll: "2027年4月",
  months: [["2027-01", "1月"], ["2027-02", "2月"], ["2027-03", "3月"]], defaultMonth: "2027-02",
  holidays: { "2027-01-01": "元日", "2027-01-11": "成人の日", "2027-02-11": "建国記念の日", "2027-02-23": "天皇誕生日" },
  univs: UNIVS, groups: GROUPS, src: SRC, events: EVENTS, fields: FIELDS, fieldOf: fieldOf, scope: "文系学部"
};
})();
