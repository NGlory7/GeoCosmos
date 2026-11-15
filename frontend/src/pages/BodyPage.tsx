import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { BODIES } from "../bodies";
import PlanetGlobe from "../components/PlanetGlobe";
import SpaceLayout from "../components/SpaceLayout";
import { coord } from "../format";
import { useLang } from "../i18n";
import { localizeMeta, localizeTargets } from "../i18nData";
import { loadAnalogIndex, loadMeta, loadTargets, targetsOf, type TargetWithCoords } from "../services/data";
import type { AnalogIndexEntry, Body, Meta } from "../types";

/** Serbest metin: dünya haritası sayfasında /scenario ile aranır (AnalogPage, testId = "custom"). */
function CustomScenario({ body, target }: { body: Body; target: TargetWithCoords }) {
  const [text, setText] = useState("");
  const navigate = useNavigate();
  const { t } = useLang();
  return (
    <form
      className="rounded-lg border border-dashed border-cyan-400/25 px-3 py-2.5"
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim()) navigate(`/${body}/${target.id}/custom?q=${encodeURIComponent(text.trim())}`);
      }}
    >
      <label className="font-mono text-[10px] tracking-[0.2em] text-cyan-200/70" htmlFor={`scn-${target.id}`}>
        {t("KENDİ SENARYON", "YOUR OWN SCENARIO")}
      </label>
      <div className="mt-1.5 flex gap-2">
        <input
          id={`scn-${target.id}`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={1000}
          placeholder={t("Ne test etmek istiyorsun? (ör. toz fırtınasında güneş paneli)", "What do you want to test? (e.g. solar panels in a dust storm)")}
          className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-1.5 text-sm text-white placeholder:text-slate-600 focus:border-cyan-400/50 focus:outline-none"
        />
        <button disabled={!text.trim()} className="rounded-lg bg-cyan-500/80 px-3 py-1.5 text-sm font-medium text-black disabled:opacity-40">
          {t("Ara", "Search")}
        </button>
      </div>
    </form>
  );
}

function TestPicker({ body, target, meta, index }: { body: Body; target: TargetWithCoords; meta: Meta; index: AnalogIndexEntry[] | null }) {
  const { t } = useLang();
  return (
    <div className="mt-3 grid gap-2">
      {meta.tests.map((test) => {
        const entry = index?.find((e) => e.target_id === target.id && e.test_id === test.id);
        // index.json'da dosyası olmayan kayıt: test bu hedefte anlamsız (test_profiles.yaml > applies_to).
        // Listede hiç gösterilmez; sebebi doğrudan test adresine gidilirse AnalogPage'de yazar.
        if (index !== null && entry !== undefined && !entry.file) return null;
        const keys = Object.keys(test.weights);
        const have = keys.filter((k) => k in target.params).length;
        const disabled = have === 0;
        const status = index === null ? t("Dünya verisi bekleniyor", "Waiting for Earth data") : entry?.file ? `${entry.count} ${t("aday", "candidates")} · ${entry.new_count ?? 0} ${t("yeni", "new")}` : "";
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
              {have}/{keys.length} PARAM{status && ` · ${status}`}
            </span>
          </Link>
        );
      })}
      <CustomScenario body={body} target={target} />
    </div>
  );
}

export default function BodyPage() {
  const { body } = useParams();
  const { t, lang } = useLang();
  const [rawTargets, setTargets] = useState<TargetWithCoords[] | null>(null);
  const [rawMeta, setMeta] = useState<Meta | null>(null);
  const targets = useMemo(() => (rawTargets ? localizeTargets(rawTargets, lang) : null), [rawTargets, lang]);
  const meta = localizeMeta(rawMeta, lang);
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

  const own = useMemo(() => (targets && (body === "mars" || body === "moon") ? targetsOf(targets, body) : []), [targets, body]);

  // Başka gök cismine geçince seçim sıfırlanır
  useEffect(() => setSelected(null), [body]);

  if (body !== "mars" && body !== "moon") return <Navigate to="/" replace />;
  const b = body as Body;
  const meta_ = BODIES[b];

  return (
    <SpaceLayout>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8">
        <Link to="/" className="font-mono text-xs tracking-wider text-slate-500 hover:text-slate-300">
          ‹ {t("GERİ", "BACK")}
        </Link>
        <h1 className="mt-4 font-mono text-2xl font-semibold tracking-wider text-white">
          {lang === "en" ? meta_.nameEn : meta_.name} <span className="font-normal text-white/40">// {meta_.tagline}</span>
        </h1>
        <p className="mt-2 text-sm text-slate-400">{t("Hedefi seç, sonra Dünya'da prova etmek istediğin testi seç.", "Pick a target, then pick the test you want to rehearse on Earth.")}</p>
        {error && <p className="mt-4 text-sm text-rose-300">{error}</p>}
        {index === null && targets && (
          <p className="mt-4 rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-xs text-amber-200/80">
            {t("Dünya taraması henüz çalıştırılmadı: test sayfalarında aday ve ısı haritası görünmez (STATUS.md).", "The Earth scan has not been run yet: test pages show no candidates or heat map (STATUS.md).")}
          </p>
        )}

        <div className="mt-6 grid items-start gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          {/* Kutu yok: gezegenin kendisi; hedefler üzerinde, seçilince oraya döner */}
          <div className="mx-auto w-full max-w-[36rem] lg:sticky lg:top-6">
            <PlanetGlobe key={b} body={b} targets={own} selected={selected} onSelect={setSelected} />
          </div>
          <ul className="grid content-start gap-4">
            {targets === null && !error && <li className="font-mono text-xs text-slate-500">{t("Yükleniyor…", "Loading…")}</li>}
            {own.map((t) => {
              const on = t.id === selected;
              return (
                <li
                  key={t.id}
                  className={`rounded-2xl border px-6 py-5 backdrop-blur-sm transition-colors ${
                    on ? "border-cyan-400/40 bg-cyan-400/[0.04]" : "border-white/10 bg-white/[0.03] hover:border-white/20"
                  }`}
                >
                  <button className="w-full text-left" onClick={() => setSelected(on ? null : t.id)} aria-expanded={on}>
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="text-lg font-medium text-white">{t.name}</span>
                      <span className="font-mono text-xs text-slate-500">{coord(t.lat, t.lon)}</span>
                    </div>
                    <p className="mt-1 text-slate-400">{t.why}</p>
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
