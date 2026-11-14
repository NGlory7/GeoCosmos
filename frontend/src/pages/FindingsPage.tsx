import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import SpaceLayout from "../components/SpaceLayout";
import { coord, num, pct, shortLabel } from "../format";
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
  const [data, setData] = useState<Loaded | null>(null);
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
        <p className="font-mono text-[11px] tracking-[0.3em] text-cyan-300/70">BULGULAR</p>
        <h1 className="mt-2 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
          Ay'a ve Mars'a gitmeden önce Dünya'da nerede prova yapmalı?
        </h1>
        <p className="mt-4 max-w-3xl text-slate-300">
          Uydu verisiyle Dünya'nın bütün karalarını taradık ve her yeri, Ay'daki ve Mars'taki gerçek hedeflerle karşılaştırdık. Amacımız
          zaten bilinen ünlü sahaları yeniden bulmak değil, az bilinen yeni test sahaları bulmaktı. Burada bunlardan üçünü anlatıyoruz:
          neden benzediklerini ve, en az onun kadar önemli, nerede benzemediklerini.
        </p>
        {error && <p className="mt-4 text-sm text-rose-300">{error}</p>}

        {/* Neden ve nasıl */}
        <section className="mt-10 grid gap-4 md:grid-cols-3">
          <Info title="Neden Dünya'da prova?">
            Bir rover'ı Mars'ta tamir etmek mümkün değil. Bu yüzden ekipman, yöntem ve ekipler önce Dünya'da, Ay'a veya Mars'a benzeyen
            yerlerde (analog sahalarda) denenir. Ama hiçbir yer her açıdan benzemez: bir yer rover sürüşü için mükemmel, buz sondajı için
            işe yaramaz olabilir.
          </Info>
          <Info title="Nasıl aradık?">
            Dünya'yı {data ? `${data.meta.grid_km} km'lik` : "eşit"} karelere böldük. Her karede NASA ve ESA uydu verisinden eğimi,
            engebeyi, sıcaklığı, kuraklığı, havadaki tozu, kayaç türünü ve donmuş zemini ölçtük. Sonra her kareyi bir hedef ve bir test
            amacı için puanladık: her test, kendi önemli gördüğü özelliklere daha çok ağırlık veriyor.
          </Info>
          <Info title="Ne bulduk?">
            {newTotal !== undefined ? (
              <>
                {data?.targets.length} hedef ve {data?.meta.tests.length} test amacının anlamlı{" "}
                {data?.index?.filter((e) => e.file).length} eşleşmesi için toplam{" "}
                <b className="text-white">{newTotal.toLocaleString("tr-TR")}</b> yeni aday.{" "}
              </>
            ) : null}
            Bilinen ünlü sahalar (Atacama, Haughton, İzlanda, Hawaii…) listeye bilerek alınmadı; onlar motoru sınamak için kullanıldı.
          </Info>
        </section>

        {/* Yıldız adaylar */}
        <h2 className="mt-14 font-mono text-sm tracking-[0.25em] text-slate-400">ÜÇ YILDIZ ADAY</h2>
        <div className="mt-4 grid gap-8">
          {FINDINGS.map((f, i) => (
            <FindingCard key={f.cell} n={i + 1} f={f} data={data} />
          ))}
        </div>

        {/* Dünya'nın taklit edemedikleri */}
        {data && (
          <section className="mt-14">
            <h2 className="font-mono text-sm tracking-[0.25em] text-slate-400">DÜNYA'NIN TAKLİT EDEMEDİKLERİ</h2>
            <p className="mt-2 max-w-3xl text-slate-300">
              Hiçbir analog saha her şeyi sağlamaz. Aşağıdakiler, Dünya'nın hiçbir yerinde gerçek anlamda bulunamayan koşullar. Bunlar için
              vakum odaları, parabolik uçuşlar ve bilgisayar benzetimleri gerekir.
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead className="font-mono text-[10px] tracking-wider text-slate-500">
                  <tr>
                    <th className="py-2 pr-4" />
                    <th className="pr-4">AY</th>
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
          <h2 className="font-mono text-sm tracking-[0.25em] text-amber-200/80">BİLMENİZ GEREKENLER</h2>
          <ul className="mt-3 grid gap-3 text-sm text-slate-300">
            {data?.validation && (
              <li>
                <b className="text-white">Sınav sonucu: {data.validation.hits}/{data.validation.holdout_total}.</b> Motoru, NASA ve ESA'nın
                kullandığı dört ünlü saha üzerinde sınadık: her biri kendi testinde Dünya'nın en iyi {pct(data.validation.top_percent, 0)}'ine
                girmeliydi ve en az {data.validation.min_hits} tanesinin girmesi gerekiyordu.{" "}
                {closest(data.validation) && <>En yakın olanlar: {closest(data.validation)}. </>}
                Bu sonucu gizlemiyoruz;{" "}
                <Link to="/dogrulama" className="text-cyan-300 hover:underline">
                  ayrıntılar doğrulama sayfasında
                </Link>
                .
              </li>
            )}
            <li>
              <b className="text-white">{data ? `${data.meta.grid_km} km` : "Kare"} çözünürlük.</b> Bir kare küçük bir krateri, bir göl
              kıyısını ya da bir vadiyi ortalamada kaybedebilir. Yıldız adaylar, sahaya gidilmeden önce daha ince ölçekte incelenmeli.
            </li>
            <li>
              <b className="text-white">Mağaralar ve lav tüpleri yörüngeden görünmez.</b> Motor sadece tüp oluşabilecek araziyi ölçebiliyor.
            </li>
            <li>
              <b className="text-white">Ay ve Mars değerleri tek bir noktadan.</b> Her hedef için değerler NASA görev verisi (LOLA, Diviner,
              MOLA) ve yayımlanmış makalelerden; kaynakların hepsi aday kartlarında yazıyor.
            </li>
          </ul>
        </section>

        <p className="mt-10 text-xs text-slate-500">
          Veri: NASA (MODIS, GPM IMERG, ASTER GED, SEDAC, LRO LOLA ve Diviner, MGS MOLA, GIBS), ESA (Copernicus DEM, CCI Permafrost), Mars
          Climate Database (LMD/ESA/CNES). Yer adları: OpenStreetMap Nominatim. Ayrıntılı kaynak listesi: DATA_SOURCES.md.
        </p>
      </main>
    </SpaceLayout>
  );
}

/** Sınav sahalarından en iyi iki dilim: "Svalbard (%2,6), Lut (%5,5)". */
function closest(v: ValidationResult) {
  return v.analogs
    .filter((a) => a.split === "holdout" && a.status === "ok" && a.percentile !== undefined)
    .sort((a, b) => (a.percentile ?? 0) - (b.percentile ?? 0))
    .slice(0, 2)
    .map((a) => `${a.name} (en iyi ${pct(a.percentile ?? 0, 1)})`)
    .join(", ");
}

function Info({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <h2 className="font-medium text-white">{title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-slate-400">{children}</p>
    </div>
  );
}

function FindingCard({ n, f, data }: { n: number; f: Finding; data: Loaded | null }) {
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
                alt={`${f.place} uydu görüntüsü`}
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
                {f.image.credit} · çerçeve: puanlanan {data?.meta.grid_km} km'lik kare
              </figcaption>
            </div>
          ) : (
            <div className="flex aspect-square items-center justify-center p-6 text-center text-sm text-slate-500">
              {data ? "Bu kare güncel tarama sonuçlarında yok: anlatı güncellenmeli." : "Yükleniyor…"}
            </div>
          )}
        </figure>

        <div className="p-6">
          <p className="font-mono text-[11px] tracking-wider text-cyan-300/80">
            {String(n).padStart(2, "0")} · {f.body === "mars" ? "MARS" : "AY"} · {target?.name ?? f.targetId} · {test?.label ?? f.testId}
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
                Bu testte <b className="text-slate-200">{a.rank}.</b> sırada
                {near >= 8 && <> · ilk 20 adayın {near}'i bu yerin 1.000 km çevresinde: tek bir şanslı kare değil, bölgesel bir sinyal</>}
              </p>
            </div>
          )}

          {known && a && (
            <p className="mt-3 rounded-lg border border-cyan-400/20 bg-cyan-400/[0.05] px-3 py-2 text-xs text-slate-300">
              Karşılaştırma: aynı testte NASA'nın bilinen sahası <b className="text-white">{known.name}</b> {num(known.score_total, 1)} puan
              alıyor (Dünya'nın en iyi {pct(known.percentile ?? 0, 1)}'i).{" "}
              {a.score_total > (known.score_total ?? 0)
                ? `Bu az bilinen ada ${num(a.score_total, 1)} puanla daha yüksekte.`
                : `Bu aday ${num(a.score_total, 1)} puan alıyor.`}
            </p>
          )}

          <p className="mt-4 text-sm leading-relaxed text-slate-300">{f.why}</p>

          {a && (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <ParamList title="Benzeyen" ok items={a.params.filter((p) => p.match)} label={label} />
              <ParamList title="Benzemeyen" ok={false} items={a.params.filter((p) => !p.match)} label={label} />
            </div>
          )}

          <div className="mt-4 grid gap-3 text-sm">
            <p>
              <span className="font-mono text-[10px] tracking-wider text-emerald-300/80">BURADA NE DENENİR · </span>
              <span className="text-slate-300">{f.use}</span>
            </p>
            <p>
              <span className="font-mono text-[10px] tracking-wider text-rose-300/80">ANALOJİ NEREDE KOPUYOR · </span>
              <span className="text-slate-300">{f.caveat}</span>
              {a && data && (
                <span className="text-slate-400">
                  {" "}
                  Ayrıca: {a.breakdown.map((k) => data.meta.breakdown_labels[k].toLocaleLowerCase("tr-TR")).join(", ")}.
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
                HARİTADA AÇ →
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
  if (!items.length) return null;
  return (
    <div>
      <p className={`font-mono text-[10px] tracking-wider ${ok ? "text-emerald-300/80" : "text-rose-300/80"}`}>
        {title.toLocaleUpperCase("tr-TR")} <span className="text-slate-500">· DÜNYA / HEDEF</span>
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
