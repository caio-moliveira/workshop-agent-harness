import type { Dados as DadosTipo } from "../types";

// Séries quantitativas (tendência/sazonal/meta) como tabelas compactas — o rastro
// numérico que sustenta o diagnóstico (não esconder o que o agente mediu; frontend.md).
function Tabela({ nome, linhas }: { nome: string; linhas: Array<Record<string, unknown>> }) {
  if (linhas.length === 0) return null;
  const colunas = Object.keys(linhas[0]);
  return (
    <div className="serie">
      <h4 className="serie-titulo">{nome}</h4>
      <table className="serie-tabela">
        <thead>
          <tr>
            {colunas.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha, i) => (
            <tr key={i}>
              {colunas.map((c) => (
                <td key={c}>{String(linha[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Dados({ dados }: { dados: DadosTipo }) {
  const series = Object.entries(dados).filter(([, linhas]) => linhas.length > 0);
  if (series.length === 0) return null;
  return (
    <section className="bloco">
      <details>
        <summary className="sql-summary">
          <span>Dados quantitativos ({series.length} séries)</span>
        </summary>
        <div className="series">
          {series.map(([nome, linhas]) => (
            <Tabela key={nome} nome={nome} linhas={linhas} />
          ))}
        </div>
      </details>
    </section>
  );
}
