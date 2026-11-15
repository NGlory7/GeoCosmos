import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { coord, num, shortLabel } from "../format";
import { LangSwitch, useLang } from "../i18n";
import { analogName, localizeLogistics, localizeMeta, sourceEn, targetNameEn } from "../i18nData";
import { roadmap, risks } from "../roadmap";
import { loadAnalogIndex, loadAnalogs, loadLogistics, loadMeta, loadTargets, type TargetWithCoords } from "../services/data";
import type { Analog, Body, Logistics, Meta, TestId } from "../types";

// Aday saha raporu: tarayıcının "PDF olarak kaydet"i ile çıktı alınır (açık tema, A4).
// Kendi senaryon sonuçları kaydedilmediği için aday, sayfaya geçerken router state ile gelir.
export default function ReportPage() {
  const { body, targetId, testId, analogId } = useParams();
  const state = useLocation().state as { analog?: Analog; query?: string } | null;
  const { t, lang, en } = useLang();
  const [rawMeta, setMeta] = useState<Meta | null>(null);
  const [rawTarget, setTarget] = useState<TargetWithCoords | null>(null);
  const [rawAnalog, setAnalog] = useState<Analog | null>(state?.analog ?? null);
  const [rawLogistics, setLogistics] = useState<Logistics | null>(null);
  const meta = localizeMeta(rawMeta, lang);
  const target = rawTarget && { ...rawTarget, name: targetNameEn(rawTarget.id, rawTarget.name, lang) };
  const analog = rawAnalog && { ...rawAnalog, name: analogName(rawAnalog, lang) };
  const logistics = localizeLogistics(rawLogistics, lang) ?? null;
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([loadMeta(), loadTargets(), loadAnalogIndex(), loadLogistics()])
      .then(async ([m, ts, idx, lg]) => {
        const e = idx?.find((x) => x.target_id === targetId && x.test_id === testId);
        const found = state?.analog ?? (e?.file ? (await loadAnalogs(e.file)).find((a) => a.id === analogId) : undefined) ?? null;
        setMeta(m);
        setTarget(ts.find((t) => t.id === targetId) ?? null);
        setAnalog(found);
        setLogistics(found ? lg?.cells[found.id] ?? null : null);
        if (!found) setError("not-found");
      })
      .catch((e) => setError(String(e)));
  }, [targetId, testId, analogId, state]);

  const test = meta?.tests.find((t) => t.id === testId);
  const b = body as Body;
  const back = `/${body}/${targetId}/${testId}${testId === "custom" && state?.query ? `?q=${encodeURIComponent(state.query)}` : ""}`;

  if (error)
    return (
      <p className="p-8 text-sm text-rose-700">
        {error === "not-found"
          ? t("Aday bulunamadı (kendi senaryon raporu, sonuç sayfasından açılmalı).", "Candidate not found (a custom scenario report must be opened from the results page).")
          : error}
      </p>
    );
  if (!meta || !target || !analog) return <p className="p-8 font-mono text-xs text-slate-500">{t("Yükleniyor…", "Loading…")}</p>;

  const testLabel = testId === "custom" ? `${t("Kendi senaryon", "Your own scenario")}${state?.query ? `: “${state.query}”` : ""}` : test?.label ?? testId;
  const phases = roadmap(analog, meta, b, logistics, testId as TestId | "custom");
  const riskList = risks(analog, meta, b, logistics);
  const today = new Date().toLocaleDateString(en ? "en-GB" : "tr-TR", { day: "numeric", month: "long", year: "numeric" });

  return (
    <div className="min-h-dvh bg-slate-100 py-6 text-slate-900 print:bg-white print:py-0">
      <div className="mx-auto mb-4 flex max-w-[52rem] items-center justify-between px-4 print:hidden">
        <Link to={back} className="font-mono text-xs tracking-wider text-slate-500 hover:text-slate-800">
          ‹ {t("SONUÇLARA DÖN", "BACK TO RESULTS")}
        </Link>
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-slate-800 p-0.5">
            <LangSwitch />
          </div>
          <button onClick={() => window.print()} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
            {t("Yazdır / PDF olarak kaydet", "Print / save as PDF")}
          </button>
        </div>
      </div>

      <article className="report mx-auto max-w-[52rem] space-y-7 bg-white px-8 py-10 shadow-sm print:max-w-none print:px-0 print:py-0 print:shadow-none sm:px-12">
        <header className="border-b border-slate-200 pb-5">
          <p className="font-mono text-[11px] tracking-[0.25em] text-slate-500">{t("GEOCOSMOS · ANALOG SAHA RAPORU", "GEOCOSMOS · ANALOG SITE REPORT")}</p>
          <h1 className="mt-2 text-2xl font-semibold">{analog.name}</h1>
          <p className="mt-1 text-sm text-slate-600">
            {analog.is_new && !analog.place ? "" : `${coord(analog.lat, analog.lon)} · `}
            {en ? `${meta.grid_km} km cell` : `${meta.grid_km} km'lik kare`} · {analog.is_new ? t("yeni aday", "new candidate") : t("bilinen analog saha", "known analog site")}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {t("Hedef", "Target")}: <b>{target.name}</b> ({b === "mars" ? "Mars" : t("Ay", "Moon")}) · Test: <b>{testLabel}</b>
          </p>
          <p className="mt-1 text-xs text-slate-400">{today}</p>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 print:grid-cols-2">
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="font-mono text-[10px] tracking-[0.2em] text-slate-500">{t("HEDEFE BENZERLİK", "SIMILARITY TO TARGET")}</p>
            <p className="mt-1 text-3xl font-semibold">
              {num(analog.score_total, 1)} <span className="text-base font-normal text-slate-400">/ 100</span>
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {meta.score_keys.map((k) => `${meta.score_labels[k]} ${num(analog.scores[k], 0)}`).join(" · ")} · {en ? `candidate #${analog.rank}` : `#${analog.rank}. aday`}
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="font-mono text-[10px] tracking-[0.2em] text-slate-500">{t("KURULUM KOLAYLIĞI", "EASE OF SETUP")}</p>
            {logistics?.score != null ? (
              <>
                <p className="mt-1 text-3xl font-semibold">
                  {num(logistics.score, 0)} <span className="text-base font-normal text-slate-400">/ 100 · {logistics.level}</span>
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {Object.values(logistics.parts).map((p) => `${p.label} ${num(p.score, 0)}`).join(" · ")}
                </p>
              </>
            ) : (
              <p className="mt-2 text-sm text-slate-500">{t("Bu kare için altyapı verisi yok.", "No infrastructure data for this cell.")}</p>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">{t("1. Parametreler · Dünya ↔ hedef", "1. Parameters · Earth ↔ target")}</h2>
          <table className="mt-2 w-full text-left text-xs">
            <thead className="text-slate-500">
              <tr>
                <th className="py-1 font-normal">{t("Parametre", "Parameter")}</th>
                <th className="py-1 text-right font-normal">{t("Burası", "This site")}</th>
                <th className="py-1 text-right font-normal">{target.name}</th>
                <th className="py-1 text-center font-normal">{t("Benzer", "Similar")}</th>
              </tr>
            </thead>
            <tbody>
              {analog.params.map((p) => (
                <tr key={p.key} className="border-t border-slate-100">
                  <td className="py-1.5 pr-2">
                    {shortLabel(meta.parameters[p.key]?.label ?? p.key)}
                    <div className="text-[10px] text-slate-400">{sourceEn(p.source, lang)}</div>
                  </td>
                  <td className="py-1.5 pr-2 text-right font-mono">{num(p.earth)}</td>
                  <td className="py-1.5 pr-2 text-right font-mono text-slate-500">{num(p.target)}</td>
                  <td className={`py-1.5 text-center ${p.match ? "text-emerald-600" : "text-rose-600"}`}>{p.match ? "✓" : "✗"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">{t("2. Altyapı ve lojistik", "2. Infrastructure and logistics")}</h2>
          {logistics?.score != null ? (
            <>
              <ul className="mt-2 grid gap-1 text-xs sm:grid-cols-2 print:grid-cols-2">
                {Object.values(logistics.parts).map((p) => (
                  <li key={p.label}>
                    <b>{p.label}</b> ({num(p.score, 0)}): {p.text}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs leading-relaxed text-slate-700">{logistics.comment}</p>
            </>
          ) : (
            <p className="mt-2 text-xs text-slate-500">{t("Veri yok; keşif gezisinde çıkarılmalı.", "No data; to be established on the scouting trip.")}</p>
          )}
        </section>

        <section className="break-inside-avoid">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">{t("3. Riskler", "3. Risks")}</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-700">
            {riskList.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>

        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">{t("4. Yol haritası", "4. Roadmap")}</h2>
          <ol className="mt-3 space-y-4">
            {phases.map((ph, i) => (
              <li key={ph.title} className="break-inside-avoid border-l-2 border-slate-300 pl-4">
                <p className="text-sm font-semibold">
                  {t("Aşama", "Phase")} {i + 1} · {ph.title}
                </p>
                <p className="text-xs text-slate-500">{ph.goal}</p>
                <ul className="mt-1.5 list-disc space-y-1 pl-5 text-xs text-slate-700">
                  {ph.steps.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </section>

        {analog.ai_comment && (
          <section className="break-inside-avoid">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
              {t("5. Yorum (Gemini, sadece motorun sayılarıyla)", `5. Commentary (Gemini, engine numbers only${analog.ai_comment_en ? "" : ", in Turkish"})`)}
            </h2>
            <p className="mt-2 whitespace-pre-line text-xs leading-relaxed text-slate-700">{t(analog.ai_comment, analog.ai_comment_en || analog.ai_comment)}</p>
          </section>
        )}

        {analog.past_tests.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">{t("Burada yapılmış çalışmalar", "Previous work at this site")}</h2>
            <ul className="mt-2 space-y-1 text-xs">
              {analog.past_tests.map((t) => (
                <li key={t.url}>
                  {t.title} — <span className="break-all text-slate-500">{t.url}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <footer className="border-t border-slate-200 pt-3 text-[10px] leading-snug text-slate-400">
          {t(
            "Benzerlik: GeoCosmos motoru (uydu verisinden 25 km'lik karelerde ölçülen parametreler). Altyapı: MAP erişim süresi 2015, WRI Küresel Santral Veritabanı, JRC Küresel Yüzey Suyu, GPW nüfus 2020, Copernicus DEM. Yol haritası ve riskler bu değerlerden kurallarla üretilir; sahaya gitmeden önce yerel kaynaklarla doğrulanmalıdır.",
            "Similarity: GeoCosmos engine (parameters measured from satellite data in 25 km cells). Infrastructure: MAP travel time 2015, WRI Global Power Plant Database, JRC Global Surface Water, GPW population 2020, Copernicus DEM. The roadmap and risks are generated from these values by rules; verify them with local sources before going into the field.",
          )}
        </footer>
      </article>
    </div>
  );
}
