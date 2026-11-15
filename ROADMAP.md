# GeoCosmos — Yol Haritası

> Ay ve Mars'taki bir hedef ve bir test amacı için, Dünya'nın tamamını NASA verisiyle tarayıp en uygun test alanlarını bulan; benzerliğin nerede koptuğunu da dürüstçe gösteren analog keşif aracı.

**Varsayım:** Hackathon 48 saat, ekip 3 kişi. Farklıysa saatler orantılı olarak kaydırılır.

## İçindekiler

- [Özet](#özet)
- [Challenge'a uygunluk](#challengea-uygunluk)
- [Ürün ve kullanıcı akışı](#ürün-ve-kullanıcı-akışı)
- [Veri ve hedefler](#veri-ve-hedefler)
- [Global keşif modu](#global-keşif-modu)
- [Mimari ve klasör yapısı](#mimari-ve-klasör-yapısı)
- [Hackathon öncesi hazırlık](#hackathon-öncesi-hazırlık)
- [48 saatlik plan](#48-saatlik-plan)
- [Görev dağılımı](#görev-dağılımı)
- [MVP ve atılabilecekler](#mvp-ve-atılabilecekler)
- [Riskler ve B planları](#riskler-ve-b-planları)
- [Sunum ve demo senaryosu](#sunum-ve-demo-senaryosu)

---

## Özet

GeoCosmos şu soruyu cevaplar: **"Ay'daki ya da Mars'taki bu yerde yapılacak bu testi, Dünya'da nerede prova ederim?"**

- Dünya'nın tüm karaları NASA verisiyle taranır ve her bölge, seçilen test amacına göre puanlanır.
- Her sonuçta benzerliğin bittiği yer açıkça gösterilir (yerçekimi, atmosfer, radyasyon, sıvı su).
- Ünlü analoglar keşif listesine girmez, motorun doğruluğunu kanıtlamak için kullanılır.
- Asıl hedef, listede olmayan **yeni adaylar** bulmaktır.

Jüriye vaadimiz: Tek bir "benzerlik yüzdesi" değil, test amacına göre veriyle kanıtlanmış ve sınırları açıkça söylenmiş bir analog önerisi.

## Challenge'a uygunluk

| Challenge ne istiyor | GeoCosmos'ta nasıl karşılanıyor |
| --- | --- |
| Dünya genelinde sistematik arama | Tüm karalar iki aşamalı ızgarayla taranıyor (25 km → 5 km) |
| Görsel benzerliğin ötesine geç | 3 boyutlu skor (topoğrafya, jeoloji, iklim) + operasyon etiketleri, her sayı NASA/ajans verisinden |
| Analojinin koptuğu yeri göster | Her kartta kopma kutusu ve parametre bazında "benzemiyor" işareti |
| Bilinen yerleri tekrarlama | Ünlü analoglar sadece doğrulama seti; keşif modu yeni aday buluyor |
| Ay üssü adayları / Mars iniş alanları | Artemis güney kutbu bölgeleri, Arcadia Planitia gibi gelecek görev hedefleri |
| Süreçleri düşün | Test amaçları süreç bazlı: toz ve rüzgar aşınması, donmuş zemin, suyla oluşan karbonat |
| Keşifle bağlantı kur | 7 test amacı gerçek görev ihtiyaçlarından geliyor |
| Yaratıcı yöntem | Amaca göre ağırlıklı benzerlik + Gemini ile serbest metinden parametre çıkarma |
| NASA ve diğer ajans verisi | NASA: Earthdata (MODIS, GPM IMERG, ASTER GED, EMIT, SEDAC), Worldview, PDS (MOLA, TES, THEMIS, CRISM), LRO (LOLA, Diviner, LEND, Mini-RF) · ESA: Copernicus DEM, Sentinel, WorldCover, CCI Permafrost · JAXA: GSMaP · CSA: RADARSAT ([DATA_SOURCES.md](DATA_SOURCES.md)) |

## Ürün ve kullanıcı akışı

1. **Gezegen seçimi:** Ay veya Mars haritasında hedef bölgeler işaretli. Üstüne gelince açılan popup, hedefin parametrelerini gösterir.
2. **Test amacı:** Hedefe tıklayınca 7 hazır testten biri seçilir ya da serbest metin yazılır (Gemini metni parametre ağırlıklarına çevirir).
   - Rover sürüşü ve tekerlek aşınması
   - Donmuş zeminde buz sondajı (ISRU)
   - Lav tüpü ve yeraltı habitatı
   - Toz fırtınası ve aşınma
   - Biyo-imza: aşırı kuraklıkta korunma
   - Biyo-imza: karbonat çökeli
   - Üs kurulumu ve iniş alanı (aydınlanma dahil)
3. **Dünya haritası:** Puanlanmış analoglar pin olarak çıkar. Keşif modunun bulduğu yeni adaylar ayrı renkte, "Yeni aday" etiketiyle gösterilir.
4. **Analog kartı:** Pine tıklayınca açılır:
   - Radar grafik (4 skor)
   - Hedef ve Dünya değerleri yan yana, her değerin yanında veri kaynağı
   - Geçmiş testler rozeti (elle girilmiş, kaynak linkli)
   - Kopma kutusu
   - Önceden üretilmiş Gemini yorumu
5. **Doğrulama paneli:** "NASA ve ESA'nın kullandığı ünlü analoglar bizim motorumuzda kaçıncı sırada?"

## Veri ve hedefler

Her sayının bir kaynağı var. Elle girilen her değer `"kaynak": "elle — <makale/link>"` etiketi taşır.

### Hedefler (3 Ay + 3 Mars)

| Gök cismi | Hedef | Neden seçildi | Öne çıkan özellik |
| --- | --- | --- | --- |
| Ay | Shackleton Krateri kenarı | Artemis güney kutbu üs bölgesi | Kalıcı gölge, olası buz, dik eğim |
| Ay | Malapert Masifi | Artemis aday bölgelerinden biri | Uzun güneşlenme, Dünya ile görüş hattı |
| Ay | Marius Hills çukuru | Lav tüpü girişi | Yeraltı habitatı, radyasyon korunması |
| Mars | Jezero Krateri | Perseverance, antik delta | Kil ve karbonat, biyo-imza hedefi |
| Mars | Gale Krateri | Curiosity, katmanlı çökeller | Sülfat ve kil, kumullar, rüzgar aşınması |
| Mars | Arcadia Planitia | İnsanlı iniş adayı | Yüzeye yakın buz, düz arazi |

> Hedef listesi ve koordinatlar hackathon öncesinde NASA kaynaklarından son kez doğrulanacak.

### Parametreler ve kaynaklar

Ayrıntılı kaynak haritası, formüller ve kapsam boşlukları: **[DATA_SOURCES.md](DATA_SOURCES.md)**.

| Parametre | Dünya verisi | Mars verisi | Ay verisi | Skor |
| --- | --- | --- | --- | --- |
| Eğim ve pürüzlülük | Copernicus DEM GLO-30 (ESA) | MOLA (PDS) | LOLA (LRO) | Topoğrafya |
| Yüzey sıcaklığı, gece-gündüz farkı | MODIS LST | Mars Climate Database (MODIS saatleriyle) | Diviner (LRO) | İklim |
| Mafik yüzey, karbonat | ASTER GED (TIR indeksleri); EMIT sadece ek kanıt | CRISM, TES (PDS) | LROC, Lunar Prospector | Jeoloji |
| Kuraklık ve bitki yokluğu | GPM IMERG yağış + MODIS NDVI (JAXA GSMaP ile kontrol) | Sabit 1 | Sabit 1 | İklim |
| Toz ve aerosol | MODIS aylık AOD (MOD08_M3) | TES toz opaklığı | Yok (parametre atılır) | İklim |
| Donmuş zemin | ESA CCI Permafrost | SHARAD, SWIM | Diviner PRP buz kararlılığı (LRO) | Jeoloji |
| Arazi örtüsü (sadece filtre) | MODIS MCD12Q1 (500 m) | — | — | — |

Mars ve Ay hedefleri için her parametre tek değerdir (PDS ürünleri veya makaleden). Mineral ve buz parametreleri, Dünya indeksleri ile makale bulguları aynı birimde olmadığı için ortak bir 0–1 sıralı ölçeğe çevrilir.

Operasyonel bilgiler puan değil, kartta ✓/✗ etiketi olarak gösterilir: yola erişim (şehre < 6 saat) ve ıssızlık (NASA SEDAC nüfus yoğunluğu < 1 kişi/km²).

### Doğrulama seti

Ünlü analoglar motoru test etmek için kullanılır, keşif listesine girmez. Yerler iki gruba ayrılır ki doğrulama gerçek bir kanıt olsun:

- **Ayar (tune):** Ağırlıklar ve toleranslar sadece bu yerlere bakılarak ayarlanır.
- **Sınav (holdout):** Başarı ölçütü sadece bu yerlerle hesaplanır. Bunlara bakarak ağırlık değiştirilmez.
- **Rapor (report):** Sırası gösterilir ama ölçüte girmez, çünkü yöntem o özelliği ölçemiyor.

| Yer | Beklenen test amacı | Grup |
| --- | --- | --- |
| Holuhraun (İzlanda) | Rover sürüşü | Ayar |
| Yungay (Atacama, Şili) | Biyo-imza: aşırı kuraklıkta korunma | Ayar |
| Haughton Krateri (Devon Adası, Kanada) | Buz sondajı | Ayar |
| Hanksville / MDRS çevresi (Utah, ABD) | Rover sürüşü | Sınav |
| Svalbard / Bockfjorden (Norveç) | Buz sondajı | Sınav |
| Salda Gölü kıyısı (Türkiye) | Biyo-imza: karbonat çökeli | Sınav |
| Lut Çölü (İran) | Toz ve aşınma | Sınav |
| Lanzarote lav tüpleri (İspanya) | Lav tüpü ve habitat | Rapor |

**Başarı ölçütü:** 4 sınav yerinden en az 3'ü, kendi test amacında ve kendi hedefine göre Dünya karelerinin en iyi %12,5'ine girmeli (ilk ölçüt %1'di, sonuç 0/4; 15 Kasım'da sonuç görüldükten sonra gevşetildi, STATUS.md). Her yerin hangi hedefe göre puanlanacağı (ör. Salda → Jezero) ve yüzdelik paydası `config/known_analogs.yaml` dosyasında.

- **Ayar yeri olmayan testler** (toz, lav tüpü): Ağırlıkları fiziksel gerekçeyle önceden sabitlendi (`test_profiles.yaml > rationale`), doğrulama sonucuna bakılarak değiştirilmez.
- **Keşif dışı liste:** Doğrulamada kullanılmayan ama zaten bilinen analoglar (Kuru Vadiler, Rio Tinto, Mauna Kea, Ries…) da "Yeni aday" sayılmaz (`known_analogs.yaml > exclude_only`).

Önceki listeden yapılan değişiklikler:

- **Dumont Dunes çıkarıldı, yerine Hanksville geldi.** Dumont Dunes yaklaşık 30 km² büyüklüğünde ve 25 km'lik karede kayboluyordu.
- **Lanzarote rapora alındı.** Lav tüpleri yer altında, kullandığımız veriler onları göremiyor. Motor sadece "genç bazaltik arazi"yi ölçebiliyor ve kart bu sınırı açıkça söylüyor.
- **Salda kalıyor.** Su maskesi kareyi ancak yarısından fazlası suysa eler (`config/grid.yaml`), göl ise karenin küçük bir kısmı.
- **Ölçüt değişti.** Eski ölçüt "8 yerden 6'sı ilk 3'te" idi. Yaklaşık 240 bin kare arasında ilk 3, 25 km çözünürlükte gerçekçi değildi.

## Global keşif modu

Tüm Dünya iki aşamada taranır. Ağır işlem Earth Engine'de, puanlama lokalde yapılır.

| Aşama | Ne yapılır | Boyut |
| --- | --- | --- |
| 1. Kaba tarama | Tüm karalar 25 km'lik karelerle puanlanır | ~240 bin kare |
| 2. Filtre | Yarısından fazlası şehir, tarım, su ya da kalıcı buz olan kareler (MODIS MCD12Q1) ve yarısından azı kara olan kıyı kareleri çıkarılır; bilinen analoglara 50 km'den yakın kareler doğrulama setine ayrılır | — |
| 3. Yakın tarama | Her test amacı için en iyi 50–100 karenin çevresi 5 km'lik karelerle yeniden puanlanır | Birkaç bin kare |
| 4. Elle kontrol | En iyi 3–5 aday NASA Worldview ve Sentinel-2 görüntüsüyle, lav akıntısı adayları RADARSAT/Sentinel-1 radarıyla, kurak bölgedekiler EMIT mineral haritalarıyla incelenir; en ilginç 1–2'si sunuma taşınır | — |

- 25 km ızgarada 6 parametrelik tablo ~10–20 MB tutar; 8 GB RAM'li laptopta rahat çalışır.
- Ham uydu verisi laptopa indirilmez. Earth Engine'de karelere küçültülür, sadece sonuç tablosu (CSV) indirilir.
- Sonucu biz seçmeyiz, motor söyler. Beklenmedik bir aday çıkarsa sunumun en güçlü anı o olur.
- **Dünya DEM'i Copernicus:** SRTM 60°K'nin kuzeyini kapsamadığı için Haughton ve Svalbard'da eğim hesaplanamıyordu.
- **Ölçek kuralı:** Eğim ve pürüzlülük çözünürlüğe bağlıdır. Copernicus DEM (30 m), MOLA (~463 m) ve LOLA verileri önce 500 m'ye indirilir, eğim ondan sonra hesaplanır. Hem Dünya kareleri hem Ay/Mars hedefleri için aynı kural geçerli (`config/grid.yaml`).

## Mimari ve klasör yapısı

Teknoloji seçimleri, veri sözleşmesi, API, Gemini kuralları ve klasör yapısı **[ARCHITECTURE.md](ARCHITECTURE.md)** dosyasında. Kısaca:

| Katman | Seçim |
| --- | --- |
| Veri işleme | Python + Earth Engine + pandas/geopandas |
| Backend | FastAPI (tek canlı endpoint: `/scenario`) |
| AI | Gemini (`google-genai`), JSON şemalı çıktı; sayı üretmez |
| Veri saklama | Parquet + GeoJSON + PNG (veritabanı sunucusu yok) |
| Frontend | React + Vite + Leaflet + Recharts + Tailwind |
| Yayınlama | Frontend: GitHub Pages / Vercel · Backend: Render / HF Spaces |

## Hackathon öncesi hazırlık

- [ ] Resmi kuralları okuyun: Önceden ne hazırlanabilir (kod, veri, sadece fikir)? Teslim şartları neler (video süresi, demo linki, proje sayfası)?
- [ ] Herkes Google Earth Engine hesabı açsın (onay gecikebilir, en erken iş bu).
- [ ] NASA Earthdata Login hesabı açın. ESA CCI Permafrost dosyası indirildi, ekipte elden dağıtılıyor (`data/raw/permafrost/`) ([DATA_SOURCES.md](DATA_SOURCES.md#hesaplar-ve-erişim)).
- [ ] Earth Engine'de **tüm karalar için** 25 km'lik tek bir katmanı (Copernicus DEM eğimi) CSV olarak dışa aktarmayı deneyin. Süreyi not edin.
- [ ] Gemini API anahtarı alın, ücretsiz kullanım limitlerini not edin.
- [ ] Moon Trek ve Mars Trek katmanlarını Leaflet'te deneyin. Çalışmazsa B planı statik mozaik görüntü.
- [x] 6 hedefin parametre değerlerini kaynaklarıyla `targets.yaml` dosyasına yazın (koordinatların son kontrolü hâlâ açık).
- [x] Doğrulama setindeki 8 yer için geçmiş test kaynaklarını (link) toplayın.
- [x] Her test amacı için ağırlıkların ilk taslağını yazın (`test_profiles.yaml`).
- [x] Repo, klasör iskeleti, `.gitignore` ve rol dağılımı hazır olsun.
- [ ] Veri sözleşmesini ([ARCHITECTURE.md](ARCHITECTURE.md#veri-sözleşmesi)) birlikte okuyun; hackathonun ilk 2 saatinde dondurulacak.

## 48 saatlik plan

Kapı 1'de, yani 20. saatte, basit ama uçtan uca çalışan bir sürüm olmalı: hedef seç → test seç → Dünya haritasında puanlı pinleri gör. Sonrası bu iskeleti zenginleştirmek. **34. saatten sonra yeni özellik eklenmez.**

```mermaid
flowchart LR
  P1["0–6. saat<br/>Kurulum ve veri"] --> P2["6–20. saat<br/>Motor + harita"]
  P2 --> G1{{"Kapı 1<br/>Uçtan uca akış"}}
  G1 --> P3["20–34. saat<br/>Kart + global keşif"]
  P3 --> G2{{"Kapı 2<br/>Özellik dondurma"}}
  G2 --> P4["34–42. saat<br/>Doğrulama ve cila"]
  P4 --> G3{{"Kapı 3<br/>Kod dondurma"}}
  G3 --> P5["42–48. saat<br/>Sunum ve teslim"]
```

| Aşama | Saat | Çıktı |
| --- | --- | --- |
| Kurulum ve veri | 0–6 | Repo çalışıyor, hedef değerleri hazır, ilk Earth Engine exportu başladı |
| Motor + harita | 6–20 | Skor motoru, kopma kuralları, Ay/Mars + Dünya haritası, ilk uçtan uca akış |
| Kart + global keşif | 20–34 | Analog kartı, kaba + yakın tarama sonuçları, kayıtlı Gemini yorumları |
| Doğrulama ve cila | 34–42 | Doğrulama tablosu, hata düzeltme, arayüz cilası |
| Sunum ve teslim | 42–48 | Demo videosu, sunum provası, teslim |

Her kapıda 10 dakikalık ekip kontrolü yapılır. Kapı geçilemiyorsa [MVP tablosunun](#mvp-ve-atılabilecekler) alt satırları atılır.

## Görev dağılımı

| Kişi | Rol | 0–20. saat | 20–34. saat | 34–48. saat |
| --- | --- | --- | --- | --- |
| A | Veri, keşif ve bilim | Hedef ve Dünya parametreleri, Earth Engine exportları, test ağırlıkları | Global kaba + yakın tarama, filtreler, adayların elle kontrolü | Doğrulama, veri kaynak listesi, rapor |
| B | Motor, backend ve AI | Skor motoru, kopma kuralları, GeoJSON çıktısı | FastAPI senaryo servisi, Gemini tercüman + yorumcu | Hata düzeltme, demo yedeği |
| C | Frontend ve sunum | Ay/Mars ve Dünya haritası, pinler | Analog kartı, radar, doğrulama paneli | Arayüz cilası, demo videosu, pitch |

## MVP ve atılabilecekler

| Öncelik | Özellik |
| --- | --- |
| Olmazsa olmaz | 6 hedef, 7 test amacı, en az 5 parametre NASA verisinden |
| Olmazsa olmaz | Ağırlıklı skor motoru ve kopma kuralları |
| Olmazsa olmaz | Ay/Mars haritası, Dünya haritası, analog kartı ve kopma kutusu |
| Olmazsa olmaz | Doğrulama tablosu |
| Olmazsa olmaz | Global kaba tarama sonucu (önceden hesaplanmış, en az 1 yeni aday) |
| Olmazsa olmaz | Kayıtlı Gemini yorumları |
| Olursa iyi | 5 km yakın tarama |
| Olursa iyi | Serbest metinli Gemini senaryo çözücü (canlı) |
| Olursa iyi | Radar grafik |
| Olursa iyi | Ay/Mars haritasında Trek katmanı (yoksa statik görüntü) |
| Atılabilir | 3D küre |
| Atılabilir | Mobil uyum, kullanıcı hesabı |

## Riskler ve B planları

| Risk | Fark etme anı | B planı |
| --- | --- | --- |
| Global Earth Engine exportu uzun sürer | 6. saatte veri yok | Izgarayı 50 km'ye büyüt ya da kıtaları sırayla export et; bu sırada elle girilmiş değerlerle devam |
| Laptop belleği yetmez | Script kilitleniyor | Daha kaba ızgara; tabloyu kıta kıta işle |
| Gemini limiti dolar / internet kesilir | Canlı çağrı hata veriyor | Kayıtlı yorumlar; senaryo çözücü için 3 hazır örnek cevap |
| Gemini sayı uydurur | Yorumda motorda olmayan sayı var | Prompt'ta yasak, çıktıda sayı kontrolü; geçmiş testler elle girilir |
| Keşif anlamsız yer bulur | Tarla, şehir, deniz, buz tabakası çıkıyor | MODIS arazi örtüsü maskesi; buz tabakaları tüm testlerde dışarıda (buz sondajı donmuş zemini ölçer, buzulu değil) |
| Doğrulama tutmaz | Ünlüler alt sırada | Ağırlıkları sadece ayar yerlerine bakarak düzelt; sınav yerlerine bakarak ayar yapma, sonucu dürüstçe raporla |
| Ay/Mars harita katmanı yüklenmez | Boş harita | Statik mozaik görüntü |
| Canlı demo çöker | Sunum anı | Demo videosu hazır, yerel sunucu yedekte |

## Sunum ve demo senaryosu

Sunumun omurgası: **"NASA'nın kullandığı yerleri motorumuz kendi buldu. Aynı motor tüm Dünya'yı taradı ve yeni adaylar buldu."**

Toplam 3 dakika (resmi süre farklıysa oranlar korunur):

1. **Problem (30 sn):** Test sahası seçimi bugün çoğunlukla uzman deneyimine dayanıyor. Tek bir "benzerlik yüzdesi" yanıltıcı: Bir yer rover testi için mükemmel, buz sondajı için işe yaramaz olabilir.
2. **Yöntem (40 sn):** Test amacına göre ağırlıklı skor, her sayı NASA verisinden, kopma kutusu benzerliğin bittiği yeri söylüyor.
3. **Kanıt (25 sn):** Doğrulama tablosu: ayarda hiç kullanmadığımız ünlü analogların kaçı kendi test amacında Dünya'nın en iyi %12,5'inde (ilk ölçüt %1'de 0/4 olduğu da söylenir).
4. **Canlı demo (70 sn):**
   - Bir Mars hedefi + test amacı → Dünya haritası → kart ve kopma kutusu.
   - Bir Ay hedefi ile aynısı.
   - Global keşif katmanı açılır, "Yeni aday" pinlerinden biri gösterilir: "Bunu biz bulduk."
   - Zaman kalırsa Gemini'ye serbest bir senaryo yazılır.
5. **Kapanış (15 sn):** "Sınırlarını dürüstçe söyleyen, veriye dayalı bir test sahası kılavuzu."

Demoda hangi yerlerin öne çıkacağı önceden ezberlenmez; senaryo motorun gerçek sonuçlarına göre son gün yazılır. Canlı demonun kaydı yedek olarak hazır tutulur.
