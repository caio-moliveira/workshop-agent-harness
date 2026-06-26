// Hook do chat: dispara o streaming e acumula os eventos num estado estruturado,
// atualizando a UI incrementalmente conforme cada evento chega.

import { useCallback, useReducer, useRef } from "react";

import { streamChat } from "../api/chat";
import type {
  EventoChat,
  EventoPremissas,
  EventoRecomendacao,
  EventoSaude,
  EventoSql,
  LinhaDados,
} from "../api/types";

export type Status = "vazio" | "carregando" | "sucesso" | "erro";

export interface Resposta {
  premissas: EventoPremissas | null;
  sqls: EventoSql[];
  dados: Record<string, LinhaDados[]> | null;
  saude: EventoSaude | null;
  fontes: string[];
  diagnostico: string;
  recomendacoes: EventoRecomendacao[];
  clarificacao: string | null;
  runId: string | null;
}

const RESPOSTA_VAZIA: Resposta = {
  premissas: null,
  sqls: [],
  dados: null,
  saude: null,
  fontes: [],
  diagnostico: "",
  recomendacoes: [],
  clarificacao: null,
  runId: null,
};

interface Estado {
  status: Status;
  pergunta: string;
  resposta: Resposta;
  erro: string | null;
}

type Acao =
  | { tipo: "iniciar"; pergunta: string }
  | { tipo: "evento"; evento: EventoChat }
  | { tipo: "concluir" }
  | { tipo: "falhar"; mensagem: string };

function aplicarEvento(resposta: Resposta, evento: EventoChat): Resposta {
  switch (evento.tipo) {
    case "premissas":
      return { ...resposta, premissas: evento };
    case "sql":
      return { ...resposta, sqls: [...resposta.sqls, evento] };
    case "dados":
      return { ...resposta, dados: evento.dados };
    case "saude":
      return { ...resposta, saude: evento };
    case "fontes":
      return { ...resposta, fontes: evento.fontes };
    case "diagnostico":
      return { ...resposta, diagnostico: evento.texto };
    case "recomendacao":
      return { ...resposta, recomendacoes: [...resposta.recomendacoes, evento] };
    case "clarificacao":
      return { ...resposta, clarificacao: evento.pergunta };
    case "run":
      return { ...resposta, runId: evento.run_id };
    case "fim":
      return resposta;
    case "erro":
      return resposta; // o status de erro é tratado no reducer principal
    default:
      return resposta;
  }
}

function reducer(estado: Estado, acao: Acao): Estado {
  switch (acao.tipo) {
    case "iniciar":
      return { status: "carregando", pergunta: acao.pergunta, resposta: RESPOSTA_VAZIA, erro: null };
    case "evento":
      if (acao.evento.tipo === "erro") {
        return { ...estado, status: "erro", erro: acao.evento.mensagem };
      }
      return { ...estado, resposta: aplicarEvento(estado.resposta, acao.evento) };
    case "concluir":
      return estado.status === "erro" ? estado : { ...estado, status: "sucesso" };
    case "falhar":
      return { ...estado, status: "erro", erro: acao.mensagem };
    default:
      return estado;
  }
}

export function useChat() {
  const [estado, dispatch] = useReducer(reducer, {
    status: "vazio",
    pergunta: "",
    resposta: RESPOSTA_VAZIA,
    erro: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const enviar = useCallback(async (pergunta: string) => {
    const limpa = pergunta.trim();
    if (!limpa) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    dispatch({ tipo: "iniciar", pergunta: limpa });
    try {
      for await (const evento of streamChat(limpa, controller.signal)) {
        dispatch({ tipo: "evento", evento });
      }
      dispatch({ tipo: "concluir" });
    } catch (e) {
      if (controller.signal.aborted) return;
      dispatch({ tipo: "falhar", mensagem: e instanceof Error ? e.message : "Erro inesperado." });
    }
  }, []);

  return { ...estado, enviar };
}
