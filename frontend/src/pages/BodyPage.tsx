import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { BODIES } from "../bodies";
import SpaceLayout from "../components/SpaceLayout";
import { loadTargets, targetsOf, type TargetWithCoords } from "../services/data";
import type { Body } from "../types";

const fmt = (v: number, pos: string, neg: string) => `${Math.abs(v).toFixed(1)}°${v >= 0 ? pos : neg}`;

// Geçici sayfa: hedef listesi. Ay/Mars haritası ve test seçimi sonraki adım.
export default function BodyPage() {
  const { body } = useParams();
  const [targets, setTargets] = useState<TargetWithCoords[] | null>(null);

  useEffect(() => {
    loadTargets().then(setTargets).catch(() => setTargets([]));
  }, []);

  if (body !== "mars" && body !== "moon") return <Navigate to="/" replace />;
  const meta = BODIES[body as Body];
  const own = targets ? targetsOf(targets, body as Body) : [];

  return (
    <SpaceLayout>
      <main className="mx-auto max-w-3xl px-4 py-10 sm:px-8">
        <Link to="/" className="font-mono text-xs tracking-wider text-slate-500 hover:text-slate-300">
          ‹ GERİ
        </Link>
        <h1 className="mt-6 font-mono text-2xl font-semibold tracking-wider text-white">
          {meta.name} <span className="font-normal text-white/40">// {meta.tagline}</span>
        </h1>
        <p className="mt-2 text-sm text-slate-400">Hedef seç. Harita ve test amacı seçimi yakında burada olacak.</p>

        <ul className="mt-8 grid gap-3">
          {targets === null && <li className="font-mono text-xs text-slate-500">Yükleniyor…</li>}
          {own.map((t) => (
            <li key={t.id} className="rounded-xl border border-white/10 bg-white/[0.03] px-5 py-4 backdrop-blur-sm">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium text-white">{t.name}</span>
                <span className="font-mono text-[11px] text-slate-500">
                  {fmt(t.lat, "K", "G")} · {fmt(t.lon, "D", "B")}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-400">{t.why}</p>
              <p className={`mt-2 font-mono text-[10px] tracking-wider ${meta.accent}`}>
                {Object.keys(t.params).length} PARAMETRE GİRİLDİ
              </p>
            </li>
          ))}
        </ul>
      </main>
    </SpaceLayout>
  );
}
