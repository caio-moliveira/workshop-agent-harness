import { useState } from "react";

import { pontosDeAchados } from "../lib/grafico";
import type { Achado } from "../types";

// Barras divergentes (gap % vs meta) a partir do zero: negativo à esquerda (abaixo da
// meta), positivo à direita. Cor reforça o sinal, mas o valor e o rótulo também o
// indicam (regra color-not-only). Tabela alternativa para leitores de tela / detalhe.
export function Grafico({ achados, periodo }: { achados: Achado[]; periodo: string }) {
  const [verTabela, setVerTabela] = useState(false);
  const pontos = pontosDeAchados(achados);
  if (pontos.length === 0) return null;

  const escala = Math.max(...pontos.map((p) => Math.abs(p.gap_pct)), 1);
  const meia = 46; // % máximo de cada lado, deixando margem para os rótulos
  const titulo = `Gap vs meta por dimensão — alvo ${periodo}`;
  const piores = pontos.filter((p) => p.gap_pct < 0).length;
  const resumo = `${titulo}. ${pontos.length} medições; ${piores} abaixo da meta.`;

  return (
    <figure className="grafico" aria-label={resumo}>
      <figcaption>
        <span>{titulo}</span>
        <button
          type="button"
          className="link-btn"
          aria-expanded={verTabela}
          onClick={() => setVerTabela((v) => !v)}
        >
          {verTabela ? "ver gráfico" : "ver dados"}
        </button>
      </figcaption>

      {verTabela ? (
        <table className="g-tabela">
          <thead>
            <tr>
              <th scope="col">dimensão</th>
              <th scope="col">janela</th>
              <th scope="col">gap %</th>
            </tr>
          </thead>
          <tbody>
            {pontos.map((p, i) => (
              <tr key={i}>
                <td>{p.dimensao}</td>
                <td>{p.serie}</td>
                <td className={p.gap_pct < 0 ? "neg" : "pos"}>{p.gap_pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="g-barras" role="img" aria-label={resumo}>
          {pontos.map((p, i) => {
            const s = (Math.abs(p.gap_pct) / escala) * meia;
            const neg = p.gap_pct < 0;
            const left = neg ? 50 - s : 50;
            return (
              <div className="g-row" key={i}>
                <span className="g-rotulo">
                  {p.dimensao} · {p.serie}
                </span>
                <div className="g-track">
                  <div className="g-zero" />
                  <div
                    className={`g-bar ${neg ? "g-bar--neg" : "g-bar--pos"}`}
                    style={{ left: `${left}%`, width: `${s}%` }}
                  />
                  <span className={`g-valor ${neg ? "neg" : "pos"}`} style={{ left: `${neg ? left - 1 : left + s + 1}%` }}>
                    {p.gap_pct > 0 ? "+" : ""}
                    {p.gap_pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </figure>
  );
}
