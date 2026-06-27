// Contrato do streaming SSE do POST /chat (backend #36/#37/#38).
// O backend emite eventos INCREMENTAIS: cada peça (premissas, cada sql, cada recomendação)
// é um evento próprio, encerrando com `fim` + `run`. O front acumula no `Turno`.

export interface Premissas {
  periodo_alvo: string;
  kpi_alvo: string;
  dimensao: Record<string, string>;
  nota: string;
}

export interface Saude {
  fraco: boolean;
  motivo: string;
  parece_sazonal: boolean;
}

export interface SqlExec {
  nome: string; // "tendencia" | "sazonal" | "meta"
  sql: string;
}

export interface Recomendacao {
  texto: string;
  fonte: string; // URI minio:// (não navegável; rastreável)
  resultado: string; // positivo | nulo | negativo | ""
}

// Séries quantitativas (tendência/sazonal/meta) — linhas genéricas para inspeção.
export type Dados = Record<string, Array<Record<string, unknown>>>;

// Cada evento SSE: o `data:` já vem achatado, com o campo `tipo`.
export type EventoChat =
  | ({ tipo: "premissas" } & Premissas)
  | { tipo: "sql"; nome: string; sql: string }
  | { tipo: "dados"; dados: Dados }
  | ({ tipo: "saude" } & Saude)
  | { tipo: "fontes"; fontes: string[] }
  | { tipo: "diagnostico"; texto: string }
  | ({ tipo: "recomendacao" } & Recomendacao)
  | { tipo: "clarificacao"; pergunta: string }
  | { tipo: "fim"; fontes: string[] }
  | {
      tipo: "run";
      run_id: string;
      thread_id: string;
      erro: string | null;
      artefatos: Record<string, string>;
    }
  | { tipo: "erro"; mensagem: string };

export type TipoEvento = EventoChat["tipo"];

export type EstadoTurno = "streaming" | "final" | "clarificacao" | "erro";

// Estado acumulado de um turno conforme os eventos chegam.
export interface Turno {
  id: string;
  pergunta: string;
  estado: EstadoTurno;
  eventosRecebidos: TipoEvento[]; // ordem de chegada (stepper de progresso)
  premissas?: Premissas;
  saude?: Saude;
  sql: SqlExec[];
  dados?: Dados;
  fontes: string[];
  diagnostico?: string;
  recomendacoes: Recomendacao[];
  clarificacao?: string;
  runId?: string;
  threadId?: string;
  artefatos?: Record<string, string>;
  erro?: string;
}
