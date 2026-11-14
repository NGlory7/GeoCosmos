import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BODIES } from "../bodies";
import Planet from "../components/Planet";
import SpaceLayout from "../components/SpaceLayout";
import { loadTargets, targetsOf, type TargetWithCoords } from "../services/data";
import type { Body } from "../types";

function BodyCard({ body, targets, size }: { body: Body; targets: TargetWithCoords[]; size: string }) {
  const meta = BODIES[body];
  const own = targetsOf(targets, body);
  // "Jezero Krateri" -> "JEZERO" (özel isimler: Türkçe büyük harf kuralı uygulanmaz)
  const names = own.map((t) => t.name.split(" ")[0].toUpperCase());
  const count = own.length ? `${own.length} HEDEF` : "HEDEFLER YÜKLENİYOR";
  const sub = own.length ? `${count} · ${names.join(" · ")}` : count;

  return (
    <Link
      to={`/${body}`}
      className={`group relative block aspect-square shrink-0 rounded-full outline-none ${size}`}
      aria-label={`${meta.name}: ${sub}`}
    >
      <Planet body={body} className="h-full w-full transition-transform duration-700 ease-out group-hover:scale-[1.03]" />
      <div className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-3 whitespace-nowrap rounded-full border border-white/10 bg-black/45 px-4 py-2.5 backdrop-blur-md transition-colors group-hover:border-white/25 group-hover:bg-black/60 group-focus-visible:border-white/50">
        <span className={`size-1.5 rounded-full shadow-[0_0_8px] ${meta.dot}`} />
        <span className="flex flex-col gap-0.5 leading-tight">
          <span className="font-mono text-[12px] font-semibold tracking-wider text-white sm:text-[13px]">
            {meta.name} <span className="font-normal text-white/40">// {meta.tagline}</span>
          </span>
          <span className={`font-mono text-[9px] tracking-wider sm:text-[10px] ${meta.accent}`}>
            {count}
            {names.length > 0 && <span className="hidden sm:inline"> · {names.join(" · ")}</span>}
          </span>
        </span>
        <span className="text-white/40 transition-transform group-hover:translate-x-0.5" aria-hidden>
          ›
        </span>
      </div>
    </Link>
  );
}

export default function Home() {
  const [targets, setTargets] = useState<TargetWithCoords[]>([]);

  useEffect(() => {
    loadTargets().then(setTargets).catch(console.error);
  }, []);

  return (
    <SpaceLayout>
      <main className="flex min-h-[calc(100dvh-57px)] flex-col items-center justify-center gap-8 px-4 py-10">
        <p className="font-mono text-[11px] tracking-[0.3em] text-slate-500">HEDEF GÖK CİSMİNİ SEÇ</p>
        <div className="flex flex-col items-center justify-center md:flex-row md:gap-4">
          <BodyCard body="mars" targets={targets} size="w-[min(92vw,34rem)] md:w-[min(48vw,34rem)]" />
          <BodyCard body="moon" targets={targets} size="w-[min(78vw,28rem)] md:w-[min(40vw,28rem)]" />
        </div>
      </main>
    </SpaceLayout>
  );
}
