import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { LangSwitch, useLang } from "../i18n";
import Starfield from "./Starfield";

export default function SpaceLayout({ children }: { children: ReactNode }) {
  const { t } = useLang();
  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-space text-slate-200">
      <Starfield />
      <div className="grid-overlay pointer-events-none fixed inset-0" aria-hidden />
      <header className="relative z-10 flex items-center justify-between gap-3 border-b border-white/10 px-4 py-4 sm:px-8">
        <Link to="/" className="font-mono text-sm font-semibold tracking-[0.2em] text-white sm:tracking-[0.35em]">
          GEOCOSMOS
        </Link>
        <nav className="flex items-center gap-3 sm:gap-5">
          <span className="hidden font-mono text-[11px] tracking-[0.2em] text-slate-500 lg:block">
            {t("AY VE MARS İÇİN DÜNYA'DA ANALOG TEST SAHASI", "EARTH ANALOG TEST SITES FOR THE MOON AND MARS")}
          </span>
          <Link to="/bulgular" className="font-mono text-[11px] tracking-[0.1em] text-cyan-300/90 hover:text-white sm:tracking-[0.2em]">
            {t("BULGULAR", "FINDINGS")}
          </Link>
          <Link to="/dogrulama" className="font-mono text-[11px] tracking-[0.1em] text-slate-400 hover:text-white sm:tracking-[0.2em]">
            {t("DOĞRULAMA", "VALIDATION")}
          </Link>
          <LangSwitch />
        </nav>
      </header>
      <div className="relative z-10">{children}</div>
    </div>
  );
}
