import math

def poisson(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)

def pazar_analizi(ev_gol, dep_gol):
    ev_gol = float(ev_gol)
    dep_gol = float(dep_gol)
    if ev_gol < 0 or dep_gol < 0:
        raise ValueError("Negatif gol beklentisi")

    sonuc = {}
    ev_kazanir = beraberlik = dep_kazanir = 0.0
    kg_var = 0.0
    toplamlar = {n: 0.0 for n in range(7)}
    ev_fark_2 = dep_fark_2 = 0.0

    for e in range(26):
        for d in range(26):
            p = poisson(e, ev_gol) * poisson(d, dep_gol)
            if e > d:
                ev_kazanir += p
            elif e == d:
                beraberlik += p
            else:
                dep_kazanir += p
            if e > 0 and d > 0:
                kg_var += p
            if e - d >= 2:
                ev_fark_2 += p
            if d - e >= 2:
                dep_fark_2 += p
            for n in toplamlar:
                if e + d >= n + 1:
                    toplamlar[n] += p

    sonuc["MS 1"] = ev_kazanir
    sonuc["MS X"] = beraberlik
    sonuc["MS 2"] = dep_kazanir
    sonuc["1X"] = ev_kazanir + beraberlik
    sonuc["X2"] = beraberlik + dep_kazanir
    sonuc["12"] = ev_kazanir + dep_kazanir
    sonuc["KG VAR"] = kg_var
    sonuc["KG YOK"] = 1 - kg_var
    sonuc["Ev -1.5 handikap"] = ev_fark_2
    sonuc["Dep -1.5 handikap"] = dep_fark_2

    for n, p in toplamlar.items():
        sonuc[f"{n}.5 UST"] = p
        sonuc[f"{n}.5 ALT"] = 1 - p

    return {
        ad: round(max(0, min(100, p * 100)), 2)
        for ad, p in sonuc.items()
    }

if __name__ == "__main__":
    for ad, oran in sorted(
        pazar_analizi(1.6, 1.2).items(),
        key=lambda x: x[1], reverse=True
    ):
        print(ad, oran)
