import { useState } from "react";

import { Documento } from "./icons";
import type { Fonte } from "../types";

// Nome curto e legível a partir da URI (último segmento, sem extensão).
function rotulo(fonte: string | null): string {
  if (!fonte) return "fonte";
  const seg = fonte.split("/").pop() ?? fonte;
  return seg.replace(/\.md$/, "");
}

function Item({ fonte }: { fonte: Fonte }) {
  const [aberto, setAberto] = useState(false);
  const id = `fonte-${rotulo(fonte.fonte)}`;
  return (
    <li className={`fonte ${fonte.colecao}`}>
      <button
        type="button"
        className="fonte-chip"
        aria-expanded={aberto}
        aria-controls={id}
        onClick={() => setAberto((v) => !v)}
      >
        <Documento />
        <span className="fonte-nome">{rotulo(fonte.fonte)}</span>
        <span className="fonte-tag">{fonte.colecao}</span>
      </button>
      {aberto && (
        <div className="fonte-detalhe" id={id}>
          {fonte.resumo && <p>{fonte.resumo}</p>}
          {fonte.fonte && <code className="fonte-uri">{fonte.fonte}</code>}
        </div>
      )}
    </li>
  );
}

export function Fontes({ fontes }: { fontes: Fonte[] }) {
  const citadas = fontes.filter((f) => f.fonte);
  if (citadas.length === 0) return null;
  return (
    <section className="bloco">
      <h3 className="bloco-titulo">Fontes citadas ({citadas.length})</h3>
      <ul className="fontes-lista">
        {citadas.map((f, i) => (
          <Item key={`${f.fonte}-${i}`} fonte={f} />
        ))}
      </ul>
    </section>
  );
}
