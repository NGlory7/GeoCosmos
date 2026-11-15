// Aday saha raporu: risk listesi ve aşamalı yol haritası. Kural tabanlı; sadece motorun çıktısını
// (parametreler, kopma noktaları, kurulum kolaylığı) yeniden düzenler, yeni sayı üretmez.
// Metinler arayüz diline göre (tx): Türkçe ve İngilizce yan yana.
import { shortLabel } from "./format";
import { tx } from "./i18n";
import type { Analog, Body, Logistics, LogisticsKey, Meta, TestId } from "./types";

export interface Phase {
  title: string;
  goal: string;
  steps: string[];
}

type Pair = [tr: string, en: string];
const pick = ([tr, en]: Pair) => tx(tr, en);

const LOGISTICS_ADVICE: Record<LogisticsKey, Pair> = {
  access: [
    "Ekip ve malzemeyi uçak, helikopter ya da sezonluk yolla taşı; taşıma penceresini hava durumuna göre planla.",
    "Move crew and equipment by plane, helicopter or seasonal road; plan the transport window around the weather.",
  ],
  power: [
    "Enerjiyi kendin getir: güneş paneli + batarya ya da jeneratör ve yakıt deposu; günlük enerji bütçesini çıkar.",
    "Bring your own power: solar panels + batteries or a generator and fuel store; work out a daily energy budget.",
  ],
  water: [
    "Suyu taşı ya da yerinde üret (kuyu, kar/buz eritme, arıtma); kişi başı günlük ihtiyacı baştan hesapla.",
    "Carry water in or produce it on site (well, melting snow/ice, treatment); calculate daily needs per person up front.",
  ],
  supply: [
    "Prefabrik modüller, yedek parçalar ve sarf malzemesinin tamamını baştan getir; yerel tedarike güvenme.",
    "Bring all prefabricated modules, spare parts and consumables from the start; do not rely on local supply.",
  ],
  altitude: [
    "İrtifa: ekibe aklimatizasyon günü ayır, jeneratör ve motor verimindeki düşüşü enerji bütçesine kat.",
    "Altitude: set aside acclimatisation days for the crew and include the drop in generator and engine efficiency in the energy budget.",
  ],
};

const CAMPAIGN: Record<TestId, Pair[]> = {
  rover: [
    [
      "Farklı eğim ve pürüzlülükte bir sürüş parkuru işaretle (hedefe en benzeyen kısımlar öncelikli).",
      "Mark out a driving course with varied slope and roughness (sections most similar to the target first).",
    ],
    ["Tekerlek aşınması, patinaj ve enerji tüketimini her sürüşte kaydet.", "Record wheel wear, slip and energy use on every drive."],
    [
      "Otonom navigasyonu (engel tanıma, rota planlama) gecikmeli komutla dene.",
      "Test autonomous navigation (obstacle detection, route planning) with delayed commands.",
    ],
  ],
  ice_drilling: [
    [
      "Donmuş zemine kademeli derinlikte sondaj yap; delme hızı, matkap gücü ve ısınmayı kaydet.",
      "Drill into frozen ground at stepped depths; record penetration rate, drill power and heating.",
    ],
    [
      "Karot örneklerinde buz oranını ölç, ısınmadan saklama zincirini (soğuk zincir) dene.",
      "Measure ice content in cores and test the cold chain for storing them without warming.",
    ],
    ["Su çıkarma (ISRU) verimini, harcanan enerjiye göre hesapla.", "Calculate water extraction (ISRU) efficiency against the energy spent."],
  ],
  lava_tube: [
    [
      "Tüp ağzını ve tavan kalınlığını drone/LIDAR ile haritala; giriş güvenliğini değerlendir.",
      "Map the tube entrance and roof thickness with drone/LIDAR; assess entry safety.",
    ],
    ["Tüp içinde iletişim, konumlama ve aydınlatma sistemlerini dene.", "Test communication, positioning and lighting systems inside the tube."],
    [
      "İçeride sıcaklık kararlılığını ve dış ortama göre koruma etkisini ölç.",
      "Measure temperature stability inside and the shielding effect compared with outside.",
    ],
  ],
  dust: [
    ["Güneş panellerinin tozlanma hızını gün/hafta aralıklarla ölç.", "Measure solar panel soiling rate at daily/weekly intervals."],
    [
      "Toz temizleme yöntemlerini (titreşim, elektrostatik, fırça) karşılaştır.",
      "Compare dust removal methods (vibration, electrostatic, brush).",
    ],
    [
      "Conta, rulman ve açılır mekanizmalarda toz kaynaklı aşınmayı izle.",
      "Monitor dust-driven wear on seals, bearings and deployable mechanisms.",
    ],
  ],
  biosignature_arid: [
    [
      "Steril örnekleme protokolünü uygula; her örnekle birlikte kontaminasyon kontrol örneği al.",
      "Follow a sterile sampling protocol; take a contamination control sample with every sample.",
    ],
    [
      "Biyo-imza / organik madde tespit cihazını sahada, laboratuvar sonucuyla karşılaştırmak üzere dene.",
      "Test the biosignature / organics detector in the field, to compare against laboratory results.",
    ],
    [
      "Örnek derinliği ile korunma ilişkisini kaydet (yüzey, 5 cm, 30 cm).",
      "Record how preservation relates to sample depth (surface, 5 cm, 30 cm).",
    ],
  ],
  biosignature_carbonate: [
    [
      "Karbonat çökellerini spektrometreyle haritala; örnek noktalarını bu haritadan seç.",
      "Map carbonate deposits with a spectrometer; choose sampling points from this map.",
    ],
    [
      "Steril örnekleme ve kontaminasyon kontrol örnekleriyle biyo-imza araması yap.",
      "Search for biosignatures with sterile sampling and contamination control samples.",
    ],
    ["Saha cihazı sonuçlarını laboratuvar analiziyle karşılaştır.", "Compare field instrument results with laboratory analysis."],
  ],
  base_site: [
    [
      "Habitat modülünü kur; kurulum süresini, ekip iş yükünü ve enerji bütçesini kaydet.",
      "Set up the habitat module; record setup time, crew workload and energy budget.",
    ],
    [
      "İniş alanı adayında zeminin taşıma kapasitesini ve toz/çakıl kalkmasını ölç.",
      "At the landing site candidate, measure ground bearing capacity and dust/gravel ejection.",
    ],
    [
      "Kapalı ortamda ekip rotasyonu ve izolasyon denemesi yap (iletişim gecikmesi dahil).",
      "Run a crew rotation and isolation trial in a closed habitat (including communication delay).",
    ],
  ],
};

export function season(lat: number): string | null {
  if (lat >= 60)
    return tx(
      "Saha çalışmasını kutup yazına planla (Haziran–Ağustos): gün ışığı, ulaşım ve sıcaklık bu pencerede elverişli.",
      "Plan fieldwork for the polar summer (June–August): daylight, access and temperature are favourable in this window.",
    );
  if (lat <= -60)
    return tx(
      "Saha çalışmasını kutup yazına planla (Aralık–Şubat): gün ışığı, ulaşım ve sıcaklık bu pencerede elverişli.",
      "Plan fieldwork for the polar summer (December–February): daylight, access and temperature are favourable in this window.",
    );
  return null;
}

export function risks(analog: Analog, meta: Meta, body: Body, logistics: Logistics | null | undefined): string[] {
  const out: string[] = [];
  for (const [k, p] of Object.entries(logistics?.parts ?? {})) {
    if (p.score < 40)
      out.push(
        `${tx("Altyapı", "Infrastructure")} · ${p.label}: ${p.text}${k === "altitude" ? tx(" (irtifa hastalığı riski)", " (altitude sickness risk)") : ""}.`,
      );
  }
  const elev = logistics?.raw.elev_m;
  const altitudeListed = (logistics?.parts.altitude?.score ?? 100) < 40;
  if (elev != null && elev >= 3000 && !altitudeListed)
    out.push(
      tx(
        `Sağlık · Ortalama yükseklik ${Math.round(elev)} m: irtifa hastalığı riski.`,
        `Health · Mean elevation ${Math.round(elev)} m: altitude sickness risk.`,
      ),
    );
  for (const p of analog.params) {
    if (!p.match) {
      const label = shortLabel(meta.parameters[p.key]?.label ?? p.key);
      out.push(
        tx(
          `Benzerlik · ${label} hedefe benzemiyor: bu konudaki sonuçlar hedefe doğrudan aktarılamaz.`,
          `Similarity · ${label} does not match the target: results on this aspect cannot be transferred directly to the target.`,
        ),
      );
    }
  }
  for (const k of analog.breakdown) out.push(`${tx("Hedef farkı", "Target difference")} · ${meta.breakdown_labels[k]}: ${meta.breakdown_notes[body][k]}`);
  return out;
}

export function roadmap(analog: Analog, meta: Meta, body: Body, logistics: Logistics | null | undefined, testId: TestId | "custom"): Phase[] {
  const matched = analog.params.filter((p) => p.match).map((p) => shortLabel(meta.parameters[p.key]?.label ?? p.key));
  const unmatched = analog.params.filter((p) => !p.match).map((p) => shortLabel(meta.parameters[p.key]?.label ?? p.key));
  const parts = Object.entries(logistics?.parts ?? {}) as [LogisticsKey, { label: string; score: number; text: string }][];
  const weak = parts.filter(([, p]) => p.score < 40);
  const strong = parts.filter(([, p]) => p.score >= 70);
  const s = season(analog.lat);
  const n = analog.past_tests.length;

  const phases: Phase[] = [
    {
      title: tx("Masa başı ön inceleme", "Desk review"),
      goal: tx("Sahaya gitmeden önce yerin gerçekten uygun olduğundan emin ol.", "Make sure the site is really suitable before going into the field."),
      steps: [
        tx(
          "Uydu görüntüsü ve Sokak Görünümü bağlantılarıyla yolları, yerleşimi ve arazi kullanımını kontrol et.",
          "Check roads, settlements and land use with the satellite image and Street View links.",
        ),
        tx(
          "Arazinin sahibini, koruma alanı olup olmadığını ve gereken izinleri (araştırma, drone, örnek çıkarma) öğren.",
          "Find out who owns the land, whether it is a protected area and which permits are needed (research, drones, sample export).",
        ),
        ...(n
          ? [
              tx(
                `Burada daha önce yapılmış ${n} çalışmayı oku; aynı izin ve lojistik yolunu kullan.`,
                `Read the ${n} previous studies done here; reuse their permit and logistics route.`,
              ),
            ]
          : []),
        ...(s ? [s] : []),
      ],
    },
    {
      title: tx("Keşif gezisi (zemin doğrulama)", "Scouting trip (ground truthing)"),
      goal: tx(
        "Uydudan gelen değerlerin yerde de doğru olduğunu küçük bir ekiple doğrula.",
        "Confirm with a small team that the satellite values hold on the ground.",
      ),
      steps: [
        ...(matched.length
          ? [tx(`Hedefe benzeyen parametreleri yerinde ölç: ${matched.join(", ")}.`, `Measure the parameters that match the target on site: ${matched.join(", ")}.`)]
          : []),
        ...(unmatched.length
          ? [
              tx(
                `Benzemeyen parametreleri not et (test sonuçlarında hesaba katılacak): ${unmatched.join(", ")}.`,
                `Note the parameters that do not match (to account for in test results): ${unmatched.join(", ")}.`,
              ),
            ]
          : []),
        tx(
          "25 km'lik karenin içinde testin kurulacağı en uygun noktayı seç; koordinatını ve fotoğraflarını kaydet.",
          "Within the 25 km cell, choose the best spot to set up the test; record its coordinates and photos.",
        ),
      ],
    },
    {
      title: tx("Lojistik ve altyapı kurulumu", "Logistics and infrastructure"),
      goal:
        logistics?.score != null
          ? tx(
              `Kurulum kolaylığı ${Math.round(logistics.score)}/100 (${logistics.level?.toLowerCase()}): eksik altyapıyı kampanyadan önce tamamla.`,
              `Ease of setup ${Math.round(logistics.score)}/100 (${logistics.level?.toLowerCase()}): fill infrastructure gaps before the campaign.`,
            )
          : tx("Ulaşım, enerji ve su planını kampanyadan önce tamamla.", "Finish the access, power and water plan before the campaign."),
      steps: [
        ...strong.map(([, p]) => tx(`Avantaj · ${p.label}: ${p.text}; bunu planın merkezine koy.`, `Advantage · ${p.label}: ${p.text}; build the plan around it.`)),
        ...weak.map(([k]) => pick(LOGISTICS_ADVICE[k])),
        ...(parts.length === 0
          ? [
              tx(
                "Bu kare için altyapı verisi yok: ulaşım, enerji ve su durumunu keşif gezisinde çıkar.",
                "No infrastructure data for this cell: establish access, power and water during the scouting trip.",
              ),
            ]
          : []),
        tx(
          "İletişim (uydu telefonu / terminal), ilk yardım ve tahliye planını hazırla.",
          "Prepare communications (satellite phone / terminal), first aid and an evacuation plan.",
        ),
      ],
    },
    {
      title: tx("Test kampanyası", "Test campaign"),
      goal: tx("Asıl test: hedefe benzeyen koşullarda ekipmanı ve prosedürleri dene.", "The main test: try equipment and procedures in target-like conditions."),
      steps:
        testId === "custom"
          ? [
              tx(
                "Senaryondaki testi, ağırlığı en yüksek parametrelerin en benzer olduğu noktada kur.",
                "Set up your scenario's test where the highest-weighted parameters are most similar.",
              ),
              tx("Her denemede ortam koşullarını (sıcaklık, rüzgar, toz) kaydet.", "Record ambient conditions (temperature, wind, dust) on every run."),
            ]
          : CAMPAIGN[testId].map(pick),
    },
    {
      title: tx("Değerlendirme ve hedefe aktarma", "Evaluation and transfer to the target"),
      goal: tx(
        "Sonuçları Dünya'nın hedeften farklı olduğu yönleri hesaba katarak yorumla.",
        "Interpret the results taking into account how Earth differs from the target.",
      ),
      steps: [
        ...analog.breakdown.map((k) => `${meta.breakdown_labels[k]}: ${meta.breakdown_notes[body][k]}`),
        tx(
          "Sonuçları ve sahadaki ölçümleri GeoCosmos skorlarıyla karşılaştır; benzerliğin koptuğu yerleri rapora ekle.",
          "Compare results and field measurements with the GeoCosmos scores; add where the analogy breaks to the report.",
        ),
      ],
    },
  ];
  return phases;
}
