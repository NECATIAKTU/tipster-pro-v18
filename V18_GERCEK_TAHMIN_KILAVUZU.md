# TIPSTER PRO V18 — Kaynak doğrulamalı tahmin aşaması

- 42 lig fikstür kataloğunda tanımlıdır; bu, 42 ligde canlı veri erişiminin doğrulandığı anlamına gelmez.
- `gercek_tahmin_v18.py`, yalnızca güncel (24 saatten yeni) `gelecek_maclar.json` içindeki henüz başlamamış maçları işler.
- Yalnızca fikstürde maçı bulunan ligler için ESPN'den tamamlanmış maç skorlarını sorgular (varsayılan 90 gün). Günlük API istekleri fazla olabilir; hız sınırı ve erişim hatası mümkündür.
- Tarihsel maç verisi, takım eşleşmesi veya en az 5 maçlık geçmiş eksikse **tahmin üretmez**; eksikleri raporlar.
- Modelin yüzdeleri istatistiksel tahminlerdir; bağımsız kalibrasyon yapılmadan başarı olasılığı olarak yorumlanmamalıdır.
- Eski `tahminler.json` ve `kayitlar.json` dosyalarını değiştirmez; `v18_yeni_tahminler.json` oluşturur. Var olan çıktının üzerine yazmaz.

## Kullanım (internet erişimi olan bir bilgisayarda)

```bash
python fikstur_yeni.py
python gercek_tahmin_v18.py --gecmis-gun 90 --cikti v18_yeni_tahminler_20261112.json
```

Test: `python -m unittest -v test_gercek_tahmin_v18.py`

## Mevcut doğrulama sınırı

Bu paketin üretildiği ortamda canlı ESPN API erişimi doğrulanmadı; dolayısıyla 42 ligden kaçında güncel gerçek tahmin üretileceği **bilinmiyor**. 3 çevrimdışı otomatik test başarılıdır; bunlar canlı veri testinin yerini tutmaz.
