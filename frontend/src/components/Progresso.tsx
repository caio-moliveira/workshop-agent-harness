import type { TipoEvento } from "../types";

// Stepper vivo: traduz os eventos SSE recebidos em passos legíveis, na ordem de chegada.
const ROTULOS: Partial<Record<TipoEvento, string>> = {
  premissas: "planejando",
  sql: "consultando dados",
  dados: "medindo",
  saude: "avaliando saúde",
  fontes: "enriquecendo",
  diagnostico: "diagnosticando",
  recomendacao: "recomendando",
};

export function Progresso({ eventos }: { eventos: TipoEvento[] }) {
  // Passos únicos, na ordem em que apareceram (sql/recomendacao repetem; mostramos uma vez).
  const passos: string[] = [];
  for (const ev of eventos) {
    const rotulo = ROTULOS[ev];
    if (rotulo && !passos.includes(rotulo)) passos.push(rotulo);
  }
  return (
    <div className="progresso" aria-live="polite">
      <span className="spinner" aria-hidden />
      <span className="progresso-passos">
        {passos.length === 0
          ? "preparando…"
          : passos.map((p, i) => (
              <span key={p} className="passo">
                {p}
                {i < passos.length - 1 ? " ✓ · " : " …"}
              </span>
            ))}
      </span>
    </div>
  );
}
