import { useState } from "react";

import { Carregando, ErroBox, SucessoVazio, Vazio } from "./components/Estados";
import { Relatorio } from "./components/Relatorio";
import { useChat } from "./hooks/useChat";

export default function App() {
  const { status, pergunta, resposta, erro, enviar } = useChat();
  const [texto, setTexto] = useState("");

  function aoEnviar(e: React.FormEvent) {
    e.preventDefault();
    void enviar(texto);
  }

  // Há algo a renderizar assim que premissas (ou uma clarificação) chega — o relatório
  // aparece parcial durante o streaming e PERMANECE mesmo se um erro interromper depois.
  const temConteudo = resposta.premissas !== null || resposta.clarificacao !== null;

  return (
    <div className="app">
      <header className="cabecalho">
        <h1>Bússola</h1>
        <p>Agente analítico de vendas — pergunte e receba um relatório fundamentado.</p>
      </header>

      <form className="entrada" onSubmit={aoEnviar}>
        <input
          type="text"
          value={texto}
          placeholder="Como melhorar minhas vendas no próximo mês?"
          onChange={(e) => setTexto(e.target.value)}
          disabled={status === "carregando"}
        />
        <button type="submit" disabled={status === "carregando" || texto.trim() === ""}>
          Perguntar
        </button>
      </form>

      <main className="conversa">
        {status === "vazio" && <Vazio />}
        {status === "carregando" && !temConteudo && <Carregando pergunta={pergunta} />}
        {status === "erro" && <ErroBox mensagem={erro ?? "Erro inesperado."} />}
        {/* Relatório (parcial ou completo) — montado uma vez; sobrevive a um erro tardio. */}
        {temConteudo && <Relatorio resposta={resposta} />}
        {status === "sucesso" && !temConteudo && <SucessoVazio />}
      </main>
    </div>
  );
}
