"""Agregação dos resultados por item, veredito pass/fail por threshold e relatório legível."""

from __future__ import annotations

from dataclasses import dataclass, field

from evals.comparadores import ResultadoGrounding
from evals.juiz import NotaJuiz


@dataclass(frozen=True)
class Limiares:
    """Thresholds do gate. Abaixo disso, o item (e o agregado) reprova."""

    faithfulness: float = 0.7
    answer_relevancy: float = 0.7
    taxa_aprovacao: float = 0.8  # fração mínima de itens aprovados p/ o veredito agregado passar


@dataclass
class ResultadoItem:
    """O placar de um item do golden."""

    id: str
    eh_controle: bool
    exec_golden_ok: bool = False
    exec_agente_ok: bool = False
    routing_ok: bool = False
    grounding: ResultadoGrounding | None = None
    nota: NotaJuiz | None = None
    erro: str | None = None

    def passou(self, lim: Limiares) -> bool:
        """Critério de aprovação do item (depende de ser controle ou de enriquecimento)."""
        if self.erro is not None:
            return False
        if not (self.exec_golden_ok and self.routing_ok):
            return False
        if self.eh_controle:
            # Controle: basta não enriquecer (routing) e o golden ser válido.
            return True
        # Enriquecimento: grounding firme + SQL do agente válido + juiz acima do limiar.
        if self.grounding is None or not self.grounding.ok:
            return False
        if not self.exec_agente_ok:
            return False
        if self.nota is None:
            return False
        return (
            self.nota.faithfulness >= lim.faithfulness
            and self.nota.answer_relevancy >= lim.answer_relevancy
        )


@dataclass
class Veredito:
    """Resultado agregado do eval."""

    itens: list[ResultadoItem] = field(default_factory=list)
    limiares: Limiares = field(default_factory=Limiares)

    @property
    def aprovados(self) -> int:
        return sum(1 for i in self.itens if i.passou(self.limiares))

    @property
    def total(self) -> int:
        return len(self.itens)

    @property
    def taxa(self) -> float:
        return self.aprovados / self.total if self.total else 0.0

    @property
    def passou(self) -> bool:
        """Gate verde: taxa de aprovação ≥ limiar agregado."""
        return self.taxa >= self.limiares.taxa_aprovacao


def formatar_relatorio(veredito: Veredito) -> str:
    """Relatório legível (uma linha por item + agregado) para terminal/CI."""
    linhas = ["# Eval EDD — resultado", ""]
    linhas.append(f"{'item':<24} {'pass':<5} {'exec':<5} {'rout':<5} {'grnd':<5} {'faith':<6} {'rel':<5}")
    linhas.append("-" * 60)
    for it in veredito.itens:
        if it.erro is not None:
            linhas.append(f"{it.id:<24} FAIL  erro: {it.erro}")
            continue
        grnd = "-" if it.grounding is None else ("ok" if it.grounding.ok else "x")
        faith = "-" if it.nota is None else f"{it.nota.faithfulness:.2f}"
        rel = "-" if it.nota is None else f"{it.nota.answer_relevancy:.2f}"
        passou = "PASS" if it.passou(veredito.limiares) else "FAIL"
        linhas.append(
            f"{it.id:<24} {passou:<5} "
            f"{('ok' if it.exec_agente_ok or it.eh_controle else 'x'):<5} "
            f"{('ok' if it.routing_ok else 'x'):<5} {grnd:<5} {faith:<6} {rel:<5}"
        )
    linhas.append("-" * 60)
    veredito_txt = "VERDE (pass)" if veredito.passou else "VERMELHO (fail)"
    linhas.append(
        f"Agregado: {veredito.aprovados}/{veredito.total} aprovados "
        f"(taxa {veredito.taxa:.0%}, limiar {veredito.limiares.taxa_aprovacao:.0%}) -> {veredito_txt}"
    )
    return "\n".join(linhas)
