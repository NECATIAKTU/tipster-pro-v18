# TIPSTER PRO V18 — Entegre sürüm / güvenli kurulum

## Ne değişti?

* Mevcut V18 tahmin motoru `gercek_tahmin_v18.py`, gol hesaplama modülleri ve 42 ESPN lig tanımı korunmuştur.
* `v18_sonuc_takip.py` maç öncesi ilk tahminleri kilitler, ESPN maç **ID** ile kesin skor doğrular, tekrar çalıştırmada eski sonucu korur.
* `v18_sonuc_ayarlari.json` yeni maçlara uygulanacak **deneysel** seçim eşiğini belirler. Bu kurallar kanıtlanmış bahis üstünlüğü / başarı değildir.
* Eskiden kilitli seçim bulunmayan 315 arşiv kaydı için **geriye dönük tahmin oluşturulmaz**. Bu kayıtlar gerçek skorları geldiğinde gösterilebilir ama doğru/yanlış istatistiğine eklenmez.
* `panel.js`, `index.html`, `panel.css` üzerinde bekleyen, doğrulanan, doğru, yanlış, bugünkü / 7 günlük / 30 günlük başarı ve filtre bölümleri vardır.
* Ana GitHub Actions akışına sonuç doğrulama, test, arşiv commit, hata kontrolleri ve GitHub Pages'e sonuç JSON yayını eklenmiştir.

## ÖNEMLİ — Mevcut GitHub reposuna hangi ZIP yüklenir?

**Mevcut, çalışan repo için `TIPSTER_PRO_V18_GUVENLI_GUNCELLEME.zip` kullanılır.** Bu ZIP, yeni/değişen dosyaları içerir, `v18_tahmin_arsivi.json` dosyasını **İÇERMEZ**. GitHub deposundaki geçmiş kayıtların üzerine eski bir kopya yazılmamalıdır.

**`TIPSTER_PRO_V18_PROFESYONEL_TAM.zip`** tam kaynak yedeğidir. İçindeki arşiv kaynak ZIP'in alındığı andaki 315 kayıtlı görüntüdür; güncel repo arşivinin üzerine *asla* uygulanmamalıdır.

### Yükleme

1. GitHub'da önce mevcut **main** dalındaki `v18_tahmin_arsivi.json` dosyasının kopyasını yedekle (silme, değiştirme).
2. **Güvenli güncelleme ZIP'ini** Dosyalar uygulamasında aç, içindeki `tipster-pro-v18-main` dizinini bul.
3. Bu dizindeki dosyaları **aynı göreli yollarıyla** mevcut GitHub deposuna aktar: `.github/workflows/` içindekiler `.github/workflows/` yoluna; diğerleri repo köküne. ZIP'i doğrudan tek dosya olarak yüklemek *kurulum değildir*. Mevcut arşiv dosyasına dokunma.
4. GitHub **Actions → TIPSTER PRO V18 - Sonuc Takip Testi** iş akışını çalıştır. İlk test tamamlanmadan ana V18 iş akışını çalıştırma.
5. Test başarılıysa **TIPSTER PRO V18 - Gercek Tahmin ve Pages** iş akışını çalıştır. İş akışı hem V18 tahminlerini üretir, sonuçları kontrol eder hem de paneli yayımlar.
6. Çalıştırma kayıtlarında `ARSIV`, `ESPN`, `DOGRULANAN`, `DOGRU`, `YANLIS` ve `Tahmin ve skor arsivini ... kaydet` adımlarını kontrol et. Panelde `Gerçek maç sonuçları` bölümünü yenile.

### Kontroller / önemli ayrıntılar

- Kaydetme için GitHub Actions `contents: write` yetkisi ve repo ayarlarında Actions yazma izni gerekir. GitHub ortamı buna izin vermezse commit/push **başarısız olabilir**. `git push --force` asla kullanılmaz.
- **0 yeni tahmin** çıktığında sistem model verisi uydurmaz: boş güncel tahmin bölümü, varsa arşiv sonuçları gösterilir.
- ESPN cevap vermezse sonuç **BEKLİYOR** kalır. Eşleşmeyen ya da ertelenen maç başarısız tahmin diye sayılmaz.
- Gerçek maçlar oynanmadıysa ✅/❌ henüz oluşmaz. Arşivdeki geçmiş kayıtlara kilitli market sonradan eklenmez.
- Kurulumda eski `/docs` veya farklı Pages iş akışları etkinse GitHub Pages çakışmaları ayrıca incelenmelidir. Bu paket yalnızca **V18 ana Pages** akışını değiştirir.
- Tek ZIP'i mobil GitHub'a doğrudan yüklemek çalışır bir dağıtım değildir: ZIP açılıp dosyalar doğru yollarına aktarılmalıdır.

## Bağımsız kontroller

```
python v18_paket_kontrol.py
python -m unittest -v test_gercek_tahmin_v18.py test_v18_sonuc_takip.py
node --check panel.js
```

Tüm eski testleri de çalıştırmak için `python -m unittest discover -p 'test_*.py'` kullanılabilir. Orijinal ZIP'te **bulunmayan 6 opsiyonel lig katalog JSON'u** yüzünden ilgili testler hâlâ hata verir. Bu katalogların gerçek verisini uydurmadık ve onları 'aktif 42 lig' diye sunmuyoruz. Eksikler: `afrika_ligler.json`, `amerika_alt_ligler.json`, `amerika_ust_ligler.json`, `asya_alt_ligler.json`, `asya_ust_ligler.json`, `avustralya_ligler.json`. Bunlar ana V18 iş akışının girdisi değildir.

## Dürüst sınır

Python/JS/YAML çevrimdışı kontrolleri başarılı olsa bile **canlı ESPN erişimi**, tüm 42 ligde güvenilir veri ve **GitHub Pages'e canlı dağıtım** yalnızca gerçek Actions çalıştırmasıyla doğrulanabilir. %100 başarı veya kazanç garantisi yoktur.
