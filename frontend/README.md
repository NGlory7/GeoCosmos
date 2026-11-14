# GeoCosmos frontend

React + Vite + TypeScript + Tailwind. Veri sözleşmesi: `src/types.ts` ve [ARCHITECTURE.md](../ARCHITECTURE.md#veri-sözleşmesi).

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (port sabit)
npm run build    # dist/
```

- `public/data/` dosyalarını `pipeline/build.py` (`make data`) üretir; elle düzenlenmez.
- Ana sayfadaki Mars ve Ay WebGL2 shader'ıyla prosedürel çizilir (`src/components/planetShader.ts`); doku dosyası yok. WebGL2 yoksa basit bir gradyan gösterilir.

| Yol | Sayfa |
| --- | --- |
| `/` | Giriş: gök cismi seçimi |
| `/mars`, `/moon` | Hedef listesi (geçici; harita ve test seçimi sonraki adım) |
