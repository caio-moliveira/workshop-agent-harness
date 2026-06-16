import { Clarificacao, Erro, VazioRelatorio } from "./Estados";
import { Fontes } from "./Fontes";
import { Grafico } from "./Grafico";
import { Markdown } from "./Markdown";
import { Progresso } from "./Progresso";
import { SqlInspector } from "./SqlInspector";
import type { Turno } from "../types";

// Painel direito: o relatório é o produto. Mostra o estado do turno selecionado.
export function Relatorio({ turno, onTentar }: { turno?: Turno; onTentar?: () => void }) {
  if (!turno) return <VazioRelatorio />;

  if (turno.estado === "streaming") {
    return (
      <div className="relatorio-carregando">
        <Progresso nos={turno.progresso} />
        <div className="skeleton skeleton-titulo" />
        <div className="skeleton" />
        <div className="skeleton" />
        <div className="skeleton skeleton-grafico" />
      </div>
    );
  }

  if (turno.estado === "erro") {
    return <Erro detalhe={turno.erro ?? "Falha ao gerar o relatório."} onTentar={onTentar} />;
  }

  if (turno.estado === "clarificacao") {
    return <Clarificacao pergunta={turno.clarificacao ?? ""} />;
  }

  const r = turno.relatorio;
  if (!r) return <VazioRelatorio />;

  return (
    <article className="relatorio">
      <header className="relatorio-head">
        <div className="relatorio-meta">
          {r.periodo && <span className="tag tag-periodo">alvo {r.periodo}</span>}
          {turno.intencao && <span className="tag">{turno.intencao}</span>}
        </div>
        {turno.perguntaReescrita && turno.perguntaReescrita !== turno.pergunta && (
          <p className="reescrita">interpretei como: “{turno.perguntaReescrita}”</p>
        )}
      </header>

      <Grafico achados={r.achados} periodo={r.periodo} />
      <Markdown>{r.relatorio}</Markdown>
      <Fontes fontes={r.fontes} />
      <SqlInspector sql={r.sql_executado} />
    </article>
  );
}
