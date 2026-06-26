// Estados de UI sempre tratados (regra frontend.md): vazio, carregando, erro.

export function Vazio() {
  return (
    <div className="estado estado-vazio">
      <p>Pergunte em linguagem natural — ex.:</p>
      <p className="exemplo">“Como melhorar a recompra na região Sul no próximo mês?”</p>
    </div>
  );
}

export function Carregando({ pergunta }: { pergunta: string }) {
  return (
    <div className="estado estado-carregando">
      <span className="pontos" aria-label="carregando">
        <i />
        <i />
        <i />
      </span>
      <span>Analisando: {pergunta}</span>
    </div>
  );
}

export function ErroBox({ mensagem }: { mensagem: string }) {
  return (
    <div className="estado estado-erro" role="alert">
      <strong>Não foi possível concluir.</strong>
      <span>{mensagem}</span>
    </div>
  );
}

export function SucessoVazio() {
  return (
    <div className="estado estado-vazio">
      <p>A consulta terminou sem um relatório. Tente reformular a pergunta.</p>
    </div>
  );
}
