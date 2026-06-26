// Renderiza o relatório do agente conforme os eventos chegam (incremental).

import type { Resposta } from "../hooks/useChat";
import { Fontes } from "./Fontes";
import { SqlExecutado } from "./SqlExecutado";

export function Relatorio({ resposta }: { resposta: Resposta }) {
  const { premissas, saude, diagnostico, recomendacoes, fontes, sqls, clarificacao, runId } =
    resposta;

  // Caminho de clarificação: a pergunta era irresolvível, o agente devolve uma pergunta.
  if (clarificacao) {
    return (
      <section className="relatorio">
        <h2>Preciso de mais contexto</h2>
        <p>{clarificacao}</p>
      </section>
    );
  }

  return (
    <section className="relatorio">
      {premissas && (
        <div className="bloco premissas">
          <h3>Premissas</h3>
          <p>{premissas.nota}</p>
          <p className="tags">
            <span className="tag">KPI: {premissas.kpi_alvo}</span>
            <span className="tag">Período-alvo: {premissas.periodo_alvo}</span>
            {Object.entries(premissas.dimensao).map(([k, v]) => (
              <span className="tag" key={k}>
                {k}: {v}
              </span>
            ))}
          </p>
        </div>
      )}

      {saude && (
        <div className={`bloco saude ${saude.fraco ? "saude-fraco" : "saude-ok"}`}>
          <strong>{saude.fraco ? "KPI abaixo da meta" : "KPI saudável"}</strong>
          <span> — {saude.motivo}</span>
        </div>
      )}

      {diagnostico && (
        <div className="bloco">
          <h3>Diagnóstico</h3>
          <p>{diagnostico}</p>
        </div>
      )}

      {recomendacoes.length > 0 && (
        <div className="bloco">
          <h3>Recomendações</h3>
          <ol className="recomendacoes">
            {recomendacoes.map((r, i) => (
              <li key={`${r.fonte}-${i}`}>
                <p>{r.texto}</p>
                <p className="rec-fonte">
                  <span className={`resultado resultado-${r.resultado || "na"}`}>
                    {r.resultado || "—"}
                  </span>
                  <code>{r.fonte}</code>
                </p>
              </li>
            ))}
          </ol>
        </div>
      )}

      <SqlExecutado sqls={sqls} />
      <Fontes fontes={fontes} />

      {runId && <p className="run-id">run: {runId}</p>}
    </section>
  );
}
