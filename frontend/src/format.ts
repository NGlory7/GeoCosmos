// Sayı ve koordinat biçimleri, arayüz diline göre (tr: ondalık virgül, %5,5; en: ondalık nokta, 5.5%).
import { getLang } from "./i18n";

const locale = () => (getLang() === "en" ? "en-US" : "tr-TR");
const nf = (digits: number) => new Intl.NumberFormat(locale(), { maximumFractionDigits: digits, minimumFractionDigits: 0 });

export function num(v: number | null | undefined, digits = 2): string {
  return v === null || v === undefined || Number.isNaN(v) ? "—" : nf(digits).format(v);
}

/** Tam sayı, binlik ayraçlı (tr 189.878 / en 189,878). */
export function int(v: number): string {
  return v.toLocaleString(locale());
}

export function coord(lat: number, lon: number): string {
  const en = getLang() === "en";
  const f = (v: number, pos: string, neg: string) => `${nf(2).format(Math.abs(v))}°${v >= 0 ? pos : neg}`;
  return en ? `${f(lat, "N", "S")} · ${f(lon, "E", "W")}` : `${f(lat, "K", "G")} · ${f(lon, "D", "B")}`;
}

export function pct(v: number, digits = 2): string {
  return getLang() === "en" ? `${nf(digits).format(v)}%` : `%${nf(digits).format(v)}`;
}

/** Config etiketindeki teknik notları atar: "Ortalama eğim (°, 500 m taban; config/...)" -> "Ortalama eğim (°)". */
export function shortLabel(label: string): string {
  const m = label.match(/^(.*?)\s*\((.*)\)\s*$/);
  if (!m) return label;
  const [, head, inner] = m;
  if (!/config\/|taban|pencere|baseline|window/.test(inner)) return label;
  return `${head} (${inner.split(/[,;]/)[0].trim()})`;
}
