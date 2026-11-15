import { useEffect, useRef, useState } from "react";
import { shortLabel } from "../format";
import { useLang } from "../i18n";
import { postScenario, ScenarioError } from "../services/data";
import type { Meta, ScenarioResponse } from "../types";

interface Props {
  targetId: string;
  meta: Meta;
  onResult: (r: ScenarioResponse | null) => void;
  /** Hedef sayfasında yazılan metin: sayfa açılınca bununla aranır. */
  initialText?: string;
  /** Yeni metinle arandığında (adres güncellensin, paylaşılabilsin). */
  onText?: (t: string) => void;
}

const EXAMPLES = {
  tr: ["Toz fırtınasında güneş panelinin tozlanmasını test etmek istiyorum", "Donmuş zeminde matkapla buz örneği almak"],
  en: ["I want to test solar panel dust build-up in a dust storm", "Drilling ice samples from frozen ground"],
};

// Serbest metin -> Gemini ağırlıkları -> motor sıralaması (POST /scenario). Gemini sayı üretmez.
export default function ScenarioBox({ targetId, meta, onResult, initialText = "", onText }: Props) {
  const { t, lang } = useLang();
  const [text, setText] = useState(initialText);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ msg: string; offline: boolean } | null>(null);
  const [last, setLast] = useState<ScenarioResponse | null>(null);

  async function run(q: string) {
    setBusy(true);
    setError(null);
    onText?.(q);
    try {
      const r = await postScenario({ text: q, target_id: targetId });
      setLast(r);
      onResult(r);
    } catch (e) {
      const err = e instanceof ScenarioError ? e : new ScenarioError(String(e));
      // Ham Gemini hatası (429 JSON'u) kullanıcıya okunur bir cümleyle gösterilir
      const quota = /429|RESOURCE_EXHAUSTED|quota/i.test(err.message);
      setError({
        msg: quota
          ? t("Gemini'nin günlük ücretsiz kotası doldu; senaryo araması kota yenilenince (ertesi gün) çalışır.", "Gemini's free daily quota is used up; scenario search works again when the quota resets (next day).")
          : err.offline
            ? t(err.message, "The scenario service is offline in this deployment; it runs locally with make api.")
            : err.message,
        offline: err.offline || quota,
      });
    } finally {
      setBusy(false);
    }
  }

  // Hedef sayfasından gelen metinle bir kez ara (hedef değişirse yeniden)
  const ranFor = useRef<string | null>(null); // StrictMode'da efekt iki kez çalışır: Gemini'ye çift istek gitmesin
  useEffect(() => {
    if (!initialText.trim() || ranFor.current === targetId) return;
    ranFor.current = targetId;
    run(initialText.trim());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetId]);

  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
      <h3 className="font-mono text-[11px] tracking-[0.2em] text-slate-500">{t("KENDİ SENARYON", "YOUR OWN SCENARIO")}</h3>
      <form
        className="mt-2 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim()) run(text.trim());
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={1000}
          placeholder={t("Ne test etmek istiyorsun?", "What do you want to test?")}
          className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-cyan-400/50 focus:outline-none"
        />
        <button
          disabled={busy || !text.trim()}
          className="rounded-lg bg-cyan-500/80 px-3 py-2 text-sm font-medium text-black disabled:opacity-40"
        >
          {busy ? "…" : t("Ara", "Search")}
        </button>
      </form>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {EXAMPLES[lang].map((ex) => (
          <button key={ex} onClick={() => setText(ex)} className="rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-slate-400 hover:text-slate-200">
            {ex}
          </button>
        ))}
      </div>
      {error && (
        <p className={`mt-2 text-xs ${error.offline ? "text-slate-400" : "text-rose-300"}`}>
          {error.msg}
          {error.offline && t(" Hazır test sonuçları çalışmaya devam ediyor.", " The predefined test results keep working.")}
        </p>
      )}
      {last && (
        <div className="mt-3 space-y-2 text-xs text-slate-400">
          {last.method === "keywords" && (
            <p className="rounded-md border border-amber-400/20 bg-amber-400/5 px-2 py-1.5 text-amber-200/80">
              {t(
                "Gemini'ye şu an ulaşılamadı. Metindeki anahtar kelimelerle hazır testlerin ağırlıkları kullanıldı:",
                "Gemini could not be reached. Keywords in your text were matched to the ready-made tests, using their weights:",
              )}{" "}
              {last.matched_tests.map((id) => meta.tests.find((x) => x.id === id)?.label ?? id).join(", ")}.
            </p>
          )}
          <p>
            {t("Ağırlıklar:", "Weights:")}{" "}
            {Object.entries(last.weights)
              .sort((a, b) => b[1] - a[1])
              .map(([k, w]) => `${shortLabel(meta.parameters[k]?.label ?? k)} ${lang === "en" ? `${Math.round(w * 100)}%` : `%${Math.round(w * 100)}`}`)
              .join(" · ")}
          </p>
          {last.unsupported.length > 0 && <p className="text-amber-200/80">{t("Dünya'da karşılığı yok:", "No equivalent on Earth:")} {last.unsupported.join(", ")}</p>}
        </div>
      )}
      {busy && <p className="mt-2 font-mono text-[11px] text-slate-500">{t("Senaryo ağırlıklara çevriliyor, Dünya taranıyor…", "Turning the scenario into weights and scanning Earth…")}</p>}
    </section>
  );
}
