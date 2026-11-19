# TIPSTER PRO V18 — Entegrasyon ve test raporu (19 Kasım 2026)

**Kaynak:** kullanıcının `tipster-pro-v18-main (1).zip` dosyası. Tahmin motoru korunmuştur.

## Sabit veriler

- Orijinal arşiv: **315 gerçek önceden kaydedilmiş maç**, 30 farklı ligde tahmin. 315 kayıt korunmuştur; 0 kayıt `kilitli_secim` içerir, o nedenle eski başarı yüzdesi **hesaplanamaz**.
- Lig katalogu: 42 ESPN lig kodu tanımlı; 42/42 canlı uçtan uca çalışma doğrulanmadı.
- Paket tahmin motorunu ve mevcut model olasılıklarını değiştirmez.

## Düzeltmeler

1. Maç ID eşleştirme (`lig|ESPN_ID`), kaynak sonuçların tutarlılığı, yalnız tamamlanmış maçların skorları.
2. Başlangıç ve hesaplama zamanı UTC kontrolü, eski ilk tahminin ve seçimin korunması.
3. Açıkça dosyada belirtilen, yeni maçlar için seçimi kilitleyen deneysel eşikler. `RISKLI` maçlar başarıya sayılmaz. Geriye dönük seçim yok.
4. ESPN kesintisinde veya tekrar çalışmada önceki skor korunur; kesinleşmemiş maçlar beklemede kalır.
5. Panelde doğrulanmış skorlar, ✅/❌, bekleyen ve günlük/haftalık/30 günlük istatistikler.
6. Aynı GitHub Actions akışında kaynak testleri → tahmin → kilitleme → sonuç kontrolü → panel hazırlama → arşiv commit → GitHub Pages.
7. Güncel repo arşivini korumak için **arşiv içermeyen güvenli güncelleme ZIP'i**.

## Testler

- Python AST sözdizimi tüm **97** orijinal Python modülü için kontrol edildi (ek yeni modüllerle sayısı artmıştır).
- V18 motoru ve yeni sonuç takibi: **18/18** test geçti.
- `node --check panel.js`: geçti.
- GitHub Actions YAML statik doğrulama: geçti.
- Geniş eski test taramasında diğer mevcut testler geçti ancak orijinal pakette olmayan **6 lig kataloğu JSON'u nedeniyle 9 hata** kaldı. Bunlar ana canlı V18 pipeline'ı tarafından kullanılmıyor ve veri uydurularak kapatılmadı.
- Canlı ESPN ve GitHub Pages dağıtımı bu çevrimdışı ortamda teyit edilmedi.

## Güvenlik

- Orijinal arşivden kayıt silinmedi.
- Geriye dönük sonuç / bahis başarısı uydurulmadı.
- GitHub push normal pull --rebase + push, force yok; çakışma olursa workflow hata verir, veri üzerine zorla yazmaz.
- `v18_tahmin_arsivi.json` tam kaynak yedeğinde bulunur, güncelleme ZIP'inde **bulunmaz**.
