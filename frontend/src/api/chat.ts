import type { EventoChat } from "../types";

// Cliente de streaming do POST /chat. A pergunta e o sessao_id vão no CORPO (nunca na
// URL/query string — regra de privacidade frontend.md). Lê o text/event-stream do
// ReadableStream e despacha cada evento SSE assim que chega.

const TIPOS_VALIDOS = ["inicio", "progresso", "clarificacao", "final", "erro"] as const;

function parseFrame(frame: string): EventoChat | null {
  let evento = "";
  const dataLinhas: string[] = [];
  for (const linha of frame.split("\n")) {
    if (linha.startsWith("event:")) evento = linha.slice(6).trim();
    else if (linha.startsWith("data:")) dataLinhas.push(linha.slice(5).trim());
  }
  if (!evento || dataLinhas.length === 0) return null;
  if (!(TIPOS_VALIDOS as readonly string[]).includes(evento)) return null;
  try {
    const dados = JSON.parse(dataLinhas.join("\n"));
    return { tipo: evento, dados } as EventoChat;
  } catch {
    return null;
  }
}

export interface OpcoesStream {
  signal?: AbortSignal;
  onEvento: (evento: EventoChat) => void;
}

export async function streamChat(
  pergunta: string,
  sessaoId: string | null,
  { signal, onEvento }: OpcoesStream,
): Promise<void> {
  const corpo: Record<string, string> = { pergunta };
  if (sessaoId) corpo.sessao_id = sessaoId;

  const resp = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(corpo),
    signal,
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`Falha ao iniciar o chat (HTTP ${resp.status}).`);
  }

  const reader = resp.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const evento = parseFrame(frame);
      if (evento) onEvento(evento);
    }
  }
  // Frame residual sem o \n\n final (stream encerrado).
  if (buffer.trim()) {
    const evento = parseFrame(buffer);
    if (evento) onEvento(evento);
  }
}
