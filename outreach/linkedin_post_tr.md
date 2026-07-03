# LinkedIn paylaşımı (TR) — katkı çağrısı

> Kopyala-yapıştır için hazır. Rakamlar `reports/lopo_ef_eval.json` ile uyumludur;
> değiştirmeden önce `just repro` ile doğrulayın.

---

Türkiye'nin CBAM (AB Sınırda Karbon Düzenlemesi) faturasıyla ilgili tek kişilik
bir açık-veri projesi yürütüyorum ve büyütmek için yardıma ihtiyacım var.

**Ne buldum:**

AB, gerçek emisyonunu belgeleyemeyen tesislere "varsayılan değer" uyguluyor —
kasıtlı olarak yüksek bir ceza rakamı. 59 Türk tesisini (çimento, çelik,
alüminyum, gübre) kapsayan açık bir veri seti kurdum; 21'inin denetimden geçmiş
gerçek emisyon rakamı kamuya açık raporlarda mevcut.

Üç sayılık basit bir formül — kapasite × rota emisyon faktörü × kapasite
kullanım oranı — AB varsayılanına göre hatayı **%82 azaltıyor** (dürüst test:
her tesis, yalnızca DİĞER tesislerden türetilen katsayıyla tahmin ediliyor;
kimse kendi cevabını görmüyor). Aynı formül, hiç ayar değiştirmeden, AB'nin
resmî kayıtlarındaki **789 Avrupa tesisinde** de doğrulandı: medyan tahmin
neredeyse birebir doğru; AB varsayılanı ise çimentoda ~2,5 kat fazla.

Basit çıkarım: AB varsayılanıyla ödeme yapan Türk ihracatçılar büyük olasılıkla
fazla ödüyor. Kaba bir mertebe tahminiyle bu, yılda yüz milyonlarca euro
olabilir (bu rakam bir ekstrapolasyondur; ihtiyatla okuyun).

**Dürüst olmak gerekirse zayıf noktalar da şunlar:**

- Doğrulanabilir örneklem küçük: 19 tesis.
- Seçilim yanlılığı olası: denetimli rapor yayımlayan şirketler muhtemelen en
  temiz tesisler. Kirli kuyruk veride görünmüyor.
- "Gerçek" rakamlar şirketlerin kendi (denetimli de olsa) beyanları.

Bu eksikler tam olarak yardım istediğim yerler:

1. **Veri çıkarma:** TSRS zorunluluğuyla her yıl onlarca yeni denetimli rapor
   yayımlanıyor. PDF'lerden emisyon rakamı çıkarabilecek herkes n'i büyütebilir.
2. **Bağımsız kontrol:** Mevcut 21 etiketin ve rota atamalarımın ikinci bir göz
   tarafından doğrulanması. (Hata bulundu ve düzeltildi — daha fazlası da
   çıkabilir; bulan kazanır.)
3. **Kapı açacak biri:** Sektör dernekleri (TÜRKÇİMENTO, ÇEBİD/TÇÜD, TİM) veya
   Bakanlık ile teması olan biri. Türkiye'nin MRV mevzuatı gereği bu verinin
   doğrulanmış tam hâli zaten devlette mevcut — açılması her şeyi çözer.
4. **Akademik ortak yazar:** Veri seti kurulu, sonuç doğrulanmış, AB
   konsültasyonuna resmî görüş sunulmuş durumda. Hakemli bir makale için zemin
   hazır.

Her şey açık: kod, veri, yöntem Apache-2.0 ile yayında. Bana inanmanız
gerekmiyor — klonlayıp `just repro` ile kendiniz üretebilirsiniz.

Site: https://iz-mrv.pages.dev
Kod + veri: https://github.com/abgnydn/iz
DOI: https://doi.org/10.5281/zenodo.20496086

#CBAM #SKDM #karbonvergisi #açıkveri #TSRS #ihracat
