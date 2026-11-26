from gol_modeli import form_ortalamasi


SURUM = "GELISTIRME ISTATISTIK V1"

MIN_MAC = 5
MIN_SAHA_MAC = 3

ALANLAR = (
    "mac",
    "attigi",
    "yedigi",
    "ev_mac",
    "ev_attigi",
    "ev_yedigi",
    "dep_mac",
    "dep_attigi",
    "dep_yedigi",
)


def takim_denetle(veri):
    if not isinstance(veri, dict):
        return False

    for alan in ALANLAR:
        deger = veri.get(alan)

        if type(deger) is not int or deger < 0:
            return False

    if veri["mac"] != veri["ev_mac"] + veri["dep_mac"]:
        return False

    if veri["attigi"] != veri["ev_attigi"] + veri["dep_attigi"]:
        return False

    if veri["yedigi"] != veri["ev_yedigi"] + veri["dep_yedigi"]:
        return False

    form = veri.get("son_maclar")

    if not isinstance(form, list):
        return False

    if len(form) != veri["mac"]:
        return False

    for skor in form:
        if not isinstance(skor, (list, tuple)):
            return False

        if len(skor) != 2:
            return False

        if any(type(x) is not int or x < 0 for x in skor):
            return False

    if sum(x[0] for x in form) != veri["attigi"]:
        return False

    if sum(x[1] for x in form) != veri["yedigi"]:
        return False

    return True


def oran(toplam, adet):
    if adet == 0:
        return None

    return round(toplam / adet, 4)


def takim_profili(isim, veri):
    if not takim_denetle(veri):
        raise ValueError("Tutarsiz takim verisi: " + isim)

    form = veri["son_maclar"]
    son5 = form[-5:]

    return {
        "takim": isim,
        "mac": veri["mac"],
        "yeterli_veri": veri["mac"] >= MIN_MAC,

        "genel_atak": oran(
            veri["attigi"], veri["mac"]
        ),

        "genel_savunma": oran(
            veri["yedigi"], veri["mac"]
        ),

        "ev_mac": veri["ev_mac"],
        "dep_mac": veri["dep_mac"],

        "ev_atak": oran(
            veri["ev_attigi"], veri["ev_mac"]
        ),

        "ev_savunma": oran(
            veri["ev_yedigi"], veri["ev_mac"]
        ),

        "dep_atak": oran(
            veri["dep_attigi"], veri["dep_mac"]
        ),

        "dep_savunma": oran(
            veri["dep_yedigi"], veri["dep_mac"]
        ),

        "ev_veri_yeterli": (
            veri["ev_mac"] >= MIN_SAHA_MAC
        ),

        "dep_veri_yeterli": (
            veri["dep_mac"] >= MIN_SAHA_MAC
        ),

        "form_mac": len(son5),

        "form_atak": form_ortalamasi(form, 0),

        "form_savunma": form_ortalamasi(form, 1),

        "son5_galibiyet": sum(
            a > b for a, b in son5
        ),

        "son5_beraberlik": sum(
            a == b for a, b in son5
        ),

        "son5_maglubiyet": sum(
            a < b for a, b in son5
        ),
    }


def lig_profili(takimlar):
    profiller = {}
    gecersiz = []

    ev_mac = 0
    dep_mac = 0
    ev_gol = 0
    dep_gol = 0
    toplam_atilan = 0
    toplam_yenilen = 0

    for isim, veri in takimlar.items():
        if not takim_denetle(veri):
            gecersiz.append(isim)
            continue

        profiller[isim] = takim_profili(
            isim, veri
        )

        ev_mac += veri["ev_mac"]
        dep_mac += veri["dep_mac"]
        ev_gol += veri["ev_attigi"]
        dep_gol += veri["dep_attigi"]

        toplam_atilan += veri["attigi"]
        toplam_yenilen += veri["yedigi"]

    tutarli = (
        not gecersiz
        and ev_mac > 0
        and ev_mac == dep_mac
        and toplam_atilan == toplam_yenilen
    )

    return {
        "surum": SURUM,
        "takim_sayisi": len(profiller),
        "gecersiz_takimlar": gecersiz,
        "lig_verisi_tutarli": tutarli,

        "lig_ev_gol_ortalamasi": (
            oran(ev_gol, ev_mac)
            if tutarli else None
        ),

        "lig_dep_gol_ortalamasi": (
            oran(dep_gol, dep_mac)
            if tutarli else None
        ),

        "lig_toplam_gol_ortalamasi": (
            oran(ev_gol + dep_gol, ev_mac)
            if tutarli else None
        ),

        "takimlar": profiller,
    }
