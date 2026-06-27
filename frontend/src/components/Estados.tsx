import { Alerta, Bussola, Chave } from "./icons";

// Estados explícitos (regra: toda chamada trata loading/erro/vazio).

export function Vazio({ exemplos, onExemplo }: { exemplos: string[]; onExemplo: (q: string) => void }) {
  return (
    <div className="estado-vazio">
      <Bussola width={40} height={40} />
      <h2>Bússola</h2>
      <p>Pergunte sobre vendas e receba um relatório com diagnóstico, recomendações com fonte e o SQL executado.</p>
      <div className="exemplos">
        {exemplos.map((q) => (
          <button type="button" key={q} className="exemplo" onClick={() => onExemplo(q)}>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

export function VazioRelatorio() {
  return (
    <div className="estado-vazio compacto">
      <Bussola width={32} height={32} />
      <p>O relatório aparece aqui quando você faz uma pergunta.</p>
    </div>
  );
}

export function Erro({ detalhe, onTentar }: { detalhe: string; onTentar?: () => void }) {
  return (
    <div className="estado-erro" role="alert">
      <Alerta />
      <div>
        <strong>Algo deu errado</strong>
        <p>{detalhe}</p>
        {onTentar && (
          <button type="button" className="btn" onClick={onTentar}>
            Tentar de novo
          </button>
        )}
      </div>
    </div>
  );
}

export function Clarificacao({ pergunta }: { pergunta: string }) {
  return (
    <div className="estado-clarificacao" role="status">
      <Chave />
      <div>
        <strong>Preciso de mais contexto</strong>
        <p>{pergunta}</p>
      </div>
    </div>
  );
}
