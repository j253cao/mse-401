import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { RecommendationsProvider } from "./RecommendationsContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RecommendationsProvider>
      <App />
    </RecommendationsProvider>
  </StrictMode>
);
