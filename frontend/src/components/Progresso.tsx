// Stepper do grafo: mostra os nós concluídos conforme chegam pelo SSE (streaming vivo).
const ROTULOS: Record<string, string> = {
  planejar: "planejar",
  perna_quantitativa: "análise quantitativa",
  enriquecer: "enriquecer (diagnóstico/prescrição)",
  clarificar: "clarificar",
  relatorio: "redigir relatório",
};

export function Progresso({ nos }: { nos: string[] }) {
  return (
    <div className="progresso" aria-live="polite">
      <span className="spinner" aria-hidden />
      <span className="progresso-passos">
        {nos.length === 0
          ? "preparando…"
          : nos.map((n, i) => (
              <span key={i} className="passo">
                {ROTULOS[n] ?? n}
                {i < nos.length - 1 ? " ✓ · " : " …"}
              </span>
            ))}
      </span>
    </div>
  );
}
