import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import AnalogCard from "../components/AnalogCard";
import EarthMap from "../components/EarthMap";
import ScenarioBox from "../components/ScenarioBox";
import SpaceLayout from "../components/SpaceLayout";
import { num } from "../format";
import {
  heatmapUrl,
  loadAnalogIndex,
  loadAnalogs,
  loadHeatmapIndex,
  loadLogistics,
  loadMeta,
  loadTargets,
  type TargetWithCoords,
} from "../services/data";
import type { Analog, AnalogIndexEntry, Body, HeatmapIndex, LogisticsFile, Meta, ScenarioResponse } from "../types";

export default function AnalogPage() {
  const { body, targetId, testId } = useParams();
  // "custom": hedef sayfasındaki "Kendi senaryon" kutusu; metin ?q= içinde, sonuç POST /scenario'dan
  const isCustom = testId === "custom";
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const [meta, setMeta] = useState<Meta | null>(null);
  const [target, setTarget] = useState<TargetWithCoords | null>(null);
  const [entry, setEntry] = useState<AnalogIndexEntry | null | undefined>(undefined);
  const [analogs, setAnalogs] = useState<Analog[]>([]);
  const [heat, setHeat] = useState<HeatmapIndex | null>(null);
  const [logi, setLogi] = useState<LogisticsFile | null>(null);
  const [scenario, setScenario] = useState<ScenarioResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showHeat, setShowHeat] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([loadMeta(), loadTargets(), loadAnalogIndex(), loadHeatmapIndex(), loadLogistics()])
      .then(async ([m, ts, idx, h, lg]) => {
        const e = idx?.find((x) => x.target_id === targetId && x.test_id === testId) ?? null;
        const list = e?.file ? await loadAnalogs(e.file) : [];
        if (!alive) return;
        setMeta(m);
        setTarget(ts.find((t) => t.id === targetId) ?? null);
        setEntry(idx === null ? null : isCustom ? undefined : e);
        setAnalogs(list);
        setHeat(h);
        setLogi(lg);
        setSelectedId(list[0]?.id ?? null);
      })
      .catch((e) => setError(String(e)));
    return () => {
      alive = false;
    };
  }, [targetId, testId]);

  const shown = scenario ? scenario.analogs : analogs;
  const selected = useMemo(() => shown.find((a) => a.id === selectedId) ?? shown[0] ?? null, [shown, selectedId]);
  const heatFile = heat?.files.find((f) => f.target_id === targetId && f.test_id === testId);
  const heatmap = heat && heatFile && !scenario ? { url: heatmapUrl(heatFile.file), bounds: heat.bounds } : null;

  if (body !== "mars" && body !== "moon") return <Navigate to="/" replace />;
  const test = meta?.tests.find((t) => t.id === testId);
  if (meta && !test && !isCustom) return <Navigate to={`/${body}`} replace />;

  return (
    <SpaceLayout>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-8">
        <Link to={`/${body}`} className="font-mono text-xs tracking-wider text-slate-500 hover:text-slate-300">
          ‹ {target?.name ?? "HEDEFLER"}
        </Link>
        <h1 className="mt-3 text-xl font-semibold text-white sm:text-2xl">
          {isCustom ? "Kendi senaryon" : test?.label ?? "…"} <span className="font-normal text-slate-400">· {target?.name}</span>
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Dünya'nın tüm karaları {meta?.grid_km ?? 25} km'lik karelerle tarandı. <span className="text-cyan-300">Mavi</span> pinler yeni aday,{" "}
          <span className="text-amber-300">sarı</span> pinler zaten bilinen analog sahalar.
          {test?.rationale && <span className="block text-xs text-slate-500">{test.rationale}</span>}
        </p>
        {error && <p className="mt-4 text-sm text-rose-300">{error}</p>}
        {entry === null && (
          <p className="mt-4 rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-sm text-amber-200/80">
            Dünya taraması henüz çalıştırılmadı (grid.parquet yok). Harita boş görünür; senaryo kutusu da API'ye bağlı. Bkz. STATUS.md.
          </p>
        )}
        {entry && !entry.file && <p className="mt-4 text-sm text-amber-200/80">{entry.reason}</p>}

        <div className="mt-5 grid gap-5 lg:grid-cols-[1.6fr_1fr]">
          <div className="relative h-[24rem] min-w-0 overflow-hidden rounded-xl border border-white/10 lg:h-[calc(100dvh-14rem)]">
            <EarthMap analogs={shown} selected={selected} onSelect={(a) => setSelectedId(a.id)} heatmap={heatmap} showHeatmap={showHeat} />
            {heatmap && (
              <label className="absolute right-3 top-3 z-[1000] flex items-center gap-2 rounded-lg bg-black/60 px-2.5 py-1.5 text-xs text-slate-300 backdrop-blur">
                <input type="checkbox" checked={showHeat} onChange={(e) => setShowHeat(e.target.checked)} />
                Isı haritası (benzerlik 0–100)
              </label>
            )}
          </div>

          <aside className="min-w-0 space-y-5 lg:max-h-[calc(100dvh-14rem)] lg:overflow-y-auto lg:pr-1">
            {isCustom && targetId && meta && (
              <ScenarioBox
                targetId={targetId}
                meta={meta}
                initialText={query}
                onText={(t) => setParams({ q: t }, { replace: true })}
                onResult={(r) => {
                  setScenario(r);
                  setSelectedId(r?.analogs[0]?.id ?? null);
                }}
              />
            )}

            {shown.length > 0 && (
              <ol className="flex gap-1.5 overflow-x-auto pb-1">
                {shown.map((a) => (
                  <li key={a.id}>
                    <button
                      onClick={() => setSelectedId(a.id)}
                      className={`whitespace-nowrap rounded-full px-2.5 py-1 font-mono text-[11px] ${
                        a.id === selected?.id ? "bg-white text-black" : a.is_new ? "bg-cyan-400/15 text-cyan-200" : "bg-amber-400/15 text-amber-200"
                      }`}
                    >
                      #{a.rank} · {num(a.score_total, 0)}
                    </button>
                  </li>
                ))}
              </ol>
            )}

            {selected && meta && target ? (
              <>
                <Link
                  to={`/${body}/${targetId}/${testId}/rapor/${selected.id}`}
                  state={isCustom ? { analog: selected, query } : undefined}
                  className="flex items-center justify-between rounded-lg border border-cyan-400/25 bg-cyan-400/5 px-3 py-2 text-sm text-cyan-100 hover:border-cyan-400/50"
                >
                  <span>Saha raporu ve yol haritası (PDF)</span>
                  <span aria-hidden>→</span>
                </Link>
                <AnalogCard analog={selected} meta={meta} body={body as Body} targetName={target.name} logistics={logi?.cells[selected.id]} />
              </>
            ) : (
              entry !== undefined && <p className="text-sm text-slate-500">Gösterilecek aday yok.</p>
            )}
          </aside>
        </div>
      </main>
    </SpaceLayout>
  );
}
