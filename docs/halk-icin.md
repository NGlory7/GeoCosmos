# GeoCosmos: Dünya'da Ay'ı ve Mars'ı aramak

> Herkes için kısa açıklama. Teknik ayrıntı: [ARCHITECTURE.md](../ARCHITECTURE.md), veri kaynakları: [DATA_SOURCES.md](../DATA_SOURCES.md), güncel durum ve sınırlılıklar: [STATUS.md](../STATUS.md).

## Neden Dünya'da arıyoruz?

Ay'a ya da Mars'a gönderilecek bir rover, matkap ya da üs ekipmanı önce Dünya'da denenir. Bunun için hedefe **benzeyen** bir yer gerekir: aynı kadar engebeli, aynı kadar kuru, aynı tür kayaçtan. Bugün bu denemeler hep aynı birkaç yerde yapılıyor: Atacama Çölü, İzlanda, Hawaii, Antarktika'nın kuru vadileri. Bu yerler iyi, ama bulunmaları büyük ölçüde tesadüf ve deneyime dayanıyor.

GeoCosmos soruyu tersine çeviriyor: **Önce hedefi ölç, sonra Dünya'nın tüm karalarını tara ve en çok benzeyen yerleri bul.**

## Nasıl çalışıyor?

1. **Hedef seçilir.** Ay'da üç yer (Shackleton Krateri kenarı, Malapert Masifi, Marius Hills lav tüpü çukuru) ve Mars'ta üç yer (Jezero, Gale, Arcadia Planitia). Hepsi gerçek görevlerin ya da aday iniş bölgelerinin hedefleri.
2. **Hedef ölçülür.** Eğim ve engebe NASA'nın lazer altimetre haritalarından (LRO LOLA, MGS MOLA), sıcaklık Diviner ölçümlerinden ve Mars Climate Database'den, buz Diviner'ın kutup verisinden gelir. Her sayının kaynağı uygulamada yazılıdır.
3. **Dünya ölçülür.** Tüm karalar 25 km'lik karelere bölündü: **250.022 kare**. Her karede aynı özellikler NASA ve ajans uydu verilerinden hesaplandı (Copernicus DEM, MODIS, GPM IMERG, ASTER, ESA CCI Permafrost). Tarım alanları, şehirler, su ve buz tabakaları dışarıda bırakıldı.
4. **Test amacı seçilir.** "Benzer" demek, ne test edileceğine bağlıdır. Bir rover için eğim ve kayaç önemlidir; bir matkap için donmuş zemin. Yedi test amacı var:
   - Rover sürüşü ve tekerlek aşınması
   - Donmuş zeminde buz sondajı (yerinde su elde etme)
   - Lav tüpü ve yeraltı habitatı
   - Toz fırtınası ve aşınma
   - Biyo-imza: aşırı kuraklıkta korunma
   - Biyo-imza: karbonat çökeli
   - Üs kurulumu ve iniş alanı (aydınlanma dahil)
5. **Benzerlik hesaplanır.** Her özellik için Dünya değeri hedefe ne kadar yakınsa o kadar puan alır; test amacına göre ağırlıklandırılır ve 0–100 arası bir skor çıkar. Ölçülemeyen bir özellik "benzemiyor" sayılmaz, "bilinmiyor" sayılır.
6. **Adaylar listelenir.** Her hedef ve test için en iyi 20 yer, birbirine 100 km'den yakın olmayacak şekilde seçilir. Toplam **500 adayın 498'i, bilinen analog sahaların 50 km dışında**: yani yeni. Her test her hedefte çalışmaz: atmosferi olmayan Ay'da toz ve biyo-imza testi, buzu olmayan hedefte buz sondajı yapılmaz (42 kombinasyonun 25'i).

## Benzerliğin bittiği yer

Dünya'da hiçbir yer Ay ya da Mars değildir. GeoCosmos bunu saklamaz, her aday kartında açıkça yazar:

- **Yerçekimi** her zaman farklıdır: Ay'da Dünya'nın altıda biri, Mars'ta yaklaşık üçte biri.
- **Atmosfer:** Ay'da yok denecek kadar ince, Mars'ta çok ince ve karbondioksitten oluşuyor.
- **Radyasyon:** İkisinde de manyetik kalkan yok.
- **Sıcaklık:** Ay kutbunun gölgelerinde −180 °C; Dünya'da karşılığı yok.

Kart, her özelliğin Dünya ve hedef değerini yan yana gösterir ve benzeyenleri ✓, benzemeyenleri ✗ ile işaretler.

## Neler bulduk?

Uygulamadaki **Bulgular** sayfası üç yıldız adayı (Taklamakan, Amund Ringnes Adası, Peru And Dağları) uydu görüntüleriyle anlatıyor. Bazı örnekler:

- **Taklamakan Çölü'nün güney kenarı (Çin):** Havasındaki toz miktarı, Curiosity'nin gezdiği Gale Krateri için hesaplanan değere çok yakın. Toz fırtınasında güneş paneli ve mekanizma testi için aday.
- **Amund Ringnes Adası (Kanada Arktiği):** Mars'ta insanlı iniş için konuşulan Arcadia Planitia gibi düz ve yüzeye yakın buzla dolu. Buz sondajı için aday.
- **Ellesmere Adası çevresi (82°K, Kanada):** Ay'ın güney kutbundaki Shackleton için "üs kurulumu" testinin ilk adayı. Güneş ufka yakın, gölgeler uzun, donmuş zemin oranı hedefe yakın.
- **Malapert'in ikilemi:** Malapert kadar engebeli yerler (Karakurum gibi) orta enlemlerde, güneşin tepede olduğu yerlerde. Kutup ışığına benzeyen yerler ise o kadar engebeli değil. Dünya'da ikisi bir arada yok. Bu da bir bulgu: o testin bir kısmı Dünya'da yapılamaz.

## Kendimizi nasıl sınadık?

Bilinen analog sahaların bir kısmını (Hanksville, Svalbard, Salda Gölü, Lut Çölü) **sınav** için ayırdık ve ayarlarda onlara hiç bakmadık. Hedefimiz: dördünden en az üçünün kendi testinde Dünya'nın en iyi %1'lik dilimine girmesiydi.

**Sonuç: Bu ölçütü sağlamıyoruz.** Svalbard en iyi %2,6'da, Lut %5,5'te, Hanksville %18'de, Salda %49'da kaldı. Bunu saklamak yerine nedenlerini yazdık:

- 25 km'lik kareler küçük sahaları yutuyor. Salda'nın karbonat şeridi birkaç km² ve karede kayboluyor. Çözüm olarak 5 km'lik yakın tarama planlandı.
- Bazı analog türleri (örneğin tüm bir çöl) %1 gibi dar bir dilime sığmayacak kadar yaygın.

Sınav sonuçlarını gördükten sonra yaptığımız her değişikliği STATUS.md'de tarihiyle ve "sonuçtan sonra yapıldı" notuyla yazdık.

## Bilerek yapmadıklarımız

- **Lav tüplerini göremiyoruz.** Tüpler yer altında; motor sadece tüp oluşabilecek araziyi (genç, bazaltik lav akıntısı) arıyor.
- **Krateri doğrudan aramıyoruz.** Krater benzeri araziyi eğim ve engebeyle buluyoruz; bilinen kraterleri (Meteor Krateri, Ries) tekrar önermiyoruz.
- **Tuz ölçmüyoruz.** Tuz düzlükleri taramada var, ama hedeflerimiz tuz birikintisi değil.
- **Buzulları dışarıda bırakıyoruz.** Donmuş zemin buz kütlesi değildir; buz tabakasını "Ay'ın buzlu toprağına benziyor" diye önermek yanlış olurdu.
- **Güney Yarımküre'de donmuş zemin verisi eksik.** And Dağları'nın yüksek kesimlerinde dağ permafrostu var ama küresel, tutarlı bir veri yok.
- **Aydınlanma geometrik.** Güneş yüksekliğini enlemden hesaplıyoruz; dağların ve krater duvarlarının gölgesi hesaba girmiyor.

## Kendin dene

Uygulamada bir hedef ve test amacı seç: Dünya haritasında benzerlik ısı haritası ve en iyi 20 aday çıkar. Bir adaya tıkla: neden benzediğini, nerede benzemediğini ve verinin kaynağını gör. "Kendi senaryon" kutusuna serbest metin yaz ("toz fırtınasında güneş paneli testi"): sistem bunu ağırlıklara çevirip yeni bir arama yapar.

## Veri kaynakları

NASA: LRO LOLA ve Diviner, MGS MOLA, MODIS (sıcaklık, bitki örtüsü, toz, arazi örtüsü), GPM IMERG (yağış), ASTER GED (kayaç türü), NASA GIBS (harita görüntüleri), SEDAC GPW (nüfus). Diğer ajanslar ve kurumlar: ESA Copernicus DEM, ESA CCI Permafrost, Mars Climate Database (LMD/ESA/CNES), Malaria Atlas Project (şehre erişim süresi). Dünya karelerinin hesabı Google Earth Engine'de yapıldı, ham uydu verisi indirilmedi (permafrost hariç: ESA CCI dosyası yerelde işlendi).
