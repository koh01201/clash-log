/* 2027年度入試（2027年4月入学・試験は2027年1〜3月）の日程データ
   試験日は2027年度（大学発表、または河合塾Kei-Net掲載）。
   出願・発表・手続は year=2027 なら2027年度の大学発表、year=2026 なら前年度（参考）。 */
(function () {

var KEINET = function (id) { return { label: "河合塾 Kei-Net（2027年度 試験日）", url: "https://search.keinet.ne.jp/" + id + "/general/schedule" }; };
var UNIVS = [
  { id: "waseda", name: "早稲田大学", short: "早稲田", hue: 352 },
  { id: "keio", name: "慶應義塾大学", short: "慶應", hue: 220 },
  { id: "tus", name: "東京理科大学", short: "東京理科", hue: 28 },
  { id: "meiji", name: "明治大学", short: "明治", hue: 268 },
  { id: "aoyama", name: "青山学院大学", short: "青学", hue: 160 },
  { id: "hosei", name: "法政大学", short: "法政", hue: 200 },
  { id: "nihon", name: "日本大学", short: "日大", hue: 8 },
  { id: "shibaura", name: "芝浦工業大学", short: "芝浦工", hue: 140 },
  { id: "denki", name: "東京電機大学", short: "電機", hue: 45 },
  { id: "tcu", name: "東京都市大学", short: "都市大", hue: 185 },
  { id: "kanagawa", name: "神奈川大学", short: "神奈川", hue: 300 },
  { id: "doshisha", name: "同志社大学", short: "同志社", hue: 245 },
  { id: "ritsumei", name: "立命館大学", short: "立命館", hue: 330 }
];

var SRC = {
  waseda: { label: "早稲田大学 2027年度一般選抜（入学センター）", url: "https://www.waseda.jp/inst/admission/assets/uploads/2026/05/2027_ippan.pdf" },
  keio: { label: "慶應義塾大学 一般選抜（2027年度）", url: "https://www.keio.ac.jp/ja/admissions/faculty/examinations/general-admissions/" },
  keioSub: { label: "慶應義塾大学 2027年度 試験教科・科目", url: "https://www.keio.ac.jp/files/d76245e2bdc5e5a3f397c40b2ae40047b4d41cd3ea399c3b4dbf969c3ad989a7" },
  tus: { label: "東京理科大学 2026年度一般選抜要項（2027年度は未公表）", url: "https://www.tus.ac.jp/today/archive/2025/GeneralExamGuidelines_2026.pdf" },
  tusTop: { label: "東京理科大学 入学者募集要項", url: "https://www.tus.ac.jp/admissions/university/guideline/general/" },
  meijiTop: { label: "明治大学 入試総合サイト", url: "https://www.meiji.ac.jp/exam/information/index.html" },
  meijiPN1: { label: "旺文社パスナビ 明治大学理工学部（前年度）", url: "https://passnavi.obunsha.co.jp/univ/3120/schedule/?facultyID=040" },
  meijiPN2: { label: "旺文社パスナビ 明治大学総合数理学部（前年度）", url: "https://passnavi.obunsha.co.jp/univ/3120/schedule/?facultyID=050" },
  aoyama: { label: "青山学院大学 2026年度入学者選抜要項", url: "https://www.aoyama.ac.jp/wp-content/uploads/2026/04/ad_2026_ippan_kyotsutest_20260410_jJ9si.pdf" },
  aoyamaPN: { label: "旺文社パスナビ 青山学院大学（前年度）", url: "https://passnavi.obunsha.co.jp/univ/2260/schedule/" },
  hoseiTop: { label: "法政大学 入試要項・入試ガイド", url: "https://nyushi.hosei.ac.jp/nyushi/guide/" },
  hoseiPN: { label: "旺文社パスナビ 法政大学（前年度）", url: "https://passnavi.obunsha.co.jp/univ/3050/schedule/" },
  nihonN: { label: "日本大学 N全学統一方式（2027年度）", url: "https://www.nihon-u.ac.jp/admission_info/application/general_information/general/n_system/" },
  nihonCst: { label: "日本大学理工学部 令和8年度入試情報", url: "https://www.cst.nihon-u.ac.jp/examination/pdf/nyushi.pdf" },
  shibaura: { label: "芝浦工業大学 2027年度入試ガイド", url: "https://www.shibaura-it.ac.jp/assets/admissions_guideboook_2027_v2.pdf" },
  denki1: { label: "東京電機大学 一般選抜（前期）2027年度", url: "https://www.dendai.ac.jp/about/admission/undergraduate/ippan/zenki.html" },
  denki2: { label: "東京電機大学 一般選抜（後期）2027年度", url: "https://www.dendai.ac.jp/about/admission/undergraduate/ippan/kouki.html" },
  tcu: { label: "東京都市大学 2027年度入試概要", url: "https://www.tcu.ac.jp/entrance/summary/" },
  tcu1: { label: "東京都市大学 前期（理工系）2027年度", url: "https://www.tcu.ac.jp/tcucms/wp-content/uploads/2026/05/previous1.pdf" },
  tcu2: { label: "東京都市大学 中期 2027年度", url: "https://www.tcu.ac.jp/tcucms/wp-content/uploads/2026/05/middle.pdf" },
  tcu3: { label: "東京都市大学 後期（2教科型）2027年度", url: "https://www.tcu.ac.jp/tcucms/wp-content/uploads/2026/09/latter1_v2.pdf" },
  kanagawa: { label: "神奈川大学 2026年度一般選抜要項（2027年度は未公表）", url: "https://www.kanagawa-u.ac.jp/admissions/faculty/about_application/general/file/general_yoko2026.pdf" },
  doshisha: { label: "同志社大学 2027年度入学試験ガイド", url: "https://www.doshisha.ac.jp/files/nyugk/page/nyushiguide2027.pdf" },
  ritsumei: { label: "立命館大学 2027年度一般選抜ガイド", url: "https://admission.ritsumei.ac.jp/assets/file/2027/application/guide/04-19.pdf" }
};

var EVENTS = [
  /* ---------- 早稲田 ---------- */
  { u: "waseda", method: "一般選抜", year: 2027,
    slots: [
      { d: "2027-02-16", f: [["基幹理工学部", "学系1・学系2・学系3・学系4"], ["創造理工学部", "建築・総合機械工・経営システム工・社会環境工・環境資源工"], ["先進理工学部", "物理・応用物理・化学・生命化学・応用化学・電気・情報生命工"]] },
      { d: "2027-02-17", f: [["創造理工学部", "建築学科のみ。2/16の筆記に加えて空間表現（120分・40点）を受ける"]], tag: "建築学科のみ・空間表現" }
    ],
    apply: ["2027-01-06", "2027-01-19", "締切日消印有効"], result: "2027-02-27", proc: "2027-03-05",
    procNote: "1次手続 3/5、Web入力・書類郵送 3/12、2次手続 3/24",
    subjects: "数学 120分・120点／理科 120分・120点（2科目、1科目60点）／外国語 90分・120点。建築学科は空間表現 120分・40点を追加",
    eiken: "利用なし（大学資料に記載なし）",
    note: "先進理工学部の生命医科学科は除いています。入試要項は11月上旬に公開予定。",
    src: ["waseda", KEINET(2293)] },

  /* ---------- 慶應 ---------- */
  { u: "keio", method: "一般選抜", year: 2027,
    slots: [{ d: "2027-02-12", f: [["理工学部", "学門A〜E"]] }],
    apply: ["2026-12-24", "2027-01-18", "Web登録 1/18 17:00まで、書類は1/4〜1/18 消印有効"], result: "2027-02-24", proc: "2027-03-12",
    subjects: "数学 150点（数I・II・III・A・B・C）／理科 200点（物理100・化学100）／外国語 150点",
    eiken: "利用なし（大学資料に記載なし）",
    src: ["keio", "keioSub"] },

  /* ---------- 東京理科（試験日=2027 Kei-Net、他=2026参考） ---------- */
  { u: "tus", method: "B方式", year: 2026,
    slots: [
      { d: "2027-02-03", f: [["創域理工学部", "数理科学・先端物理"]], tag: "数理科学・先端物理のみ" },
      { d: "2027-02-06", f: [["創域理工学部", "建築・先端化学・電気電子情報工・機械航空宇宙工・社会基盤工"]], tag: "数理・先端物理以外の5学科" }
    ],
    apply: ["2026-01-07", "2026-01-22"], result: "2026-02-20", proc: "2026-02-26", procNote: "2次手続 3/11（前年度）",
    subjects: "数学 100点（数I〜III・A〜C）／英語 100点／理科 100点（学科により指定）",
    eiken: "B方式は利用なし（英語資格はA方式の一部で利用）",
    note: "生命生物科学科は除いています。",
    src: [KEINET(2262), "tus", "tusTop"] },
  { u: "tus", method: "S方式", year: 2026,
    slots: [
      { d: "2027-02-03", f: [["創域理工学部", "電気電子情報工学科"]], tag: "電気電子情報工のみ" },
      { d: "2027-02-06", f: [["創域理工学部", "数理科学科"]], tag: "数理科学のみ" }
    ],
    apply: ["2026-01-07", "2026-01-22"], result: "2026-02-20", proc: "2026-02-26",
    subjects: "電気電子情報工：数学100・英語100・物理200／数理科学：数学300・英語100",
    eiken: "利用なし",
    src: [KEINET(2262), "tus", "tusTop"] },
  { u: "tus", method: "B方式", year: 2026,
    slots: [{ d: "2027-02-04", f: [["先進工学部", "生命システム工学科を除く各学科"]] }],
    apply: ["2026-01-07", "2026-01-22"], result: "2026-02-19", proc: "2026-02-25", procNote: "2次手続 3/11（前年度）",
    subjects: "数学 100点／英語 100点／理科 100点（学科により指定）", eiken: "利用なし",
    src: [KEINET(2262), "tus", "tusTop"] },
  { u: "tus", method: "B方式", year: 2026,
    slots: [{ d: "2027-02-05", f: [["理学部第一部", "数学・物理・化学・応用数学・応用化学"]] }],
    apply: ["2026-01-07", "2026-01-22"], result: "2026-02-21", proc: "2026-02-27", procNote: "2次手続 3/11（前年度）",
    subjects: "数学 100点／英語 100点／理科 100点（学科により指定）", eiken: "利用なし",
    src: [KEINET(2262), "tus", "tusTop"] },
  { u: "tus", method: "B方式", year: 2026,
    slots: [{ d: "2027-02-08", f: [["工学部", "全学科"]] }],
    apply: ["2026-01-07", "2026-01-22"], result: "2026-02-25", proc: "2026-03-02", procNote: "2次手続 3/11（前年度）",
    subjects: "数学 100点／英語 100点／理科 100点（学科により指定）", eiken: "利用なし",
    src: [KEINET(2262), "tus", "tusTop"] },
  { u: "tus", method: "B方式", year: 2026,
    slots: [{ d: "2027-02-03", f: [["創域情報学部", ""]] }],
    apply: [null, null], result: null, proc: null,
    subjects: null, eiken: null,
    note: "前年度の要項に日程が見当たらないため、出願・発表・手続は要項の公開を待って確認が必要です。",
    src: [KEINET(2262), "tusTop"] },

  /* ---------- 明治（試験日=2027 Kei-Net、他=前年度パスナビ） ---------- */
  { u: "meiji", method: "全学部統一入試", year: 2026,
    slots: [{ d: "2027-02-05", f: [["理工学部", ""]] }],
    apply: ["2026-01-06", "2026-01-16"], result: "2026-02-14", proc: "2026-02-26",
    subjects: null, eiken: null,
    src: [KEINET(2286), "meijiPN1", "meijiTop"] },
  { u: "meiji", method: "学部別入試", year: 2026,
    slots: [{ d: "2027-02-07", f: [["理工学部", ""]] }],
    apply: ["2026-01-06", "2026-01-22"], result: "2026-02-14", proc: "2026-02-26",
    subjects: null, eiken: null,
    src: [KEINET(2286), "meijiPN1", "meijiTop"] },
  { u: "meiji", method: "全学部統一入試", year: 2026,
    slots: [{ d: "2027-02-05", f: [["総合数理学部", "現象数理・先端メディアサイエンス・ネットワークデザイン"]] }],
    apply: ["2026-01-06", "2026-01-16"], result: "2026-02-11", proc: "2026-02-19",
    subjects: null, eiken: "英語4技能試験活用方式あり（全学部統一入試）",
    src: [KEINET(2286), "meijiPN2", "meijiTop"] },
  { u: "meiji", method: "学部別入試", year: 2026,
    slots: [{ d: "2027-02-17", f: [["総合数理学部", "現象数理・先端メディアサイエンス・ネットワークデザイン"]] }],
    apply: ["2026-01-06", "2026-01-26"], result: "2026-02-24", proc: "2026-03-03",
    subjects: null, eiken: null,
    note: "2027年度は学部別入試の出題範囲に変更あり（大学発表）。",
    src: [KEINET(2286), "meijiPN2", "meijiTop"] },

  /* ---------- 青学（試験日=2027 Kei-Net、他=2026） ---------- */
  { u: "aoyama", method: "全学部日程", year: 2026,
    slots: [{ d: "2027-02-07", f: [["理工学部", "物理科学・数理サイエンス・化学・生命科学・電気電子工・機械創造工・経営システム工・情報テクノロジー"]] }],
    apply: ["2026-01-05", "2026-01-19", "Web登録 23:00まで、書類は1/22 必着"], result: "2026-02-14", proc: "2026-02-24",
    subjects: "外国語 80分・150点／数学 70分・150点／理科 60分・100点（学科により選択科目が異なる）",
    eiken: null,
    src: [KEINET(2200), "aoyama"] },
  { u: "aoyama", method: "個別学部日程 A方式", year: 2026,
    slots: [{ d: "2027-02-10", f: [["理工学部", "全7学科"]] }],
    apply: ["2026-01-05", "2026-01-21", "書類は1/23 必着"], result: "2026-02-17", proc: "2026-02-25",
    subjects: "外国語・数学・理科 各150点", eiken: null,
    src: [KEINET(2200), "aoyama", "aoyamaPN"] },
  { u: "aoyama", method: "個別学部日程 B方式", year: 2026,
    slots: [{ d: "2027-02-11", f: [["理工学部", "全7学科"]] }],
    apply: ["2026-01-05", "2026-01-21", "書類は1/23 必着"], result: "2026-02-17", proc: "2026-02-25",
    subjects: "外国語 100点／数学 200点／理科 200点", eiken: null,
    src: [KEINET(2200), "aoyama", "aoyamaPN"] },

  /* ---------- 法政（試験日=2027 Kei-Net、他=前年度パスナビ） ---------- */
  { u: "hosei", method: "T日程・英語外部試験利用", year: 2026,
    slots: [{ d: "2027-02-05", f: [["理工学部", ""], ["デザイン工学部", ""], ["情報科学部", ""]] }],
    apply: ["2026-01-07", "2026-01-16"], result: "2026-02-17", proc: "2026-02-20",
    subjects: null, eiken: "英語外部試験利用入試あり（T日程と同日）",
    note: "生命科学部は対象外です。",
    src: [KEINET(2279), "hoseiPN", "hoseiTop"] },
  { u: "hosei", method: "A方式（個別日程）", year: 2026,
    slots: [{ d: "2027-02-11", f: [["理工学部", "機械工（機械工学専修）・応用情報工"], ["デザイン工学部", "都市環境デザイン工・システムデザイン"], ["情報科学部", "ディジタルメディア"]], tag: "学科ごとに試験日が違う", l2: "この日に受ける学科：機械工・応用情報工・都市環境デザイン工・システムデザイン・ディジタルメディア" }],
    apply: ["2026-01-07", "2026-01-28"], result: "2026-02-19", proc: "2026-02-25",
    subjects: null, eiken: null,
    src: [KEINET(2279), "hoseiPN", "hoseiTop"] },
  { u: "hosei", method: "A方式（個別日程）", year: 2026,
    slots: [{ d: "2027-02-14", f: [["理工学部", "電気電子工・経営システム工・創生科学"], ["デザイン工学部", "建築"], ["情報科学部", "コンピュータ科学"]], tag: "学科ごとに試験日が違う", l2: "この日に受ける学科：電気電子工・経営システム工・創生科学・建築・コンピュータ科学" }],
    apply: ["2026-01-07", "2026-02-02"], result: "2026-02-21", proc: "2026-02-27",
    subjects: null, eiken: null,
    src: [KEINET(2279), "hoseiPN", "hoseiTop"] },

  /* ---------- 日大 ---------- */
  { u: "nihon", method: "N全学統一方式 第1期", year: 2027,
    slots: [{ d: "2027-02-01", f: [["理工学部", ""], ["生産工学部", ""], ["工学部（郡山）", ""]] }],
    apply: [null, "2027-01-22", "郵送必着"], result: "2027-02-15", resultNote: "理工・生産工 2/15、工 2/12",
    proc: null, subjects: null, eiken: null,
    src: ["nihonN", KEINET(2267)] },
  { u: "nihon", method: "A個別方式", year: 2026,
    slots: [{ d: "2027-02-11", f: [["理工学部", "土木・交通システム・建築・海洋建築・まちづくり・機械・精密機械・航空宇宙・電気・電子・応用情報・物質応用化学・物理・数学"]] }],
    apply: ["2026-01-05", "2026-01-30"], result: "2026-02-19", proc: "2026-02-27", procNote: "二段階手続で3/25まで延長可（前年度）",
    subjects: "数学（数I・II・III・A・B・C）／理科（物理・化学から選択）／英語（全問マークシート）",
    eiken: null,
    src: [KEINET(2267), "nihonCst"] },
  { u: "nihon", method: "A個別方式 第1期", year: 2026,
    slots: [{ d: "2027-02-02", f: [["生産工学部", ""]] }],
    apply: [null, null], result: null, proc: null, subjects: null, eiken: null,
    src: [KEINET(2267)] },
  { u: "nihon", method: "A個別方式", year: 2026,
    slots: [{ d: "2027-02-03", f: [["工学部（郡山）", ""]], pick: "2/3・2/4の2日実施。1日だけか両日受けられるかは要項で確認", tag: "2/3・2/4・受け方は要項で確認" }, { d: "2027-02-04", f: [["工学部（郡山）", ""]], pick: "2/3・2/4の2日実施。1日だけか両日受けられるかは要項で確認", tag: "2/3・2/4・受け方は要項で確認" }],
    apply: [null, null], result: null, proc: null, subjects: null, eiken: null,
    src: [KEINET(2267)] },
  { u: "nihon", method: "A個別方式 第2期", year: 2026,
    slots: [{ d: "2027-02-09", f: [["生産工学部", ""]] }],
    apply: [null, null], result: null, proc: null, subjects: null, eiken: null,
    src: [KEINET(2267)] },
  { u: "nihon", method: "N全学統一方式 第2期", year: 2027,
    slots: [{ d: "2027-03-04", f: [["理工学部", ""], ["生産工学部", ""], ["工学部（郡山）", ""]] }],
    apply: [null, "2027-02-25", "郵送必着"], result: "2027-03-15", resultNote: "理工・工 3/15、生産工 3/12",
    proc: null, subjects: null, eiken: null,
    src: ["nihonN", KEINET(2267)] },

  /* ---------- 芝浦工（2027年度 公式） ---------- */
  { u: "shibaura", method: "前期日程（A方式・B方式）", year: 2027,
    slots: [
      { d: "2027-02-01", f: [["工学部", "機械（基幹機械）・電気（電気・ロボット工学）・情報（情報工学）"], ["システム理工学部", "数理科学"], ["デザイン工学部", "プロダクトデザイン"], ["建築学部", "都市・建築デザイン"]], tag: "学科ごとに試験日が違う", l2: "この日に受ける学科：基幹機械・電気ロボット工学・情報工学・数理科学・プロダクトデザイン・都市建築デザイン" },
      { d: "2027-02-02", f: [["工学部", "機械（先進機械）・物質（化学・生命工学）・情報（情報通信）"], ["システム理工学部", "情報（IoT・ソフトウェア・メディア・データサイエンス）"], ["デザイン工学部", "システムデザイン・UXデザイン"], ["建築学部", "空間・建築デザイン"]], tag: "学科ごとに試験日が違う", l2: "この日に受ける学科：先進機械・化学生命工学・情報通信・情報（IoT／ソフトウェア／メディア／データサイエンス）・システムデザイン・UXデザイン・空間建築デザイン" },
      { d: "2027-02-03", f: [["工学部", "物質（環境・物質工学）・電気（先端電子工学）・土木工学"], ["システム理工学部", "機械・電気、建築（建築・環境都市）"], ["建築学部", "先進的プロジェクトデザイン"]], tag: "学科ごとに試験日が違う", l2: "この日に受ける学科：環境物質工学・先端電子工学・土木工学・機械電気（システム理工）・建築／環境都市（システム理工）・先進的プロジェクトデザイン" }
    ],
    apply: ["2027-01-07", "2027-01-15", "消印有効"], result: "2027-02-14", proc: "2027-02-20", procNote: "1次手続 2/20、2次手続 3/14",
    subjects: "数学・理科（物理・化学）。A方式は英語を共通テストまたは英検で得点化、B方式は数学の配点が高い",
    eiken: "A方式：英語は共通テストか英検のスコアで得点化。B方式：英語資格・検定試験の基準を満たすことが出願要件",
    note: "システム理工学部の生命科学科は除いています。",
    src: ["shibaura", KEINET(2219)] },
  { u: "shibaura", method: "全学統一日程（A方式・B方式）", year: 2027,
    slots: [{ d: "2027-02-04", f: [["工学部", ""], ["システム理工学部", "生命科学科を除く"], ["デザイン工学部", ""], ["建築学部", ""]] }],
    apply: ["2027-01-07", "2027-01-15", "消印有効"], result: "2027-02-14", proc: "2027-02-20", procNote: "1次手続 2/20、2次手続 3/14",
    subjects: "数学・理科（物理・化学）。英語の扱いは前期日程と同じ",
    eiken: "前期日程と同じ（A方式は英検等で得点化、B方式は基準スコアが出願要件）",
    src: ["shibaura", KEINET(2219)] },
  { u: "shibaura", method: "後期日程", year: 2027,
    slots: [{ d: "2027-02-21", f: [["工学部", ""], ["システム理工学部", "生命科学科を除く"], ["デザイン工学部", ""], ["建築学部", ""]] }],
    apply: ["2027-02-05", "2027-02-15", "消印有効"], result: "2027-03-01", proc: "2027-03-05", procNote: "1次手続 3/5、2次手続 3/14",
    subjects: null, eiken: null,
    src: ["shibaura", KEINET(2219)] },

  /* ---------- 電機（2027年度 公式） ---------- */
  { u: "denki", method: "前期（英語外部試験利用を含む）", year: 2027,
    slots: ["2027-02-01", "2027-02-02", "2027-02-03", "2027-02-04", "2027-02-05"].map(function (d) {
      return { d: d, f: [["工学部", ""], ["システムデザイン工学部", ""], ["未来科学部", ""], ["理工学部", "生命科学系を除く"]], pick: "学科に関係なく2/1〜2/5から自由に選べる。複数の日を受けることもできる（同じ日に4学科・学系まで併願可）", tag: "2/1〜2/5・複数日受験可" };
    }),
    apply: ["2027-01-07", "2027-01-20"], result: "2027-02-12", proc: "2027-02-19", procNote: "1次（入学金）2/19、2次（授業料等）3/3",
    subjects: null, eiken: "前期・英語外部試験利用あり（基準は要項で確認）",
    src: ["denki1", KEINET(2259)] },
  { u: "denki", method: "後期（英語外部試験利用を含む）", year: 2027,
    slots: ["2027-02-27", "2027-02-28"].map(function (d) {
      return { d: d, f: [["工学部", ""], ["システムデザイン工学部", ""], ["未来科学部", ""], ["理工学部", "生命科学系を除く"]], pick: "学科に関係なく2/27・2/28から自由に選べる。両日受けることもできる", tag: "2/27・2/28・両日受験可" };
    }),
    apply: ["2027-02-12", "2027-02-18"], result: "2027-03-08", proc: "2027-03-15",
    subjects: null, eiken: null,
    src: ["denki2", KEINET(2259)] },

  /* ---------- 都市大（2027年度 公式） ---------- */
  { u: "tcu", method: "前期（3教科型）", year: 2027,
    slots: ["2027-02-01", "2027-02-02", "2027-02-03"].map(function (d) {
      return { d: d, f: [["理工学部", ""], ["建築都市デザイン学部", ""], ["情報工学部", ""]], pick: "3日間とも全学科が対象。何日でも受けられ、同じ学科を複数日受けることもできる（1日最大4出願、3日間で最大12出願）。学外試験場は2/1・2/2のみ", tag: "2/1〜2/3・複数日受験可" };
    }),
    apply: ["2027-01-05", "2027-01-21", "1/21 17:00まで"], result: "2027-02-12", proc: "2027-02-18", procNote: "1次手続 2/18。2次は併願先により3/2・3/11・3/24",
    subjects: "理科（物理・化学）・数学・英語の3教科 300点",
    eiken: "英検・GTECなどを英語のみなし得点（50〜90点）に換算可。英検は準2級以上",
    src: ["tcu1", "tcu", KEINET(2282)] },
  { u: "tcu", method: "中期", year: 2027,
    slots: [{ d: "2027-02-20", f: [["理工学部", ""], ["建築都市デザイン学部", ""], ["情報工学部", ""]] }],
    apply: ["2027-01-05", "2027-02-13", "2/13 17:00まで"], result: "2027-02-25", proc: "2027-03-02", procNote: "国公立併願者は3/11・3/24まで延納可",
    subjects: "理科（物理・化学）80分・数学（数I〜III・A・B）90分・英語 80分の3教科 300点",
    eiken: null,
    src: ["tcu2", "tcu", KEINET(2282)] },
  { u: "tcu", method: "後期（2教科型）", year: 2027,
    slots: [{ d: "2027-03-04", f: [["理工学部", ""], ["建築都市デザイン学部", ""], ["情報工学部", ""]] }],
    apply: ["2027-01-05", "2027-02-26", "2/26 17:00まで"], result: "2027-03-10", proc: "2027-03-14",
    subjects: "数学と、理科または英語の2教科",
    eiken: null,
    src: ["tcu3", "tcu", KEINET(2282)] },

  /* ---------- 神奈川（試験日=2027 Kei-Net、他=2026要項） ---------- */
  { u: "kanagawa", method: "全学統一", year: 2026,
    slots: [{ d: "2027-02-04", f: [["工学部・建築学部・情報学部・理学部・化学生命学部（応用化学科）", "生物系を除く"]] }],
    apply: ["2026-01-07", "2026-01-16", "消印有効"], result: "2026-02-18", proc: "2026-03-06",
    subjects: null, eiken: "利用できる方式あり（要項で確認）",
    note: "学部ごとに実施する方式は要項で確認が必要です。",
    src: [KEINET(2306), "kanagawa"] },
  { u: "kanagawa", method: "前期 3科目型", year: 2026,
    slots: ["2027-02-06", "2027-02-07", "2027-02-08"].map(function (d) {
      return { d: d, f: [["工学部・建築学部・情報学部・理学部・化学生命学部（応用化学科）", "生物系を除く"]], pick: "3日間の3科目型はまとめて合否を判定（2026年度要項）。何日受けられるかは要項で確認", tag: "2/6〜2/8・受け方は要項で確認" };
    }),
    apply: ["2026-01-07", "2026-01-16", "消印有効"], result: "2026-02-18", proc: "2026-03-06",
    subjects: "理科・数学（90分）・外国語", eiken: "利用できる方式あり（要項で確認）",
    note: "学部ごとに実施する方式は要項で確認が必要です。",
    src: [KEINET(2306), "kanagawa"] },
  { u: "kanagawa", method: "後期 2科目型", year: 2026,
    slots: [{ d: "2027-03-04", f: [["工学部・建築学部・情報学部・理学部・化学生命学部（応用化学科）", "生物系を除く"]] }],
    apply: ["2026-02-13", "2026-02-20", "消印有効"], result: "2026-03-12", proc: "2026-03-18",
    subjects: null, eiken: null,
    src: [KEINET(2306), "kanagawa"] },

  /* ---------- 同志社（2027年度 公式） ---------- */
  { u: "doshisha", method: "全学部日程（理系）", year: 2027,
    slots: [{ d: "2027-02-04", f: [["理工学部", "インテリジェント情報工・情報システムデザイン・電気工・電子工・機械システム工・機械理工・機能分子・生命化学・化学システム創成工・環境システム・数理システム"]] }],
    apply: ["2026-12-21", "2027-01-07", "締切日消印有効"], result: "2027-02-15", proc: null,
    subjects: "英語 100分・200点／数学 100分・200点／理科 75分・150点",
    eiken: "利用なし",
    src: ["doshisha", KEINET(2498)] },
  { u: "doshisha", method: "学部個別日程", year: 2027,
    slots: [{ d: "2027-02-10", f: [["理工学部", "全10学科"]] }],
    apply: ["2026-12-21", "2027-01-07", "締切日消印有効"], result: "2027-02-19", proc: null,
    subjects: "英語・数学・理科（全学部日程と同じ教科で配点が異なる）",
    eiken: "利用なし",
    src: ["doshisha", KEINET(2498)] },

  /* ---------- 立命館（2027年度 公式） ---------- */
  { u: "ritsumei", method: "全学統一方式（理系）", year: 2027,
    slots: ["2027-02-02", "2027-02-03"].map(function (d) {
      return { d: d, f: [["理工学部", ""], ["情報理工学部", ""]], pick: "試験日が違えば、同じ学部・学科でも両日受けられる", tag: "2/2・2/3・両日受験可" };
    }),
    apply: ["2027-01-06", "2027-01-22", "1/22 23:00まで"], result: "2027-02-16", proc: "2027-03-01",
    subjects: "英語 100点／数学 100点／理科（物理または化学）100点",
    eiken: "個別試験の方式では利用なし（共通テスト方式で英検準1級以上などを満点換算）",
    src: ["ritsumei", KEINET(2504)] },
  { u: "ritsumei", method: "学部個別配点方式", year: 2027,
    slots: [{ d: "2027-02-07", f: [["理工学部", "理科1科目型・理科2科目型"], ["情報理工学部", "理科1科目型・情報理工学部型"]] }],
    apply: ["2027-01-06", "2027-01-26", "1/26 23:00まで"], result: "2027-02-17", proc: "2027-03-01",
    subjects: "全学統一方式と同じ形式で、配点が学部ごとに異なる",
    eiken: null,
    src: ["ritsumei", KEINET(2504)] },
  { u: "ritsumei", method: "後期分割方式", year: 2027,
    slots: [{ d: "2027-03-07", f: [["理工学部", ""], ["情報理工学部", ""]] }],
    apply: ["2027-02-12", "2027-02-26", "2/26 23:00まで"], result: "2027-03-17", proc: "2027-03-24",
    subjects: null, eiken: null,
    src: ["ritsumei", KEINET(2504)] }
];

window.NYUSHI = window.NYUSHI || {};
window.NYUSHI[2027] = {
  y: 2027, asof: "2026年10月7日", exam: "2027年1〜3月", enroll: "2027年4月",
  months: [["2026-12", "12月"], ["2027-01", "1月"], ["2027-02", "2月"], ["2027-03", "3月"]], defaultMonth: "2027-02",
  holidays: { "2027-01-01": "元日", "2027-01-11": "成人の日", "2027-02-11": "建国記念の日", "2027-02-23": "天皇誕生日" },
  univs: UNIVS, src: SRC, events: EVENTS
};
})();
