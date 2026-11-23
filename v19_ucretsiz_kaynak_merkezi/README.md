# V19 - Ücretsiz Kaynak Keşif Merkezi (pilot 2)

Bu modül mevcut `v19_ucretsiz_ligler/ligler.json` dosyasını okur ve 25 lig için ücretsiz Football Charts katalog eşleştirmelerini denetler. Kod, V18 ana motora, tahmin arşivlerine, panele ve V19'un eski dosyalarına **yazmaz**. Tahmin üretmez.

## Çalıştırma

Python 3.11; ek paket yok:

```bash
python -m unittest discover -s v19_ucretsiz_kaynak_merkezi/tests -v
python v19_ucretsiz_kaynak_merkezi/merkez.py --limit 10 --cikti v19_kaynak_kesif_raporu.json
```

GitHub Actions'ta test branch `v19-review` kullanılır, rapor artifact olarak saklanır.

**Kısıtlar**: Kaynaksız 25 istek/gün olduğu için katalog + 10 lig * 2 istek = 21 sorgu (IP ortak kotası). İsteğe bağlı ücretsiz anahtar `FC_API_KEY` ortam değişkeninden okunur, kodda tutulmaz. Ücretsiz anahtar kişisel araştırma içindir, üçüncü kişilerin kullandığı panel için uygun olduğunu varsaymayın. Github Pages'e kaynak verileri yayımlamayın. Kaynak sayfasındaki lisans ve kullanım koşullarına uyun. Bu kod otomatik ticari veri beslemesi değildir.

Sadece kesin isim eşleşmesi ya da sağlayıcı belgelerinde doğrulanan kodlar kullanılabilir. Yanlış eşleşmeleri otomatik kabul etmez. Her lig için gerçekten fikstür ve geçmiş sonuç bulunduğunda, maç bazında kimlik ve tarih kontrollerini içeren entegrasyon modülü ayrıca yapılmalıdır.
