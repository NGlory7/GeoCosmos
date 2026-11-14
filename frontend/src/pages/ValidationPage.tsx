import { useEffect, useState } from "react";
import SpaceLayout from "../components/SpaceLayout";
import { num, pct } from "../format";
import { loadMeta, loadTargets, loadValidation, type TargetWithCoords } from "../services/data";
import type { Meta, ValidationAnalog, ValidationResult } from "../types";

const SPLIT: Record<ValidationAnalog["split"], { label: string; cls: string; help: string }> = {
  tune: { label: "AYAR", cls: "bg-slate-400/15 text-slate-300", help: "Ağırlıklar sadece bu yerlere bakılarak ayarlanır." },
  holdout: { label: "SINAV", cls: "bg-cyan-400/15 text-cyan-300", help: "Başarı ölçütü sadece bunlarla hesaplanır; bunlara bakarak ayar yapılmaz." },
  report: { label: "RAPOR", cls: "bg-white/5 text-slate-400", help: "Sırası gösterilir, ölçüte girmez: yöntem bu özelliği ölçemiyor." },
};

const STATUS: Record<ValidationAnalog["status"], string> = {
  ok: "",
  missing_cell: "Izgarada karesi yok",
  no_target_values: "Hedefte bu testin değeri yok",
};

export default function ValidationPage() {
  const [res, setRes] = useState<ValidationResult | null | undefined>(undefined);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [targets, setTargets] = useState<TargetWithCoords[]>([]);

  useEffect(() => {
    Promise.all([loadValidation(), loadMeta(), loadTargets()]).then(([v, m, t]) => {
      setRes(v);
      setMeta(m);
      setTargets(t);
    });
  }, []);

  const testLabel = (id: string) => meta?.tests.find((t) => t.id === id)?.label ?? id;
  const targetName = (id?: string) => targets.find((t) => t.id === id)?.name ?? id ?? "—";

  return (
    <SpaceLayout>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <h1 className="font-mono text-2xl font-semibold tracking-wider text-white">DOĞRULAMA</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          NASA ve ESA'nın kullandığı ünlü analog sahalar, motorumuzda kendi test amaçları için Dünya karelerinin yüzde kaçlık diliminde?
          Ünlü sahalar keşif listesine girmez; motorun doğruluğunu ölçmek için kullanılır.
        </p>

        {res === null && (
          <p className="mt-6 rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-sm text-amber-200/80">
            Doğrulama henüz çalıştırılmadı: Dünya taraması (grid.parquet) bekleniyor. Bkz. STATUS.md.
          </p>
        )}

        {res && (
          <>
            <section className={`mt-6 rounded-xl border p-5 ${res.passed ? "border-emerald-400/30 bg-emerald-400/5" : "border-rose-400/30 bg-rose-400/5"}`}>
              <p className="font-mono text-4xl font-semibold text-white">
                {res.hits}/{res.holdout_total}
              </p>
              <p className="mt-1 text-sm text-slate-300">
                sınav sahası kendi test amacında Dünya'nın en iyi {pct(res.top_percent, 0)}'inde (gereken: {res.min_hits}) ·{" "}
                <span className={res.passed ? "text-emerald-300" : "text-rose-300"}>{res.passed ? "GEÇTİ" : "GEÇMEDİ"}</span>
              </p>
              <p className="mt-1 text-xs text-slate-500">Payda: {res.denominator.toLocaleString("tr-TR")} kare (maskeli olmayanlar + doğrulama kareleri)</p>
            </section>

            <table className="mt-6 w-full text-left text-sm">
              <thead className="font-mono text-[10px] tracking-wider text-slate-500">
                <tr>
                  <th className="py-2">GRUP</th>
                  <th>SAHA</th>
                  <th>TEST · HEDEF</th>
                  <th className="text-right">DİLİM</th>
                  <th className="text-right">SIRA</th>
                </tr>
              </thead>
              <tbody>
                {res.analogs.map((a) => (
                  <tr key={a.id} className="border-t border-white/5 align-top">
                    <td className="py-2.5 pr-2">
                      <span className={`rounded-full px-2 py-0.5 font-mono text-[10px] ${SPLIT[a.split].cls}`} title={SPLIT[a.split].help}>
                        {SPLIT[a.split].label}
                      </span>
                    </td>
                    <td className="py-2.5 pr-2 text-slate-200">
                      {a.name}
                      {a.note && <div className="mt-0.5 text-xs text-slate-500">{a.note}</div>}
                      {a.past_tests.slice(0, 2).map((t) => (
                        <a key={t.url} href={t.url} target="_blank" rel="noreferrer" className="mt-0.5 block text-xs text-cyan-300/80 hover:underline">
                          {t.title}
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
                      {a.rank ? `${a.rank.toLocaleString("tr-TR")} · ${num(a.score_total, 1)}` : "—"}
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
