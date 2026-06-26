// Contrato da API — espelha os eventos SSE emitidos por backend/app/services/chat.py.
// União discriminada por `tipo`; nada de `any`.

export type ValorCelula = string | number | null;
export type LinhaDados = Record<string, ValorCelula>;

export interface EventoPremissas {
  tipo: "premissas";
  periodo_alvo: string;
  kpi_alvo: string;
  dimensao: Record<string, string>;
  nota: string;
}

export interface EventoSql {
  tipo: "sql";
  nome: string;
  sql: string;
}

export interface EventoDados {
  tipo: "dados";
  dados: Record<string, LinhaDados[]>;
}

export interface EventoSaude {
  tipo: "saude";
  fraco: boolean;
  motivo: string;
  parece_sazonal: boolean;
}

export interface EventoFontes {
  tipo: "fontes";
  fontes: string[];
}

export interface EventoDiagnostico {
  tipo: "diagnostico";
  texto: string;
}

export interface EventoRecomendacao {
  tipo: "recomendacao";
  texto: string;
  fonte: string;
  resultado: string;
}

export interface EventoClarificacao {
  tipo: "clarificacao";
  pergunta: string;
}

export interface EventoFim {
  tipo: "fim";
  fontes: string[];
}

export interface EventoRun {
  tipo: "run";
  run_id: string;
  erro: string | null;
  artefatos: Record<string, string>;
}

export interface EventoErro {
  tipo: "erro";
  mensagem: string;
}

export type EventoChat =
  | EventoPremissas
  | EventoSql
  | EventoDados
  | EventoSaude
  | EventoFontes
  | EventoDiagnostico
  | EventoRecomendacao
  | EventoClarificacao
  | EventoFim
  | EventoRun
  | EventoErro;
