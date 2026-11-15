import type { Body } from "./types";

export interface BodyMeta {
  id: Body;
  name: string;
  nameEn: string;
  tagline: string;
  dot: string; // Tailwind renk sınıfı
  accent: string;
}

export const BODIES: Record<Body, BodyMeta> = {
  mars: {
    id: "mars",
    name: "MARS",
    nameEn: "MARS",
    tagline: "CRIMSON REGOLITH",
    dot: "bg-orange-300 shadow-orange-300/80",
    accent: "text-orange-200/70",
  },
  moon: {
    id: "moon",
    name: "AY (MOON)",
    nameEn: "MOON",
    tagline: "LUNAR SILICATE",
    dot: "bg-sky-200 shadow-sky-200/80",
    accent: "text-sky-200/70",
  },
};
