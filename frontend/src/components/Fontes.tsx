import { useState } from "react";

import { Documento } from "./icons";

// Nome curto e legível a partir da URI (último segmento, sem extensão).
function rotulo(fonte: string): string {
  const seg = fonte.split("/").pop() ?? fonte;
  return seg.replace(/\.md$/, "");
}

// Coleção inferida do path da URI (diagnostico/prescricao) — só para rotular o chip.
function colecao(fonte: string): string {
  if (fonte.includes("/prescricao/")) return "prescrição";
  if (fonte.includes("/diagnostico/")) return "diagnóstico";
  return "fonte";
}

function Item({ fonte }: { fonte: string }) {
  const [aberto, setAberto] = useState(false);
  const id = `fonte-${rotulo(fonte)}`;
  return (
    <li className="fonte">
      <button
        type="button"
        className="fonte-chip"
        aria-expanded={aberto}
        aria-controls={id}
        onClick={() => setAberto((v) => !v)}
      >
        <Documento />
        <span className="fonte-nome">{rotulo(fonte)}</span>
        <span className="fonte-tag">{colecao(fonte)}</span>
      </button>
      {aberto && (
        <div className="fonte-detalhe" id={id}>
          <code className="fonte-uri">{fonte}</code>
        </div>
      )}
    </li>
  );
}

// Fontes citadas (URIs minio:// rastreáveis, não navegáveis). Inspecionáveis — o analista
// precisa ver o que o agente usou (frontend.md).
export function Fontes({ fontes }: { fontes: string[] }) {
  const unicas = [...new Set(fontes.filter(Boolean))];
  if (unicas.length === 0) return null;
  return (
    <section className="bloco">
      <h3 className="bloco-titulo">Fontes citadas ({unicas.length})</h3>
      <ul className="fontes-lista">
        {unicas.map((f, i) => (
          <Item key={`${f}-${i}`} fonte={f} />
        ))}
      </ul>
    </section>
  );
}
