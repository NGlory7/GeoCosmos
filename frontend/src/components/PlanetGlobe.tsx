import { useEffect, useRef, useState } from "react";
import type { TargetWithCoords } from "../services/data";
import type { Body } from "../types";
import { GLOBE_FRAG } from "./globeShader";
import Planet, { PLANET_FRACTION } from "./Planet";
import { VERT } from "./planetShader";

// NASA Trek eşdikdörtgen karoları (z0'da 2 x 1 karo, her seviyede 2 kat). CORS açık.
const TREK: Record<Body, { url: string; credit: string }> = {
  mars: {
    url: "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
    credit: "NASA Mars Trek · Viking MDIM 2.1 renkli mozaik",
  },
  moon: {
    url: "https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
    credit: "NASA Moon Trek · LRO WAC küresel mozaik",
  },
};
const TILE = 256;
const ZOOMS = [1, 2]; // önce hızlı (1024 px), sonra keskin (2048 px)
const LIGHT: [number, number, number] = [-0.35, 0.35, 0.87]; // sol-üst-önden: görünen yüz aydınlık

const DEG = Math.PI / 180;
type Vec3 = [number, number, number];

/** Gövde koordinatı: boylam 0 izleyiciye (+z), kuzey +y. */
function bodyVec(lat: number, lon: number): Vec3 {
  return [Math.cos(lat * DEG) * Math.sin(lon * DEG), Math.sin(lat * DEG), Math.cos(lat * DEG) * Math.cos(lon * DEG)];
}

/** Görüş merkezi (lat0, lon0) için gövde -> görüş dönüşümü: Rx(lat0) · Ry(-lon0). */
function viewMatrix(lat0: number, lon0: number) {
  const a = lat0 * DEG;
  const b = -lon0 * DEG;
  const apply = ([x, y, z]: Vec3): Vec3 => {
    const x1 = x * Math.cos(b) + z * Math.sin(b);
    const z1 = -x * Math.sin(b) + z * Math.cos(b);
    return [x1, y * Math.cos(a) - z1 * Math.sin(a), y * Math.sin(a) + z1 * Math.cos(a)];
  };
  const c0 = apply([1, 0, 0]);
  const c1 = apply([0, 1, 0]);
  const c2 = apply([0, 0, 1]);
  return {
    columnMajor: new Float32Array([...c0, ...c1, ...c2]),
    apply,
  };
}

function loadMosaic(body: Body, z: number): Promise<HTMLCanvasElement> {
  const cols = 2 ** (z + 1);
  const rows = 2 ** z;
  const canvas = document.createElement("canvas");
  canvas.width = cols * TILE;
  canvas.height = rows * TILE;
  const ctx = canvas.getContext("2d")!;
  const jobs: Promise<void>[] = [];
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      jobs.push(
        new Promise((resolve, reject) => {
          const img = new Image();
          img.crossOrigin = "anonymous";
          img.onload = () => {
            ctx.drawImage(img, x * TILE, y * TILE, TILE, TILE);
            resolve();
          };
          img.onerror = () => reject(new Error(`Trek karosu yüklenemedi: ${z}/${y}/${x}`));
          img.src = TREK[body].url.replace("{z}", String(z)).replace("{y}", String(y)).replace("{x}", String(x));
        }),
      );
    }
  }
  return Promise.all(jobs).then(() => canvas);
}

const wrap180 = (d: number) => ((((d + 180) % 360) + 360) % 360) - 180;

interface Props {
  body: Body;
  targets: TargetWithCoords[];
  selected: string | null;
  onSelect: (id: string | null) => void;
}

export default function PlanetGlobe({ body, targets, selected, onSelect }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const markerRefs = useRef(new Map<string, HTMLButtonElement>());
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  // Kare döngüsü güncel hedefleri buradan okur (dokular hedef değişince yeniden yüklenmesin)
  const targetsRef = useRef(targets);
  targetsRef.current = targets;

  // Görüş durumu: React render'ı dışında, her karede güncellenir
  const view = useRef({ lat: 15, lon: 0, goal: null as { lat: number; lon: number } | null, auto: true, dragging: false });

  // Başlangıçta hedeflerin ortalama boylamına bak
  useEffect(() => {
    if (!targets.length || selected) return;
    const v = targets.map((t) => bodyVec(0, t.lon)).reduce((s, p) => [s[0] + p[0], 0, s[2] + p[2]] as Vec3, [0, 0, 0] as Vec3);
    view.current.lon = Math.atan2(v[0], v[2]) / DEG;
  }, [targets]);

  // Seçilen hedefe dön; seçim kalkınca yavaş dönüşe geri geç
  useEffect(() => {
    const t = targets.find((x) => x.id === selected);
    view.current.goal = t ? { lat: t.lat, lon: t.lon } : null;
    view.current.auto = !t;
  }, [selected, targets]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;
    const gl = canvas.getContext("webgl2", { premultipliedAlpha: true, antialias: false });
    if (!gl) {
      setFailed(true);
      return;
    }

    const compile = (type: number, src: string) => {
      const sh = gl.createShader(type)!;
      gl.shaderSource(sh, src);
      gl.compileShader(sh);
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh) ?? "");
      return sh;
    };
    const prog = gl.createProgram()!;
    try {
      gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
      gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, GLOBE_FRAG));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog) ?? "");
    } catch (e) {
      console.error(e);
      setFailed(true);
      return;
    }
    gl.useProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "aPos");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    const uView = gl.getUniformLocation(prog, "uView");
    const uPx = gl.getUniformLocation(prog, "uPx");
    gl.uniform1i(gl.getUniformLocation(prog, "uKind"), body === "mars" ? 0 : 1);
    gl.uniform3fv(gl.getUniformLocation(prog, "uLight"), LIGHT);
    gl.uniform1i(gl.getUniformLocation(prog, "uTex"), 0);

    const tex = gl.createTexture();
    let alive = true;
    let hasTex = false;
    (async () => {
      for (const z of ZOOMS) {
        try {
          const mosaic = await loadMosaic(body, z);
          if (!alive) return;
          gl.bindTexture(gl.TEXTURE_2D, tex);
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, mosaic);
          gl.generateMipmap(gl.TEXTURE_2D);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
          // Kutuplara yakın doku boylam yönünde çok sıkışır: anizotropik filtre ışınsal izleri azaltır
          const aniso = gl.getExtension("EXT_texture_filter_anisotropic");
          if (aniso) {
            const max = gl.getParameter(aniso.MAX_TEXTURE_MAX_ANISOTROPY_EXT) as number;
            gl.texParameterf(gl.TEXTURE_2D, aniso.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(8, max));
          }
          hasTex = true;
          setReady(true);
        } catch (e) {
          console.error(e);
          if (!hasTex) setFailed(true);
          return;
        }
      }
    })();

    let size = 0;
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      size = canvas.clientWidth;
      const px = Math.min(Math.round(size * dpr), 1600);
      canvas.width = px;
      canvas.height = px;
      gl.viewport(0, 0, px, px);
      gl.uniform1f(uPx, 2 / px);
    };
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();

    // Sürükleyerek çevirme
    let last: { x: number; y: number } | null = null;
    const down = (e: PointerEvent) => {
      if ((e.target as HTMLElement).closest("button")) return;
      last = { x: e.clientX, y: e.clientY };
      view.current.dragging = true;
      view.current.auto = false;
      view.current.goal = null;
      wrap.setPointerCapture(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (!last) return;
      const r = (size * PLANET_FRACTION) / 2;
      const v = view.current;
      v.lon = wrap180(v.lon - ((e.clientX - last.x) / r) / DEG);
      v.lat = Math.max(-89.9, Math.min(89.9, v.lat + ((e.clientY - last.y) / r) / DEG));
      last = { x: e.clientX, y: e.clientY };
    };
    const up = () => {
      last = null;
      view.current.dragging = false;
    };
    wrap.addEventListener("pointerdown", down);
    wrap.addEventListener("pointermove", move);
    wrap.addEventListener("pointerup", up);
    wrap.addEventListener("pointercancel", up);

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let prev = performance.now();
    let raf = 0;
    const frame = (now: number) => {
      const dt = Math.min((now - prev) / 1000, 0.1);
      prev = now;
      const v = view.current;
      if (v.goal) {
        const k = reduced ? 1 : 1 - Math.exp(-dt * 4);
        v.lon = wrap180(v.lon + wrap180(v.goal.lon - v.lon) * k);
        v.lat += (v.goal.lat - v.lat) * k;
      } else if (v.auto && !v.dragging && !reduced) {
        v.lon = wrap180(v.lon + dt * 4); // 4°/sn
        v.lat += (15 - v.lat) * (1 - Math.exp(-dt * 0.8));
      }

      const m = viewMatrix(v.lat, v.lon);
      if (hasTex) {
        gl.uniformMatrix3fv(uView, false, m.columnMajor);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      }

      // İşaretler: aynı matrisle ekrana; arka yüzdekiler gizli
      const r = (size * PLANET_FRACTION) / 2;
      for (const t of targetsRef.current) {
        const el = markerRefs.current.get(t.id);
        if (!el) continue;
        const [x, y, z] = m.apply(bodyVec(t.lat, t.lon));
        const vis = Math.max(0, Math.min(1, (z - 0.02) / 0.15));
        el.style.transform = `translate(${size / 2 + x * r}px, ${size / 2 - y * r}px)`;
        el.style.opacity = String(vis);
        el.style.pointerEvents = vis > 0.3 ? "auto" : "none";
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    return () => {
      alive = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
      wrap.removeEventListener("pointerdown", down);
      wrap.removeEventListener("pointermove", move);
      wrap.removeEventListener("pointerup", up);
      wrap.removeEventListener("pointercancel", up);
      gl.deleteTexture(tex);
      gl.deleteBuffer(buf);
      gl.deleteProgram(prog);
    };
  }, [body]);

  return (
    <figure className="w-full">
      <div ref={wrapRef} className="relative aspect-square w-full cursor-grab touch-none select-none active:cursor-grabbing">
        {/* Doku yüklenene kadar (ya da yüklenemezse) prosedürel gezegen */}
        <Planet
          body={body}
          className={`absolute inset-0 h-full w-full transition-opacity duration-700 ${ready && !failed ? "opacity-0" : "opacity-100"}`}
        />
        <canvas
          ref={canvasRef}
          className={`absolute inset-0 h-full w-full transition-opacity duration-700 ${ready && !failed ? "opacity-100" : "opacity-0"}`}
          aria-hidden
        />
        {/* İşaretler sadece gerçek doku üzerinde: prosedürel yedekte konumları anlamsız olur */}
        {ready && !failed && targets.map((t) => {
          const on = t.id === selected;
          return (
            <button
              key={t.id}
              ref={(el) => {
                if (el) markerRefs.current.set(t.id, el);
                else markerRefs.current.delete(t.id);
              }}
              onClick={() => onSelect(on ? null : t.id)}
              aria-label={t.name}
              aria-pressed={on}
              className="group absolute left-0 top-0 opacity-0 will-change-transform"
            >
              <span
                className={`absolute -translate-x-1/2 -translate-y-1/2 rounded-full border-2 transition-all ${
                  on ? "size-4 border-white bg-cyan-400 shadow-[0_0_14px_rgba(34,211,238,0.9)]" : "size-3 border-white/80 bg-orange-400/90 group-hover:size-4"
                }`}
              />
              <span
                className={`absolute left-3 top-0 -translate-y-1/2 whitespace-nowrap rounded-md bg-black/65 px-2 py-0.5 font-mono text-[11px] text-white backdrop-blur transition-opacity ${
                  on ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                }`}
              >
                {t.name}
              </span>
            </button>
          );
        })}
      </div>
      <figcaption className="mt-2 text-center font-mono text-[10px] tracking-wider text-slate-600">
        Sürükleyerek çevir · {TREK[body].credit}
      </figcaption>
    </figure>
  );
}
