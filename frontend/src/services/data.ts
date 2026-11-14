import type { Body, Target } from "../types";

export interface TargetWithCoords extends Target {
  lat: number;
  lon: number;
}

interface TargetFeatureCollection {
  type: "FeatureCollection";
  features: { geometry: { coordinates: [number, number] }; properties: Target }[];
}

let cache: Promise<TargetWithCoords[]> | null = null;

// frontend/public/data/targets.geojson (pipeline/build.py üretir)
export function loadTargets(): Promise<TargetWithCoords[]> {
  cache ??= fetch(`${import.meta.env.BASE_URL}data/targets.geojson`)
    .then((r) => {
      if (!r.ok) throw new Error(`targets.geojson okunamadı (${r.status})`);
      return r.json() as Promise<TargetFeatureCollection>;
    })
    .then((fc) =>
      fc.features.map((f) => ({ ...f.properties, lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] })),
    );
  return cache;
}

export function targetsOf(all: TargetWithCoords[], body: Body) {
  return all.filter((t) => t.body === body);
}
