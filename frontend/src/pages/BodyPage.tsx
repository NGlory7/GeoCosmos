import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { BODIES } from "../bodies";
import PlanetMap from "../components/PlanetMap";
import SpaceLayout from "../components/SpaceLayout";
import { coord } from "../format";
import { loadAnalogIndex, loadMeta, loadTargets, targetsOf, type TargetWithCoords } from "../services/data";
import type { AnalogIndexEntry, Body, Meta } from "../types";

function TestPicker({ body, target, meta, index }: { body: Body; target: TargetWithCoords; meta: Meta; index: AnalogIndexEntry[] | null }) {
  return (
    <div className="mt-3 grid gap-2">
      {meta.tests.map((test) => {
        const keys = Object.keys(test.weights);
        const have = keys.filter((k) => k in target.params).length;
        const entry = index?.find((e) => e.target_id === target.id && e.test_id === test.id);
        const disabled = have === 0;
        const status = index === null ? "Dünya verisi bekleniyor" : entry?.file ? `${entry.count} aday · ${entry.new_count ?? 0} yeni` : "sonuç yok";
        return (
          <Link
            key={test.id}
            to={disabled ? "#" : `/${body}/${target.id}/${test.id}`}
            aria-disabled={disabled}
            className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm transition-colors ${
              disabled ? "pointer-events-none border-white/5 text-slate-600" : "border-white/10 text-slate-200 hover:border-cyan-400/40 hover:bg-cyan-400/5"
            }`}
          >
            <span>{test.label}</span>
            <span className="shrink-0 font-mono text-[10px] text-slate-500">
              {have}/{keys.length} PARAM · {status}
            </span>
          </Link>
        );
      })}
    </div>
  );
}

export default function BodyPage() {
  const { body } = useParams();
  const [targets, setTargets] = useState<TargetWithCoords[] | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [index, setIndex] = useState<AnalogIndexEntry[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([loadTargets(), loadMeta(), loadAnalogIndex()])
      .then(([t, m, i]) => {
        setTargets(t);
        setMeta(m);
        setIndex(i);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (body !== "mars" && body !== "moon") return <Navigate to="/" replace />;
  const b = body as Body;
  const meta_ = BODIES[b];
  const own = targets ? targetsOf(targets, b) : [];

  return (
    <SpaceLayout>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8">
        <Link to="/" className="font-mono text-xs tracking-wider text-slate-500 hover:text-slate-300">
          ‹ GERİ
        </Link>
        <h1 className="mt-4 font-mono text-2xl font-semibold tracking-wider text-white">
          {meta_.name} <span className="font-normal text-white/40">// {meta_.tagline}</span>
        </h1>
        <p className="mt-2 text-sm text-slate-400">Hedefi seç, sonra Dünya'da prova etmek istediğin testi seç.</p>
        {error && <p className="mt-4 text-sm text-rose-300">{error}</p>}
        {index === null && targets && (
          <p className="mt-4 rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-xs text-amber-200/80">
            Dünya taraması henüz çalıştırılmadı: test sayfalarında aday ve ısı haritası görünmez (STATUS.md).
          </p>
        )}

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="h-[22rem] min-w-0 overflow-hidden rounded-xl border border-white/10 lg:h-[34rem]">
            {targets && <PlanetMap body={b} targets={own} selected={selected} onSelect={setSelected} />}
          </div>
          <ul className="grid content-start gap-3">
            {targets === null && !error && <li className="font-mono text-xs text-slate-500">Yükleniyor…</li>}
            {own.map((t) => {
              const on = t.id === selected;
              return (
                <li key={t.id} className={`rounded-xl border px-4 py-3 backdrop-blur-sm ${on ? "border-cyan-400/40 bg-cyan-400/[0.04]" : "border-white/10 bg-white/[0.03]"}`}>
                  <button className="w-full text-left" onClick={() => setSelected(on ? null : t.id)}>
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="font-medium text-white">{t.name}</span>
                      <span className="font-mono text-[11px] text-slate-500">{coord(t.lat, t.lon)}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-400">{t.why}</p>
                  </button>
                  {on && meta && <TestPicker body={b} target={t} meta={meta} index={index} />}
                </li>
              );
            })}
          </ul>
        </div>
      </main>
    </SpaceLayout>
  );
}
