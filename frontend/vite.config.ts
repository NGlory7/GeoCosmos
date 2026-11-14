import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Port sabit (ARCHITECTURE.md > Frontend notları): API'nin CORS listesiyle uyuşsun.
// VITE_BASE: GitHub Pages alt yolu (.github/workflows/pages.yml > /GeoCosmos/); yerelde "/".
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true },
});
