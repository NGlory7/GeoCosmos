import type {
  Analog,
  AnalogIndexEntry,
  Body,
  HeatmapIndex,
  LogisticsFile,
  Meta,
  ScenarioRequest,
  ScenarioResponse,
  Target,
  ValidationResult,
} from "../types";

// Tüm dosyaları pipeline/build.py (make data) üretir: frontend/public/data/
const DATA = `${import.meta.env.BASE_URL}data/`;
// Canlı API sadece /scenario için (ARCHITECTURE.md > API). Yoksa arayüzün geri kalanı çalışır.
// Boş string: bu yayında API yok (ör. GitHub Pages) -> senaryo kutusu "çevrimdışı" der.
export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface TargetWithCoords extends Target {
  lat: number;
  lon: number;
}

interface FeatureCollection<P> {
  type: "FeatureCollection";
  features: { geometry: { coordinates: [number, number] }; properties: P }[];
}

/** JSON dosyası; henüz üretilmediyse null (404 ya da geliştirme sunucusunun HTML yedeği). */
async function getJson<T>(path: string): Promise<T | null> {
  const r = await fetch(DATA + path);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`${path} okunamadı (${r.status})`);
  if ((r.headers.get("content-type") ?? "").includes("text/html")) return null;
  return (await r.json()) as T;
}

const cache = new Map<string, Promise<unknown>>();
function cached<T>(key: string, load: () => Promise<T>): Promise<T> {
  if (!cache.has(key)) cache.set(key, load());
  return cache.get(key) as Promise<T>;
}

export function loadTargets(): Promise<TargetWithCoords[]> {
  return cached("targets", async () => {
    const fc = await getJson<FeatureCollection<Target>>("targets.geojson");
    if (!fc) throw new Error("targets.geojson yok: make data çalıştırın");
    return fc.features.map((f) => ({ ...f.properties, lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] }));
  });
}

export function targetsOf(all: TargetWithCoords[], body: Body) {
  return all.filter((t) => t.body === body);
}

export function loadMeta(): Promise<Meta> {
  return cached("meta", async () => {
    const m = await getJson<Meta>("meta.json");
    if (!m) throw new Error("meta.json yok: make data çalıştırın");
    return m;
  });
}

/** null: Dünya verisi (grid.parquet) henüz işlenmedi. */
export function loadAnalogIndex(): Promise<AnalogIndexEntry[] | null> {
  return cached("analog-index", () => getJson<AnalogIndexEntry[]>("analogs/index.json"));
}

export function loadAnalogs(file: string): Promise<Analog[]> {
  return cached(`analogs/${file}`, async () => {
    const fc = await getJson<FeatureCollection<Analog>>(`analogs/${file}`);
    return fc ? fc.features.map((f) => f.properties) : [];
  });
}

export function loadHeatmapIndex(): Promise<HeatmapIndex | null> {
  return cached("heatmap-index", () => getJson<HeatmapIndex>("heatmaps/index.json"));
}

export function heatmapUrl(file: string) {
  return `${DATA}heatmaps/${file}`;
}

/** null: logistics.json henüz üretilmedi (pipeline/logistics.py). */
export function loadLogistics(): Promise<LogisticsFile | null> {
  return cached("logistics", () => getJson<LogisticsFile>("logistics.json"));
}

export function loadValidation(): Promise<ValidationResult | null> {
  return cached("validation", () => getJson<ValidationResult>("validation.json"));
}

export class ScenarioError extends Error {
  constructor(
    message: string,
    public offline = false,
  ) {
    super(message);
  }
}

export async function postScenario(req: ScenarioRequest): Promise<ScenarioResponse> {
  if (!API_URL) throw new ScenarioError("Bu yayında senaryo servisi yok; yerelde make api ile çalışır.", true);
  let r: Response;
  try {
    r = await fetch(`${API_URL}/scenario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  } catch {
    throw new ScenarioError("Senaryo servisi şu an çevrimdışı.", true);
  }
  if (!r.ok) {
    const detail = await r.json().then((j: { detail?: string }) => j.detail).catch(() => undefined);
    throw new ScenarioError(detail ?? `Senaryo servisi hata verdi (${r.status}).`, r.status >= 500);
  }
  return (await r.json()) as ScenarioResponse;
}
