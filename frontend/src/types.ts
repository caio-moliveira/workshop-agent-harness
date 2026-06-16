// Contrato do streaming SSE do POST /chat (backend #23/#24).

export interface Achado {
  kpi: string;
  dimensao: string;
  periodo_alvo?: string;
  tendencia_gap_pct?: number | null;
  sazonal_gap_pct?: number | null;
  abaixo_tendencia?: boolean;
  abaixo_sazonal?: boolean;
}

export interface Fonte {
  colecao: string; // "diagnostico" | "prescricao"
  dimensao?: string;
  fonte: string | null; // URI minio:// (não navegável; inspecionável)
  resumo?: string;
}

export interface Recomendacao {
  kpi: string;
  dimensao?: string;
  acao?: string;
  resultado?: string | null; // positivo | nulo | negativo
  fonte: string | null;
}

// Spec Vega-Lite emitido pelo backend (charts.spec_gaps).
export interface GraficoSpec {
  title?: string;
  data?: { values?: Array<Record<string, unknown>> };
  [k: string]: unknown;
}

export interface RelatorioFinal {
  run_id: string;
  sessao_id: string;
  intencao: string;
  pergunta_reescrita: string;
  periodo: string;
  premissas: string[];
  relatorio: string; // markdown
  achados: Achado[];
  fontes: Fonte[];
  recomendacoes: Recomendacao[];
  sql_executado: string[];
  artefatos: Record<string, string>;
  grafico?: GraficoSpec | null; // derivado no cliente a partir dos achados (fallback)
}

export type EventoChat =
  | { tipo: "inicio"; dados: { run_id: string; sessao_id: string; intencao: string; pergunta_reescrita: string } }
  | { tipo: "progresso"; dados: { no: string } }
  | { tipo: "clarificacao"; dados: { run_id: string; sessao_id: string; pergunta: string } }
  | { tipo: "final"; dados: RelatorioFinal }
  | { tipo: "erro"; dados: { run_id: string; detalhe: string } };

export type EstadoTurno = "streaming" | "final" | "clarificacao" | "erro";

export interface Turno {
  id: string;
  pergunta: string;
  estado: EstadoTurno;
  progresso: string[]; // nós do grafo concluídos, na ordem
  intencao?: string;
  perguntaReescrita?: string;
  relatorio?: RelatorioFinal;
  clarificacao?: string;
  erro?: string;
}
