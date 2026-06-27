"""Métricas de avaliação — funções PURAS (sem I/O, sem LLM), o que as torna testáveis.

Quatro sinais, alinhados ao contrato do golden (PRD §13):
- roteamento: o agente enriqueceu exatamente quando devia (controle não enriquece).
- recall de fontes: fração das `fontes_esperadas` que o agente recuperou (grounding).
- precisão de distratores: o agente evitou citar os `distratores`.
- execução: o agente de fato mediu (rodou SQL e obteve dados não-vazios).

A faithfulness (LLM-judge) é avaliada à parte em `judge.py` — não é pura.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PontuacaoCaso:
    """Pontuação determinística de um caso (sem a faithfulness, que vem do judge)."""

    roteamento_ok: bool
    recall_fontes: float  # 0..1 — só faz sentido p/ casos que enriquecem
    distratores_citados: int
    execucao_ok: bool
    esperado_enriquece: bool  # p/ segmentar o recall (controle tem recall trivial 1.0)

    @property
    def precisao_ok(self) -> bool:
        """Nenhum distrator citado = precisão de recuperação intacta."""
        return self.distratores_citados == 0


def acerto_roteamento(esperado_enriquece: bool, fontes_recuperadas: list[str]) -> bool:
    """Roteamento correto: enriqueceu (≥1 fonte) sse o caso previa enriquecimento.

    Controle (n4/n6) prevê NÃO enriquecer — acerto = nenhuma fonte recuperada.
    """
    enriqueceu = len(fontes_recuperadas) > 0
    return enriqueceu == esperado_enriquece


def recall_fontes(esperadas: list[str], recuperadas: list[str]) -> float:
    """Fração das fontes esperadas presentes nas recuperadas. Sem esperadas → 1.0."""
    if not esperadas:
        return 1.0
    achadas = sum(1 for f in esperadas if f in set(recuperadas))
    return achadas / len(esperadas)


def conta_distratores(distratores: list[str], recuperadas: list[str]) -> int:
    """Quantos distratores (fontes plausíveis mas erradas) vazaram para a recuperação."""
    recup = set(recuperadas)
    return sum(1 for d in distratores if d in recup)


def pontuar_caso(
    *,
    esperado_enriquece: bool,
    fontes_esperadas: list[str],
    distratores: list[str],
    fontes_recuperadas: list[str],
    rodou_sql: bool,
    dados_nao_vazios: bool,
) -> PontuacaoCaso:
    """Combina os sinais determinísticos de um caso."""
    return PontuacaoCaso(
        roteamento_ok=acerto_roteamento(esperado_enriquece, fontes_recuperadas),
        recall_fontes=recall_fontes(fontes_esperadas, fontes_recuperadas),
        distratores_citados=conta_distratores(distratores, fontes_recuperadas),
        execucao_ok=rodou_sql and dados_nao_vazios,
        esperado_enriquece=esperado_enriquece,
    )


@dataclass(frozen=True)
class Agregado:
    """Resumo do eval inteiro — o que vira o número de baseline."""

    n_casos: int
    roteamento_ok: int
    recall_medio: float  # sobre todos os casos (controles inflam: têm recall trivial 1.0)
    recall_medio_central: float  # SÓ casos que enriquecem — o número honesto de grounding
    casos_sem_distrator: int
    execucao_ok: int
    faithfulness_media: float | None  # None se o judge não rodou


def agregar(pontuacoes: list[PontuacaoCaso], faithfulness: list[float] | None = None) -> Agregado:
    """Agrega as pontuações dos casos num resumo (médias e contagens)."""
    n = len(pontuacoes)
    if n == 0:
        return Agregado(0, 0, 0.0, 0.0, 0, 0, None)
    recall_medio = sum(p.recall_fontes for p in pontuacoes) / n
    # Recall central: média só sobre casos que deviam enriquecer (controle não conta).
    centrais = [p.recall_fontes for p in pontuacoes if p.esperado_enriquece]
    recall_central = sum(centrais) / len(centrais) if centrais else 0.0
    faith_media = sum(faithfulness) / len(faithfulness) if faithfulness else None
    return Agregado(
        n_casos=n,
        roteamento_ok=sum(1 for p in pontuacoes if p.roteamento_ok),
        recall_medio=recall_medio,
        recall_medio_central=recall_central,
        casos_sem_distrator=sum(1 for p in pontuacoes if p.precisao_ok),
        execucao_ok=sum(1 for p in pontuacoes if p.execucao_ok),
        faithfulness_media=faith_media,
    )
