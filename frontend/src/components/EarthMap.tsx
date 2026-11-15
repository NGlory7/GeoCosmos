import { useEffect } from "react";
import { CircleMarker, ImageOverlay, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import { num } from "../format";
import type { Analog } from "../types";

// NASA GIBS (Worldview'in karo servisi), Web Mercator: ısı haritası PNG'leri de Web Mercator.
const GIBS =
  "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg";

function FlyTo({ analog }: { analog: Analog | null }) {
  const map = useMap();
  useEffect(() => {
    if (analog) map.flyTo([analog.lat, analog.lon], Math.max(map.getZoom(), 5), { duration: 0.8 });
  }, [analog, map]);
  return null;
}

interface Props {
  analogs: Analog[];
  selected: Analog | null;
  onSelect: (a: Analog) => void;
  heatmap: { url: string; bounds: [[number, number], [number, number]] } | null;
  showHeatmap: boolean;
}

export default function EarthMap({ analogs, selected, onSelect, heatmap, showHeatmap }: Props) {
  return (
    <MapContainer
      center={[20, 0]}
      zoom={2}
      minZoom={2}
      maxZoom={10}
      worldCopyJump
      className="h-full w-full rounded-xl"
      style={{ background: "#0b1220" }}
    >
      <TileLayer url={GIBS} attribution="NASA GIBS / Worldview · Blue Marble" maxNativeZoom={8} />
      {heatmap && showHeatmap && <ImageOverlay url={heatmap.url} bounds={heatmap.bounds} opacity={0.85} />}
      {analogs.map((a) => {
        const on = selected?.id === a.id;
        const color = a.is_new ? "#22d3ee" : "#fbbf24";
        return (
          <CircleMarker
            key={a.id}
            center={[a.lat, a.lon]}
            radius={on ? 11 : 7}
            pathOptions={{ color: on ? "#fff" : color, weight: on ? 3 : 2, fillColor: color, fillOpacity: 0.8 }}
            eventHandlers={{ click: () => onSelect(a) }}
          >
            <Tooltip direction="top" offset={[0, -8]}>
              #{a.rank} {a.name} · {num(a.score_total, 1)}
            </Tooltip>
          </CircleMarker>
        );
      })}
      <FlyTo analog={selected} />
    </MapContainer>
  );
}
