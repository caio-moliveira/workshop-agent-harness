import { Clarificacao, Erro, VazioRelatorio } from "./Estados";
import { Dados } from "./Dados";
import { Fontes } from "./Fontes";
import { Markdown } from "./Markdown";
import { Progresso } from "./Progresso";
import { SqlInspector } from "./SqlInspector";
import type { Premissas, Recomendacao, Saude, Turno } from "../types";

function BlocoPremissas({ premissas }: { premissas: Premissas }) {
  const recorte =
    Object.keys(premissas.dimensao).length > 0
      ? Object.entries(premissas.dimensao)
          .map(([k, v]) => `${k}: ${v}`)
          .join(", ")
      : "agregado";
  return (
    <header className="relatorio-head">
      <div className="relatorio-meta">
        <span className="tag tag-periodo">alvo {premissas.periodo_alvo}</span>
        <span className="tag">{premissas.kpi_alvo}</span>
        <span className="tag">{recorte}</span>
      </div>
      <p className="reescrita">{premissas.nota}</p>
    </header>
  );
}

function BadgeSaude({ saude }: { saude: Saude }) {
  const classe = saude.fraco ? "saude fraco" : "saude saudavel";
  const rotulo = saude.fraco ? "abaixo do esperado" : "saudável";
  return (
    <div className={classe}>
      <strong>{rotulo}</strong> · {saude.motivo}
      {saude.parece_sazonal && " · variação sazonal"}
    </div>
  );
}

function Recomendacoes({ recomendacoes }: { recomendacoes: Recomendacao[] }) {
  if (recomendacoes.length === 0) return null;
  const rotuloFonte = (f: string) => f.split("/").pop()?.replace(/\.md$/, "") ?? f;
  return (
    <section className="bloco">
      <h3 className="bloco-titulo">Recomendações ({recomendacoes.length})</h3>
      <ol className="recomendacoes">
        {recomendacoes.map((r, i) => (
          <li key={`${r.fonte}-${i}`} className="recomendacao">
            <p>{r.texto}</p>
            <div className="recomendacao-fonte">
              <code title={r.fonte}>{rotuloFonte(r.fonte)}</code>
              {r.resultado && <span className={`resultado ${r.resultado}`}>{r.resultado}</span>}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

// Painel direito: o relatório é o produto. Renderiza INCREMENTALMENTE o que já chegou
// (premissas → saúde → diagnóstico → recomendações → fontes → SQL), com o stepper enquanto
// o stream segue. Não espera o relatório inteiro (frontend.md).
export function Relatorio({ turno, onTentar }: { turno?: Turno; onTentar?: () => void }) {
  if (!turno) return <VazioRelatorio />;

  if (turno.estado === "erro") {
    return <Erro detalhe={turno.erro ?? "Falha ao gerar o relatório."} onTentar={onTentar} />;
  }
  if (turno.estado === "clarificacao") {
    return <Clarificacao pergunta={turno.clarificacao ?? ""} />;
  }

  const semConteudo = turno.estado === "streaming" && !turno.premissas;
  if (semConteudo) {
    return (
      <div className="relatorio-carregando">
        <Progresso eventos={turno.eventosRecebidos} />
        <div className="skeleton skeleton-titulo" />
        <div className="skeleton" />
        <div className="skeleton" />
      </div>
    );
  }

  return (
    <article className="relatorio">
      {turno.estado === "streaming" && <Progresso eventos={turno.eventosRecebidos} />}
      {turno.premissas && <BlocoPremissas premissas={turno.premissas} />}
      {turno.saude && <BadgeSaude saude={turno.saude} />}
      {turno.diagnostico && (
        <section className="bloco">
          <h3 className="bloco-titulo">Diagnóstico</h3>
          <Markdown>{turno.diagnostico}</Markdown>
        </section>
      )}
      <Recomendacoes recomendacoes={turno.recomendacoes} />
      {turno.estado === "final" &&
        turno.recomendacoes.length === 0 &&
        turno.saude &&
        !turno.saude.fraco && (
          <p className="nota-saudavel">
            KPI saudável — é oportunidade, não deficit. Sem recomendação corretiva.
          </p>
        )}
      {turno.dados && <Dados dados={turno.dados} />}
      <Fontes fontes={turno.fontes} />
      <SqlInspector sql={turno.sql} />
    </article>
  );
}
