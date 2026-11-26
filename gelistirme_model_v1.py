from gol_modeli import mac_analizi

from gelistirme_istatistik_v1 import (
    takim_denetle,
    lig_profili,
    MIN_MAC,
)


SURUM = "GELISTIRME MODEL V1"

GOL_CIZGILERI = (
    "1.5_ust",
    "2.5_ust",
    "3.5_ust",
    "4.5_ust",
    "5.5_ust",
    "6.5_ust",
)


def model_denetimi(ev, dep, takimlar):

    if ev == dep:
        raise ValueError("Ayni takim")

    if ev not in takimlar:
        raise ValueError("Ev sahibi verisi eksik")

    if dep not in takimlar:
        raise ValueError("Deplasman verisi eksik")

    for isim in (ev, dep):

        veri = takimlar[isim]

        if not takim_denetle(veri):
            raise ValueError(
                "Tutarsiz takim verisi: " + isim
            )

        if veri["mac"] < MIN_MAC:
            raise ValueError(
                "Yetersiz takim verisi: " + isim
            )

    return True


def olasilik_denetimi(sonuc):

    onceki = 100.0

    for alan in GOL_CIZGILERI:

        deger = sonuc.get(alan)

        if type(deger) not in (int, float):
            return False

        if not 0 <= deger <= 100:
            return False

        if deger > onceki:
            return False

        onceki = deger

    return True


def model_analizi(ev, dep, takimlar):

    model_denetimi(ev, dep, takimlar)

    lig = lig_profili(takimlar)

    if not lig["lig_verisi_tutarli"]:
        raise ValueError("Lig verisi tutarsiz")

    sonuc = mac_analizi(ev, dep, takimlar)

    if not olasilik_denetimi(sonuc):
        raise ValueError("Model olasilik hatasi")

    return {
        "surum": SURUM,
        "ev_sahibi": ev,
        "deplasman": dep,
        "lig_ortalama": lig[
            "lig_toplam_gol_ortalamasi"
        ],
        "ev_veri_adedi": takimlar[ev]["mac"],
        "dep_veri_adedi": takimlar[dep]["mac"],
        "sonuc": sonuc,
        "veri_denetimi": True,
    }
