// Veri sözleşmesinin TypeScript hâli. Python karşılığı: core/schemas.py
// Değişiklik gerekirse önce ARCHITECTURE.md > Veri sözleşmesi güncellenir.

export type Body = "moon" | "mars";
export type TestId = "rover" | "ice_drilling" | "lava_tube" | "dust" | "biosignature";
export type BreakdownKey = "gravity" | "atmosphere" | "radiation" | "liquid_water" | "biology";
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
}

export interface ScenarioRequest {
  text: string;
  target_id: string;
}

export interface ScenarioResponse {
  weights: Record<string, number>;
  unsupported: string[];
  analogs: Analog[];
}
