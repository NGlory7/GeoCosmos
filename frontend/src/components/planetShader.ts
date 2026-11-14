// Gezegen shader'ı: dokusuz, tamamen prosedürel (dosya indirmeye gerek yok).
// Küre analitik çizilir; arazi 3B gürültüden gelir, dikiş (seam) olmaz.
// Mars: albedo bölgeleri, kanyon, aşınmış kraterler, kutup başlıkları, ince atmosfer.
// Ay: maria / yayla ayrımı, çok ölçekli keskin kraterler, ışınlı genç krater,
//     Lommel-Seeliger ışığı (Ay'ın kenarda kararmayan parlaklığı).

export const VERT = /* glsl */ `#version 300 es
in vec2 aPos;
out vec2 vUv;
void main() {
  vUv = aPos;
  gl_Position = vec4(aPos, 0.0, 1.0);
}`;

export const FRAG = /* glsl */ `#version 300 es
precision highp float;

in vec2 vUv;
out vec4 outColor;

uniform float uTime;
uniform int uKind;     // 0 = Mars, 1 = Ay
uniform vec3 uLight;   // güneş yönü (görüş uzayı)
uniform float uPx;     // bir pikselin uv karşılığı

const float PR = 0.82; // kanvas içinde gezegen yarıçapı (kalanı atmosfer parıltısı)

// --- Ashima 3B simplex gürültü ---
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 1.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute(permute(permute(
            i.z + vec4(0.0, i1.z, i2.z, 1.0))
          + i.y + vec4(0.0, i1.y, i2.y, 1.0))
          + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

float fbm(vec3 p, int oct) {
  float a = 0.5, s = 0.0;
  for (int i = 0; i < 6; i++) {
    if (i >= oct) break;
    s += a * snoise(p);
    p = p * 2.03 + vec3(1.7, 9.2, 3.1);
    a *= 0.5;
  }
  return s;
}

vec3 hash3(vec3 p) {
  p = vec3(dot(p, vec3(127.1, 311.7, 74.7)),
           dot(p, vec3(269.5, 183.3, 246.1)),
           dot(p, vec3(113.5, 271.9, 124.6)));
  return fract(sin(p) * 43758.5453123);
}

// Krater alanı: x = yükseklik, y = tazelik (genç kraterin parlak ejekta'sı)
// density: hücrede krater olma olasılığı; erosion: 0 keskin .. 1 aşınmış
vec2 craters(vec3 p, float density, float erosion) {
  vec3 c = floor(p);
  vec3 f = p - c;
  float h = 0.0;
  float fresh = 0.0;
  for (int i = -1; i <= 1; i++)
  for (int j = -1; j <= 1; j++)
  for (int k = -1; k <= 1; k++) {
    vec3 g = vec3(float(i), float(j), float(k));
    vec3 r = hash3(c + g);
    if (r.z > density) continue;
    vec3 o = g + 0.2 + 0.6 * hash3(c + g + 17.31);
    float rad = 0.16 + 0.34 * r.x * r.x;
    float d = length(o - f) / rad;
    if (d > 2.4) continue;
    float age = r.y;                              // 1 = genç
    float sharp = mix(1.0 - erosion, 1.0, age * age);
    float bowl = d < 1.0 ? max(d * d - 1.0, -0.78) : 0.0;
    float rim = exp(-pow((d - 1.0) / (0.16 + 0.2 * erosion), 2.0));
    float ej = d > 1.0 ? exp(-(d - 1.0) * 3.2) * 0.12 : 0.0;
    h += (bowl * 0.95 + rim * 0.32 + ej) * rad * sharp;
    fresh = max(fresh, step(0.82, age) * exp(-max(d - 0.9, 0.0) * 2.2));
  }
  return vec2(h, fresh);
}

mat3 rotY(float a) { float c = cos(a), s = sin(a); return mat3(c, 0.0, -s, 0.0, 1.0, 0.0, s, 0.0, c); }
mat3 rotZ(float a) { float c = cos(a), s = sin(a); return mat3(c, s, 0.0, -s, c, 0.0, 0.0, 0.0, 1.0); }

vec3 toLinear(vec3 c) { return pow(c, vec3(2.2)); }

void main() {
  vec2 p = vUv;
  float d = length(p) / PR;

  // Küre normali (dışarıdaki pikseller kenara kenetlenir: türevler tanımlı kalsın)
  vec2 q = p / PR;
  if (d > 0.999) q *= 0.999 / d;
  vec3 n = vec3(q, sqrt(max(0.0, 1.0 - dot(q, q))));

  vec3 L = normalize(uLight);
  bool mars = uKind == 0;
  float tilt = mars ? 0.44 : 0.12;
  float spin = uTime * (mars ? 0.03 : 0.02) + (mars ? 2.4 : 0.6);
  vec3 s = rotY(spin) * rotZ(-tilt) * n;

  vec3 albedo;
  float h;

  if (mars) {
    // Büyük ölçekli albedo: parlak toz ovaları + koyu bazaltik bölgeler (Syrtis benzeri)
    float big = fbm(s * 1.3 + 3.0, 5);
    float darkM = smoothstep(0.04, 0.34, big + 0.14 * fbm(s * 5.0, 3));
    float mid = fbm(s * 3.2 + 7.0, 4);
    vec3 bright = vec3(0.80, 0.50, 0.30);
    vec3 ochre = vec3(0.68, 0.38, 0.22);
    vec3 dark = vec3(0.34, 0.22, 0.16);
    albedo = mix(bright, ochre, smoothstep(-0.35, 0.45, mid));
    albedo = mix(albedo, dark, darkM * 0.82);
    albedo *= 0.9 + 0.2 * fbm(s * 18.0, 3);

    // Uzaktan Mars'ta kraterler değil albedo öne çıkar: seyrek, aşınmış kraterler
    vec2 c1 = craters(s * 4.5, 0.22, 0.8);
    vec2 c2 = craters(s * 12.0, 0.22, 0.7);
    h = c1.x / 4.5 + c2.x / 12.0 * 0.6;
    h += 0.01 * fbm(s * 6.0, 5);

    // Hafif koyu çizgiler ve rüzgar izleri (krater arkası toz gölgeleri yerine yumuşak bantlar)
    float streak = fbm(vec3(s.x * 3.0, s.y * 14.0, s.z * 3.0) + 4.0, 3);
    albedo *= 1.0 - 0.06 * smoothstep(0.1, 0.5, streak);

    // Kutup başlıkları (kuzey büyük, güney küçük)
    float capN = smoothstep(0.86, 0.9, s.y + 0.04 * fbm(s * 9.0, 3));
    float capS = smoothstep(0.93, 0.955, -s.y + 0.03 * fbm(s * 9.0 + 5.0, 3));
    float cap = max(capN, capS);
    albedo = mix(albedo, vec3(0.95, 0.93, 0.90), cap);
    h *= 1.0 - 0.75 * cap;
    h *= 0.55;
  } else {
    // Maria (koyu bazalt ovaları) bir yarımkürede yoğun
    // Maria: büyük, yuvarlak hatlı koyu ovalar (eski çarpma havzalarını dolduran bazalt)
    vec3 mq = s * 0.75 + vec3(5.0, 1.0, 2.0);
    mq += 0.18 * vec3(snoise(s * 2.2), snoise(s * 2.2 + 9.0), snoise(s * 2.2 + 4.0)); // kıvrımlı kıyılar
    float m = fbm(mq, 3) + 0.42 * dot(s, normalize(vec3(0.15, 0.3, 1.0))) - 0.08;
    float mare = smoothstep(0.08, 0.26, m);
    vec3 high = vec3(0.72, 0.71, 0.69);
    vec3 mareC = vec3(0.36, 0.36, 0.37);
    albedo = mix(high, mareC, mare);
    albedo *= 1.0 - 0.12 * mare * smoothstep(-0.2, 0.4, fbm(s * 3.0 + 2.0, 3)); // maria içi ton farkı
    albedo *= 0.9 + 0.2 * fbm(s * 4.0, 4);
    albedo *= 0.96 + 0.08 * fbm(s * 40.0, 2);

    // Kraterler: yaylalarda yoğun, maria'da seyrek; uzaktan bakıldığı için kabartma ölçülü
    float cm = 1.0 - 0.85 * mare;
    vec2 c1 = craters(s * 3.0, 0.28, 0.3);
    vec2 c2 = craters(s * 8.0, 0.4, 0.3);
    vec2 c3 = craters(s * 22.0, 0.5, 0.3);
    h = (c1.x / 3.0 * 0.8 + c2.x / 8.0 * 0.8 + c3.x / 22.0 * 0.6) * cm;
    h += 0.006 * fbm(s * 9.0, 4) * cm;
    albedo += 0.12 * max(c2.y, c3.y) * cm;

    // Işınlı genç krater (Tycho benzeri)
    vec3 tc = normalize(vec3(-0.25, -0.55, 0.8));
    float ang = acos(clamp(dot(s, tc), -1.0, 1.0));
    vec3 t1 = normalize(cross(tc, vec3(0.0, 1.0, 0.0)));
    vec3 t2 = cross(tc, t1);
    float th = atan(dot(s, t2), dot(s, t1));
    float ray = smoothstep(0.35, 0.9, snoise(vec3(cos(th), sin(th), 0.0) * 7.0 + ang * 2.0));
    ray *= exp(-ang * 2.0) * smoothstep(0.03, 0.06, ang);
    albedo += ray * 0.2;
    float td = ang / 0.035;
    h += (td < 1.0 ? (td * td - 1.0) * 0.012 : 0.0) + exp(-pow((td - 1.0) / 0.25, 2.0)) * 0.004;
    albedo += 0.25 * exp(-td * 0.8);
    h *= 0.9;
  }

  // Ekran-uzayı bump mapping (Mikkelsen): yükseklikten normal
  vec3 dpdx = dFdx(n), dpdy = dFdy(n);
  float dhx = dFdx(h), dhy = dFdy(h);
  vec3 r1 = cross(dpdy, n), r2 = cross(n, dpdx);
  float det = dot(dpdx, r1);
  vec3 grad = sign(det) * (dhx * r1 + dhy * r2);
  vec3 N = normalize(abs(det) * n - grad);

  float mu0 = dot(N, L);
  float muG = dot(n, L);
  float mu = max(n.z, 0.05);
  vec3 lin = toLinear(albedo);
  vec3 col;

  if (mars) {
    float diff = clamp((mu0 + 0.04) / 1.04, 0.0, 1.0);
    diff = mix(diff, pow(diff, 0.75), 0.35);
    diff *= smoothstep(-0.12, 0.08, muG);              // yumuşak gün batımı
    col = lin * diff * 1.15;
    // İnce atmosfer: kenarda turuncu pus
    float haze = pow(1.0 - n.z, 2.6);
    float lit = smoothstep(-0.25, 0.5, muG);
    col = mix(col, toLinear(vec3(0.92, 0.6, 0.42)) * lit, haze * 0.5);
  } else {
    float m0 = max(mu0, 0.0);
    float ls = min(2.0 * m0 / (m0 + mu), 1.35);         // Lommel-Seeliger
    float bright = mix(m0, ls * 0.62, 0.72);
    bright *= smoothstep(-0.02, 0.03, muG);            // havasız: keskin terminatör
    col = lin * bright * 1.35;
  }
  col += lin * 0.006;                                   // çok hafif ortam ışığı

  // Kenar yumuşatma + Mars atmosfer parıltısı
  float a = 1.0 - smoothstep(1.0 - 1.5 * uPx / PR, 1.0, d);
  float ga = 0.0;
  if (mars && d > 0.98) {
    vec3 dir = normalize(vec3(p, 0.0));
    float side = smoothstep(-0.4, 0.7, dot(dir, L));
    ga = exp(-(d - 1.0) * 26.0) * 0.55 * side;
  }

  // Kanvas premultiplied alpha bekler: renk <= alfa
  vec3 surf = clamp(pow(max(col, 0.0), vec3(1.0 / 2.2)), 0.0, 1.0);
  vec3 glowC = vec3(1.0, 0.62, 0.42);
  float outA = a + ga * (1.0 - a);
  outColor = vec4(surf * a + glowC * ga * (1.0 - a), outA);
}`;
