
"use strict";

/*
  TIPSTER PRO V18
  PANEL.JS — ASLAN SONUC VE TAHMIN PANELI

  - Mevcut tahmin JSON dosyalarini okur.
  - Tahmin motoruna mudahale etmez.
  - Kilitli tahminleri onceliklendirir.
  - Model yuzdelerini degistirmez.
  - ASLAN renk sistemi:
      80 - 100   : Yesil
      70 - 79.9  : Kahverengi
      50 - 69.9  : Normal
       0 - 49.9  : Gri
  - Gercek basari oranini yalnizca
    sonuclanmis kilitli tahminlerden hesaplar.
*/

const $ = id => document.getElementById(id);

const LINES = [
  "1.5", "2.5", "3.5",
  "4.5", "5.5", "6.5"
];

const COLORS = Object.freeze({
  green: "#22c55e",
  brown: "#c46a35",
  grey: "#94a3b8",
  red: "#ef4444"
});

const THRESHOLDS = Object.freeze({
  "1.5": 75,
  "2.5": 65,
  "3.5": 65,
  "4.5": 65,
  "5.5": 65,
  "6.5": 65
});

const S = {
  records: [],
  filtered: [],
  page: 0,
  size: 40,
  source: "",
  topLimit: null,
  onlyFinal: false
};

let resultRecords = [];
let aslanRecords = [];

/* ======================================
   TEMEL YARDIMCI FONKSIYONLAR
====================================== */

function keys(obj, names) {
  if (!obj || typeof obj !== "object") {
    return null;
  }

  for (const key of names) {
    const value = obj[key];

    if (
      value !== undefined &&
      value !== null &&
      value !== ""
    ) {
      return value;
    }
  }

  return null;
}

function dateNum(value) {
  const n = Date.parse(String(value || ""));

  return Number.isFinite(n) ? n : null;
}

function pct(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const n = Number(
    String(value)
      .replace("%", "")
      .replace(",", ".")
      .trim()
  );

  return (
    Number.isFinite(n) &&
    n >= 0 &&
    n <= 100
  ) ? n : null;
}

function arr(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (!data || typeof data !== "object") {
    return [];
  }

  for (const key of [
    "tahminler",
    "maclar",
    "predictions",
    "matches",
    "records",
    "data"
  ]) {
    if (Array.isArray(data[key])) {
      return data[key];
    }
  }

  return [];
}

function td(row, value) {
  const cell = document.createElement("td");
  cell.textContent = String(value ?? "");
  row.appendChild(cell);
  return cell;
}

function setText(id, value) {
  const element = $(id);

  if (element) {
    element.textContent = String(value);
  }
}

function aramaMetni(value) {
  return String(value || "")
    .toLocaleLowerCase("tr-TR")
    .replace(/ı/g, "i")
    .replace(/ğ/g, "g")
    .replace(/ü/g, "u")
    .replace(/ş/g, "s")
    .replace(/ö/g, "o")
    .replace(/ç/g, "c");
}

function tarihYaz(value) {
  if (!value) {
    return "Tarih yok";
  }

  const n = dateNum(value);

  if (n === null) {
    return String(value)
      .slice(0, 16)
      .replace("T", " ");
  }

  return new Date(n)
    .toISOString()
    .slice(0, 16)
    .replace("T", " ");
}

/* ======================================
   RENK MOTORU
====================================== */

function tahminRengi(value) {
  const n = pct(value);

  if (n === null) {
    return "";
  }

  if (n >= 80) {
    return COLORS.green;
  }

  if (n >= 70) {
    return COLORS.brown;
  }

  if (n < 50) {
    return COLORS.grey;
  }

  return "";
}

function tahminStili(cell, value) {
  if (!cell) {
    return;
  }

  const color = tahminRengi(value);

  cell.style.color = color;
  cell.style.fontWeight = color ? "700" : "400";
}

function tahminMetni(line, value) {
  const probability = pct(value);

  const market = String(line || "")
    .replace(/\bUST\b/gi, "ÜST")
    .replace(/\bOVER\b/gi, "ÜST");

  if (probability === null) {
    return market || "—";
  }

  return market + " — %" +
    probability.toFixed(1);
}

/* ======================================
   TAHMIN NORMALIZASYONU
====================================== */

function normalize(x, index) {
  if (
    !x ||
    typeof x !== "object" ||
    Array.isArray(x)
  ) {
    return null;
  }

  const home = keys(x, [
    "ev_sahibi",
    "ev",
    "home_team",
    "home",
    "takim1"
  ]);

  const away = keys(x, [
    "deplasman",
    "dep",
    "away_team",
    "away",
    "takim2"
  ]);

  const name = keys(x, [
    "mac", "maç", "match", "fixture"
  ]) || [home, away]
    .filter(Boolean)
    .join(" - ");

  const league = String(
    keys(x, [
      "lig",
      "league",
      "lig_adi",
      "lig_kodu"
    ]) || "Bilinmeyen lig"
  );

  const kickoff = keys(x, [
    "tarih",
    "date",
    "kickoff",
    "baslama_zamani",
    "start_time"
  ]);

  const made = keys(x, [
    "hesaplama_zamani",
    "hesaplama_zamani_utc",
    "created_at",
    "created_utc",
    "prediction_time"
  ]);

  const prediction = keys(x, [
    "tahmin",
    "prediction",
    "karar",
    "secim",
    "market"
  ]);

  const embedded = (
    prediction &&
    typeof prediction === "object" &&
    !Array.isArray(prediction)
  ) ? prediction : {};

  const probs = keys(x, [
    "olasiliklar",
    "probabilities"
  ]) || {};

  const marketText = (
    typeof prediction === "string"
  ) ? prediction : "";

  const probabilities = {};

  for (const line of LINES) {
    const key = line + "_ust";

    probabilities[line] = pct(
      keys(probs, [
        key,
        line + "_over"
      ]) ??
      keys(embedded, [
        key,
        line + "_over"
      ]) ??
      keys(x, [
        key,
        line + "_over"
      ])
    );
  }

  const general = pct(keys(x, [
    "olasilik",
    "probability",
    "guven",
    "confidence",
    "yuzde"
  ]));

  const marketMatch = marketText.match(
    /([1-6][.,]5)\s*(?:ÜST|UST|OVER)/i
  );

  const selected = marketMatch
    ? marketMatch[1].replace(",", ".")
    : null;

  if (
    selected &&
    probabilities[selected] === null
  ) {
    probabilities[selected] = general;
  }

  const start = dateNum(kickoff);
  const created = dateNum(made);

  const verified = (
    start !== null &&
    created !== null &&
    created < start
  );

  const id = [
    league,
    String(home || name || ""),
    String(away || ""),
    String(kickoff || "")
  ]
    .join("|")
    .toLocaleLowerCase("tr-TR");

  return {
    id,
    name: String(name || "Maç adı yok"),
    league,
    kickoff: String(kickoff || ""),
    start,
    created,
    verified,
    risk: !verified,
    marketText,
    probabilities,
    selected,
    index,
    archiveChoice: x.kilitli_secim || null,
    sourceId: String(
      keys(x, ["id"]) || ""
    ),
    leagueCode: String(
      keys(x, ["lig_kodu"]) || ""
    )
  };
}

/* ======================================
   KILITLI TAHMIN BULMA
====================================== */

function finalChoice(r) {
  if (!r.verified) {
    return null;
  }

  const choice = String(
    r.archiveChoice || ""
  )
    .trim()
    .toUpperCase()
    .replace(/Ü/g, "U")
    .replace(/\s+/g, " ");

  if (choice === "RISKLI") {
    return {
      risk: true,
      locked: true
    };
  }

  const match = /^([1-6]\.5) UST$/
    .exec(choice);

  if (match) {
    const line = match[1];

    const probability = r.probabilities[line];

    return {
      line,
      probability,
      risk: false,
      locked: true
    };
  }


  return {
    risk: true,
    locked: false
  };
}

function chosen(r) {
  const market = $("market")?.value || "all";

  if (market !== "all") {
    return [
      market,
      r.probabilities[market] ?? null
    ];
  }

  const available = LINES
    .map(line => [
      line,
      r.probabilities[line]
    ])
    .filter(item => item[1] !== null);

  if (!available.length) {
    return ["", null];
  }

  available.sort(
    (a, b) => b[1] - a[1]
  );

  return available[0];
}

/* ======================================
   TOP TAHMINLER
====================================== */

function topTahminler(adet) {
  const now = Date.now();

  return S.records
    .filter(r =>
      r.verified &&
      r.start !== null &&
      r.start > now
    )
    .map(r => ({
      ...r,
      topSecim: finalChoice(r)
    }))
    .filter(r =>
      r.topSecim &&
      !r.topSecim.risk &&
      r.topSecim.line &&
      r.topSecim.probability !== null &&
      Number.isFinite(
        r.topSecim.probability
      )
    )
    .sort(
      (a, b) =>
        b.topSecim.probability -
        a.topSecim.probability
    )
    .slice(0, adet);
}

/* ======================================
   ANA TAHMIN TABLOSU
====================================== */

function tahminSatiriOlustur(r) {
  const tr = document.createElement("tr");

  const first = td(tr, r.name);

  const league = document.createElement("div");

  league.className = "muted";
  league.textContent = r.league;

  first.appendChild(league);

  const final = finalChoice(r);

  const finalCell = td(tr, "");

  if (
    final &&
    !final.risk &&
    final.line
  ) {
    finalCell.textContent = tahminMetni(
      final.line + " ÜST",
      final.probability
    );

    tahminStili(
      finalCell,
      final.probability
    );

    if (!final.locked) {
      finalCell.title =
        "Model önerisi; kilitli seçim değil";
    }
  } else {
    finalCell.textContent = "RİSKLİ";
    finalCell.style.color = COLORS.grey;
  }

  td(tr, tarihYaz(r.kickoff));

  for (const line of LINES) {
    const value = r.probabilities[line];

    const cell = td(
      tr,
      value !== null
        ? "%" + value.toFixed(1)
        : "—"
    );

    if (value !== null) {
      cell.className = "probability";
    }
  }

  const state = td(tr, "");

  const pill = document.createElement("span");

  pill.className =
    "pill" + (r.risk ? " review" : "");

  pill.textContent = r.verified
    ? "Maç öncesi kayıt"
    : "İnceleme gerekli";

  state.appendChild(pill);

  return tr;
}

function render() {
  const tbody = $("rows");

  if (!tbody) {
    return;
  }

  const query = aramaMetni(
    $("search")?.value?.trim() || ""
  );

  const market = $("market")?.value || "all";
  const valid = $("valid")?.value || "all";
  const sort = $("sort")?.value || "date";

  let records = S.records.filter(r => {
    const searchText = aramaMetni(
      r.name + " " + r.league
    );

    const marketOk = (
      market === "all" ||
      r.probabilities[market] !== null
    );

    const validOk = (
      valid === "all" ||
      (
        valid === "pre"
          ? r.verified
          : !r.verified
      )
    );

    return (
      searchText.includes(query) &&
      marketOk &&
      validOk
    );
  });

  records.sort((a, b) => {
    if (sort === "prob") {
      return (
        (chosen(b)[1] ?? -1) -
        (chosen(a)[1] ?? -1)
      );
    }

    if (sort === "league") {
      return a.league.localeCompare(
        b.league,
        "tr"
      );
    }

    return (
      (a.start ?? Infinity) -
      (b.start ?? Infinity)
    );
  });

  if (S.topLimit !== null) {
    const top = topTahminler(S.topLimit);
    const selected = new Set(
      top.map(r => r.index)
    );

    records = top.filter(
      r => selected.has(r.index)
    );
  }

  S.filtered = records;

  const pages = Math.max(
    1,
    Math.ceil(records.length / S.size)
  );

  S.page = Math.max(
    0,
    Math.min(S.page, pages - 1)
  );

  tbody.replaceChildren();

  const visible = records.slice(
    S.page * S.size,
    (S.page + 1) * S.size
  );

  for (const r of visible) {
    tbody.appendChild(
      tahminSatiriOlustur(r)
    );
  }

  setText(
    "total",
    S.records.length.toLocaleString("tr-TR")
  );

  setText(
    "unique",
    new Set(
      S.records.map(r => r.id)
    ).size.toLocaleString("tr-TR")
  );

  setText(
    "pre",
    S.records
      .filter(r => r.verified)
      .length.toLocaleString("tr-TR")
  );

  setText(
    "flagged",
    S.records
      .filter(r => !r.verified)
      .length.toLocaleString("tr-TR")
  );

  setText(
    "meta",
    "Kaynak: " + S.source +
    " • Model olasılıkları başarı oranı değildir"
  );

  setText(
    "notice",
    S.topLimit !== null
      ? "TOP " + S.topLimit +
        ": " + records.length +
        " maç gösteriliyor."
      : records.length +
        " kayıt eşleşti. Gerçek model yüzdeleri gösterilir."
  );

  setText(
    "page",
    (S.page + 1) + " / " + pages
  );

  if ($("prev")) {
    $("prev").disabled = S.page === 0;
  }

  if ($("next")) {
    $("next").disabled =
      S.page >= pages - 1;
  }
}

/* ======================================
   ANA VERI YUKLEME
====================================== */

async function load() {
  setText("status", "Dosya yükleniyor");

  try {
    const response = await fetch(
      "./panel_tahminler.json",
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error(
        "HTTP " + response.status
      );
    }

    const data = await response.json();

    S.records = arr(data)
      .map(normalize)
      .filter(Boolean);

    S.source = "panel_tahminler.json";
    S.page = 0;

    render();

    setText(
      "status",
      S.records.length
        ? "Dosya okundu"
        : "Kayıt bulunamadı"
    );

  } catch (err) {
    console.error(
      "Panel veri hatası:",
      err
    );

    S.records = [];
    S.source = "yüklenemedi";

    render();

    setText("status", "Veri hatası");

    setText(
      "notice",
      "panel_tahminler.json okunamadı."
    );
  }
}

/* ======================================
   CSV DISA AKTARMA
====================================== */

function exportCsv() {
  const fields = [
    "Lig",
    "Maç",
    "Başlangıç UTC",
    "Tahmin",
    "Model yüzdesi",
    ...LINES.map(
      line => line + " ÜST %"
    ),
    "Kayıt durumu"
  ];

  const rows = S.filtered.map(r => {
    const final = finalChoice(r);

    return [
      r.league,
      r.name,
      r.kickoff,
      final && !final.risk
        ? final.line + " ÜST"
        : "RİSKLİ",
      final && !final.risk
        ? final.probability ?? ""
        : "",
      ...LINES.map(
        line => r.probabilities[line] ?? ""
      ),
      r.verified
        ? "Maç öncesi"
        : "İnceleme gerekli"
    ];
  });

  const csv = "\uFEFF" +
    [fields, ...rows]
      .map(row =>
        row.map(value =>
          '"' +
          String(value ?? "")
            .replace(/"/g, '""') +
          '"'
        ).join(",")
      )
      .join("\r\n");

  const blob = new Blob(
    [csv],
    {
      type: "text/csv;charset=utf-8"
    }
  );

  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");

  a.href = url;
  a.download =
    "tipster-pro-v18-tahminler.csv";

  document.body.appendChild(a);
  a.click();
  a.remove();

  setTimeout(
    () => URL.revokeObjectURL(url),
    1000
  );
}

/* ======================================
   SONUC VE BASARI RAPORLARI
====================================== */

function resultRate(records) {
  const graded = records.filter(
    r =>
      r.tahmin_sonucu === "DOGRU" ||
      r.tahmin_sonucu === "YANLIS"
  );

  if (!graded.length) {
    return "Henüz yok";
  }

  const wins = graded.filter(
    r => r.tahmin_sonucu === "DOGRU"
  ).length;

  return (
    100 * wins / graded.length
  ).toFixed(1) +
    "% (" + graded.length + ")";
}

function resultRender() {
  const body = $("result-rows");

  if (!body) {
    return;
  }

  const filter =
    $("result-filter")?.value || "all";

  const rows = resultRecords
    .filter(r => {
      if (filter === "all") {
        return true;
      }

      if (filter === "BEKLIYOR") {
        return r.durum !== "DOGRULANDI";
      }

      if (filter === "DEGERLENDIRILMEDI") {
        return (
          r.durum === "DOGRULANDI" &&
          !r.tahmin_sonucu
        );
      }

      return r.tahmin_sonucu === filter;
    })
    .sort((a, b) =>
      (dateNum(b.mac?.tarih) ?? 0) -
      (dateNum(a.mac?.tarih) ?? 0)
    );

  body.replaceChildren();

  for (const r of rows) {
    const tr = document.createElement("tr");

    const m = r.mac || {};

    td(
      tr,
      [
        m.ev_sahibi || "?",
        m.deplasman || "?"
      ].join(" - ")
    );

    td(
      tr,
      String(m.tarih || "")
        .slice(0, 16)
        .replace("T", " ")
    );

    const selection = String(
      r.kilitli_secim || ""
    );

    td(
      tr,
      selection
        ? selection
            .replace(/ UST/g, " ÜST")
            .replace(/RISKLI/g, "RİSKLİ")
        : "Önceden seçim yok"
    );

    td(tr, r.sonuc?.skor || "—");

    const status =
      r.tahmin_sonucu === "DOGRU"
        ? "✅ DOĞRU"
      : r.tahmin_sonucu === "YANLIS"
        ? "❌ YANLIŞ"
      : r.durum === "DOGRULANDI"
        ? "— (hesaba dahil değil)"
        : "⏳ BEKLİYOR";

    const cell = td(tr, status);

    cell.className =
      r.tahmin_sonucu === "DOGRU"
        ? "result-ok"
      : r.tahmin_sonucu === "YANLIS"
        ? "result-bad"
        : "result-pending";

    body.appendChild(tr);
  }

  if (!rows.length) {
    const tr = document.createElement("tr");
    const cell = td(
      tr,
      "Bu filtrede kayıt bulunamadı."
    );

    cell.colSpan = 5;
    body.appendChild(tr);
  }

  setText(
    "result-note",
    rows.length +
    " kayıt eşleşti; tüm eşleşmeler gösteriliyor. " +
    "Başarı yalnızca kilitli ve değerlendirilmiş seçimlerden hesaplanır."
  );
}

async function loadResults() {
  try {
    const response = await fetch(
      "./v18_dogrulanan_sonuclar.json",
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error(
        "HTTP " + response.status
      );
    }

    const data = await response.json();

    if (!Array.isArray(data.kayitlar)) {
      throw new Error(
        "Geçersiz sonuç dosyası"
      );
    }

    resultRecords = data.kayitlar.filter(
      r =>
        r &&
        typeof r === "object" &&
        !Array.isArray(r)
    );

    const completed = resultRecords.filter(
      r =>
        r.durum === "DOGRULANDI" &&
        r.sonuc
    );

    const wins = completed.filter(
      r => r.tahmin_sonucu === "DOGRU"
    ).length;

    const losses = completed.filter(
      r => r.tahmin_sonucu === "YANLIS"
    ).length;

    setText("wins", wins);
    setText("losses", losses);
    setText("finished", completed.length);

    setText(
      "pending",
      resultRecords.length -
        completed.length
    );

    setText(
      "ungraded",
      completed.length -
        wins -
        losses
    );

    setText(
      "winrate",
      resultRate(completed)
    );

    const now = Date.now();

    const beginningToday =
      Math.floor(now / 86400000) *
      86400000;

    function periodSince(start) {
      return resultRate(
        completed.filter(r => {
          const t = dateNum(
            r.mac?.tarih
          );

          return (
            t !== null &&
            t >= start &&
            t <= now
          );
        })
      );
    }

    setText(
      "todayrate",
      periodSince(beginningToday)
    );

    setText(
      "weekrate",
      periodSince(
        now - 7 * 86400000
      )
    );

    setText(
      "monthrate",
      periodSince(
        now - 30 * 86400000
      )
    );

    resultRender();
    render();

  } catch (err) {
    console.error(
      "Sonuç dosyası hatası:",
      err
    );

    resultRecords = [];

    setText(
      "result-note",
      "Sonuç raporu henüz okunamadı."
    );

    for (const id of [
      "wins",
      "losses",
      "finished",
      "pending",
      "ungraded",
      "winrate",
      "todayrate",
      "weekrate",
      "monthrate"
    ]) {
      setText(id, "—");
    }

    $("result-rows")?.replaceChildren();
    render();
  }
}

/* ======================================
   ASLAN MODU — SONUC PANELI
====================================== */

function aslanSonucPaneliKur() {
  const section = $("aslan-modu");

  if (!section) {
    return;
  }

  $("aslan-durum")?.remove();

  let panel = $("aslan-sonuc-paneli");

  if (!panel) {
    panel = document.createElement("div");
    panel.id = "aslan-sonuc-paneli";

    panel.innerHTML = `
      <h3>🦁 ASLAN MODU — Gerçek sonuçlar</h3>

      <p class="muted">
        Yalnızca maç başlamadan önce kilitlenen
        ASLAN tahminleri değerlendirilir.
      </p>

      <div class="result-summary">
        <span>🟢 Güçlü tahmin:
          <strong id="aslan-yesil">—</strong>
        </span>

        <span>🟡 Orta güven:
          <strong id="aslan-sari">—</strong>
        </span>

        <span>⚪ Normal:
          <strong id="aslan-normal">—</strong>
        </span>

        <span>✅ Doğru:
          <strong id="aslan-dogru">—</strong>
        </span>

        <span>❌ Yanlış:
          <strong id="aslan-yanlis">—</strong>
        </span>

        <span>⏳ Bekleyen:
          <strong id="aslan-bekleyen">—</strong>
        </span>

        <span>Başarı:
          <strong id="aslan-basari">—</strong>
        </span>
      </div>

      <p
        class="muted"
        id="aslan-sonuc-bilgi"
      >
        ASLAN sonuçları yükleniyor...
      </p>

      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>Maç</th>
              <th>Kilitli tahmin</th>
              <th>Skor</th>
              <th>Sonuç</th>
            </tr>
          </thead>

          <tbody
            id="aslan-sonuc-satirlari"
          ></tbody>
        </table>
      </div>
    `;

    const discovery =
      $("aslan-kesif-ekrani");

    if (discovery) {
      section.insertBefore(
        panel,
        discovery
      );
    } else {
      section.appendChild(panel);
    }
  }

  aslanSonuclariniYukle();
}

/* ======================================
   ASLAN KESIF RENKLERI
====================================== */

function kesifRenkleriniUygula() {
  const table = $("aslan-tablo");

  if (!table) {
    return;
  }

  for (const row of table.rows) {
    const cells = row.cells;

    if (cells.length !== 5) {
      continue;
    }

    const value = pct(
      cells[3].textContent
    );

    if (value === null) {
      continue;
    }

    for (const index of [2, 3]) {
      tahminStili(
        cells[index],
        value
      );
    }
  }
}

function kesifTakibiniBaslat() {
  const table = $("aslan-tablo");

  if (!table) {
    return;
  }

  const observer = new MutationObserver(
    () => kesifRenkleriniUygula()
  );

  observer.observe(table, {
    childList: true,
    subtree: true
  });

  kesifRenkleriniUygula();
}

/* ======================================
   ASLAN GERCEK SONUCLAR
====================================== */

async function aslanSonuclariniYukle() {
  const tbody =
    $("aslan-sonuc-satirlari");

  if (!tbody) {
    return;
  }

  try {
    const response = await fetch(
      "./aslan_dogrulanan_sonuclar.json?t=" +
        Date.now(),
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error(
        "HTTP " + response.status
      );
    }

    const data = await response.json();

    if (!Array.isArray(data.kayitlar)) {
      throw new Error(
        "Geçersiz ASLAN sonuç dosyası"
      );
    }

    aslanRecords = data.kayitlar.filter(
      r =>
        r &&
        typeof r === "object" &&
        !Array.isArray(r)
    );

    const countClass = type =>
      aslanRecords.filter(
        r => r.guven_sinifi === type
      ).length;

    const graded = aslanRecords.filter(
      r =>
        r.durum === "DOGRULANDI" &&
        (
          r.tahmin_sonucu === "DOGRU" ||
          r.tahmin_sonucu === "YANLIS"
        )
    );

    const wins = graded.filter(
      r => r.tahmin_sonucu === "DOGRU"
    ).length;

    const losses = graded.length - wins;

    const pending = aslanRecords.filter(
      r => r.durum === "BEKLIYOR"
    ).length;

    setText(
      "aslan-yesil",
      countClass("YESIL")
    );

    setText(
      "aslan-sari",
      countClass("SARI")
    );

    setText(
      "aslan-normal",
      countClass("NORMAL")
    );

    setText("aslan-dogru", wins);
    setText("aslan-yanlis", losses);
    setText("aslan-bekleyen", pending);

    setText(
      "aslan-basari",
      graded.length
        ? (
          100 * wins / graded.length
        ).toFixed(1) + "%"
        : "Henüz yok"
    );

    setText(
      "aslan-sonuc-bilgi",
      "Kilitli tahmin: " +
        aslanRecords.length +
      " | Değerlendirilen: " +
        graded.length +
      " | Başarı yalnızca gerçek sonuçlardan hesaplanır."
    );

    const sorted = [...aslanRecords]
      .sort((a, b) =>
        String(
          b.tarih || ""
        ).localeCompare(
          String(a.tarih || "")
        )
      );

    tbody.replaceChildren();

    for (const r of sorted.slice(0, 120)) {
      const row = document.createElement("tr");

      td(
        row,
        String(r.ev_sahibi || "?") +
          " - " +
          String(r.deplasman || "?")
      );

      const probability =
        pct(r.model_yuzdesi);

      const choice = String(
        r.tahmin || "—"
      )
        .replace(/\bUST\b/gi, "ÜST")
        .replace(/RISKLI/gi, "RİSKLİ");

      const predictionCell = td(
        row,
        tahminMetni(
          choice,
          probability
        )
      );

      if (
        choice.toLocaleUpperCase("tr-TR")
          .includes("RİSKLİ")
      ) {
        predictionCell.style.color =
          COLORS.grey;

        predictionCell.style.fontWeight =
          "400";
      } else {
        tahminStili(
          predictionCell,
          probability
        );
      }

      td(
        row,
        r.skor || "—"
      );

      let result = "⏳ BEKLİYOR";

      if (
        r.durum === "DOGRULANDI" &&
        r.tahmin_sonucu === "DOGRU"
      ) {
        result = "✅ DOĞRU";
      } else if (
        r.durum === "DOGRULANDI" &&
        r.tahmin_sonucu === "YANLIS"
      ) {
        result = "❌ YANLIŞ";
      } else if (
        r.durum === "INCELEME"
      ) {
        result = "İNCELEME";
      }

      const resultCell = td(
        row,
        result
      );

      if (result === "✅ DOĞRU") {
        resultCell.style.color =
          COLORS.green;
      }

      if (result === "❌ YANLIŞ") {
        resultCell.style.color =
          COLORS.red;
      }

      tbody.appendChild(row);
    }

    if (!sorted.length) {
      const row = document.createElement("tr");

      const cell = td(
        row,
        "Henüz kilitlenmiş ASLAN tahmini yok."
      );

      cell.colSpan = 4;
      tbody.appendChild(row);
    }

  } catch (err) {
    console.error(
      "ASLAN sonuç dosyası hatası:",
      err
    );

    setText(
      "aslan-sonuc-bilgi",
      "ASLAN sonuç dosyası okunamadı: " +
        err.message
    );
  }
}

/* ======================================
   KONTROLLER VE OLAYLAR
====================================== */

function bind(id, event, handler) {
  const element = $(id);

  if (element) {
    element.addEventListener(
      event,
      handler
    );
  }
}

function filtreyiSifirla() {
  S.page = 0;
  S.topLimit = null;
  render();
}

function init() {
  for (const id of [
    "search",
    "market",
    "valid",
    "sort"
  ]) {
    bind(
      id,
      id === "search"
        ? "input"
        : "change",
      filtreyiSifirla
    );
  }

  bind("refresh", "click", () => {
    load();
    loadResults();
    aslanSonuclariniYukle();
  });

  bind(
    "export",
    "click",
    exportCsv
  );

  bind("prev", "click", () => {
    if (S.page > 0) {
      S.page--;
      render();
    }
  });

  bind("next", "click", () => {
    if (
      (S.page + 1) * S.size <
      S.filtered.length
    ) {
      S.page++;
      render();
    }
  });

  for (const [id, amount] of [
    ["top5", 5],
    ["top10", 10],
    ["top20", 20]
  ]) {
    bind(id, "click", () => {
      S.topLimit = amount;
      S.page = 0;
      render();
    });
  }

  bind("topall", "click", () => {
    S.topLimit = null;
    S.page = 0;
    render();
  });

  bind(
    "result-filter",
    "change",
    resultRender
  );

  aslanSonucPaneliKur();
  kesifTakibiniBaslat();

  load();
  loadResults();
}

/* ======================================
   BASLAT
====================================== */

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    init,
    { once: true }
  );
} else {
  init();
}
/* MERSIN LAB - BAGIMSIZ PANEL */

async function mersinPanelKur() {
  if (document.getElementById("mersin-lab-panel")) return;

  const alan = document.createElement("section");
  alan.id = "mersin-lab-panel";
  alan.style.cssText =
    "margin:20px 10px;padding:16px;background:#111827;color:#fff;border:1px solid #334155;border-radius:12px";

  const baslik = document.createElement("h2");
  baslik.textContent = "MERSİN LAB V15";
  baslik.style.color = "#22c55e";
  alan.appendChild(baslik);

  const bilgi = document.createElement("p");
  bilgi.textContent = "Deneysel istatistik analizi - Veriler yükleniyor";
  alan.appendChild(bilgi);

  document.body.appendChild(alan);

  try {
    const url =
      "https://raw.githubusercontent.com/NECATIAKTU/mersin-lab/main/mersin_panel.json";

    const cevap = await fetch(url, {
      cache: "no-store"
    });

    if (!cevap.ok) throw new Error("JSON okunamadı");

    const veri = await cevap.json();

    const maclar = Array.isArray(veri)
      ? veri
      : Object.values(veri).find(x =>
          Array.isArray(x) &&
          x.some(m => m && m.ev_sahibi && m.deplasman)
        );

    if (!Array.isArray(maclar)) {
      throw new Error("Maç listesi bulunamadı");
    }

    const guncel = maclar.filter(m =>
      Date.parse(m.tarih) > Date.now()
    );

    const aktif = guncel.filter(m =>
      m.durum === "DENEYSEL" && m.olasiliklar
    ).length;

    bilgi.textContent =
      "DENEYSEL | Fikstür: " + guncel.length +
      " | Aktif: " + aktif +
      " | Yetersiz veri: " + (guncel.length - aktif);

    const kaydir = document.createElement("div");
    kaydir.style.overflowX = "auto";

    const tablo = document.createElement("table");
    tablo.style.cssText =
      "width:100%;border-collapse:collapse;font-size:13px";

    const cizgiler = [
      "1.5", "2.5", "3.5",
      "4.5", "5.5", "6.5"
    ];

    function satir(degerler, baslikMi = false) {
      const tr = document.createElement("tr");

      degerler.forEach(deger => {
        const td = document.createElement(
          baslikMi ? "th" : "td"
        );

        td.textContent = deger;
        td.style.cssText =
          "padding:10px;border-bottom:1px solid #334155;white-space:nowrap";

        tr.appendChild(td);
      });

      tablo.appendChild(tr);
      return tr;
    }

    satir([
      "Lig", "Maç",
      ...cizgiler.map(c => c + " ÜST"),
      "Durum"
    ], true);

    for (const mac of guncel) {
      const yuzdeler = cizgiler.map(c => {
        const p = mac.olasiliklar?.[c];

        return typeof p === "number" &&
          Number.isFinite(p) &&
          p >= 0 && p <= 100
          ? "%" + p.toFixed(2)
          : "—";
      });

      satir([
        mac.lig || "—",
        mac.ev_sahibi + " - " + mac.deplasman,
        ...yuzdeler,
        mac.durum === "DENEYSEL"
          ? "DENEYSEL"
          : "YETERSİZ VERİ"
      ]);
    }

    kaydir.appendChild(tablo);
    alan.appendChild(kaydir);

  } catch (hata) {
    bilgi.textContent =
      "MERSİN LAB veri bağlantısı kurulamadı.";
    console.error("MERSIN LAB:", hata);
  }
}

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded", mersinPanelKur,
    { once: true }
  );
} else {
  mersinPanelKur();
}
