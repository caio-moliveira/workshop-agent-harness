// Único ponto de acesso à API (regra frontend.md). POST /chat via fetch + streaming —
// EventSource só faz GET, então parseamos o SSE manualmente do ReadableStream.

import type { EventoChat } from "./types";

function parseBlocoSse(bloco: string): EventoChat | null {
  // Spec SSE: múltiplas linhas `data:` no mesmo evento são unidas por "\n".
  const dados = bloco
    .split("\n")
    .filter((l) => l.startsWith("data:"))
    .map((l) => l.slice("data:".length).replace(/^ /, ""))
    .join("\n")
    .trim();
  return dados ? (JSON.parse(dados) as EventoChat) : null;
}

/** Faz a pergunta e produz os eventos do agente conforme chegam (incremental). */
export async function* streamChat(
  pergunta: string,
  signal?: AbortSignal,
): AsyncGenerator<EventoChat> {
  const resposta = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pergunta }),
    signal,
  });

  if (!resposta.ok || resposta.body === null) {
    throw new Error(`Falha ao consultar o agente (HTTP ${resposta.status}).`);
  }

  const leitor = resposta.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await leitor.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep = buffer.indexOf("\n\n");
    while (sep !== -1) {
      const bloco = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const evento = parseBlocoSse(bloco);
      if (evento) yield evento;
      sep = buffer.indexOf("\n\n");
    }
  }
}
