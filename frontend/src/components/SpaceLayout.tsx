import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import Starfield from "./Starfield";

export default function SpaceLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-space text-slate-200">
      <Starfield />
      <div className="grid-overlay pointer-events-none fixed inset-0" aria-hidden />
      <header className="relative z-10 flex items-center justify-between border-b border-white/10 px-4 py-4 sm:px-8">
        <Link to="/" className="font-mono text-sm font-semibold tracking-[0.35em] text-white">
          GEOCOSMOS
        </Link>
        <nav className="flex items-center gap-5">
          <span className="hidden font-mono text-[11px] tracking-[0.2em] text-slate-500 lg:block">
            AY VE MARS İÇİN DÜNYA'DA ANALOG TEST SAHASI
          </span>
          <Link to="/dogrulama" className="font-mono text-[11px] tracking-[0.2em] text-slate-400 hover:text-white">
            DOĞRULAMA
          </Link>
        </nav>
      </header>
      <div className="relative z-10">{children}</div>
    </div>
  );
}
