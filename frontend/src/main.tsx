import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import "./index.css";
import Home from "./pages/Home";

// Harita/grafik kütüphaneleri ayrı parçada: giriş sayfası onları beklemez.
const BodyPage = lazy(() => import("./pages/BodyPage"));
const AnalogPage = lazy(() => import("./pages/AnalogPage"));
const ValidationPage = lazy(() => import("./pages/ValidationPage"));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Suspense fallback={<div className="min-h-dvh bg-space" />}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dogrulama" element={<ValidationPage />} />
        <Route path="/:body" element={<BodyPage />} />
        <Route path="/:body/:targetId/:testId" element={<AnalogPage />} />
      </Routes>
      </Suspense>
    </BrowserRouter>
  </StrictMode>,
);
