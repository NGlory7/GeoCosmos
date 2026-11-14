import { useState } from "react";
import { shortLabel } from "../format";
import { postScenario, ScenarioError } from "../services/data";
import type { Meta, ScenarioResponse } from "../types";

interface Props {
  targetId: string;
  meta: Meta;
  onResult: (r: ScenarioResponse | null) => void;
}

const EXAMPLES = ["Toz fırtınasında güneş panelinin tozlanmasını test etmek istiyorum", "Donmuş zeminde matkapla buz örneği almak"];

// Serbest metin -> Gemini ağırlıkları -> motor sıralaması (POST /scenario). Gemini sayı üretmez.
export default function ScenarioBox({ targetId, meta, onResult }: Props) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ msg: string; offline: boolean } | null>(null);
  const [last, setLast] = useState<ScenarioResponse | null>(null);

  async function run(t: string) {
    setBusy(true);
    setError(null);
    try {
      const r = await postScenario({ text: t, target_id: targetId });
      setLast(r);
      onResult(r);
    } catch (e) {
      const err = e instanceof ScenarioError ? e : new ScenarioError(String(e));
      setError({ msg: err.message, offline: err.offline });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
      <h3 className="font-mono text-[11px] tracking-[0.2em] text-slate-500">KENDİ SENARYON</h3>
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
          placeholder="Ne test etmek istiyorsun?"
          className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-cyan-400/50 focus:outline-none"
        />
        <button
          disabled={busy || !text.trim()}
          className="rounded-lg bg-cyan-500/80 px-3 py-2 text-sm font-medium text-black disabled:opacity-40"
        >
          {busy ? "…" : "Ara"}
        </button>
      </form>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => setText(ex)} className="rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-slate-400 hover:text-slate-200">
            {ex}
          </button>
        ))}
      </div>
      {error && (
        <p className={`mt-2 text-xs ${error.offline ? "text-slate-400" : "text-rose-300"}`}>
          {error.msg}
          {error.offline && " Hazır test sonuçları çalışmaya devam ediyor."}
        </p>
      )}
      {last && (
        <div className="mt-3 space-y-2 text-xs text-slate-400">
          {last.method === "keywords" && (
            <p className="rounded-md border border-amber-400/20 bg-amber-400/5 px-2 py-1.5 text-amber-200/80">
              Gemini'ye şu an ulaşılamadı. Metindeki anahtar kelimelerle hazır testlerin ağırlıkları kullanıldı:{" "}
              {last.matched_tests.map((id) => meta.tests.find((t) => t.id === id)?.label ?? id).join(", ")}.
            </p>
          )}
          <p>
            Ağırlıklar:{" "}
            {Object.entries(last.weights)
              .sort((a, b) => b[1] - a[1])
              .map(([k, w]) => `${shortLabel(meta.parameters[k]?.label ?? k)} %${Math.round(w * 100)}`)
              .join(" · ")}
          </p>
          {last.unsupported.length > 0 && <p className="text-amber-200/80">Dünya'da karşılığı yok: {last.unsupported.join(", ")}</p>}
          <button
            onClick={() => {
              setLast(null);
              onResult(null);
            }}
            className="text-cyan-300 hover:underline"
          >
            Hazır teste dön
          </button>
        </div>
      )}
    </section>
  );
}
