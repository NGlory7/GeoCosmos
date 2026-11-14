import { useEffect, useRef, useState } from "react";
import type { Body } from "../types";
import { FRAG, VERT } from "./planetShader";

// Tüm gezegenler aynı güneşi görür: sağ-üst-önden.
const SUN: [number, number, number] = [0.55, 0.3, 0.78];

// Kanvasın kenarında atmosfer parıltısına yer bırakılır; gezegen çapı = kanvas × PLANET_FRACTION.
export const PLANET_FRACTION = 0.82;

function compile(gl: WebGL2RenderingContext, type: number, src: string) {
  const sh = gl.createShader(type)!;
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(sh) ?? "shader derlenemedi");
  }
  return sh;
}

interface Props {
  body: Body;
  className?: string;
}

export default function Planet({ body, className }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl2", { premultipliedAlpha: true, antialias: false });
    if (!gl) {
      setFailed(true);
      return;
    }

    let prog: WebGLProgram;
    try {
      prog = gl.createProgram()!;
      gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VERT));
      gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, FRAG));
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

    const uTime = gl.getUniformLocation(prog, "uTime");
    const uPx = gl.getUniformLocation(prog, "uPx");
    gl.uniform1i(gl.getUniformLocation(prog, "uKind"), body === "mars" ? 0 : 1);
    gl.uniform3fv(gl.getUniformLocation(prog, "uLight"), SUN);

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const px = Math.min(Math.round(canvas.clientWidth * dpr), 1600);
      if (canvas.width !== px) {
        canvas.width = px;
        canvas.height = px;
      }
      gl.viewport(0, 0, px, px);
      gl.uniform1f(uPx, 2 / px);
    };
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const t0 = performance.now();
    let raf = 0;
    const draw = () => {
      gl.uniform1f(uTime, reduced ? 0 : (performance.now() - t0) / 1000);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      if (!reduced) raf = requestAnimationFrame(draw);
    };
    draw();
    // Hareket kapalıysa tek kare çizilir; boyut değişince yeniden çizilir.
    const redraw = reduced ? new ResizeObserver(() => draw()) : null;
    redraw?.observe(canvas);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      redraw?.disconnect();
      gl.deleteBuffer(buf);
      gl.deleteProgram(prog);
    };
  }, [body]);

  if (failed) {
    // WebGL yoksa basit yedek
    const bg =
      body === "mars"
        ? "radial-gradient(circle at 65% 38%, #d9895a, #a4502c 45%, #3a1a10 80%)"
        : "radial-gradient(circle at 65% 38%, #d8d6d2, #8d8b88 50%, #262626 85%)";
    return (
      <div className={className} aria-hidden>
        <div className="mx-auto rounded-full" style={{ width: `${PLANET_FRACTION * 100}%`, aspectRatio: "1", marginTop: "9%", background: bg }} />
      </div>
    );
  }

  return <canvas ref={ref} className={className} aria-hidden />;
}
