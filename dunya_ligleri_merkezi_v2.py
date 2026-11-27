import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dunya_ligleri_merkezi_v1 import bolge_bul
from v18_lig_kapsam_denetimi import read_league_registry


SURUM = "DUNYA LIGLERI MERKEZI V2"


def oku(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def tarih(value):
    try:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        return None


def kimlik(mac):
    if not isinstance(mac, dict):
        raise ValueError("Gecersiz mac")

    lig = mac.get("lig_kodu")
    ev = mac.get("ev_sahibi")
    dep = mac.get("deplasman")
    dt = tarih(mac.get("tarih"))

    if not all(
        isinstance(x, str) and x.strip()
        for x in (lig, ev, dep)
    ) or dt is None:
        raise ValueError("Eksik mac kimligi")

    return (
        lig,
        ev.strip().casefold(),
        dep.strip().casefold(),
        dt.isoformat()
    )


def indeks(data, alan):
    if not isinstance(data, dict):
        raise ValueError("Gecersiz veri dosyasi")

    records = data.get(alan)

    if not isinstance(records, list):
        raise ValueError("Mac listesi bulunamadi")

    result = {}
    tekrar = 0

    for mac in records:
        key = kimlik(mac)

        if key in result:
            tekrar += 1
            continue

        result[key] = mac

    return result, tekrar


def analiz(registry, fikstur, model, panel):

    fs, ft = indeks(fikstur, "maclar")
    ms, mt = indeks(model, "tahminler")
    ps, pt = indeks(panel, "tahminler")

    now = tarih(panel.get("olusturulma_utc"))

    if now is None:
        raise ValueError("Panel zamani gecersiz")

    model_time = tarih(model.get("olusturulma_utc"))

    if model_time is None:
        raise ValueError("Model zamani gecersiz")

    audit = model.get("lig_denetimi", {})
    kaynak = fikstur.get("lig_sayilari", {})
    ertelenen = set(fikstur.get("ertelenen_ligler", []))

    hatalar = Counter(
        x.get("lig")
        for x in fikstur.get("hatalar", [])
        if isinstance(x, dict)
    )

    eksikler = []
    sayac = Counter()
    lig_sayac = Counter()

    for key, mac in fs.items():

        lig = key[0]
        kickoff = tarih(mac["tarih"])

        if kickoff <= model_time:
            durum = "MODEL_ONCESI_BASLAMIS"

        elif kickoff <= now:
            durum = "YAYIN_ONCESI_BASLAMIS"

        elif key in ms and key in ps:
            durum = "PANELDE_VAR"

        elif key in ps:
            durum = "ESKI_ARSIVDEN_PANELDE"

        elif key in ms:
            durum = "MODELDE_VAR_PANELDE_YOK"

        elif audit.get(lig, {}).get("durum") == "YETERSIZ_VERI":
            durum = "GECMIS_VERI_YETERSIZ"

        else:
            durum = "MODELDE_YOK_NEDEN_BELIRSIZ"

        sayac[durum] += 1
        lig_sayac[(lig, durum)] += 1

        if durum not in (
            "PANELDE_VAR",
            "ESKI_ARSIVDEN_PANELDE"
        ):
            eksikler.append({
                **mac,
                "teshis": durum
            })

    fcounts = Counter(k[0] for k in fs)
    mcounts = Counter(k[0] for k in ms)
    pcounts = Counter(k[0] for k in ps)

    ligler = []

    for lig in sorted(
        set(registry) | set(fcounts)
        | set(mcounts) | set(pcounts)
    ):

        bilgi = audit.get(lig, {})

        if lig in ertelenen:
            durum = "AKTIF_DEGIL"

        elif hatalar[lig]:
            durum = "KAYNAK_HATASI_VAR"

        elif fcounts[lig]:
            durum = "FIKSTUR_VAR"

        elif lig in kaynak:
            durum = "FIKSTUR_BOS"

        else:
            durum = "TARAMA_DOGRULANMADI"

        ligler.append({
            "lig_kodu": lig,
            "lig": registry.get(lig, lig),
            "bolge": bolge_bul(lig),
            "kaynak_durumu": durum,
            "fikstur_mac": fcounts[lig],
            "model_mac": mcounts[lig],
            "panel_mac": pcounts[lig],
            "kaynak_hatasi": hatalar[lig],
            "gecmis_mac": bilgi.get("tamamlanmis_mac"),
            "gecmis_hata_gunu": bilgi.get("hata_gunu"),
            "mac_durumlari": {
                d: n
                for (l, d), n in lig_sayac.items()
                if l == lig
            }
        })

    eligible = {
        k for k, mac in fs.items()
        if tarih(mac["tarih"]) > now
    }

    return {
        "surum": SURUM,
        "tarih_utc": now.isoformat(),
        "toplam_tanimli_lig": len(registry),
        "fikstur_mac": len(fs),
        "model_mac": len(ms),
        "panel_mac": len(ps),
        "panel_lig": len(pcounts),
        "tekrar_fikstur": ft,
        "tekrar_model": mt,
        "tekrar_panel": pt,
        "durum_sayilari": dict(sayac),
        "model_durumlari": model.get(
            "durum_sayilari", {}
        ),
        "panel_kapsama_yuzdesi": (
            round(
                100 * len(eligible & ps.keys())
                / len(eligible), 2
            ) if eligible else None
        ),
        "panelde_eksik_gelecek_mac": len(
            eligible - ps.keys()
        ),
        "fikstur_disinda_panel_mac": len(
            ps.keys() - fs.keys()
        ),
        "ligler": ligler,
        "eksik_maclar": eksikler,
        "ana_motor_degisti": False,
        "uyari": (
            "Mevcut kaynak dosyalari denetlenmistir. "
            "Canli kaynak dogrulamasi yapilmamistir."
        )
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--fikstur",
        default="gelecek_maclar.json"
    )

    parser.add_argument(
        "--model",
        default="v18_canli_cikti.json"
    )

    parser.add_argument(
        "--panel",
        default="panel_tahminler.json"
    )

    parser.add_argument(
        "--cikti",
        default="dunya_ligleri_raporu_v2.json"
    )

    args = parser.parse_args()

    registry = read_league_registry(
        "fikstur_yeni.py"
    )

    report = analiz(
        registry,
        oku(args.fikstur),
        oku(args.model),
        oku(args.panel)
    )

    with Path(args.cikti).open(
        "x", encoding="utf-8"
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("FIKSTUR:", report["fikstur_mac"])
    print("MODEL:", report["model_mac"])
    print("PANEL:", report["panel_mac"])
    print("DURUMLAR:", report["durum_sayilari"])
    print("KAPSAMA:", report["panel_kapsama_yuzdesi"])
    print("EKSIK:", report["panelde_eksik_gelecek_mac"])


if __name__ == "__main__":
    main()
