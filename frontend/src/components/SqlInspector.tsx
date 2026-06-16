import { Banco } from "./icons";

// SQL executado, inspecionável (regra "SQL inspecionável"). Read-only — só exibe o que
// o agente rodou contra o schema `negocio` (RO). Colapsado por padrão (disclosure).
export function SqlInspector({ sql }: { sql: string[] }) {
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
              <pre>
                <code>{q.trim()}</code>
              </pre>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
