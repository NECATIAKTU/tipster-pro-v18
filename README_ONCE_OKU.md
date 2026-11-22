# TIPSTER PRO V19 — BEŞ AŞAMALI KORUMALI YAMA

## Amaç ve güvenlik
Bu paket V18'in çalışan koduna **dokunmadan** bağımsız denetim ve örnek geçmiş maç performansı hesaplar. Mevcut `v19_motor/` dizinini, ASLAN MODU'nu, `panel.js` dosyasını, JSON arşivlerini veya V18 iş akışlarını değiştirmez. Tek başına sistemi onarmaz veya V19'u canlıya almaz; rapor ve ölçüm sağlayan **ilk doğrulama yamasıdır**.

## Beş aşama
1. **Veri:** ESPN geçmiş JSON'unu temizler; veri geçerliliğini ve tekrarları raporlar. Takım kimlikleri ayrıca doğrulanmalıdır.
2. **Model:** Ev/deplasman odaklı shrinkage–Poisson modelini tarih sırasıyla test eder. Sadece **önceki gün** ve eski maç verileri kullanılır; gerçek bitiş zamanı bilinmediğinde aynı gün veri sızıntısı önlenir.
3. **Hata:** V18 kilitli seçimlerini gerçek sonuçla ve maç öncesi zaman kurallarıyla kontrol eder; Brier ve Wilson güven aralıklarını raporlar.
4. **Karar:** Gol çizgisi eşiklerini kontrol eder ama bahis kararı üretmez. Kalibrasyon, fiyat/odds ve bağımsız test olmadan canlı tahmin izni vermez.
5. **Yayın:** Arşiv kimliği ve panel tarihlerini kontrol eden, **salt okunur** yayın öncesi denetim raporlar.

## Güvenli GitHub kurulumu
**Önerilen:** önce `v19-review` adlı AYRI bir dal açın, sonra ZIP'i telefonunuzdaki Dosyalar uygulamasında çıkarın. Çıkan paketin içindeki `v19_patch/`, `tests/` ve `.github/workflows/v19-bes-asama-denetim.yml` yollarını **depo köküne** yükleyin. ZIP'i doğrudan GitHub'a tek dosya olarak atmak kodları çalışır hâle getirmez; GitHub ZIP içeriğini kendisi açmaz.

**Önemli:** `.github/workflows` klasöründeki dosyanın uzantısı `.yml` olarak kalmalı. Başka workflow dosyalarının üzerine yazmayın. İnceleme dalında Actions çalıştırıp sonuçları doğrulamadan `main` dalına geçmeyin. Bu iş akışı yalnızca manuel çalışır (`workflow_dispatch`); hiç commit/push/deploy yapmaz.

## Yerel kullanım
```
python -m unittest discover -s tests -p 'test_patch.py' -v
python -m v19_patch.cli --arsiv v18_tahmin_arsivi.json --ayarlar v18_sonuc_ayarlari.json --panel panel_tahminler.json --cikti V19_DENETIM_YENI.json
```
Gerçek kronolojik model testi için ayrıca geçmiş sonuç JSON'u gereklidir:
```
python -m v19_patch.cli --arsiv v18_tahmin_arsivi.json --gecmis espn_gecmis_maclar.json --ayarlar v18_sonuc_ayarlari.json --panel panel_tahminler.json --cikti V19_GECMIS_DENETIM_YENI.json
```
Çıktı **yeni** dosya olmalıdır; mevcut raporun üzerine yazılmaz. `espn_gecmis_maclar.json` depoda yoksa Aşama 2 otomatik olarak `GECMIS_VERI_GIRILMEDI` raporlar; örnek/demonstrasyon verisinden gerçek başarı çıkarılmaz.

## Sınırlar
- V18 aktif model halen ESPN'nin ev/deplasman sahası ve form özelliklerini tam olarak kullanmıyor. Bu paket o kodu değiştirmez, alternatif araştırma modeli sunar.
- V19'un mevcut 13 unit testi gerçek tahmin performansını kanıtlamaz.
- 96/138 gibi geçmiş kayda dayalı oranlar tek başına güvenilir geleceğe yönelik başarı veya kârlılık ölçütü değildir.
- ESPN geçmiş maçlarının kesin sonuçlanma zamanı bilinmediğinde aynı gün maçları eğitim için atlamak güvenlik açısından daha doğrudur ama örneklemi azaltır.
- İlk gün yalnızca arşiv raporu çıkması normaldir; sonraki aşamada veri toplayıcısı ayrı, kontrollü ve doğrulanmış bir yoldan bağlanmalıdır.
