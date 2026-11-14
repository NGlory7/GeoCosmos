import { useEffect, useRef } from "react";

// Sabit yıldız alanı: boyut değişince yeniden çizilir, animasyon yok (GPU gezegenlere kalsın).
export default function Starfield() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Her çizimde aynı gökyüzü: sabit tohumlu rastgele sayı üreteci
    const rng = (seed: number) => () => {
      seed = (seed * 1664525 + 1013904223) % 4294967296;
      return seed / 4294967296;
    };

    const draw = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const rand = rng(7);
      const count = Math.round((w * h) / 2200);
      for (let i = 0; i < count; i++) {
        const x = rand() * w;
        const y = rand() * h;
        const m = Math.pow(rand(), 6); // çoğu sönük, azı parlak
        const r = 0.35 + m * 1.3;
        const alpha = 0.25 + m * 0.75;
        const tint = rand();
        const color = tint < 0.15 ? "200,215,255" : tint > 0.9 ? "255,228,200" : "235,238,245";
        ctx.fillStyle = `rgba(${color},${alpha})`;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    const ro = new ResizeObserver(draw);
    ro.observe(canvas);
    return () => ro.disconnect();
  }, []);

  return <canvas ref={ref} className="pointer-events-none fixed inset-0 h-full w-full" aria-hidden />;
}
