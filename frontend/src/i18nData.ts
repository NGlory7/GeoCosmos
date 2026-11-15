// Veri dosyalarındaki (meta.json, targets.geojson, validation.json, logistics.json) Türkçe etiketlerin
// İngilizcesi. Tek kaynak hâlâ config/: burada sadece çeviri var, sayı yok. Eşleşmeyen anahtar Türkçe kalır.
// config/ içinde etiket değişirse buradaki karşılığı da güncellenmeli.
import { num } from "./format";
import type { Lang } from "./i18n";
import type { Analog, Logistics, LogisticsKey, Meta, ValidationAnalog } from "./types";
import type { TargetWithCoords } from "./services/data";

const SCORE_LABELS: Record<string, string> = { topography: "Topography", geology: "Geology", climate: "Climate" };

const TESTS: Record<string, { label: string; rationale?: string }> = {
  rover: { label: "Rover driving and wheel wear" },
  ice_drilling: { label: "Ice drilling in frozen ground (ISRU)" },
  lava_tube: {
    label: "Lava tubes and underground habitats",
    rationale:
      "Lava tubes cannot be seen from orbit; the engine only measures terrain where tubes can form (young, mafic, low-slope lava flows). So the mafic surface dominates and slope is kept low.",
  },
  dust: {
    label: "Dust storms and abrasion",
    rationale:
      "What decides a dust test is airborne dust (AOD) and the dry, bare surface that feeds it; a large day-night temperature swing strengthens thermal winds and physical weathering.",
  },
  biosignature_arid: {
    label: "Biosignatures: preservation in extreme aridity",
    rationale:
      "In hyper-arid settings organic matter and biosignatures are preserved because water is absent (Atacama; Gale's present-day surface). Aridity is decisive; a large day-night swing and a dusty surface bring it closer to Mars surface conditions. Absolute temperature is not scored; it is shown in the breakdown box.",
  },
  biosignature_carbonate: {
    label: "Biosignatures: carbonate deposits",
    rationale:
      "Jezero's targets are the marginal carbonates and the olivine-carbonate unit: carbonate precipitated when ultramafic rock reacts with water (serpentinisation) can preserve microbial traces; Salda's hydromagnesite forms by the same process. Carbonate (more than the target is not penalised) and mafic/ultramafic bedrock are decisive. Today's climate does not decide whether carbonate is present, so aridity has no weight. No tuning site: weights were fixed in advance and are not changed after seeing the test result.",
  },
  base_site: {
    label: "Base construction and landing site",
    rationale:
      "Terrain geometry decides landing and base construction (slope, roughness: hazard detection, construction, roads). Sun elevation stands for power and visibility: at a polar base the Sun sits near the horizon, shadows are long and panels are vertical. Nearby ice is for in-situ resource use (ISRU). Sun elevation is geometric; the longer sunlight on peaks like Malapert (local horizon) is not modelled on Earth or at the target. Aridity stands for a bare, unvegetated surface.",
  },
};

const PARAMS: Record<string, string> = {
  slope_deg: "Mean slope (°, 500 m baseline)",
  roughness_m: "Surface roughness (m, std of 500 m elevation in a 5 km window)",
  surface_temp_c: "Mean surface temperature (°C)",
  temp_range_c: "Day-night temperature range (°C)",
  aridity: "Aridity (0 = humid, 1 = fully dry)",
  dust_aod: "Dust / aerosol optical depth (550 nm)",
  mafic_index: "Mafic / basaltic surface (0-1 ordinal scale)",
  carbonate_index: "Carbonate signature (0-1 ordinal scale)",
  ground_ice: "Frozen ground / near-surface ice (0-1)",
  sun_elevation_deg: "Annual mean noon Sun elevation (°, geometric)",
};

const BREAKDOWN_LABELS: Record<string, string> = {
  gravity: "Gravity",
  atmosphere: "Atmosphere",
  radiation: "Radiation",
  liquid_water: "Liquid water",
  biology: "Biology",
  temperature: "Temperature",
};

const BREAKDOWN_NOTES: Record<string, Record<string, string>> = {
  moon: {
    gravity: "Gravity is ~1/6 of Earth's (1.62 m/s²); dust and wheels behave differently.",
    atmosphere: "Practically no atmosphere; no wind erosion and no heat convection.",
    radiation: "No magnetic field or atmospheric shielding; the surface is directly exposed to cosmic rays.",
    liquid_water: "No liquid water on the surface; ice only in permanent shadow.",
    biology: "No known biological process; every Earth site hosts microbial life.",
    temperature: "Surface temperature is about −180 °C in permanent shadow and +120 °C at equatorial noon; nothing on Earth matches it.",
  },
  mars: {
    gravity: "Gravity is ~38% of Earth's (3.71 m/s²).",
    atmosphere: "Very thin atmosphere (~0.6%), mostly CO₂; dust is transported differently.",
    radiation: "No global magnetic field; surface radiation is far higher than on Earth.",
    liquid_water: "No stable liquid water on the surface today; the water cycle is active at Earth sites.",
    biology: "Earth sites host modern life; this is a contamination risk for biosignature tests.",
    temperature: "Annual mean surface temperature is roughly −40 to −75 °C depending on the target; tens of degrees colder than Earth's desert analogs.",
  },
};

const OPS: Record<string, string> = {
  road_access: "Road access (< 6 h to a city)",
  remote: "Remote (< 1 person/km²)",
};

const TARGETS: Record<string, { name: string; why: string }> = {
  moon_shackleton: { name: "Shackleton Crater rim", why: "Artemis south-pole base region" },
  moon_malapert: { name: "Malapert Massif", why: "One of the Artemis candidate regions" },
  moon_marius_hills: { name: "Marius Hills pit", why: "Lava tube skylight" },
  mars_jezero: { name: "Jezero Crater", why: "Perseverance, ancient delta" },
  mars_gale: { name: "Gale Crater", why: "Curiosity, layered sediments" },
  mars_arcadia: { name: "Arcadia Planitia", why: "Crewed landing candidate" },
};

const KNOWN: Record<string, { name: string; note?: string }> = {
  holuhraun: { name: "Holuhraun (Iceland)" },
  yungay: { name: "Yungay (Atacama, Chile)" },
  haughton: { name: "Haughton Crater (Devon Island, Canada)" },
  hanksville: {
    name: "Hanksville / MDRS area (Utah, USA)",
    note:
      "Replaces Dumont Dunes. At ~30 km², Dumont Dunes was averaged away in a 25 km cell; the Mars-like terrain around Hanksville is large enough to fill the cell.",
  },
  svalbard: { name: "Svalbard / Bockfjorden (Norway)" },
  salda: {
    name: "Lake Salda shore (Türkiye)",
    note:
      "The real target is not the lake water but the hydromagnesite deposits on the shore: a strip of a few km². Averaged over the 25 km cell with surrounding rock and lake water, the carbonate signal disappears (the cell's ASTER carbonate ratio is 1.0003, below the global median). The low rank is a resolution problem, not a weighting one; the fix is a 5 km fine scan. It stays in the test set: it was not removed after seeing the result.",
  },
  lut: { name: "Lut Desert (Iran)" },
  lanzarote: {
    name: "Lanzarote lava tubes (Spain)",
    note:
      "Lava tubes are underground; Copernicus DEM, MODIS and ASTER cannot see them. In the lava_tube test the engine can only measure \"young basaltic volcanic terrain\". The island is also small, so most of its 25 km cells are sea. Its rank is reported but not counted as a success; this limit should be stated clearly on the card.",
  },
};
// Aday listesindeki bilinen sahalar Türkçe adla gelir (known_analogs.yaml > name).
const KNOWN_BY_TR_NAME: Record<string, string> = {
  "Holuhraun (İzlanda)": KNOWN.holuhraun.name,
  "Yungay (Atacama, Şili)": KNOWN.yungay.name,
  "Haughton Krateri (Devon Adası, Kanada)": KNOWN.haughton.name,
  "Hanksville / MDRS çevresi (Utah, ABD)": KNOWN.hanksville.name,
  "Svalbard / Bockfjorden (Norveç)": KNOWN.svalbard.name,
  "Salda Gölü kıyısı (Türkiye)": KNOWN.salda.name,
  "Lut Çölü (İran)": KNOWN.lut.name,
  "Lanzarote lav tüpleri (İspanya)": KNOWN.lanzarote.name,
};

const metaCache = new WeakMap<Meta, Meta>();

export function localizeMeta(meta: Meta, lang: Lang): Meta;
export function localizeMeta(meta: Meta | null, lang: Lang): Meta | null;
export function localizeMeta(meta: Meta | null, lang: Lang): Meta | null {
  if (!meta || lang === "tr") return meta;
  const hit = metaCache.get(meta);
  if (hit) return hit;
  const map = <T extends string>(rec: Record<T, string>, en: Record<string, string>) =>
    Object.fromEntries(Object.entries(rec).map(([k, v]) => [k, en[k] ?? v])) as Record<T, string>;
  const out: Meta = {
    ...meta,
    score_labels: map(meta.score_labels, SCORE_LABELS),
    tests: meta.tests.map((t) => ({
      ...t,
      label: TESTS[t.id]?.label ?? t.label,
      rationale: t.rationale ? TESTS[t.id]?.rationale ?? t.rationale : "",
    })),
    parameters: Object.fromEntries(Object.entries(meta.parameters).map(([k, p]) => [k, { ...p, label: PARAMS[k] ?? p.label }])),
    breakdown_labels: map(meta.breakdown_labels, BREAKDOWN_LABELS),
    breakdown_notes: {
      moon: map(meta.breakdown_notes.moon, BREAKDOWN_NOTES.moon),
      mars: map(meta.breakdown_notes.mars, BREAKDOWN_NOTES.mars),
    },
    ops_labels: map(meta.ops_labels, OPS),
  };
  metaCache.set(meta, out);
  return out;
}

export function localizeTargets(targets: TargetWithCoords[], lang: Lang): TargetWithCoords[] {
  if (lang === "tr") return targets;
  return targets.map((t) => ({ ...t, name: TARGETS[t.id]?.name ?? t.name, why: TARGETS[t.id]?.why ?? t.why }));
}

export function targetNameEn(id: string, fallback: string, lang: Lang): string {
  return lang === "en" ? TARGETS[id]?.name ?? fallback : fallback;
}

export function localizeValidation(a: ValidationAnalog, lang: Lang): ValidationAnalog {
  if (lang === "tr" || !KNOWN[a.id]) return a;
  return { ...a, name: KNOWN[a.id].name, note: a.note ? KNOWN[a.id].note ?? a.note : "" };
}

/** Adayın adı koordinatsa ("36.29°K, 82.46°D") ve yer adı varsa yer adı (OpenStreetMap, pipeline/placenames.py);
 * bilinen sahanın adı ("Hanksville / MDRS çevresi") olduğu gibi kalır. Yer adı yoksa koordinat,
 * İngilizcede N/S/E/W ile yazılır. */
export function isCoordName(name: string): boolean {
  return /^-?\d/.test(name);
}

export function analogName(a: Pick<Analog, "name" | "place">, lang: Lang): string {
  if (a.place && isCoordName(a.name)) return a.place[lang];
  if (lang === "tr") return a.name;
  if (KNOWN_BY_TR_NAME[a.name]) return KNOWN_BY_TR_NAME[a.name];
  return a.name.replace(/°K\b/g, "°N").replace(/°G\b/g, "°S").replace(/°D\b/g, "°E").replace(/°B\b/g, "°W");
}

/** index.json > reason (test bu hedefte neden yok). */
export function reasonEn(reason: string, lang: Lang): string {
  if (lang === "tr") return reason;
  if (/sadece Mars/.test(reason)) return "This test only makes sense for Mars targets (test_profiles.yaml > applies_to)";
  const m = reason.match(/Hedefte (\w+) = ([\d.]+); bu test en az ([\d.]+) gerektirir/);
  if (m) return `Target has ${m[1]} = ${m[2]}; this test needs at least ${m[3]} (test_profiles.yaml > applies_to)`;
  return reason;
}

// --- Kurulum kolaylığı: İngilizce metin ham değerlerden yeniden kurulur (core/logistics.py ile aynı kurallar) ---

const LOGI_LABELS: Record<LogisticsKey, string> = {
  access: "Access",
  power: "Power",
  water: "Water",
  supply: "Workforce and supplies",
  altitude: "Altitude",
};
const LEVELS: Record<string, string> = { Kolay: "Easy", Orta: "Moderate", Zor: "Hard" };
const ADVICE: Record<LogisticsKey, string> = {
  access: "Crew and equipment must travel by plane, helicopter or seasonal road; plan the transport window around the weather.",
  power: "Connecting to the grid is not realistic: bring solar panels + batteries or a generator and fuel store from the start.",
  water: "Water must be carried in or produced on site (well, melting snow/ice, treatment); calculate daily needs up front.",
  supply: "No workforce or building materials nearby: bring all prefabricated modules and spare parts from the start.",
  altitude: "Altitude reduces crew health (altitude sickness) and generator/engine efficiency; an acclimatisation plan is needed.",
};
const FUEL: Record<string, string> = { "Wave and Tidal": "wave/tidal" };

function people(n: number): string {
  if (n < 100) return "almost nobody lives";
  if (n < 1e4) return `~${num(Math.round(n / 100) * 100, 0)} people`;
  if (n < 1e6) return `~${num(Math.round(n / 1000), 0)} thousand people`;
  return `~${num(n / 1e6, 1)} million people`;
}

function describeEn(key: LogisticsKey, r: Logistics["raw"]): string | null {
  switch (key) {
    case "access": {
      const m = r.access_min;
      if (m == null) return null;
      if (m < 120) return `~${num(m, 0)} min to the nearest city`;
      return m < 48 * 60 ? `~${num(m / 60, 1)} h to the nearest city` : `~${num(m / 1440, 1)} days to the nearest city`;
    }
    case "power": {
      if (r.plant_none) return "no registered power plant within 500 km";
      if (r.plant_km == null) return null;
      const p = r.plant;
      const what = [p ? FUEL[p.fuel] ?? p.fuel.toLowerCase() : null, p?.mw ? `${num(p.mw, 0)} MW` : null].filter(Boolean).join(", ");
      return `nearest power plant ${num(r.plant_km, 0)} km${what ? ` (${what})` : ""}`;
    }
    case "water":
      if (r.water_none) return "no permanent lake/river within 100 km";
      if (r.water_km == null) return null;
      return r.water_km < 1 ? "permanent lake/river inside the cell" : `nearest permanent lake/river ${num(r.water_km, 0)} km`;
    case "supply":
      return r.pop_region == null ? null : `${people(r.pop_region)} within 100 km`;
    case "altitude":
      return r.elev_m == null ? null : `mean elevation ${num(r.elev_m, 0)} m`;
  }
}

export function localizeLogistics(l: Logistics | null | undefined, lang: Lang): Logistics | null | undefined {
  if (!l || lang === "tr" || l.score == null) return l;
  const parts: Logistics["parts"] = {};
  for (const [k, p] of Object.entries(l.parts) as [LogisticsKey, { label: string; score: number; text: string }][]) {
    parts[k] = { ...p, label: LOGI_LABELS[k], text: describeEn(k, l.raw) ?? p.text };
  }
  const level = LEVELS[l.level ?? ""] ?? l.level;
  const good = Object.values(parts).filter((p) => p!.score >= 70);
  const weak = (Object.entries(parts) as [LogisticsKey, { score: number; text: string }][]).filter(([, p]) => p.score < 40);
  const missing = (Object.keys(LOGI_LABELS) as LogisticsKey[]).filter((k) => !(k in parts)).map((k) => LOGI_LABELS[k]);
  const out = [`Ease of setup ${num(l.score, 1)}/100 (${level?.toLowerCase()}).`];
  if (good.length) out.push(`Strengths: ${good.map((p) => p!.text).join("; ")}.`);
  if (weak.length) {
    out.push(`Weaknesses: ${weak.map(([, p]) => p.text).join("; ")}.`);
    out.push(...weak.map(([k]) => ADVICE[k]));
  }
  if (missing.length) out.push(`No data, not scored: ${missing.join(", ")}.`);
  return { ...l, level, parts, comment: out.join(" ") };
}

/** Parametre kaynağı (analog params > source). */
export function sourceEn(source: string, lang: Lang): string {
  if (lang === "tr") return source;
  if (source.startsWith("Hesap —")) return "Computed — cell latitude and Earth's obliquity 23.44° (core/geo.py)";
  return source.replace("MODIS aylık AOD", "MODIS monthly AOD");
}
