// Aday saha raporu: risk listesi ve aşamalı yol haritası. Kural tabanlı; sadece motorun çıktısını
// (parametreler, kopma noktaları, kurulum kolaylığı) yeniden düzenler, yeni sayı üretmez.
import { shortLabel } from "./format";
import type { Analog, Body, Logistics, LogisticsKey, Meta, TestId } from "./types";

export interface Phase {
  title: string;
  goal: string;
  steps: string[];
}

const LOGISTICS_ADVICE: Record<LogisticsKey, string> = {
  access: "Ekip ve malzemeyi uçak, helikopter ya da sezonluk yolla taşı; taşıma penceresini hava durumuna göre planla.",
  power: "Enerjiyi kendin getir: güneş paneli + batarya ya da jeneratör ve yakıt deposu; günlük enerji bütçesini çıkar.",
  water: "Suyu taşı ya da yerinde üret (kuyu, kar/buz eritme, arıtma); kişi başı günlük ihtiyacı baştan hesapla.",
  supply: "Prefabrik modüller, yedek parçalar ve sarf malzemesinin tamamını baştan getir; yerel tedarike güvenme.",
  altitude: "İrtifa: ekibe aklimatizasyon günü ayır, jeneratör ve motor verimindeki düşüşü enerji bütçesine kat.",
};

const CAMPAIGN: Record<TestId, string[]> = {
  rover: [
    "Farklı eğim ve pürüzlülükte bir sürüş parkuru işaretle (hedefe en benzeyen kısımlar öncelikli).",
    "Tekerlek aşınması, patinaj ve enerji tüketimini her sürüşte kaydet.",
    "Otonom navigasyonu (engel tanıma, rota planlama) gecikmeli komutla dene.",
  ],
  ice_drilling: [
    "Donmuş zemine kademeli derinlikte sondaj yap; delme hızı, matkap gücü ve ısınmayı kaydet.",
    "Karot örneklerinde buz oranını ölç, ısınmadan saklama zincirini (soğuk zincir) dene.",
    "Su çıkarma (ISRU) verimini, harcanan enerjiye göre hesapla.",
  ],
  lava_tube: [
    "Tüp ağzını ve tavan kalınlığını drone/LIDAR ile haritala; giriş güvenliğini değerlendir.",
    "Tüp içinde iletişim, konumlama ve aydınlatma sistemlerini dene.",
    "İçeride sıcaklık kararlılığını ve dış ortama göre koruma etkisini ölç.",
  ],
  dust: [
    "Güneş panellerinin tozlanma hızını gün/hafta aralıklarla ölç.",
    "Toz temizleme yöntemlerini (titreşim, elektrostatik, fırça) karşılaştır.",
    "Conta, rulman ve açılır mekanizmalarda toz kaynaklı aşınmayı izle.",
  ],
  biosignature_arid: [
    "Steril örnekleme protokolünü uygula; her örnekle birlikte kontaminasyon kontrol örneği al.",
    "Biyo-imza / organik madde tespit cihazını sahada, laboratuvar sonucuyla karşılaştırmak üzere dene.",
    "Örnek derinliği ile korunma ilişkisini kaydet (yüzey, 5 cm, 30 cm).",
  ],
  biosignature_carbonate: [
    "Karbonat çökellerini spektrometreyle haritala; örnek noktalarını bu haritadan seç.",
    "Steril örnekleme ve kontaminasyon kontrol örnekleriyle biyo-imza araması yap.",
    "Saha cihazı sonuçlarını laboratuvar analiziyle karşılaştır.",
  ],
  base_site: [
    "Habitat modülünü kur; kurulum süresini, ekip iş yükünü ve enerji bütçesini kaydet.",
    "İniş alanı adayında zeminin taşıma kapasitesini ve toz/çakıl kalkmasını ölç.",
    "Kapalı ortamda ekip rotasyonu ve izolasyon denemesi yap (iletişim gecikmesi dahil).",
  ],
};

export function season(lat: number): string | null {
  if (lat >= 60) return "Saha çalışmasını kutup yazına planla (Haziran–Ağustos): gün ışığı, ulaşım ve sıcaklık bu pencerede elverişli.";
  if (lat <= -60) return "Saha çalışmasını kutup yazına planla (Aralık–Şubat): gün ışığı, ulaşım ve sıcaklık bu pencerede elverişli.";
  return null;
}

export function risks(analog: Analog, meta: Meta, body: Body, logistics: Logistics | null | undefined): string[] {
  const out: string[] = [];
  for (const [, p] of Object.entries(logistics?.parts ?? {})) {
    if (p.score < 40) out.push(`Altyapı · ${p.label}: ${p.text}${p.label === "Yükseklik" ? " (irtifa hastalığı riski)" : ""}.`);
  }
  const elev = logistics?.raw.elev_m;
  const altitudeListed = (logistics?.parts.altitude?.score ?? 100) < 40;
  if (elev != null && elev >= 3000 && !altitudeListed) out.push(`Sağlık · Ortalama yükseklik ${Math.round(elev)} m: irtifa hastalığı riski.`);
  for (const p of analog.params) {
    if (!p.match) out.push(`Benzerlik · ${shortLabel(meta.parameters[p.key]?.label ?? p.key)} hedefe benzemiyor: bu konudaki sonuçlar hedefe doğrudan aktarılamaz.`);
  }
  for (const k of analog.breakdown) out.push(`Hedef farkı · ${meta.breakdown_labels[k]}: ${meta.breakdown_notes[body][k]}`);
  return out;
}

export function roadmap(analog: Analog, meta: Meta, body: Body, logistics: Logistics | null | undefined, testId: TestId | "custom"): Phase[] {
  const matched = analog.params.filter((p) => p.match).map((p) => shortLabel(meta.parameters[p.key]?.label ?? p.key));
  const unmatched = analog.params.filter((p) => !p.match).map((p) => shortLabel(meta.parameters[p.key]?.label ?? p.key));
  const parts = Object.entries(logistics?.parts ?? {}) as [LogisticsKey, { label: string; score: number; text: string }][];
  const weak = parts.filter(([, p]) => p.score < 40);
  const strong = parts.filter(([, p]) => p.score >= 70);
  const s = season(analog.lat);

  const phases: Phase[] = [
    {
      title: "Masa başı ön inceleme",
      goal: "Sahaya gitmeden önce yerin gerçekten uygun olduğundan emin ol.",
      steps: [
        "Uydu görüntüsü ve Sokak Görünümü bağlantılarıyla yolları, yerleşimi ve arazi kullanımını kontrol et.",
        "Arazinin sahibini, koruma alanı olup olmadığını ve gereken izinleri (araştırma, drone, örnek çıkarma) öğren.",
        ...(analog.past_tests.length ? [`Burada daha önce yapılmış ${analog.past_tests.length} çalışmayı oku; aynı izin ve lojistik yolunu kullan.`] : []),
        ...(s ? [s] : []),
      ],
    },
    {
      title: "Keşif gezisi (zemin doğrulama)",
      goal: "Uydudan gelen değerlerin yerde de doğru olduğunu küçük bir ekiple doğrula.",
      steps: [
        ...(matched.length ? [`Hedefe benzeyen parametreleri yerinde ölç: ${matched.join(", ")}.`] : []),
        ...(unmatched.length ? [`Benzemeyen parametreleri not et (test sonuçlarında hesaba katılacak): ${unmatched.join(", ")}.`] : []),
        "25 km'lik karenin içinde testin kurulacağı en uygun noktayı seç; koordinatını ve fotoğraflarını kaydet.",
      ],
    },
    {
      title: "Lojistik ve altyapı kurulumu",
      goal: logistics?.score != null ? `Kurulum kolaylığı ${Math.round(logistics.score)}/100 (${logistics.level?.toLowerCase()}): eksik altyapıyı kampanyadan önce tamamla.` : "Ulaşım, enerji ve su planını kampanyadan önce tamamla.",
      steps: [
        ...strong.map(([, p]) => `Avantaj · ${p.label}: ${p.text}; bunu planın merkezine koy.`),
        ...weak.map(([k]) => LOGISTICS_ADVICE[k]),
        ...(parts.length === 0 ? ["Bu kare için altyapı verisi yok: ulaşım, enerji ve su durumunu keşif gezisinde çıkar."] : []),
        "İletişim (uydu telefonu / terminal), ilk yardım ve tahliye planını hazırla.",
      ],
    },
    {
      title: "Test kampanyası",
      goal: "Asıl test: hedefe benzeyen koşullarda ekipmanı ve prosedürleri dene.",
      steps:
        testId === "custom"
          ? ["Senaryondaki testi, ağırlığı en yüksek parametrelerin en benzer olduğu noktada kur.", "Her denemede ortam koşullarını (sıcaklık, rüzgar, toz) kaydet."]
          : CAMPAIGN[testId],
    },
    {
      title: "Değerlendirme ve hedefe aktarma",
      goal: "Sonuçları Dünya'nın hedeften farklı olduğu yönleri hesaba katarak yorumla.",
      steps: [
        ...analog.breakdown.map((k) => `${meta.breakdown_labels[k]}: ${meta.breakdown_notes[body][k]}`),
        "Sonuçları ve sahadaki ölçümleri GeoCosmos skorlarıyla karşılaştır; benzerliğin koptuğu yerleri rapora ekle.",
      ],
    },
  ];
  return phases;
}
