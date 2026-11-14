import L from "leaflet";
import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { TargetWithCoords } from "../services/data";
import type { Body } from "../types";

// NASA Trek WMTS (eşdikdörtgen; z=0'da 2 x 1 karo = Leaflet EPSG:4326 ızgarası).
const TILES: Record<Body, { url: string; attribution: string; maxNativeZoom: number }> = {
  mars: {
    url: "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
    attribution: "NASA Mars Trek · MGS MOLA renkli gölgeli kabartma",
    maxNativeZoom: 7,
  },
  moon: {
    url: "https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
    attribution: "NASA Moon Trek · LRO WAC küresel mozaik",
    maxNativeZoom: 7,
  },
};

const WORLD: L.LatLngBoundsExpression = [
  [-90, -180],
  [90, 180],
];

function FlyTo({ target }: { target: TargetWithCoords | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo([Math.max(target.lat, -85), target.lon], Math.max(map.getZoom(), 3), { duration: 0.8 });
  }, [target, map]);
  return null;
}

interface Props {
  body: Body;
  targets: TargetWithCoords[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export default function PlanetMap({ body, targets, selected, onSelect }: Props) {
  const tiles = TILES[body];
  const current = targets.find((t) => t.id === selected) ?? null;
  return (
    <MapContainer
      crs={L.CRS.EPSG4326}
      center={[0, 0]}
      zoom={1}
      minZoom={1}
      maxZoom={8}
      maxBounds={WORLD}
      worldCopyJump={false}
      className="h-full w-full rounded-xl"
      style={{ background: "#05070b" }}
    >
      <TileLayer url={tiles.url} attribution={tiles.attribution} noWrap bounds={WORLD} maxNativeZoom={tiles.maxNativeZoom} />
      {targets.map((t) => {
        const on = t.id === selected;
        return (
          <CircleMarker
            key={t.id}
            center={[t.lat, t.lon]}
            radius={on ? 10 : 7}
            pathOptions={{ color: on ? "#fff" : "#fdba74", weight: on ? 3 : 2, fillColor: "#f97316", fillOpacity: 0.85 }}
            eventHandlers={{ click: () => onSelect(t.id) }}
          >
            <Tooltip direction="top" offset={[0, -8]}>
              {t.name}
            </Tooltip>
          </CircleMarker>
        );
      })}
      <FlyTo target={current} />
    </MapContainer>
  );
}
