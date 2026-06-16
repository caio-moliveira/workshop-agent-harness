import { useCallback, useRef, useState } from "react";

import { streamChat } from "../api/chat";
import type { Turno } from "../types";

let _seq = 0;
const novoId = () => `t${++_seq}-${Date.now()}`;

interface UseChat {
  turnos: Turno[];
  sessaoId: string | null;
  enviando: boolean;
  selecionadoId: string | null;
  selecionar: (id: string) => void;
  enviar: (pergunta: string) => void;
}

function patch(turnos: Turno[], id: string, mudanca: Partial<Turno>): Turno[] {
  return turnos.map((t) => (t.id === id ? { ...t, ...mudanca } : t));
}

export function useChat(): UseChat {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [sessaoId, setSessaoId] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [selecionadoId, setSelecionadoId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const enviar = useCallback(
    (pergunta: string) => {
      const texto = pergunta.trim();
      if (!texto || enviando) return;

      const id = novoId();
      setTurnos((ts) => [...ts, { id, pergunta: texto, estado: "streaming", progresso: [] }]);
      setSelecionadoId(id);
      setEnviando(true);

      const controller = new AbortController();
      abortRef.current = controller;

      streamChat(texto, sessaoId, {
        signal: controller.signal,
        onEvento: (evento) => {
          switch (evento.tipo) {
            case "inicio":
              setSessaoId(evento.dados.sessao_id);
              setTurnos((ts) =>
                patch(ts, id, {
                  intencao: evento.dados.intencao,
                  perguntaReescrita: evento.dados.pergunta_reescrita,
                }),
              );
              break;
            case "progresso":
              setTurnos((ts) =>
                patch(ts, id, {
                  progresso: [...(ts.find((t) => t.id === id)?.progresso ?? []), evento.dados.no],
                }),
              );
              break;
            case "clarificacao":
              setTurnos((ts) =>
                patch(ts, id, { estado: "clarificacao", clarificacao: evento.dados.pergunta }),
              );
              break;
            case "final":
              setTurnos((ts) => patch(ts, id, { estado: "final", relatorio: evento.dados }));
              break;
            case "erro":
              setTurnos((ts) =>
                patch(ts, id, { estado: "erro", erro: evento.dados.detalhe }),
              );
              break;
          }
        },
      })
        .catch((err: unknown) => {
          if (controller.signal.aborted) return;
          const msg = err instanceof Error ? err.message : "Erro de rede.";
          setTurnos((ts) =>
            patch(ts, id, (ts.find((t) => t.id === id)?.estado === "final"
              ? {}
              : { estado: "erro", erro: msg })),
          );
        })
        .finally(() => {
          // Stream encerrado sem evento final/clarificação/erro -> marca erro.
          setTurnos((ts) =>
            patch(ts, id, ts.find((t) => t.id === id)?.estado === "streaming"
              ? { estado: "erro", erro: "A resposta terminou sem relatório." }
              : {}),
          );
          setEnviando(false);
          abortRef.current = null;
        });
    },
    [enviando, sessaoId],
  );

  return { turnos, sessaoId, enviando, selecionadoId, selecionar: setSelecionadoId, enviar };
}
