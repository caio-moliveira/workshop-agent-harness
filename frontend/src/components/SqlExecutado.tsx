// SQL executado inspecionável — o rastro não fica escondido (regra frontend.md).

import type { EventoSql } from "../api/types";
import { Inspetor } from "./Inspetor";

export function SqlExecutado({ sqls }: { sqls: EventoSql[] }) {
  if (sqls.length === 0) return null;
  return (
    <Inspetor titulo={`SQL executado (${sqls.length})`}>
      {sqls.map((s, i) => (
        <div key={`${s.nome}-${i}`} className="sql-bloco">
          <span className="sql-nome">{s.nome}</span>
          <pre>{s.sql}</pre>
        </div>
      ))}
    </Inspetor>
  );
}
