
"use strict";

const $ = id => document.getElementById(id);
const LINES = ["1.5", "2.5", "3.5", "4.5", "5.5", "6.5"];

const S = {
  records: [],
  filtered: [],
  page: 0,
  size: 40,
  source: "",
  topLimit: null,
  onlyFinal: false
};

const keys = (o, ks) => {
  if (!o || typeof o !== "object") return null;
  for (const k of ks) {
    if (o[k] !== undefined && o[k] !== null && o[k] !== "") {
      return o[k];
    }
  }
  return null;
};

const dateNum = v => {
  const n = Date.parse(String(v || ""));
  return Number.isFinite(n) ? n : null;
};

const pct = v => {
  if (v == null || v === "") return null;
  const n = Number(String(v).replace("%", "").replace(",", "."));
  return Number.isFinite(n) && n >= 0 && n <= 100 ? n : null;
};

const arr = d => Array.isArray(d)
  ? d
  : d && typeof d === "object"
    ? (["tahminler", "maclar", "predictions", "matches", "records", "data"]
        .map(k => d[k]).find(Array.isArray) || [])
    : [];

function normalize(x, i) {
  if (!x || typeof x !== "object" || Array.isArray(x)) return null;

  const home = keys(x, ["ev_sahibi", "ev", "home_team", "home", "takim1"]);
  const away = keys(x, ["deplasman", "dep", "away_team", "away", "takim2"]);
  const name = keys(x, ["mac", "maç", "match", "fixture"]) ||
    [home, away].filter(Boolean).join(" - ");

  const league = String(
    keys(x, ["lig", "league", "lig_adi", "lig_kodu"]) || "Bilinmeyen lig"
  );

  const kickoff = keys(x, [
    "tarih", "date", "kickoff", "baslama_zamani", "start_time"
  ]);

  const made = keys(x, [
    "hesaplama_zamani",
    "hesaplama_zamani_utc",
    "created_at",
    "created_utc",
    "prediction_time"
  ]);

  const prediction = keys(x, [
    "tahmin", "prediction", "karar", "secim", "market"
  ]);

  const probs = keys(x, ["olasiliklar", "probabilities"]) || {};

  const embedded = prediction &&
    typeof prediction === "object" &&
    !Array.isArray(prediction) ? prediction : {};

  const marketText = typeof prediction === "string" ? prediction : "";
  const probabilities = {};

  for (const line of LINES) {
    const key = line + "_ust";
    probabilities[line] = pct(
      keys(probs, [key, line + "_over"]) ??
      keys(embedded, [key, line + "_over"]) ??
      keys(x, [key, line + "_over"])
    );
  }

  const general = pct(keys(x, [
    "olasilik", "probability", "guven", "confidence", "yuzde"
  ]));

  const matches = marketText.match(/([1-6][.,]5)\s*(?:ÜST|UST|OVER)/i);
  const selected = matches ? matches[1].replace(",", ".") : null;

  if (selected && probabilities[selected] === null) {
    probabilities[selected] = general;
  }

  const start = dateNum(kickoff);
  const created = dateNum(made);
  const verified = start !== null && created !== null && created < start;
  const risk = !verified;

  const id = [
    league,
    String(home || name || ""),
    String(away || ""),
    String(kickoff || "")
  ].join("|").toLocaleLowerCase("tr");

  return {
    id,
    name: String(name || "Maç adı yok"),
    league,
    kickoff: String(kickoff || ""),
    start,
    created,
    verified,
    risk,
    marketText,
    probabilities,
    selected,
    index: i,
    sourceId: String(keys(x, ["id"]) || ""),
    leagueCode: String(keys(x, ["lig_kodu"]) || "")
  };
}
function lockedRecord(r) {
  const match = resultRecords.find(x =>
    x.kimlik === r.sourceId || x.kimlik === r.leagueCode + "|" + r.sourceId
  );
  return match || null;
}


function finalChoice(r) {
  if (!r.verified) return null;

  const record = lockedRecord(r);
  const choice = String(record?.kilitli_secim || "");

  if (choice === "RISKLI") {
    return { risk: true, locked: true };
  }

  const match = /^([1-6]\.5) UST$/.exec(choice);

  if (match) {
    const line = match[1];
    const probability =
      pct(record?.olasiliklar?.[line + "_ust"]) ??
      r.probabilities[line];

    if (probability !== null && Number.isFinite(probability)) {
      return { line, probability, locked: true };
    }
  }

  const thresholds = {
    "1.5": 75,
    "2.5": 65,
    "3.5": 65,
    "4.5": 65,
    "5.5": 65,
    "6.5": 65
  };

  for (const line of [...LINES].reverse()) {
    const probability = r.probabilities[line];

    if (
      probability !== null &&
      Number.isFinite(probability) &&
      probability >= thresholds[line]
    ) {
      return { line, probability, locked: false };
    }
  }

  return { risk: true, locked: false };
}

function chosen(r) {
  const market = $("market").value;

  if (market !== "all") {
    return [market, r.probabilities[market]];
  }

  const available = LINES
    .map(line => [line, r.probabilities[line]])
    .filter(item => item[1] !== null);

  if (!available.length) return ["", null];

  available.sort((a, b) => b[1] - a[1]);
  return available[0];
}


function topTahminler(adet) {
  const simdi = Date.now();

  return S.records
    .filter(r =>
      r.verified &&
      r.start !== null &&
      r.start > simdi
    )
    .map(r => ({
      ...r,
      topSecim: finalChoice(r)
    }))
    .filter(r =>
      r.topSecim &&
      !r.topSecim.risk &&
      r.topSecim.line &&
      Number.isFinite(r.topSecim.probability)
    )
    .sort((a, b) =>
      b.topSecim.probability - a.topSecim.probability
    )
    .slice(0, adet);
}


function td(tr, value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  tr.append(cell);
  return cell;
}

function aramaMetni(metin) {
  return String(metin || "")
    .toLowerCase()
    .replace(/ı/g, "i")
    .replace(/ğ/g, "g")
    .replace(/ü/g, "u")
    .replace(/ş/g, "s")
    .replace(/ö/g, "o")
    .replace(/ç/g, "c");
}

function render() {
  
  const query = aramaMetni($("search").value.trim());

  const market = $("market").value;
  const valid = $("valid").value;

  S.filtered = S.records.filter(r =>
    
    
    
    aramaMetni(r.name + " " + r.league + " " + (r.league.startsWith("Ingiltere") ? "İngiltere England English" : r.league.startsWith("Turkiye") ? "Türkiye Turkey Turkish" : r.league.startsWith("Iskocya") ? "İskoçya Scotland Scottish" : "")).includes(query) &&



      
      
    (market === "all" || r.probabilities[market] !== null) &&
    (valid === "all" || (valid === "pre" ? r.verified : !r.verified))
  );

  const sort = $("sort").value;

  S.filtered.sort((a, b) =>
    sort === "prob"
      ? (chosen(b)[1] ?? -1) - (chosen(a)[1] ?? -1)
      : sort === "league"
        ? a.league.localeCompare(b.league, "tr")
        : (a.start ?? Infinity) - (b.start ?? Infinity)
  );

  const pages = Math.max(1, Math.ceil(S.filtered.length / S.size));
  S.page = Math.min(S.page, pages - 1);

  const tbody = $("rows");
  tbody.replaceChildren();

  for (const r of S.filtered.slice(
    S.page * S.size,
    (S.page + 1) * S.size
  )) {
    const tr = document.createElement("tr");
    const first = td(tr, r.name);

    const small = document.createElement("div");
    small.textContent = r.league;
    small.className = "muted";
    first.append(small);

    td(
      tr,
      r.start !== null
        ? new Date(r.start).toISOString().slice(0, 16).replace("T", " ")
        : "Tarih yok"
    );

    for (const line of LINES) {
      const value = r.probabilities[line];
      const cell = td(
        tr,
        value !== null ? value.toFixed(1) + "%" : "—"
      );
      if (value !== null) cell.className = "probability";
    }
const final = finalChoice(r);
const finalTd = document.createElement("td");
const finalLabel = document.createElement("span");

if (final && !final.risk && final.line) {
  finalLabel.textContent =
    final.line + " ÜST — %" + final.probability.toFixed(1);
  finalLabel.style.color = "#22c55e";
  finalLabel.style.fontWeight = "bold";
} else {
  finalLabel.textContent = "RİSKLİ";
  finalLabel.style.color = "#94a3b8";
}

finalTd.append(finalLabel);
tr.append(finalTd);
    for (const line of LINES) {
      const value = r.probabilities[line];
      const cell = td(
        tr,
        value !== null ? value.toFixed(1) + "%" : "—"
      );
      if (value !== null) cell.className = "probability";
    }
    const state = document.createElement("td");
    const pill = document.createElement("span");

    pill.className = "pill" + (r.risk ? " review" : "");
    pill.textContent = r.verified
      ? "Maç öncesi kayıt"
      : "İnceleme gerekli";

    state.append(pill);
    tr.append(state);
    tbody.append(tr);
  }

  $("total").textContent = S.records.length.toLocaleString("tr-TR");
  $("unique").textContent =
    new Set(S.records.map(r => r.id)).size.toLocaleString("tr-TR");

  $("pre").textContent =
    S.records.filter(r => r.verified).length.toLocaleString("tr-TR");

  $("flagged").textContent =
    S.records.filter(r => !r.verified).length.toLocaleString("tr-TR");

  $("meta").textContent =
    "Kaynak: " + S.source +
    " • Model olasılıkları başarı oranı değildir";

  $("notice").textContent =
    S.filtered.length +
    " kayıt eşleşti. Yalnızca dosyadaki gerçek model yüzdeleri gösterilir.";

  $("page").textContent = S.page + 1 + " / " + pages;
  $("prev").disabled = S.page === 0;
  $("next").disabled = S.page >= pages - 1;
}

async function load() {
  $("status").textContent = "Dosya yükleniyor";

  try {
    const response = await fetch("./panel_tahminler.json", {
      cache: "no-store"
    });

    if (!response.ok) throw Error("HTTP " + response.status);

    const data = await response.json();
    S.records = arr(data).map(normalize).filter(Boolean);
    S.source = "panel_tahminler.json";
    S.page = 0;

    render();

    $("status").textContent = S.records.length
      ? "Dosya okundu"
      : "Kayıt bulunamadı";

  } catch (err) {
    S.records = [];
    S.source = "yüklenemedi";
    render();
    $("status").textContent = "Veri hatası";
    $("notice").textContent = "panel_tahminler.json okunamadı.";
  }
}

function exportCsv() {
  const fields = [
    "Lig",
    "Maç",
    "Başlangıç UTC",
    ...LINES.map(line => line + " ÜST %"),
    "Kayıt durumu"
  ];

  const lines = [
    fields,
    ...S.filtered.map(r => [
      r.league,
      r.name,
      r.kickoff,
      ...LINES.map(line => r.probabilities[line] ?? ""),
      r.verified ? "Maç öncesi" : "İnceleme gerekli"
    ])
  ];

  const csv = "\uFEFF" + lines
    .map(line => line.map(v =>
      '"' + String(v ?? "").replace(/"/g, '""') + '"'
    ).join(","))
    .join("\r\n");

  const url = URL.createObjectURL(
    new Blob([csv], { type: "text/csv;charset=utf-8" })
  );

  const a = document.createElement("a");
  a.href = url;
  a.download = "tipster-pro-filtreli-tahminler.csv";
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

for (const id of ["search", "market", "valid", "sort"]) {
  $(id).addEventListener(
    id === "search" ? "input" : "change",
    () => {
      S.page = 0;
      render();
    }
  );
}

$("refresh").addEventListener("click", load);
$("export").addEventListener("click", exportCsv);

$("prev").addEventListener("click", () => {
  if (S.page > 0) {
    S.page--;
    render();
  }
});

$("next").addEventListener("click", () => {
  if ((S.page + 1) * S.size < S.filtered.length) {
    S.page++;
    render();
  }
});

for (const [id, adet] of [["top5", 5], ["top10", 10], ["top20", 20]]) {
  $(id).addEventListener("click", () => {
    const liste = topTahminler(adet);
    const secilenler = new Set(liste.map(r => r.id));

    $("search").value = "";
    $("market").value = "all";
    $("valid").value = "pre";
    $("sort").value = "prob";

    S.page = 0;
    render();

    S.filtered = liste.filter(r => secilenler.has(r.id));
    S.page = 0;
    S.size = 40;

    const tbody = $("rows");
    tbody.replaceChildren();

    for (const r of S.filtered) {
      const tr = document.createElement("tr");
      td(tr, r.name);
      

      const final = r.topSecim;

const cell = td(
  tr,
  final.line + " ÜST"
);
cell.style.color = "#22c55e";
cell.style.fontWeight = "bold";
td(tr, new Date(r.start).toISOString().slice(0, 16).replace("T", " "));
      td(tr, "Maç öncesi kayıt");
      tbody.append(tr);
    }

    $("notice").textContent =
      "TOP " + adet + ": " + liste.length +
      " maç. Başlamamış ve doğrulanmış kayıtlar, model yüzdesine göre sıralandı.";
    $("page").textContent = "1 / 1";
    $("prev").disabled = true;
    $("next").disabled = true;
  });
}

$("topall").addEventListener("click", () => {
  S.page = 0;
  render();
});

load();


// Result report is separate from model probabilities. Historical unselected
// matches must never contribute to the realized win/loss rate.
let resultRecords = [];
function resultRate(records) {
  const graded = records.filter(r => r.tahmin_sonucu === "DOGRU" || r.tahmin_sonucu === "YANLIS");
  if (!graded.length) return "Henüz yok";
  const wins = graded.filter(r => r.tahmin_sonucu === "DOGRU").length;
  return (100 * wins / graded.length).toFixed(1) + "% (" + graded.length + ")";
}
function resultRender() {
  const body = $("result-rows");
  const filter = $("result-filter").value;
  const rows = resultRecords.filter(r => {
    if (filter === "all") return true;
    if (filter === "BEKLIYOR") return r.durum !== "DOGRULANDI";
    if (filter === "DEGERLENDIRILMEDI") return r.durum === "DOGRULANDI" && !r.tahmin_sonucu;
    return r.tahmin_sonucu === filter;
  }).sort((a, b) => (dateNum(b.mac?.tarih) ?? 0) - (dateNum(a.mac?.tarih) ?? 0));
  body.replaceChildren();
  for (const r of rows.slice(0, 120)) {
    const tr = document.createElement("tr");
    const m = r.mac || {};
    td(tr, [m.ev_sahibi || "?", m.deplasman || "?"].join(" - "));
    td(tr, String(m.tarih || "").slice(0, 16).replace("T", " "));
    td(tr, r.kilitli_secim ? r.kilitli_secim.replace(" UST", " ÜST") : "Önceden seçim yok");
    td(tr, r.sonuc?.skor || "—");
    const status = r.tahmin_sonucu === "DOGRU" ? "✅ DOĞRU"
      : r.tahmin_sonucu === "YANLIS" ? "❌ YANLIŞ"
      : r.durum === "DOGRULANDI" ? "— (hesaba dahil değil)" : "⏳ BEKLİYOR";
    const cell = td(tr, status);
    cell.className = r.tahmin_sonucu === "DOGRU" ? "result-ok"
      : r.tahmin_sonucu === "YANLIS" ? "result-bad" : "result-pending";
    body.append(tr);
  }
  if (!rows.length) {
    const tr = document.createElement("tr");
    const cell = td(tr, "Bu filtrede kayıt bulunamadı.");
    cell.colSpan = 5;
    body.append(tr);
  }
  $("result-note").textContent = rows.length + " kayıt eşleşti; en yeni 120 kayıt gösteriliyor. Başarı yalnızca önceden kilitlenmiş seçimlerden hesaplanır.";
}
async function loadResults() {
  const note = $("result-note");
  try {
    const response = await fetch("./v18_dogrulanan_sonuclar.json", {cache:"no-store"});
    if (!response.ok) throw Error("HTTP " + response.status);
    const data = await response.json();
    if (!Array.isArray(data.kayitlar)) throw Error("Geçersiz sonuç dosyası");
    resultRecords = data.kayitlar.filter(r => r && typeof r === "object" && !Array.isArray(r));
    const completed = resultRecords.filter(r => r.durum === "DOGRULANDI" && r.sonuc);
    const wins = completed.filter(r => r.tahmin_sonucu === "DOGRU").length;
    const losses = completed.filter(r => r.tahmin_sonucu === "YANLIS").length;
    $("wins").textContent = wins;
    $("losses").textContent = losses;
    $("finished").textContent = completed.length;
    $("pending").textContent = resultRecords.length - completed.length;
    $("ungraded").textContent = completed.length - wins - losses;
    $("winrate").textContent = resultRate(completed);
    const now = Date.now();
    const beginningToday = Math.floor(now / 86400000) * 86400000;
    function periodSince(start) {
      return resultRate(completed.filter(r => {
        const t = dateNum(r.mac?.tarih);
        return t !== null && t >= start && t <= now;
      }));
    }
    $("todayrate").textContent = periodSince(beginningToday);
    $("weekrate").textContent = periodSince(now - 7 * 86400000);
    $("monthrate").textContent = periodSince(now - 30 * 86400000);
    resultRender();
    render();
  } catch (err) {
    resultRecords = [];
    note.textContent = "Sonuç raporu henüz yayımlanmadı veya okunamadı. Model tahminleri başarı sonucu sayılmaz.";
    for (const id of ["wins","losses","finished","pending","ungraded","winrate","todayrate","weekrate","monthrate"]) $(id).textContent = "—";
    $("result-rows").replaceChildren();
  }
}
$("result-filter").addEventListener("change", resultRender);
$("refresh").addEventListener("click", loadResults);
loadResults();
