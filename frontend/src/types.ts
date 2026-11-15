// Veri sözleşmesinin TypeScript hâli. Python karşılığı: core/schemas.py
// Değişiklik gerekirse önce ARCHITECTURE.md > Veri sözleşmesi güncellenir.

export type Body = "moon" | "mars";
export type TestId = "rover" | "ice_drilling" | "lava_tube" | "dust" | "biosignature_arid" | "biosignature_carbonate" | "base_site";
export type BreakdownKey = "gravity" | "atmosphere" | "radiation" | "liquid_water" | "biology" | "temperature";
// Operasyon bilgisi puan değil: Analog.ops_tags (kartta ✓/✗).
export type ScoreKey = "topography" | "geology" | "climate";

export interface SourcedValue {
  value: number;
  source: string;
}

// targets.geojson -> feature.properties (koordinat geometry içinde)
export interface Target {
  id: string;
  body: Body;
  name: string;
  why: string;
  params: Record<string, SourcedValue>;
}

export interface AnalogParam {
  key: string;
  earth: number | null;
  target: number;
  source: string;
  match: boolean;
}

export interface PastTest {
  title: string;
  url: string;
}

// null: bu test amacında o boyuta ağırlık verilmemiş
export type Scores = Record<ScoreKey, number | null>;

// analogs/<hedef>_<test>.geojson -> feature.properties
export interface Analog {
  id: string;
  name: string;
  // Kare merkezinin yer adı (OpenStreetMap, pipeline/placenames.py); önbellekte yoksa null/eksik
  place?: { tr: string; en: string } | null;
  is_new: boolean;
  target_id: string;
  test_id: TestId | "custom"; // "custom": /scenario sonucu
  lat: number; // Dünya'daki kare merkezi; /scenario yanıtında pin bundan çizilir
  lon: number;
  rank: number;
  score_total: number;
  scores: Scores;
  params: AnalogParam[];
  ops_tags: Record<string, boolean>; // road_access, remote
  breakdown: BreakdownKey[];
  past_tests: PastTest[];
  ai_comment: string;
  ai_comment_en?: string; // Gemini çevirisi; yoksa İngilizce arayüzde Türkçe yorum gösterilir
}

// logistics.json (pipeline/logistics.py -> core/logistics.py): kurulum kolaylığı, benzerliğe katılmaz
export type LogisticsKey = "access" | "power" | "water" | "supply" | "altitude";
export interface LogisticsRaw {
  lat: number;
  lon: number;
  access_min: number | null;
  elev_m: number | null;
  pop_region: number | null;
  water_km: number | null;
  water_none: boolean;
  plant_km: number | null;
  plant_none: boolean;
  plant: { name: string; fuel: string; mw: number; country: string } | null;
  plant_mw_region: number | null;
}
export interface Logistics {
  raw: LogisticsRaw;
  score: number | null;
  level: string | null;
  parts: Partial<Record<LogisticsKey, { label: string; score: number; text: string }>>;
  comment: string;
}
export interface LogisticsFile {
  labels: Record<LogisticsKey, string>;
  sources: Record<string, string>;
  note: string;
  cells: Record<string, Logistics>;
}

// meta.json (pipeline/build.py > write_meta): arayüz etiketleri, tek kaynak config/
export interface TestMeta {
  id: TestId;
  label: string;
  weights: Record<string, number>;
  breakdown: BreakdownKey[];
  at_least: string[];
  rationale: string;
}

export interface Meta {
  score_keys: ScoreKey[];
  score_labels: Record<ScoreKey, string>;
  tests: TestMeta[];
  parameters: Record<string, { label: string; dimension: ScoreKey; tolerance: number; earth_source: string }>;
  breakdown_always: BreakdownKey[];
  breakdown_labels: Record<BreakdownKey, string>;
  breakdown_notes: Record<Body, Record<BreakdownKey, string>>;
  ops_labels: Record<string, string>;
  grid_km: number;
}

// analogs/index.json
export interface AnalogIndexEntry {
  target_id: string;
  test_id: TestId;
  file: string | null; // null: hedefte bu testin değeri yok, bkz. reason
  count: number;
  new_count?: number;
  params_used?: string[];
  params_total?: number;
  reason?: string;
}

// validation.json
export interface ValidationAnalog {
  id: string;
  name: string;
  test_id: TestId;
  split: "tune" | "holdout" | "report";
  targets: string[];
  status: "ok" | "missing_cell" | "no_target_values";
  target_id?: string;
  score_total?: number;
  rank?: number;
  percentile?: number;
  hit?: boolean;
  cell_id?: string;
  note: string;
  past_tests: PastTest[];
}

export interface ValidationResult {
  hits: number;
  min_hits: number;
  holdout_total: number;
  top_percent: number;
  passed: boolean;
  denominator: number;
  analogs: ValidationAnalog[];
}

// heatmaps/index.json (PNG'ler Web Mercator; L.imageOverlay(url, bounds))
export interface HeatmapIndex {
  crs: "EPSG:3857";
  bounds: [[number, number], [number, number]];
  value: "score_total";
  vmin: number;
  vmax: number;
  colormap: string;
  files: { target_id: string; test_id: TestId; file: string }[];
}

export interface ScenarioRequest {
  text: string;
  target_id: string;
}

export interface ScenarioResponse {
  // gemini: canlı çeviri · cache: önbellek · keywords: Gemini yok, anahtar kelimeyle hazır testler
  method: "gemini" | "cache" | "keywords";
  matched_tests: TestId[]; // sadece keywords
  weights: Record<string, number>;
  unsupported: string[];
  analogs: Analog[];
}
