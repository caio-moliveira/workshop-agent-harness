import { useState } from "react";

import { Enviar } from "./icons";

// Input da pergunta. Enter envia; Shift+Enter quebra linha. Desabilita durante o envio
// (regra: desabilitar gatilho em operação async). A pergunta vai no corpo do POST.
export function Composer({ enviando, onEnviar }: { enviando: boolean; onEnviar: (q: string) => void }) {
  const [texto, setTexto] = useState("");

  const submeter = () => {
    const q = texto.trim();
    if (!q || enviando) return;
    onEnviar(q);
    setTexto("");
  };

  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        submeter();
      }}
    >
      <textarea
        className="composer-input"
        placeholder="Pergunte sobre vendas… (ex.: como melhorar o faturamento por região?)"
        value={texto}
        rows={1}
        aria-label="Pergunta"
        onChange={(e) => setTexto(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submeter();
          }
        }}
      />
      <button
        type="submit"
        className="composer-btn"
        disabled={enviando || !texto.trim()}
        aria-label="Enviar pergunta"
      >
        {enviando ? <span className="spinner" aria-hidden /> : <Enviar />}
      </button>
    </form>
  );
}
