// Dokulu küre: NASA Trek eşdikdörtgen mozaiği (Mars: Viking MDIM 2.1 renkli, Ay: LRO WAC)
// analitik bir küreye sarılır. Yön uView matrisinden gelir (JS hedefe döndürür);
// aynı matris hedef işaretlerini de ekrana yansıtır, bu yüzden ikisi hep örtüşür.

export const GLOBE_FRAG = /* glsl */ `#version 300 es
precision highp float;

in vec2 vUv;
out vec4 outColor;

uniform sampler2D uTex;
uniform mat3 uView;    // gövde -> görüş
uniform vec3 uLight;
uniform int uKind;     // 0 = Mars, 1 = Ay
uniform float uPx;

const float PR = 0.82;
const float PI = 3.141592653589793;

void main() {
  vec2 p = vUv;
  float d = length(p) / PR;
  vec2 q = p / PR;
  if (d > 0.999) q *= 0.999 / d;
  vec3 n = vec3(q, sqrt(max(0.0, 1.0 - dot(q, q))));

  // Görüş -> gövde (enlem/boylam)
  vec3 s = transpose(uView) * n;
  float lat = asin(clamp(s.y, -1.0, 1.0));
  float lon = atan(s.x, s.z);

  // Boylam dikişinde mipmap hatası olmasın (Tarini): iki u'dan türevi küçük olanı
  float u1 = fract(lon / (2.0 * PI) + 0.5);
  float u2 = fract(u1 + 0.5) - 0.5;
  float u = fwidth(u1) <= fwidth(u2) + 1e-6 ? u1 : u2;
  float v = 0.5 - lat / PI;
  vec3 albedo = pow(texture(uTex, vec2(u, v)).rgb, vec3(2.2));

  vec3 L = normalize(uLight);
  float mu0 = dot(n, L);
  vec3 col;
  if (uKind == 0) {
    float diff = clamp((mu0 + 0.15) / 1.15, 0.0, 1.0);
    col = albedo * (0.06 + 1.25 * diff);
    float haze = pow(1.0 - n.z, 2.6);
    col = mix(col, pow(vec3(0.92, 0.6, 0.42), vec3(2.2)) * smoothstep(-0.25, 0.5, mu0), haze * 0.45);
  } else {
    float m0 = max(mu0, 0.0);
    float ls = min(2.0 * m0 / (m0 + max(n.z, 0.05)), 1.35); // Lommel-Seeliger
    col = albedo * (0.04 + 1.45 * mix(m0, ls * 0.62, 0.72));
  }

  float a = 1.0 - smoothstep(1.0 - 1.5 * uPx / PR, 1.0, d);
  float ga = 0.0;
  if (uKind == 0 && d > 0.98) {
    vec3 dir = normalize(vec3(p, 0.0));
    ga = exp(-(d - 1.0) * 26.0) * 0.5 * smoothstep(-0.4, 0.7, dot(dir, L));
  }
  vec3 surf = clamp(pow(max(col, 0.0), vec3(1.0 / 2.2)), 0.0, 1.0);
  outColor = vec4(surf * a + vec3(1.0, 0.62, 0.42) * ga * (1.0 - a), a + ga * (1.0 - a));
}`;
