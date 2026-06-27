import { useCallback, useRef, useState } from "react";

import { streamChat } from "../api/chat";
import type { EventoChat, Turno } from "../types";

let _seq = 0;
const novoId = () => `t${++_seq}-${Date.now()}`;

interface UseChat {
  turnos: Turno[];
  threadId: string | null;
  enviando: boolean;
  selecionadoId: string | null;
  selecionar: (id: string) => void;
  enviar: (pergunta: string) => void;
}

function patch(turnos: Turno[], id: string, muda: (t: Turno) => Partial<Turno>): Turno[] {
  return turnos.map((t) => (t.id === id ? { ...t, ...muda(t) } : t));
}

// Aplica um evento SSE ao turno acumulado (renderização incremental: cada peça entra
// no estado assim que chega, sem esperar o relatório inteiro).
function aplicar(t: Turno, ev: EventoChat): Partial<Turno> {
  const base = { eventosRecebidos: [...t.eventosRecebidos, ev.tipo] };
  switch (ev.tipo) {
    case "premissas": {
      const { tipo: _t, ...premissas } = ev;
      return { ...base, premissas };
    }
    case "sql":
      return { ...base, sql: [...t.sql, { nome: ev.nome, sql: ev.sql }] };
    case "dados":
      return { ...base, dados: ev.dados };
    case "saude": {
      const { tipo: _t, ...saude } = ev;
      return { ...base, saude };
    }
    case "fontes":
      return { ...base, fontes: ev.fontes };
    case "diagnostico":
      return { ...base, diagnostico: ev.texto };
    case "recomendacao": {
      const { tipo: _t, ...rec } = ev;
      return { ...base, recomendacoes: [...t.recomendacoes, rec] };
    }
    case "clarificacao":
      return { ...base, estado: "clarificacao", clarificacao: ev.pergunta };
    case "fim":
      // `final` só se não tiver caído antes em clarificação/erro. Mescla as fontes do `fim`
      // (robustez: hoje elas vêm no evento `fontes`, mas o `fim` também as carrega).
      return {
        ...base,
        fontes: ev.fontes.length > 0 ? [...new Set([...t.fontes, ...ev.fontes])] : t.fontes,
        estado: t.estado === "streaming" ? "final" : t.estado,
      };
    case "run":
      return {
        ...base,
        runId: ev.run_id,
        threadId: ev.thread_id,
        artefatos: ev.artefatos,
        estado: ev.erro ? "erro" : t.estado === "clarificacao" ? "clarificacao" : "final",
        erro: ev.erro ?? t.erro,
      };
    case "erro":
      return { ...base, estado: "erro", erro: ev.mensagem };
  }
}

export function useChat(): UseChat {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [selecionadoId, setSelecionadoId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const enviar = useCallback(
    (pergunta: string) => {
      const texto = pergunta.trim();
      if (!texto || enviando) return;

      const id = novoId();
      const novo: Turno = {
        id,
        pergunta: texto,
        estado: "streaming",
        eventosRecebidos: [],
        sql: [],
        fontes: [],
        recomendacoes: [],
      };
      setTurnos((ts) => [...ts, novo]);
      setSelecionadoId(id);
      setEnviando(true);

      const controller = new AbortController();
      abortRef.current = controller;

      streamChat(texto, threadId, {
        signal: controller.signal,
        onEvento: (ev) => {
          // O thread_id devolvido no `run` mantém a conversa (multi-turno) no próximo envio.
          if (ev.tipo === "run" && ev.thread_id) setThreadId(ev.thread_id);
          setTurnos((ts) => patch(ts, id, (t) => aplicar(t, ev)));
        },
      })
        .catch((err: unknown) => {
          if (controller.signal.aborted) return;
          const msg = err instanceof Error ? err.message : "Erro de rede.";
          setTurnos((ts) =>
            patch(ts, id, (t) => (t.estado === "final" ? {} : { estado: "erro", erro: msg })),
          );
        })
        .finally(() => {
          setTurnos((ts) =>
            patch(ts, id, (t) =>
              t.estado === "streaming"
                ? { estado: "erro", erro: "A resposta terminou sem relatório." }
                : {},
            ),
          );
          setEnviando(false);
          abortRef.current = null;
        });
    },
    [enviando, threadId],
  );

  return { turnos, threadId, enviando, selecionadoId, selecionar: setSelecionadoId, enviar };
}
