// Bloco colapsável genérico — usado para expor o rastro (SQL, dados) sem poluir a leitura.

import { useState, type ReactNode } from "react";

export function Inspetor({
  titulo,
  children,
  aberto = false,
}: {
  titulo: string;
  children: ReactNode;
  aberto?: boolean;
}) {
  const [visivel, setVisivel] = useState(aberto);
  return (
    <div className="inspetor">
      <button type="button" className="inspetor-toggle" onClick={() => setVisivel((v) => !v)}>
        {visivel ? "▾" : "▸"} {titulo}
      </button>
      {visivel && <div className="inspetor-corpo">{children}</div>}
    </div>
  );
}
