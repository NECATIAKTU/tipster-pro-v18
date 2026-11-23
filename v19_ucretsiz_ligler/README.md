# V19 — Ücretsiz lig veri denetimi (pilot 1)

Bu klasör **hiçbir V18 dosyasını, arşivi, tahmin motorunu ya da GitHub Pages panelini yazmaz.**
Yalnızca 9 sıfır-fikstür ligi ve 16 ek lig adayını listeler ve ücretsiz kaynakları test eder.

## Ücretsiz kaynaklar

- ESPN scoreboard: halka açık, anahtarsız, **resmî API/SLA garantisi yok**. Sıfır maç, lig kodunun hatalı olduğunu tek başına kanıtlamaz.
- Football-Data.co.uk: İskoçya Championship (SC1) ve League One (SC2) için ücretsiz geçmiş CSV kaynak adayı; CSV'nin güncelliği ve koşulları kullanım öncesi kontrol edilmeli.
- OpenFootball: açık veri seçeneği; bu pilotta henüz otomatik bağlantı kurulmadı.

## Çalıştırma

Python 3.11 yeterli; `pip install` gerekmez.

```bash
python -m unittest discover -s v19_ucretsiz_ligler/tests -v
python v19_ucretsiz_ligler/denetim.py --gun 7 --cikti v19_ucretsiz_lig_raporu.json
```

30 günlük daha kapsamlı denetim: `--gun 30`.
Tüm aday ligleri raporda görmek için: `--adaylari-goster` (doğrulanmamış kodlara istek gönderilmez).

Bu proje mevcut GitHub deposundaki **v19-review** dalına eklenmeli. `.github/workflows/v19-ucretsiz-lig-test.yml` sadece manuel tetiklenir (`workflow_dispatch`); **main** dalına birleştirme ve mevcut otomatik iş akışını değiştirme yapılmamalıdır.

## Kabul ölçütü

- API yanıtı ile gerçek fikstür birbirinden ayrılır.
- Fikstür ve geçmiş skoru ayrı ayrı doğrulanır.
- Eksik veri durumunda tahmin üretilmez.
- Lig ve sağlayıcı kaynakları raporda açık görünür.
- Gerçek veri ve takım eşleştirme doğrulanmadan canlı panele eklenmez.
