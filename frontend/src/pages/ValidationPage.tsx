import { useEffect, useState } from "react";
import SpaceLayout from "../components/SpaceLayout";
import { int, num, pct } from "../format";
import { useLang } from "../i18n";
import { localizeMeta, localizeTargets, localizeValidation } from "../i18nData";
import { loadMeta, loadTargets, loadValidation, type TargetWithCoords } from "../services/data";
import type { Meta, ValidationAnalog, ValidationResult } from "../types";

const SPLIT_CLS: Record<ValidationAnalog["split"], string> = {
  tune: "bg-slate-400/15 text-slate-300",
  holdout: "bg-cyan-400/15 text-cyan-300",
  report: "bg-white/5 text-slate-400",
};
const DOT_CLS: Record<ValidationAnalog["split"], string> = {
  tune: "bg-slate-300",
  holdout: "bg-cyan-300",
  report: "bg-slate-500",
};

// Yüzdelik ekseni logaritmik: %2 ile %5 arasındaki fark, %50 ile %100 arasındaki kadar okunur.
const AXIS_MIN = 0.5;
const AXIS_MAX = 100;
const TICKS = [1, 2, 5, 10, 20, 50, 100];
const TICKS_NARROW = new Set([1, 5, 20, 100]); // dar ekranda üst üste binmesin
const CHANCE = 50; // rastgele seçilen bir karenin beklenen yüzdeliği
const xPos = (p: number) => {
  const v = Math.min(AXIS_MAX, Math.max(AXIS_MIN, p));
  return ((Math.log(v) - Math.log(AXIS_MIN)) / (Math.log(AXIS_MAX) - Math.log(AXIS_MIN))) * 100;
};

function PercentileChart({ res }: { res: ValidationResult }) {
  const { t, en } = useLang();
  const order: ValidationAnalog["split"][] = ["holdout", "tune", "report"];
  const rows = res.analogs
    .filter((a) => a.status === "ok" && a.percentile !== undefined)
    .sort((a, b) => order.indexOf(a.split) - order.indexOf(b.split) || (a.percentile ?? 0) - (b.percentile ?? 0));
  const holdout = rows.filter((a) => a.split === "holdout");
  const leftOfChance = holdout.filter((a) => (a.percentile ?? 100) < CHANCE).length;
  const groupLabel = (s: ValidationAnalog["split"]) =>
    s === "holdout" ? t("SINAV", "TEST") : s === "tune" ? t("AYAR", "TUNING") : t("RAPOR", "REPORT");

  return (
    <section className="mt-6 rounded-xl border border-white/10 bg-white/[0.02] p-4 sm:p-5">
      <h2 className="font-mono text-[11px] tracking-[0.2em] text-slate-400">
        {t("HER SAHANIN SIRASI · ŞANSA GÖRE", "EACH SITE'S RANK · COMPARED WITH CHANCE")}
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        {t(
          "Nokta, sahanın kendi testinde Dünya karelerinin yüzde kaçlık diliminde olduğunu gösterir; sola doğru daha iyi. Eksen logaritmik.",
          "Each dot shows which percentile of Earth's cells the site falls in for its own test; further left is better. Logarithmic axis.",
        )}
      </p>

      <div className="mt-4 grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)] gap-x-3 sm:grid-cols-[minmax(0,13rem)_minmax(0,1fr)_4.5rem]">
        {rows.map((a, i) => {
          const p = a.percentile ?? 0;
          const first = i === 0 || rows[i - 1].split !== a.split;
          return (
            <div key={a.id} className="contents">
              {first && (
                <p className="col-span-full mt-2 font-mono text-[10px] tracking-wider text-slate-500 first:mt-0">{groupLabel(a.split)}</p>
              )}
              <p className="truncate py-1.5 text-xs text-slate-300" title={a.name}>
                {a.name}
              </p>
              <div className="relative py-1.5">
                <div className="absolute inset-x-0 top-1/2 h-px bg-white/10" />
                {/* ölçüt bölgesi: en iyi top_percent */}
                <div className="absolute inset-y-0 left-0 bg-emerald-400/10" style={{ width: `${xPos(res.top_percent)}%` }} />
                <div className="absolute inset-y-0 w-px bg-amber-300/60" style={{ left: `${xPos(CHANCE)}%` }} />
                <span
                  className={`absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-black/60 ${
                    a.split === "holdout" && a.hit ? "bg-emerald-300" : DOT_CLS[a.split]
                  }`}
                  style={{ left: `${xPos(p)}%` }}
                  title={`${a.name}: ${pct(p)}`}
                />
                <span className="invisible text-xs">.</span>
              </div>
              <p className="hidden py-1.5 text-right font-mono text-[11px] text-slate-400 sm:block">{pct(p, 1)}</p>
            </div>
          );
        })}

        {/* eksen */}
        <span />
        <div className="relative mt-1 h-8">
          {TICKS.map((tk) => (
            <span
              key={tk}
              className={`absolute top-0 -translate-x-1/2 font-mono text-[10px] text-slate-500 ${TICKS_NARROW.has(tk) ? "" : "hidden sm:inline"}`}
              style={{ left: `${xPos(tk)}%` }}
            >
              {pct(tk, 0)}
            </span>
          ))}
          <span className="absolute top-4 -translate-x-1/2 whitespace-nowrap font-mono text-[10px] text-amber-300/80" style={{ left: `${xPos(CHANCE)}%` }}>
            {t("şans", "chance")}
          </span>
          <span className="absolute left-0 top-4 whitespace-nowrap font-mono text-[10px] text-emerald-300/80">
            {t(`ölçüt: en iyi ${pct(res.top_percent, 1)}`, `criterion: top ${pct(res.top_percent, 1)}`)}
          </span>
        </div>
        <span className="hidden sm:block" />
      </div>

      <p className="mt-4 text-xs leading-relaxed text-slate-400">
        {en ? (
          <>
            A randomly chosen cell lands on average at the {pct(CHANCE, 0)} mark (the yellow line). {leftOfChance} of {holdout.length} test
            sites sit to its left: the engine ranks these known analogs better than chance. But only a dot inside the green band counts as a hit.{" "}
            <b className="text-slate-200">
              The criterion was originally the top 1% (result: 0/4); it was relaxed to the current value after that result was seen
            </b>
            .
          </>
        ) : (
          <>
            Rastgele seçilen bir kare ortalamada {pct(CHANCE, 0)}'lik dilime düşer (sarı çizgi). {holdout.length} sınav sahasının{" "}
            {leftOfChance} tanesi bunun solunda: motor bu bilinen analogları şanstan iyi sıralıyor. Ama isabet sayılan sadece yeşil bölgedeki noktalar.{" "}
            <b className="text-slate-200">
              Ölçüt başta en iyi %1'di (sonuç: 0/4); bu sonuç görüldükten sonra bugünkü değere gevşetildi
            </b>
            .
          </>
        )}
      </p>
    </section>
  );
}

export default function ValidationPage() {
  const { t, lang, en } = useLang();
  const [raw, setRes] = useState<ValidationResult | null | undefined>(undefined);
  const [rawMeta, setMeta] = useState<Meta | null>(null);
  const [rawTargets, setTargets] = useState<TargetWithCoords[]>([]);

  useEffect(() => {
    Promise.all([loadValidation(), loadMeta(), loadTargets()]).then(([v, m, tg]) => {
      setRes(v);
      setMeta(m);
      setTargets(tg);
    });
  }, []);

  const meta = localizeMeta(rawMeta, lang);
  const targets = localizeTargets(rawTargets, lang);
  const res = raw ? { ...raw, analogs: raw.analogs.map((a) => localizeValidation(a, lang)) } : raw;
  const testLabel = (id: string) => meta?.tests.find((x) => x.id === id)?.label ?? id;
  const targetName = (id?: string) => targets.find((x) => x.id === id)?.name ?? id ?? "—";

  const SPLIT: Record<ValidationAnalog["split"], { label: string; help: string }> = {
    tune: { label: t("AYAR", "TUNING"), help: t("Ağırlıklar sadece bu yerlere bakılarak ayarlanır.", "Weights are tuned by looking at these sites only.") },
    holdout: {
      label: t("SINAV", "TEST"),
      help: t("Başarı ölçütü sadece bunlarla hesaplanır; bunlara bakarak ayar yapılmaz.", "The success criterion uses these sites only; nothing is tuned by looking at them."),
    },
    report: {
      label: t("RAPOR", "REPORT"),
      help: t("Sırası gösterilir, ölçüte girmez: yöntem bu özelliği ölçemiyor.", "Rank is shown but not counted: the method cannot measure this property."),
    },
  };
  const STATUS: Record<ValidationAnalog["status"], string> = {
    ok: "",
    missing_cell: t("Izgarada karesi yok", "No cell in the grid"),
    no_target_values: t("Hedefte bu testin değeri yok", "Target has no values for this test"),
  };

  return (
    <SpaceLayout>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <h1 className="font-mono text-2xl font-semibold tracking-wider text-white">{t("DOĞRULAMA", "VALIDATION")}</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          {t(
            "NASA ve ESA'nın kullandığı ünlü analog sahalar, motorumuzda kendi test amaçları için Dünya karelerinin yüzde kaçlık diliminde? Ünlü sahalar keşif listesine girmez; motorun doğruluğunu ölçmek için kullanılır.",
            "Where do the famous analog sites used by NASA and ESA rank among all of Earth's cells, for their own test purpose? Famous sites are kept out of the discovery list; they are used to measure the engine.",
          )}
        </p>

        {res === null && (
          <p className="mt-6 rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-sm text-amber-200/80">
            {t(
              "Doğrulama henüz çalıştırılmadı: Dünya taraması (grid.parquet) bekleniyor. Bkz. STATUS.md.",
              "Validation has not been run yet: waiting for the Earth scan (grid.parquet). See STATUS.md.",
            )}
          </p>
        )}

        {res && (
          <>
            <section className={`mt-6 rounded-xl border p-5 ${res.passed ? "border-emerald-400/30 bg-emerald-400/5" : "border-rose-400/30 bg-rose-400/5"}`}>
              <p className="font-mono text-4xl font-semibold text-white">
                {res.hits}/{res.holdout_total}
              </p>
              <p className="mt-1 text-sm text-slate-300">
                {en
                  ? `test sites in the top ${pct(res.top_percent, 1)} of Earth for their own test (needed: ${res.min_hits})`
                  : `sınav sahası kendi test amacında Dünya'nın en iyi ${pct(res.top_percent, 1)}'inde (gereken: ${res.min_hits})`}{" "}
                · <span className={res.passed ? "text-emerald-300" : "text-rose-300"}>{res.passed ? t("GEÇTİ", "PASSED") : t("GEÇMEDİ", "NOT PASSED")}</span>
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {t(`Payda: ${int(res.denominator)} kare (maskeli olmayanlar + doğrulama kareleri)`, `Denominator: ${int(res.denominator)} cells (unmasked cells + validation cells)`)}
              </p>
            </section>

            <PercentileChart res={res} />

            <table className="mt-6 w-full text-left text-sm">
              <thead className="font-mono text-[10px] tracking-wider text-slate-500">
                <tr>
                  <th className="py-2">{t("GRUP", "GROUP")}</th>
                  <th>{t("SAHA", "SITE")}</th>
                  <th>{t("TEST · HEDEF", "TEST · TARGET")}</th>
                  <th className="text-right">{t("DİLİM", "PERCENTILE")}</th>
                  <th className="text-right">{t("SIRA", "RANK")}</th>
                </tr>
              </thead>
              <tbody>
                {res.analogs.map((a) => (
                  <tr key={a.id} className="border-t border-white/5 align-top">
                    <td className="py-2.5 pr-2">
                      <span className={`rounded-full px-2 py-0.5 font-mono text-[10px] ${SPLIT_CLS[a.split]}`} title={SPLIT[a.split].help}>
                        {SPLIT[a.split].label}
                      </span>
                    </td>
                    <td className="py-2.5 pr-2 text-slate-200">
                      {a.name}
                      {a.note && <div className="mt-0.5 text-xs text-slate-500">{a.note}</div>}
                      {a.past_tests.slice(0, 2).map((pt) => (
                        <a key={pt.url} href={pt.url} target="_blank" rel="noreferrer" className="mt-0.5 block text-xs text-cyan-300/80 hover:underline">
                          {pt.title}
                        </a>
                      ))}
                    </td>
                    <td className="py-2.5 pr-2 text-xs text-slate-400">
                      {testLabel(a.test_id)}
                      <div className="text-slate-500">{targetName(a.target_id ?? a.targets[0])}</div>
                    </td>
                    <td className="py-2.5 pr-2 text-right font-mono">
                      {a.status === "ok" ? (
                        <span className={a.split === "holdout" ? (a.hit ? "text-emerald-300" : "text-rose-300") : "text-slate-300"}>
                          {pct(a.percentile ?? 0)}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-500">{STATUS[a.status]}</span>
                      )}
                    </td>
                    <td className="py-2.5 text-right font-mono text-xs text-slate-400">
                      {a.rank ? `${int(a.rank)} · ${num(a.score_total, 1)}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </main>
    </SpaceLayout>
  );
}
