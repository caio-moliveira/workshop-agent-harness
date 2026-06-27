import { Banco } from "./icons";
import type { SqlExec } from "../types";

// SQL executado, inspecionável (regra "SQL inspecionável"). Read-only — só exibe o que
// o agente rodou contra o schema `negocio` (RO, com guardrails). Colapsado por padrão.
export function SqlInspector({ sql }: { sql: SqlExec[] }) {
  if (sql.length === 0) return null;
  return (
    <section className="bloco">
      <details>
        <summary className="sql-summary">
          <Banco />
          <span>SQL executado ({sql.length})</span>
        </summary>
        <ol className="sql-lista">
          {sql.map((q, i) => (
            <li key={i}>
              <span className="sql-nome">{q.nome}</span>
              <pre>
                <code>{q.sql.trim()}</code>
              </pre>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
