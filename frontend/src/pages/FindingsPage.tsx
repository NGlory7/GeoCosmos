import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import SpaceLayout from "../components/SpaceLayout";
import { coord, int, num, pct, shortLabel } from "../format";
import { useLang, type Lang } from "../i18n";
import { localizeMeta, localizeTargets, localizeValidation } from "../i18nData";
import { loadAnalogIndex, loadAnalogs, loadMeta, loadTargets, loadValidation, type TargetWithCoords } from "../services/data";
import type { Analog, AnalogIndexEntry, Body, Meta, TestId, ValidationResult } from "../types";

// Halka açık bulgular sayfası: motorun bulduğu yıldız adayları, sade dille.
// Anlatı elle yazılır; sayıların hepsi üretilmiş dosyalardan (make data) okunur, sayfada sayı uydurulmaz.
// Aday karesi `cell` ile sabitlenir: tarama yeniden çalışıp bu kare listeden çıkarsa sayfa bunu açıkça söyler.

interface Finding {
  cell: string; // analog id (grid.parquet kare kimliği)
  body: Body;
  targetId: string;
  testId: TestId;
  place: string;
  region: string; // ters coğrafi kodlama: OpenStreetMap Nominatim
  title: string;
  why: string;
  use: string;
  caveat: string;
  image: { layer: string; date?: string; credit: string };
  en: { place: string; region: string; title: string; why: string; use: string; caveat: string; credit: string };
  compareWith?: string; // validation.json'daki bilinen saha (aynı test ve hedef)
}

const FINDINGS: Finding[] = [
  {
    cell: "g25_36.288_82.459",
    body: "mars",
    targetId: "mars_gale",
    testId: "dust",
    place: "Taklamakan Çölü'nün güney kenarı",
    region: "Keriya ilçesi, Hotan, Sincan (Çin)",
    title: "Mars tozunun Dünya'daki provası",
    why:
      "Bu karenin havasındaki toz miktarı, Curiosity'nin gezdiği Gale Krateri için hesaplanan değerle neredeyse aynı. Arazinin engebesi de Gale'inkiyle birebir örtüşüyor. Kare, Kunlun Dağları'nın eteğinde, dünyanın en büyük toz kaynaklarından biri olan Taklamakan Çölü'nün kenarında.",
    use: "Toz fırtınasında güneş paneli kirlenmesi, eklem ve contalara toz girişi, rüzgar aşındırması ve dağ eteğinde rover sürüşü aynı sahada denenebilir.",
    caveat: "Gece-gündüz sıcaklık farkı Mars'tan çok küçük. Toz, Mars'ın ince karbondioksit atmosferinde Dünya'dakinden farklı taşınır.",
    image: { layer: "Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual", credit: "NASA GIBS · Landsat WELD yıllık mozaik" },
    en: {
      place: "Southern edge of the Taklamakan Desert",
      region: "Keriya County, Hotan, Xinjiang (China)",
      title: "A rehearsal for Martian dust on Earth",
      why:
        "The amount of dust in the air over this cell is almost the same as the value calculated for Gale Crater, where Curiosity drives. The roughness of the terrain also closely matches Gale's. The cell lies at the foot of the Kunlun Mountains, on the edge of the Taklamakan Desert, one of the world's largest dust sources.",
      use: "Solar panel soiling in dust storms, dust getting into joints and seals, wind abrasion and rover driving on a mountain foot can all be tested at the same site.",
      caveat: "The day-night temperature swing is much smaller than on Mars. Dust moves differently in Mars' thin carbon dioxide atmosphere than on Earth.",
      credit: "NASA GIBS · Landsat WELD annual mosaic",
    },
  },
  {
    cell: "g25_77.889_-96.496",
    body: "mars",
    targetId: "mars_arcadia",
    testId: "ice_drilling",
    place: "Amund Ringnes Adası",
    region: "Kanada Arktik Takımadaları, Nunavut (Kanada)",
    title: "Arcadia'nın buzlu düzlüğü, Kanada'nın kuzeyinde",
    why:
      "Arcadia Planitia, Mars'ta insanlı iniş için konuşulan bölgelerden biri: düz, kuru ve yüzeye yakın buzla dolu. Bu ada da öyle. Donmuş zemin oranı ve arazinin düzlüğü Arcadia ile neredeyse aynı çıkıyor.",
    use: "Buzlu zeminde matkap ve örnek alma, yüzeye yakın buzdan su elde etme (ISRU) denemeleri ve düz arazide iniş alanı değerlendirmesi için uygun.",
    caveat: "Arcadia çok daha soğuk ve gece-gündüz farkı çok daha büyük. Arktik yazında yüzey eriyip sıvı su oluşur; Mars'ta bu olmaz.",
    image: { layer: "MODIS_Terra_CorrectedReflectance_TrueColor", date: "2023-07-28", credit: "NASA GIBS · MODIS Terra, 28 Temmuz 2023" },
    en: {
      place: "Amund Ringnes Island",
      region: "Canadian Arctic Archipelago, Nunavut (Canada)",
      title: "Arcadia's icy plain, in northern Canada",
      why:
        "Arcadia Planitia is one of the regions discussed for a crewed Mars landing: flat, dry and full of near-surface ice. So is this island. Its frozen-ground fraction and flatness come out almost identical to Arcadia's.",
      use: "Suited to drilling and sampling in icy ground, extracting water from near-surface ice (ISRU) and assessing landing sites on flat terrain.",
      caveat: "Arcadia is much colder and its day-night swing is much larger. In the Arctic summer the surface thaws and liquid water forms; that does not happen on Mars.",
      credit: "NASA GIBS · MODIS Terra, 28 July 2023",
    },
    compareWith: "haughton",
  },
  {
    cell: "g25_-15.261_-73.242",
    body: "moon",
    targetId: "moon_shackleton",
    testId: "rover",
    place: "Peru And Dağları",
    region: "Corculla, Páucar del Sara Sara, Ayacucho (Peru)",
    title: "Ay'ın güney kutbundaki krater kenarına benzeyen engebe",
    why:
      "Artemis'in üs bölgesi olarak düşünülen Shackleton Krateri'nin kenarı dik ve engebeli. Bu karenin engebesi Shackleton'ınkiyle neredeyse metre metre aynı, eğimi de çok yakın. Üstelik yola erişimi olan bir yer: ekip ve ekipman götürmek kolay.",
    use: "Dik ve engebeli arazide rover sürüşü, eğimde çekiş ve devrilme sınırları, otonom yol planlama algoritmaları.",
    caveat:
      "Burada yağış ve bitki var, Ay'da yok. Ay kutbunun alçak güneşi ve kilometrelerce uzanan gölgeleri rover testinin hesabında yer almıyor; \"Üs kurulumu ve iniş alanı\" testi güneş yüksekliğini de ölçüyor (Shackleton için ilk aday Ellesmere Adası, Kanada).",
    image: { layer: "Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual", credit: "NASA GIBS · Landsat WELD yıllık mozaik" },
    en: {
      place: "Peruvian Andes",
      region: "Corculla, Páucar del Sara Sara, Ayacucho (Peru)",
      title: "Rugged terrain like a crater rim at the Moon's south pole",
      why:
        "The rim of Shackleton Crater, considered as the Artemis base region, is steep and rugged. This cell's roughness matches Shackleton's almost metre for metre, and its slope is very close too. It also has road access: getting a crew and equipment there is easy.",
      use: "Rover driving on steep, rugged terrain, traction and tip-over limits on slopes, autonomous path-planning algorithms.",
      caveat:
        "There is rain and vegetation here; there is none on the Moon. The low Sun and kilometre-long shadows of the lunar pole are not part of the rover test; the \"Base construction and landing site\" test also measures Sun elevation (first candidate for Shackleton: Ellesmere Island, Canada).",
      credit: "NASA GIBS · Landsat WELD annual mosaic",
    },
  },
];

const HALF_SPAN_LAT = 0.5; // görüntü kenarı ~110 km

function gibsUrl(f: Finding, lat: number, lon: number) {
  const dLon = HALF_SPAN_LAT / Math.max(Math.cos((lat * Math.PI) / 180), 0.15);
  const bbox = [lat - HALF_SPAN_LAT, lon - dLon, lat + HALF_SPAN_LAT, lon + dLon].map((v) => v.toFixed(3)).join(",");
  const q = new URLSearchParams({
    SERVICE: "WMS",
    REQUEST: "GetMap",
    VERSION: "1.3.0",
    LAYERS: f.image.layer,
    STYLES: "",
    CRS: "EPSG:4326", // WMS 1.3.0: BBOX enlem, boylam sırasıyla
    BBOX: bbox,
    WIDTH: "480",
    HEIGHT: "480",
    FORMAT: "image/jpeg",
  });
  if (f.image.date) q.set("TIME", f.image.date);
  return `https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?${q}`;
}

function km(aLat: number, aLon: number, bLat: number, bLon: number) {
  const r = Math.PI / 180;
  const h = Math.sin(((bLat - aLat) * r) / 2) ** 2 + Math.cos(aLat * r) * Math.cos(bLat * r) * Math.sin(((bLon - aLon) * r) / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

interface Loaded {
  meta: Meta;
  targets: TargetWithCoords[];
  index: AnalogIndexEntry[] | null;
  validation: ValidationResult | null;
  lists: Record<string, Analog[]>; // target_test -> adaylar
}

export default function FindingsPage() {
  const { t, lang, en } = useLang();
  const [raw, setData] = useState<Loaded | null>(null);
  const data: Loaded | null = raw && {
    ...raw,
    meta: localizeMeta(raw.meta, lang),
    targets: localizeTargets(raw.targets, lang),
    validation: raw.validation && { ...raw.validation, analogs: raw.validation.analogs.map((a) => localizeValidation(a, lang)) },
  };
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([loadMeta(), loadTargets(), loadAnalogIndex(), loadValidation()])
      .then(async ([meta, targets, index, validation]) => {
        const lists: Record<string, Analog[]> = {};
        await Promise.all(
          FINDINGS.map(async (f) => {
            const e = index?.find((x) => x.target_id === f.targetId && x.test_id === f.testId);
            lists[`${f.targetId}_${f.testId}`] = e?.file ? await loadAnalogs(e.file) : [];
          }),
        );
        if (alive) setData({ meta, targets, index, validation, lists });
      })
      .catch((e) => setError(String(e)));
    return () => {
      alive = false;
    };
  }, []);

  const newTotal = data?.index?.reduce((s, e) => s + (e.new_count ?? 0), 0);

  return (
    <SpaceLayout>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <p className="font-mono text-[11px] tracking-[0.3em] text-cyan-300/70">{t("BULGULAR", "FINDINGS")}</p>
        <h1 className="mt-2 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
          {t("Ay'a ve Mars'a gitmeden önce Dünya'da nerede prova yapmalı?", "Where on Earth should we rehearse before going to the Moon and Mars?")}
        </h1>
        <p className="mt-4 max-w-3xl text-slate-300">
          {t(
            "Uydu verisiyle Dünya'nın bütün karalarını taradık ve her yeri, Ay'daki ve Mars'taki gerçek hedeflerle karşılaştırdık. Amacımız zaten bilinen ünlü sahaları yeniden bulmak değil, az bilinen yeni test sahaları bulmaktı. Burada bunlardan üçünü anlatıyoruz: neden benzediklerini ve, en az onun kadar önemli, nerede benzemediklerini.",
            "We scanned all of Earth's land with satellite data and compared every place with real targets on the Moon and Mars. Our goal was not to rediscover famous, well-known sites but to find lesser-known new test sites. Here we describe three of them: why they are similar and, just as important, where they are not.",
          )}
        </p>
        {error && <p className="mt-4 text-sm text-rose-300">{error}</p>}

        {/* Neden ve nasıl */}
        <section className="mt-10 grid gap-4 md:grid-cols-3">
          <Info title={t("Neden Dünya'da prova?", "Why rehearse on Earth?")}>
            {t(
              "Bir rover'ı Mars'ta tamir etmek mümkün değil. Bu yüzden ekipman, yöntem ve ekipler önce Dünya'da, Ay'a veya Mars'a benzeyen yerlerde (analog sahalarda) denenir. Ama hiçbir yer her açıdan benzemez: bir yer rover sürüşü için mükemmel, buz sondajı için işe yaramaz olabilir.",
              "You cannot repair a rover on Mars. So equipment, methods and crews are first tried on Earth, in places that resemble the Moon or Mars (analog sites). But no place is similar in every way: a site can be perfect for rover driving and useless for ice drilling.",
            )}
          </Info>
          <Info title={t("Nasıl aradık?", "How did we search?")}>
            {en
              ? `We divided Earth into ${data ? `${data.meta.grid_km} km` : "equal"} cells. In each cell we measured slope, roughness, temperature, aridity, airborne dust, rock type and frozen ground from NASA and ESA satellite data. Then we scored every cell for a target and a test purpose: each test gives more weight to the properties that matter to it.`
              : `Dünya'yı ${data ? `${data.meta.grid_km} km'lik` : "eşit"} karelere böldük. Her karede NASA ve ESA uydu verisinden eğimi, engebeyi, sıcaklığı, kuraklığı, havadaki tozu, kayaç türünü ve donmuş zemini ölçtük. Sonra her kareyi bir hedef ve bir test amacı için puanladık: her test, kendi önemli gördüğü özelliklere daha çok ağırlık veriyor.`}
          </Info>
          <Info title={t("Ne bulduk?", "What did we find?")}>
            {newTotal !== undefined ? (
              en ? (
                <>
                  A total of <b className="text-white">{int(newTotal)}</b> new candidates across the{" "}
                  {data?.index?.filter((e) => e.file).length} meaningful combinations of {data?.targets.length} targets and{" "}
                  {data?.meta.tests.length} test purposes.{" "}
                </>
              ) : (
                <>
                  {data?.targets.length} hedef ve {data?.meta.tests.length} test amacının anlamlı{" "}
                  {data?.index?.filter((e) => e.file).length} eşleşmesi için toplam <b className="text-white">{int(newTotal)}</b> yeni aday.{" "}
                </>
              )
            ) : null}
            {t(
              "Bilinen ünlü sahalar (Atacama, Haughton, İzlanda, Hawaii…) listeye bilerek alınmadı; onlar motoru sınamak için kullanıldı.",
              "Famous known sites (Atacama, Haughton, Iceland, Hawaii…) were deliberately left out of the list; they were used to test the engine.",
            )}
          </Info>
        </section>

        {/* Yıldız adaylar */}
        <h2 className="mt-14 font-mono text-sm tracking-[0.25em] text-slate-400">{t("ÜÇ YILDIZ ADAY", "THREE STANDOUT CANDIDATES")}</h2>
        <div className="mt-4 grid gap-8">
          {FINDINGS.map((f, i) => (
            <FindingCard key={f.cell} n={i + 1} f={f} data={data} />
          ))}
        </div>

        <MalapertDilemma />

        {/* Dünya'nın taklit edemedikleri */}
        {data && (
          <section className="mt-14">
            <h2 className="font-mono text-sm tracking-[0.25em] text-slate-400">{t("DÜNYA'NIN TAKLİT EDEMEDİKLERİ", "WHAT EARTH CANNOT IMITATE")}</h2>
            <p className="mt-2 max-w-3xl text-slate-300">
              {t(
                "Hiçbir analog saha her şeyi sağlamaz. Aşağıdakiler, Dünya'nın hiçbir yerinde gerçek anlamda bulunamayan koşullar. Bunlar için vakum odaları, parabolik uçuşlar ve bilgisayar benzetimleri gerekir.",
                "No analog site provides everything. The conditions below cannot truly be found anywhere on Earth. They need vacuum chambers, parabolic flights and computer simulations.",
              )}
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead className="font-mono text-[10px] tracking-wider text-slate-500">
                  <tr>
                    <th className="py-2 pr-4" />
                    <th className="pr-4">{t("AY", "MOON")}</th>
                    <th>MARS</th>
                  </tr>
                </thead>
                <tbody>
                  {(["gravity", "atmosphere", "radiation", "temperature"] as const).map((k) => (
                    <tr key={k} className="border-t border-white/5 align-top">
                      <td className="py-2.5 pr-4 font-medium text-white">{data.meta.breakdown_labels[k]}</td>
                      <td className="py-2.5 pr-4 text-slate-300">{data.meta.breakdown_notes.moon[k]}</td>
                      <td className="py-2.5 text-slate-300">{data.meta.breakdown_notes.mars[k]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Dürüst sınırlar */}
        <section className="mt-14 rounded-2xl border border-amber-400/20 bg-amber-400/[0.04] p-6">
          <h2 className="font-mono text-sm tracking-[0.25em] text-amber-200/80">{t("BİLMENİZ GEREKENLER", "WHAT YOU SHOULD KNOW")}</h2>
          <ul className="mt-3 grid gap-3 text-sm text-slate-300">
            {data?.validation && (
              <li>
                {en ? (
                  <>
                    <b className="text-white">
                      Test result: {data.validation.hits}/{data.validation.holdout_total}.
                    </b>{" "}
                    We tested the engine on {data.validation.holdout_total} famous sites used by NASA and ESA: each had to reach the top{" "}
                    {pct(data.validation.top_percent, 1)} of Earth for its own test, and at least {data.validation.min_hits} had to make it (the original criterion was the top 1%, where the result was 0/4; it was relaxed after that result was seen).{" "}
                    {closest(data.validation, lang) && <>Closest: {closest(data.validation, lang)}. </>}
                    We do not hide this result;{" "}
                    <Link to="/dogrulama" className="text-cyan-300 hover:underline">
                      details and a comparison with chance are on the validation page
                    </Link>
                    .
                  </>
                ) : (
                  <>
                    <b className="text-white">
                      Sınav sonucu: {data.validation.hits}/{data.validation.holdout_total}.
                    </b>{" "}
                    Motoru, NASA ve ESA'nın kullandığı {data.validation.holdout_total} ünlü saha üzerinde sınadık: her biri kendi testinde
                    Dünya'nın en iyi {pct(data.validation.top_percent, 1)}'ine girmeliydi ve en az {data.validation.min_hits} tanesinin girmesi
                    gerekiyordu (ilk ölçüt en iyi %1'di ve sonuç 0/4'tü; ölçüt bu sonuç görüldükten sonra gevşetildi). {closest(data.validation, lang) && <>En yakın olanlar: {closest(data.validation, lang)}. </>}
                    Bu sonucu gizlemiyoruz;{" "}
                    <Link to="/dogrulama" className="text-cyan-300 hover:underline">
                      ayrıntılar ve şansla karşılaştırma doğrulama sayfasında
                    </Link>
                    .
                  </>
                )}
              </li>
            )}
            <li>
              <b className="text-white">
                {data ? `${data.meta.grid_km} km` : t("Kare", "Cell")} {t("çözünürlük.", "resolution.")}
              </b>{" "}
              {t(
                "Bir kare küçük bir krateri, bir göl kıyısını ya da bir vadiyi ortalamada kaybedebilir. Yıldız adaylar, sahaya gidilmeden önce daha ince ölçekte incelenmeli.",
                "A cell can average away a small crater, a lake shore or a valley. Standout candidates should be examined at a finer scale before anyone goes to the field.",
              )}
            </li>
            <li>
              <b className="text-white">{t("Mağaralar ve lav tüpleri yörüngeden görünmez.", "Caves and lava tubes cannot be seen from orbit.")}</b>{" "}
              {t("Motor sadece tüp oluşabilecek araziyi ölçebiliyor.", "The engine can only measure terrain where tubes can form.")}
            </li>
            <li>
              <b className="text-white">{t("Ay ve Mars değerleri tek bir noktadan.", "Moon and Mars values come from a single point.")}</b>{" "}
              {t(
                "Her hedef için değerler NASA görev verisi (LOLA, Diviner, MOLA) ve yayımlanmış makalelerden; kaynakların hepsi aday kartlarında yazıyor.",
                "Values for each target come from NASA mission data (LOLA, Diviner, MOLA) and published papers; every source is listed on the candidate cards.",
              )}
            </li>
          </ul>
        </section>

        <p className="mt-10 text-xs text-slate-500">
          {t(
            "Veri: NASA (MODIS, GPM IMERG, ASTER GED, SEDAC, LRO LOLA ve Diviner, MGS MOLA, GIBS), ESA (Copernicus DEM, CCI Permafrost), Mars Climate Database (LMD/ESA/CNES). Yer adları: OpenStreetMap Nominatim. Ayrıntılı kaynak listesi: DATA_SOURCES.md.",
            "Data: NASA (MODIS, GPM IMERG, ASTER GED, SEDAC, LRO LOLA and Diviner, MGS MOLA, GIBS), ESA (Copernicus DEM, CCI Permafrost), Mars Climate Database (LMD/ESA/CNES). Place names: OpenStreetMap Nominatim. Full source list: DATA_SOURCES.md.",
          )}
        </p>
      </main>
    </SpaceLayout>
  );
}

/** Sınav sahalarından en iyi iki dilim: "Svalbard (%2,6), Lut (%5,5)". */
function closest(v: ValidationResult, lang: Lang) {
  return v.analogs
    .filter((a) => a.split === "holdout" && a.status === "ok" && a.percentile !== undefined)
    .sort((a, b) => (a.percentile ?? 0) - (b.percentile ?? 0))
    .slice(0, 2)
    .map((a) => (lang === "en" ? `${a.name} (top ${pct(a.percentile ?? 0, 1)})` : `${a.name} (en iyi ${pct(a.percentile ?? 0, 1)})`))
    .join(", ");
}

// Malapert × üs kurulumu: ilk adaylar iki gruba ayrılıyor; iki koşulu birden sağlayan kare yok.
// Sayılar: frontend/public/data/analogs/moon_malapert_base_site.geojson (1-5. adaylar) ve
// grid.parquet (maskesiz 189.878 kare; pürüzlülük ≥ 417 m olan 331 karenin en kuzeydekisi 52,3°;
// |enlem| ≥ 56° karelerin en pürüzlüsü 382 m). Veri değişirse burası elle güncellenmeli.
const DILEMMA_SIDES = [
  {
    tr: { head: "Arazisi benzeyen", where: "Karakurum (Çin–Pakistan), 1-3. sıra", rough: "~480 m", sun: "~52°", score: "60,4" },
    en: { head: "Terrain matches", where: "Karakoram (China–Pakistan), ranks 1-3", rough: "~480 m", sun: "~52°", score: "60.4" },
    ok: "rough" as const,
  },
  {
    tr: { head: "Işığı benzeyen", where: "Ellesmere Adası (Kanada, 82°K), 4-5. sıra", rough: "~240 m", sun: "~8°", score: "58,7" },
    en: { head: "Light matches", where: "Ellesmere Island (Canada, 82°N), ranks 4-5", rough: "~240 m", sun: "~8°", score: "58.7" },
    ok: "sun" as const,
  },
];

function MalapertDilemma() {
  const { t, en } = useLang();
  return (
    <section className="mt-14 rounded-2xl border border-violet-400/20 bg-violet-400/[0.04] p-6">
      <p className="font-mono text-[11px] tracking-[0.3em] text-violet-300/80">{t("BULAMADIĞIMIZ YER", "THE PLACE WE COULD NOT FIND")}</p>
      <h2 className="mt-2 text-2xl font-semibold text-white">{t("Malapert'in ikilemi", "The Malapert dilemma")}</h2>
      <p className="mt-3 max-w-3xl text-slate-300">
        {t(
          "Malapert Masifi, Artemis'in Ay güney kutbundaki aday bölgelerinden biri: hem dağlık (engebe 467 m) hem de güneş ufka çok yakın (öğlen ortalama 4°). Üs kurulumu testi ikisine de önem veriyor. Motorun ilk adayları iki gruba ayrıldı ve puanları neredeyse eşit: biri araziyi, öbürü ışığı tutturuyor, ikisini birden tutturan yok.",
          "Malapert Massif is one of the Artemis candidate regions at the Moon's south pole: mountainous (roughness 467 m) with the Sun very close to the horizon (4° at noon on average). The base construction test cares about both. The engine's top candidates split into two groups with almost equal scores: one matches the terrain, the other the light, and none matches both.",
        )}
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {DILEMMA_SIDES.map((s) => {
          const x = en ? s.en : s.tr;
          return (
            <div key={s.ok} className="rounded-xl border border-white/10 bg-black/20 p-4">
              <p className="font-medium text-white">{x.head}</p>
              <p className="mt-0.5 text-xs text-slate-400">{x.where}</p>
              <dl className="mt-3 grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-1 text-sm">
                <dt className="text-slate-400">{t("Engebe", "Roughness")}</dt>
                <dd className="font-mono text-slate-200">{x.rough}</dd>
                <dd className={s.ok === "rough" ? "text-emerald-300" : "text-rose-300"}>{s.ok === "rough" ? "✓" : "✗"}</dd>
                <dt className="text-slate-400">{t("Öğlen güneşi", "Noon Sun")}</dt>
                <dd className="font-mono text-slate-200">{x.sun}</dd>
                <dd className={s.ok === "sun" ? "text-emerald-300" : "text-rose-300"}>{s.ok === "sun" ? "✓" : "✗"}</dd>
                <dt className="text-slate-400">{t("Puan", "Score")}</dt>
                <dd className="font-mono text-slate-200">{x.score}</dd>
                <dd />
              </dl>
            </div>
          );
        })}
      </div>
      <p className="mt-5 max-w-3xl text-sm text-slate-300">
        {t(
          "Bu bir rastlantı değil. Dünya'nın 189.878 karesinde Malapert kadar engebeli (417 m üstü) 331 kare var ve en kuzeydekisi 52° enlemde. Güneşin yeterince alçak olduğu 56°'nin kuzeyinde en engebeli kare 382 m. Dünya'nın en sarp dağları orta enlemlerde; kutuplarda bu kadar engebeli buzsuz arazi yok.",
          "This is not a coincidence. Of Earth's 189,878 cells, 331 are as rough as Malapert (above 417 m), and the northernmost lies at 52°. North of 56°, where the Sun is low enough, the roughest cell is 382 m. Earth's steepest mountains are at mid-latitudes; the poles have no ice-free land this rugged.",
        )}
      </p>
      <p className="mt-3 max-w-3xl text-sm text-slate-300">
        <b className="text-white">{t("Sonuç:", "Takeaway:")}</b>{" "}
        {t(
          "Malapert'e gidecek bir görevin provası Dünya'da tek bir sahada yapılamaz. Arazi provası Karakurum'da, alçak güneş ve uzun gölge provası Arktik'te ayrı ayrı yapılmalı.",
          "A mission to Malapert cannot be rehearsed at a single site on Earth. Terrain must be rehearsed in the Karakoram, and the low Sun and long shadows separately in the Arctic.",
        )}
      </p>
      <p className="mt-3 max-w-3xl text-xs text-slate-500">
        {t(
          "Not: güneş yüksekliği sadece enlemden hesaplanıyor; Malapert'in tepesinin yerel ufkun üstünde kalıp daha uzun güneş alması modelde yok. 25 km'den küçük ölçekte (ör. Alaska ve Grönland kıyı dağları) ikilem yumuşayabilir ama kalkmaz.",
          "Note: Sun elevation is computed from latitude only; Malapert's summit staying above the local horizon and getting longer sunlight is not modelled. At scales finer than 25 km (e.g. coastal mountains of Alaska and Greenland) the dilemma may soften but does not go away.",
        )}{" "}
        <Link to="/moon/moon_malapert/base_site" className="text-cyan-300 hover:underline">
          {t("Adayların tam listesi", "Full candidate list")}
        </Link>
      </p>
    </section>
  );
}

function Info({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <h2 className="font-medium text-white">{title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-slate-400">{children}</p>
    </div>
  );
}

function FindingCard({ n, f: base, data }: { n: number; f: Finding; data: Loaded | null }) {
  const { t, lang, en } = useLang();
  const f = en ? { ...base, ...base.en, image: { ...base.image, credit: base.en.credit } } : base;
  const list = data?.lists[`${f.targetId}_${f.testId}`] ?? [];
  const a = list.find((x) => x.id === f.cell);
  const target = data?.targets.find((t) => t.id === f.targetId);
  const test = data?.meta.tests.find((t) => t.id === f.testId);
  const known = f.compareWith ? data?.validation?.analogs.find((x) => x.id === f.compareWith && x.status === "ok") : undefined;
  const near = a ? list.slice(0, 20).filter((x) => km(a.lat, a.lon, x.lat, x.lon) < 1000).length : 0;
  const label = (key: string) => shortLabel(data?.meta.parameters[key]?.label ?? key);

  return (
    <article className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03]">
      <div className="grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
        <figure className="self-start bg-black/40">
          {a ? (
            <div className="relative aspect-square">
              <img
                src={gibsUrl(f, a.lat, a.lon)}
                alt={t(`${f.place} uydu görüntüsü`, `Satellite image of ${f.place}`)}
                decoding="async"
                className="aspect-square w-full object-cover"
              />
              {/* Puanlanan kare: görüntü kenarı 2 × HALF_SPAN_LAT derece enlem */}
              <span
                className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 border-2 border-cyan-300/90 shadow-[0_0_0_9999px_rgba(0,0,0,0.15)]"
                style={{ width: `${((data?.meta.grid_km ?? 25) / 111 / (2 * HALF_SPAN_LAT)) * 100}%`, aspectRatio: "1" }}
                aria-hidden
              />
              <figcaption className="absolute bottom-0 left-0 right-0 bg-black/60 px-3 py-1.5 font-mono text-[10px] text-slate-300">
                {f.image.credit} · {en ? `frame: the scored ${data?.meta.grid_km} km cell` : `çerçeve: puanlanan ${data?.meta.grid_km} km'lik kare`}
              </figcaption>
            </div>
          ) : (
            <div className="flex aspect-square items-center justify-center p-6 text-center text-sm text-slate-500">
              {data ? t("Bu kare güncel tarama sonuçlarında yok: anlatı güncellenmeli.", "This cell is not in the current scan results: the story needs updating.") : t("Yükleniyor…", "Loading…")}
            </div>
          )}
        </figure>

        <div className="p-6">
          <p className="font-mono text-[11px] tracking-wider text-cyan-300/80">
            {String(n).padStart(2, "0")} · {f.body === "mars" ? "MARS" : t("AY", "MOON")} · {target?.name ?? f.targetId} · {test?.label ?? f.testId}
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-white">{f.place}</h3>
          <p className="text-sm text-slate-400">
            {f.region}
            {a && <span className="ml-2 font-mono text-xs text-slate-500">{coord(a.lat, a.lon)}</span>}
          </p>
          <p className="mt-3 font-medium text-slate-200">{f.title}</p>

          {a && (
            <div className="mt-4 flex flex-wrap items-end gap-x-6 gap-y-2">
              <div>
                <span className="font-mono text-3xl font-semibold text-white">{num(a.score_total, 1)}</span>
                <span className="ml-1 text-xs text-slate-500">/ 100</span>
              </div>
              <p className="text-xs text-slate-400">
                {en ? (
                  <>
                    Rank <b className="text-slate-200">#{a.rank}</b> in this test
                    {near >= 8 && <> · {near} of the top 20 candidates lie within 1,000 km of here: not one lucky cell but a regional signal</>}
                  </>
                ) : (
                  <>
                    Bu testte <b className="text-slate-200">{a.rank}.</b> sırada
                    {near >= 8 && <> · ilk 20 adayın {near}'i bu yerin 1.000 km çevresinde: tek bir şanslı kare değil, bölgesel bir sinyal</>}
                  </>
                )}
              </p>
            </div>
          )}

          {known && a && (
            <p className="mt-3 rounded-lg border border-cyan-400/20 bg-cyan-400/[0.05] px-3 py-2 text-xs text-slate-300">
              {en ? (
                <>
                  Comparison: in the same test NASA's known site <b className="text-white">{known.name}</b> scores {num(known.score_total, 1)}{" "}
                  (top {pct(known.percentile ?? 0, 1)} of Earth).{" "}
                  {a.score_total > (known.score_total ?? 0)
                    ? `This little-known island scores higher, at ${num(a.score_total, 1)}.`
                    : `This candidate scores ${num(a.score_total, 1)}.`}
                </>
              ) : (
                <>
                  Karşılaştırma: aynı testte NASA'nın bilinen sahası <b className="text-white">{known.name}</b> {num(known.score_total, 1)} puan
                  alıyor (Dünya'nın en iyi {pct(known.percentile ?? 0, 1)}'i).{" "}
                  {a.score_total > (known.score_total ?? 0)
                    ? `Bu az bilinen ada ${num(a.score_total, 1)} puanla daha yüksekte.`
                    : `Bu aday ${num(a.score_total, 1)} puan alıyor.`}
                </>
              )}
            </p>
          )}

          <p className="mt-4 text-sm leading-relaxed text-slate-300">{f.why}</p>

          {a && (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <ParamList title={t("Benzeyen", "Similar")} ok items={a.params.filter((p) => p.match)} label={label} />
              <ParamList title={t("Benzemeyen", "Not similar")} ok={false} items={a.params.filter((p) => !p.match)} label={label} />
            </div>
          )}

          <div className="mt-4 grid gap-3 text-sm">
            <p>
              <span className="font-mono text-[10px] tracking-wider text-emerald-300/80">{t("BURADA NE DENENİR · ", "WHAT CAN BE TESTED HERE · ")}</span>
              <span className="text-slate-300">{f.use}</span>
            </p>
            <p>
              <span className="font-mono text-[10px] tracking-wider text-rose-300/80">{t("ANALOJİ NEREDE KOPUYOR · ", "WHERE THE ANALOGY BREAKS · ")}</span>
              <span className="text-slate-300">{f.caveat}</span>
              {a && data && (
                <span className="text-slate-400">
                  {" "}
                  {t("Ayrıca:", "Also:")} {a.breakdown.map((k) => data.meta.breakdown_labels[k].toLocaleLowerCase(lang === "en" ? "en-US" : "tr-TR")).join(", ")}.
                </span>
              )}
            </p>
          </div>

          {a && (
            <div className="mt-5 flex flex-wrap items-center gap-3 text-xs">
              {Object.entries(a.ops_tags).map(([k, v]) => (
                <span key={k} className={`rounded-full px-2 py-0.5 ${v ? "bg-emerald-400/10 text-emerald-300" : "bg-white/5 text-slate-500"}`}>
                  {v ? "✓" : "✗"} {data?.meta.ops_labels[k] ?? k}
                </span>
              ))}
              <Link to={`/${f.body}/${f.targetId}/${f.testId}`} className="ml-auto font-mono text-cyan-300 hover:underline">
                {t("HARİTADA AÇ →", "OPEN ON MAP →")}
              </Link>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

function ParamList({
  title,
  ok,
  items,
  label,
}: {
  title: string;
  ok: boolean;
  items: Analog["params"];
  label: (key: string) => string;
}) {
  const { t, lang } = useLang();
  if (!items.length) return null;
  return (
    <div>
      <p className={`font-mono text-[10px] tracking-wider ${ok ? "text-emerald-300/80" : "text-rose-300/80"}`}>
        {title.toLocaleUpperCase(lang === "en" ? "en-US" : "tr-TR")} <span className="text-slate-500">· {t("DÜNYA / HEDEF", "EARTH / TARGET")}</span>
      </p>
      <ul className="mt-1 grid gap-1 text-xs">
        {items.map((p) => (
          <li key={p.key} className="flex justify-between gap-3 border-b border-white/5 pb-1">
            <span className="text-slate-400">{label(p.key)}</span>
            <span className="whitespace-nowrap font-mono text-slate-200">
              {num(p.earth, 2)} <span className="text-slate-500">/ {num(p.target, 2)}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
