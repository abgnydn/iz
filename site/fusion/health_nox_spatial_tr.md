# Füzyon #4 — Sanayi Baskısı × Sağlık (Mekânsal Çerçeve)

*Doğrulandı 2026-05-29. İl-bazlı solunum hastalığı ölüm istatistikleri TÜİK tarafından **tesis-atfı regresyonu için yeterli ayrıntıda yayımlanmıyor**, bu yüzden bu analiz mekânsal çerçeveyi kuruyor ve veri boşluğunu politika bulgusu olarak işaretliyor.*

## Ana Başlık

Türkiye şunları yayımlıyor:
- İstasyon-bazlı hava kalitesi ölçümleri (Çevre Bakanlığı Ulusal Hava Kalitesi İzleme Ağı)
- İl-bazlı **tüm-nedenli** ölüm istatistikleri (TÜİK Ölüm ve Ölüm Nedeni İstatistikleri)

Türkiye **şunları yayımlamıyor**:
- Tesis atfı için yeterli ayrıntıda neden-bazlı il ölüm istatistikleri (J00-J99 solunum)
- İlçe-bazlı ölüm istatistikleri

**Politika sonucu**: iz-1, 36 ilde 21 tesis için tesis-çözünürlüklü NOx (Beirle uydu ayrışması) + denetim-düzeyi Kapsam 1'e sahip. TÜİK il × ICD-10 J-bölümü ölümleri yayımladığı anda, bu veri seti Türkiye'deki ilk tesis-bazlı hava-kirliliği-atfı çalışmasına hazır hâle gelir.

## Veri setimizdeki sanayi baskısına göre üst iller

| İl | Tesis | Toplam kapasite (t/yıl) | Denetim Kapsam 1 (tCO₂) | Beirle NOx Σ (kg/s) | Kalıcı kirlilik? | Sektörler |
|---|---|---|---|---|---|---|
| Hatay | 4 | 13.000.000 | 10.663.364 | — | — | çelik |
| Zonguldak | 1 | 4.000.000 | 6.667.232 | — | — | çelik |
| Karabük | 1 | 3.500.000 | 5.650.626 | — | ✓ Yıldız 2022 | çelik |
| Kocaeli | 5 | 17.000.000 | 4.164.753 | — | ✓ Yıldız 2022 | çimento, çelik, alüminyum, gübre |
| Çanakkale | 2 | 9.500.000 | 3.466.000 | — | — | çimento, çelik |
| Adana | 1 | 3.500.000 | 1.669.072 | — | — | çimento |
| Isparta | 1 | 5.000.000 | 1.669.072 | — | — | çimento |
| Afyonkarahisar | 1 | 1.800.000 | 1.200.000 | — | — | çimento |
| İstanbul | 1 | 4.500.000 | 1.514.000 | — | — | çimento |
| Bursa | 1 | 2.000.000 | 1.121.545 | — | ✓ Yıldız 2022 | çimento |

## Çapraz referans: kalıcı-kirlilik illeri (Yıldız 2022) vs tesis ayak izimiz

- Veri setimiz 14 kalıcı-kirlilik ilinden 7'sini kapsıyor: **Bursa, Kocaeli, Konya, Karabük, Manisa, Şanlıurfa, Tekirdağ**
- Veri setimizde tesis OLMAYAN kalıcı iller: **Gaziantep, Iğdır, Düzce, Karaman, Kahramanmaraş, Sakarya, Yalova** — muhtemelen CBAM-dışı sanayi (enerji, rafineri, ısıtma) tarafından sürükleniyor

## Bu hangi araştırmayı mümkün kılar

TÜİK il × ICD-10-J ölümlerini yayımladığında (ya da Sağlık Bakanlığı'na akademik veri-paylaşım talebiyle), iz-1 tesis-baskı katmanı şuralara doğrudan bağlanır:

1. **Aşırı solunum-mortalitesi regresyonu** — il başına Beirle NOx akışı (kg/s, bizim veri) → 100k'da solunum mortalitesi (TÜİK)
2. **Kalıcı-kirlilik atfı** — tesislerimizin bulunduğu VE PM10'un AB sınırını aştığı 8-12 il için fazlalığı Beirle katmanı üzerinden belirli operatörlere tahsis et
3. **Karşı-olgusal modelleme** — her operatörün yayımlanmış 2030 azaltım hedefinde, illerinde beklenen aşağı akış solunum-mortalitesi azalmasını hesapla

## Çekinceler

- Yıldız 2022 PM10 kullandı, NO₂ değil; kalıcı-kirlilik ili listesi doğrudan NOx ölçüsü yerine sanayi baskısı için bir vekildir.
- 14-il kalıcı liste, sanayi-olmayan dağ / toz-baskın illeri (Iğdır) içeriyor — kirlilik-kaynağı atfı bu çözünürlükte gerçekten zor.
- Beirle 2023 v2 NOx akışları ≤15 km eşleştirme belirsizliğine sahip; şehir-seviyesinde duman çözünürlüğü iddia etmiyoruz.
- Doğru sonraki adım, Sağlık Bakanlığı'na il × yıl × ICD-10-J ölümleri için akademik veri-paylaşım talebidir. TR kamu-verisi normlarında ~6 haftalık geri dönüş.
