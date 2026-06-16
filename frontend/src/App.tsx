import { Composer } from "./components/Composer";
import { Conversa } from "./components/Conversa";
import { Vazio } from "./components/Estados";
import { Bussola } from "./components/icons";
import { Relatorio } from "./components/Relatorio";
import { useChat } from "./hooks/useChat";

const EXEMPLOS = [
  "Como melhorar o faturamento por região no próximo mês?",
  "Por que o faturamento de Eletrônicos no marketplace caiu?",
  "O que fazer com a queda do faturamento da loja física?",
];

export default function App() {
  const { turnos, sessaoId, enviando, selecionadoId, selecionar, enviar } = useChat();
  const selecionado = turnos.find((t) => t.id === selecionadoId) ?? turnos[turnos.length - 1];
  const vazio = turnos.length === 0;

  return (
    <div className="app">
      <header className="topo">
        <div className="marca">
          <Bussola width={22} height={22} />
          <span>Bússola</span>
          <span className="sub">agente analítico de vendas</span>
        </div>
        {sessaoId && (
          <span className="sessao" title={`sessão ${sessaoId}`}>
            sessão ativa · multi-turno
          </span>
        )}
      </header>

      <main className="painel">
        <section className="coluna conversa" aria-label="Conversa">
          <div className="conversa-rolagem">
            {vazio ? (
              <Vazio exemplos={EXEMPLOS} onExemplo={enviar} />
            ) : (
              <Conversa turnos={turnos} selecionadoId={selecionado?.id ?? null} onSelecionar={selecionar} />
            )}
          </div>
          <Composer enviando={enviando} onEnviar={enviar} />
        </section>

        <section className="coluna relatorio-pane" aria-label="Relatório">
          <div className="relatorio-rolagem">
            <Relatorio
              turno={selecionado}
              onTentar={selecionado ? () => enviar(selecionado.pergunta) : undefined}
            />
          </div>
        </section>
      </main>
    </div>
  );
}
