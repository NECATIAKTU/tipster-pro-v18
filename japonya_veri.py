import csv
import io
from urllib.request import urlopen

def japonya_verisi_al(url):
    with urlopen(url, timeout=30) as cevap:
        metin = cevap.read().decode("utf-8-sig")

    return list(csv.DictReader(io.StringIO(metin)))
