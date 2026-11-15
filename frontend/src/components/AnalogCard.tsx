import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer } from "recharts";
import { num, shortLabel } from "../format";
import { useLang } from "../i18n";
import { sourceEn } from "../i18nData";
import type { Analog, Body, Logistics, Meta } from "../types";

function ScoreRadar({ analog, meta }: { analog: Analog; meta: Meta }) {
  const data = meta.score_keys.map((k) => ({
    label: `${meta.score_labels[k]}${analog.scores[k] === null ? " (—)" : ""}`,
    value: analog.scores[k] ?? 0,
  }));
  return (
    <div className="h-44 w-full">
      <ResponsiveContainer>
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="rgb(255 255 255 / 0.15)" />
          <PolarAngleAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar dataKey="value" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.35} isAnimationActive={false} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Kare merkezini Google Maps'te açar. Doğrudan panorama bağlantısı (map_action=pano) sadece noktanın
 *  birkaç metre yakınına bakıyor ve kare merkezi nadiren yolda olduğu için siyah ekran veriyordu.
 *  Bunun yerine uydu görüntüsü + Sokak Görünümü kapsama katmanı (!5m1!1e5) açılır: mavi çizgiler
 *  araç çekimi olan yollar, noktalar fotoğraf küreleri; tıklanınca panorama açılır. */
function GroundLinks({ lat, lon, km }: { lat: number; lon: number; km: number }) {
  const { t, en } = useLang();
  const ll = `${lat.toFixed(5)},${lon.toFixed(5)}`;
  const links = [
    { label: t("Sokak Görünümü haritası", "Street View coverage"), href: `https://www.google.com/maps/@${ll},11z/data=!3m1!1e3!5m1!1e5` },
    { label: t("Uydu görüntüsü", "Satellite image"), href: `https://www.google.com/maps/@?api=1&map_action=map&center=${ll}&zoom=11&basemap=satellite` },
    { label: t("Yer fotoğrafları", "Place photos"), href: `https://www.google.com/maps/search/?api=1&query=${ll}` },
  ];
  return (
    <div className="mt-3">
      <div className="flex flex-wrap gap-1.5">
        {links.map((l) => (
          <a
            key={l.label}
            href={l.href}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-slate-300 hover:border-cyan-400/40 hover:text-cyan-200"
          >
            {l.label} ↗
          </a>
        ))}
      </div>
      <p className="mt-1 text-[10px] text-slate-600">
        {en
          ? `Google Maps · centre of the ${km} km cell. On the Street View map, click a blue line or dot to open a panorama; remote areas (Arctic, high mountains) may have no coverage.`
          : `Google Maps · ${km} km'lik karenin merkezi. Sokak Görünümü haritasında mavi çizgiye ya da noktaya tıkla, panorama açılır; uzak bölgelerde (Arktik, yüksek dağ) çekim olmayabilir.`}
      </p>
    </div>
  );
}

const LEVEL_STYLE: Record<string, string> = {
  Kolay: "bg-emerald-400/15 text-emerald-300",
  Orta: "bg-amber-400/15 text-amber-300",
  Zor: "bg-rose-400/15 text-rose-300",
  Easy: "bg-emerald-400/15 text-emerald-300",
  Moderate: "bg-amber-400/15 text-amber-300",
  Hard: "bg-rose-400/15 text-rose-300",
};

function barColor(s: number) {
  return s >= 70 ? "bg-emerald-400/70" : s >= 40 ? "bg-amber-400/70" : "bg-rose-400/70";
}

/** Kurulum kolaylığı (logistics.json): benzerlikten ayrı; kalemler ve kural tabanlı yorum. */
export function LogisticsSection({ logistics }: { logistics: Logistics | null | undefined }) {
  const { t } = useLang();
  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="font-mono text-[11px] tracking-[0.2em] text-slate-500">{t("KURULUM KOLAYLIĞI", "EASE OF SETUP")}</h3>
        {logistics?.score != null && (
          <span className="flex shrink-0 items-baseline gap-2 whitespace-nowrap">
            <span className={`rounded-full px-2 py-0.5 font-mono text-[10px] tracking-wider ${LEVEL_STYLE[logistics.level ?? ""] ?? ""}`}>
              {logistics.level?.toUpperCase()}
            </span>
            <span className="font-mono text-lg font-semibold text-white">{num(logistics.score, 0)}</span>
            <span className="text-xs text-slate-500">/ 100</span>
          </span>
        )}
      </div>
      {!logistics || logistics.score == null ? (
        <p className="mt-2 text-xs text-slate-500">{t("Bu kare için altyapı verisi çekilmedi (sadece hazır testlerin adaylarında var).", "No infrastructure data was fetched for this cell (only available for candidates of the predefined tests).")}</p>
      ) : (
        <>
          <ul className="mt-3 space-y-2">
            {Object.entries(logistics.parts).map(([k, p]) => (
              <li key={k} className="text-xs">
                <div className="flex justify-between gap-2">
                  <span className="text-slate-300">{p.label}</span>
                  <span className="font-mono text-slate-400">{num(p.score, 0)}</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-white/5">
                  <div className={`h-1.5 rounded-full ${barColor(p.score)}`} style={{ width: `${Math.max(2, p.score)}%` }} />
                </div>
                <div className="mt-0.5 text-[11px] text-slate-500">{p.text}</div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs leading-relaxed text-slate-300">{logistics.comment}</p>
          <p className="mt-2 text-[10px] leading-snug text-slate-600">
            {t(
              "Benzerlik puanına katılmaz: ıssızlık bazı testlerde istenen bir özelliktir. Kaynak: MAP erişim süresi 2015, WRI Küresel Santral Veritabanı, JRC Küresel Yüzey Suyu, GPW nüfus 2020, Copernicus DEM. Kurallar: config/grid.yaml > logistics.",
              "Not part of the similarity score: remoteness is a desired property for some tests. Sources: MAP travel time 2015, WRI Global Power Plant Database, JRC Global Surface Water, GPW population 2020, Copernicus DEM. Rules: config/grid.yaml > logistics.",
            )}
          </p>
        </>
      )}
    </section>
  );
}

interface Props {
  analog: Analog;
  meta: Meta;
  body: Body;
  targetName: string;
  logistics?: Logistics | null;
}

export default function AnalogCard({ analog, meta, body, targetName, logistics }: Props) {
  const test = meta.tests.find((t) => t.id === analog.test_id);
  const used = analog.params.length;
  const total = test ? Object.keys(test.weights).length : used;
  const notes = meta.breakdown_notes[body];
  const { t, lang } = useLang();

  return (
    <article className="space-y-5">
      <header>
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-slate-500">#{analog.rank}</span>
          {analog.is_new ? (
            <span className="rounded-full bg-cyan-400/15 px-2 py-0.5 font-mono text-[10px] tracking-wider text-cyan-300">{t("YENİ ADAY", "NEW CANDIDATE")}</span>
          ) : (
            <span className="rounded-full bg-amber-400/15 px-2 py-0.5 font-mono text-[10px] tracking-wider text-amber-300">{t("BİLİNEN SAHA", "KNOWN SITE")}</span>
          )}
        </div>
        <h2 className="mt-1 text-lg font-semibold text-white">{analog.name}</h2>
        <p className="mt-1 text-sm text-slate-400">
          {t(`${targetName} için benzerlik:`, `Similarity to ${targetName}:`)} <span className="font-mono text-2xl font-semibold text-cyan-300">{num(analog.score_total, 1)}</span>
          <span className="text-slate-500"> / 100</span>
        </p>
        <GroundLinks lat={analog.lat} lon={analog.lon} km={meta.grid_km} />
        {used < total && (
          <p className="mt-2 rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-xs text-amber-200/80">
            {t(
              `Bu skor ${total} parametreden ${used} tanesiyle hesaplandı; hedefte değeri olmayanlar hesaba katılmadı.`,
              `This score uses ${used} of ${total} parameters; those without a target value were left out.`,
            )}
          </p>
        )}
      </header>

      <ScoreRadar analog={analog} meta={meta} />

      <section>
        <h3 className="font-mono text-[11px] tracking-[0.2em] text-slate-500">{t("PARAMETRELER · DÜNYA ↔ HEDEF", "PARAMETERS · EARTH ↔ TARGET")}</h3>
        <table className="mt-2 w-full text-left text-xs">
          <tbody>
            {analog.params.map((p) => (
              <tr key={p.key} className="border-t border-white/5 align-top">
                <td className="py-1.5 pr-2 text-slate-300">
                  {shortLabel(meta.parameters[p.key]?.label ?? p.key)}
                  <div className="text-[10px] text-slate-500">{sourceEn(p.source, lang)}</div>
                </td>
                <td className="py-1.5 pr-2 text-right font-mono text-slate-200">{num(p.earth)}</td>
                <td className="py-1.5 pr-2 text-right font-mono text-slate-400">{num(p.target)}</td>
                <td className={`py-1.5 text-center ${p.match ? "text-emerald-400" : "text-rose-400"}`} title={p.match ? t("benziyor", "similar") : t("benzemiyor", "not similar")}>
                  {p.match ? "✓" : "✗"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="rounded-xl border border-rose-400/20 bg-rose-400/5 p-3">
        <h3 className="font-mono text-[11px] tracking-[0.2em] text-rose-300/80">{t("BENZERLİĞİN KOPTUĞU YER", "WHERE THE ANALOGY BREAKS")}</h3>
        <ul className="mt-2 space-y-1.5 text-xs text-slate-300">
          {analog.breakdown.map((k) => (
            <li key={k}>
              <span className="font-medium text-rose-200">{meta.breakdown_labels[k]}:</span> {notes[k]}
            </li>
          ))}
        </ul>
      </section>

      <LogisticsSection logistics={logistics} />

      {Object.keys(analog.ops_tags).length > 0 && (
        <section className="flex flex-wrap gap-2">
          {Object.entries(analog.ops_tags).map(([k, v]) => (
            <span key={k} className={`rounded-full px-2.5 py-1 text-[11px] ${v ? "bg-emerald-400/10 text-emerald-300" : "bg-white/5 text-slate-500"}`}>
              {v ? "✓" : "✗"} {meta.ops_labels[k] ?? k}
            </span>
          ))}
        </section>
      )}

      {analog.past_tests.length > 0 && (
        <section>
          <h3 className="font-mono text-[11px] tracking-[0.2em] text-slate-500">{t("BURADA YAPILMIŞ TESTLER", "TESTS DONE HERE")}</h3>
          <ul className="mt-2 space-y-1 text-xs">
            {analog.past_tests.map((t) => (
              <li key={t.url}>
                <a href={t.url} target="_blank" rel="noreferrer" className="text-cyan-300 hover:underline">
                  {t.title}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {analog.ai_comment && (
        <section>
          <h3 className="font-mono text-[11px] tracking-[0.2em] text-slate-500">{t("YORUM (GEMINI · SADECE MOTORUN SAYILARIYLA)", "COMMENTARY (GEMINI · ENGINE NUMBERS ONLY · IN TURKISH)")}</h3>
          <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-300">{analog.ai_comment}</p>
        </section>
      )}
    </article>
  );
}
