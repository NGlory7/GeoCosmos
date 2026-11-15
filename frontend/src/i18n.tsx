// Arayüz dili: Türkçe (tr) ve İngilizce (en). Jüri ve uluslararası kullanıcı için İngilizce.
// Seçim sırası: adresteki ?lang=en|tr > daha önce seçilen (localStorage) > tarayıcı dili (tr ise tr, değilse en).
// Metinler bileşenin içinde yan yana yazılır: t("Türkçe", "English"). Veri dosyalarındaki etiketlerin
// İngilizcesi i18nData.ts'de.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "tr" | "en";

function initialLang(): Lang {
  try {
    const q = new URLSearchParams(window.location.search).get("lang");
    if (q === "en" || q === "tr") return q;
    const s = window.localStorage.getItem("geocosmos-lang");
    if (s === "en" || s === "tr") return s;
  } catch {
    // gizli pencere / engellenmiş depolama: tarayıcı diline düş
  }
  return navigator.language?.toLowerCase().startsWith("tr") ? "tr" : "en";
}

let current: Lang = initialLang();

/** Bileşen dışı kod (format.ts, roadmap.ts) için o anki dil. */
export function getLang(): Lang {
  return current;
}

const LangContext = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({ lang: current, setLang: () => {} });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setState] = useState<Lang>(current);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = (l: Lang) => {
    current = l;
    try {
      window.localStorage.setItem("geocosmos-lang", l);
    } catch {
      // kaydedilemezse sadece bu oturumda geçerli
    }
    setState(l);
  };
  return <LangContext.Provider value={{ lang, setLang }}>{children}</LangContext.Provider>;
}

export function useLang() {
  const { lang, setLang } = useContext(LangContext);
  const t = (tr: string, en: string) => (lang === "en" ? en : tr);
  return { lang, setLang, t, en: lang === "en" };
}

/** Bileşen dışı: tr(..) / en(..) seçimi. */
export function tx(tr: string, en: string): string {
  return current === "en" ? en : tr;
}

export function LangSwitch() {
  const { lang, setLang } = useLang();
  return (
    <div className="flex overflow-hidden rounded-full border border-white/15 font-mono text-[10px] tracking-wider" role="group" aria-label="Language / Dil">
      {(["tr", "en"] as const).map((l) => (
        <button
          key={l}
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          className={`px-2 py-0.5 ${lang === l ? "bg-white text-black" : "text-slate-400 hover:text-white"}`}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
