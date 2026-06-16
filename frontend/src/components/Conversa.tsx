import { Progresso } from "./Progresso";
import type { Turno } from "../types";

function ResumoAssistente({ turno }: { turno: Turno }) {
  switch (turno.estado) {
    case "streaming":
      return <Progresso nos={turno.progresso} />;
    case "final":
      return <span className="resumo ok">Relatório pronto · {turno.relatorio?.periodo}</span>;
    case "clarificacao":
      return <span className="resumo aviso">Pediu mais contexto</span>;
    case "erro":
      return <span className="resumo erro">Falhou — {turno.erro}</span>;
  }
}

export function Conversa({
  turnos,
  selecionadoId,
  onSelecionar,
}: {
  turnos: Turno[];
  selecionadoId: string | null;
  onSelecionar: (id: string) => void;
}) {
  return (
    <ul className="conversa-lista">
      {turnos.map((t) => {
        const ativo = t.id === selecionadoId;
        return (
          <li key={t.id} className="turno">
            <div className="balao usuario">{t.pergunta}</div>
            <button
              type="button"
              className={`balao agente ${ativo ? "ativo" : ""}`}
              aria-pressed={ativo}
              onClick={() => onSelecionar(t.id)}
            >
              <ResumoAssistente turno={t} />
            </button>
          </li>
        );
      })}
    </ul>
  );
}
