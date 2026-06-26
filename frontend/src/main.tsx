import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";

const raiz = document.getElementById("root");
if (raiz === null) {
  throw new Error("Elemento #root não encontrado.");
}

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
