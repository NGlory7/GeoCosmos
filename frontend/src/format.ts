// Türkçe sayı ve koordinat biçimleri (ondalık virgül).
const nf = (digits: number) => new Intl.NumberFormat("tr-TR", { maximumFractionDigits: digits, minimumFractionDigits: 0 });

export function num(v: number | null | undefined, digits = 2): string {
  return v === null || v === undefined || Number.isNaN(v) ? "—" : nf(digits).format(v);
}

export function coord(lat: number, lon: number): string {
  const f = (v: number, pos: string, neg: string) => `${nf(2).format(Math.abs(v))}°${v >= 0 ? pos : neg}`;
  return `${f(lat, "K", "G")} · ${f(lon, "D", "B")}`;
}

export function pct(v: number, digits = 2): string {
  return `%${nf(digits).format(v)}`;
}

/** Config etiketindeki teknik notları atar: "Ortalama eğim (°, 500 m taban; config/...)" -> "Ortalama eğim (°)". */
export function shortLabel(label: string): string {
  const m = label.match(/^(.*?)\s*\((.*)\)\s*$/);
  if (!m) return label;
  const [, head, inner] = m;
  if (!/config\/|taban|pencere/.test(inner)) return label;
  return `${head} (${inner.split(/[,;]/)[0].trim()})`;
}
