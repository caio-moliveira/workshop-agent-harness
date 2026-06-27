"""Templates de SQL determinísticos por KPI (ADR 0004).

O LLM escolhe `kpi_alvo` + `dimensao` (nó `planejar`); aqui o código monta o SQL —
mesmo input, mesmo SQL, mesmo resultset. Tudo passa pelos guardrails do `run_sql` e pelo
papel `agente_ro`. Valores de dimensão vêm do catálogo (validados); escapamos aspas por
segurança defensiva.
"""

from __future__ import annotations

from agent.periodo import JanelasTemporais

# KPIs medidos sobre a tabela `pedidos` (mesma forma; muda só a expressão de agregação).
_EXPR_KPI: dict[str, str] = {
    "faturamento": "round(sum(p.valor_total), 2)",
    "ticket_medio": "round(sum(p.valor_total) / nullif(count(*), 0), 2)",
    "taxa_recompra": (
        "round(avg((EXISTS (SELECT 1 FROM negocio.pedidos a "
        "WHERE a.cliente_id = p.cliente_id AND a.data_pedido < p.data_pedido))::int), 3)"
    ),
}

# Dimensão -> (join, coluna de nome) para filtrar sobre `pedidos p`.
_JOIN_DIM: dict[str, tuple[str, str]] = {
    "regiao": ("JOIN negocio.regioes d ON d.id = p.regiao_id", "d.nome"),
    "canal": ("JOIN negocio.canais d ON d.id = p.canal_id", "d.nome"),
}


class TemplateNaoSuportadoError(ValueError):
    """Combinação KPI×dimensão fora do que esta fatia (ADR 0004) cobre."""


def _escapa(valor: str) -> str:
    return valor.replace("'", "''")


def _fragmento_dimensao(dimensao: dict[str, str]) -> tuple[str, str]:
    """(join, condição WHERE) para a dimensão. Vazio = agregado (sem recorte)."""
    if not dimensao:
        return "", ""
    if len(dimensao) != 1:
        raise TemplateNaoSuportadoError("Apenas uma dimensão por consulta nesta fatia.")
    ((chave, valor),) = dimensao.items()
    if chave not in _JOIN_DIM:
        raise TemplateNaoSuportadoError(f"Dimensão {chave!r} não suportada por template.")
    join, coluna = _JOIN_DIM[chave]
    return join, f" AND {coluna} = '{_escapa(valor)}'"


# Dimensão -> (join na metas, coluna de nome, demais eixos que devem ser NULL na meta).
_META_DIM: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "regiao": (
        "JOIN negocio.regioes dm ON dm.id = m.regiao_id",
        "dm.nome",
        ("canal_id", "categoria_id"),
    ),
    "canal": (
        "JOIN negocio.canais dm ON dm.id = m.canal_id",
        "dm.nome",
        ("regiao_id", "categoria_id"),
    ),
}


def _consulta_meta(kpi: str, dimensao: dict[str, str], j: JanelasTemporais) -> str:
    """Meta de referência: a mais recente cadastrada ATÉ o mês-alvo.

    O mês-alvo (mês+1) costuma ser futuro e não ter meta; usamos a meta mais recente
    disponível (≤ alvo) como referência. Eixos não usados ficam NULL na tabela.
    """
    alvo = j.ano_alvo * 100 + j.mes_alvo
    base = (
        f"SELECT m.valor_meta AS valor_meta FROM negocio.metas m {{join}} "
        f"WHERE m.kpi = '{_escapa(kpi)}' AND (m.ano * 100 + m.mes) <= {alvo}"
    )
    ordem = " ORDER BY m.ano DESC, m.mes DESC LIMIT 1"
    if not dimensao:
        return base.format(join="") + (
            " AND m.regiao_id IS NULL AND m.canal_id IS NULL AND m.categoria_id IS NULL" + ordem
        )
    ((chave, valor),) = dimensao.items()
    if chave not in _META_DIM:
        raise TemplateNaoSuportadoError(f"Meta não suportada para dimensão {chave!r}.")
    join, coluna, nulos = _META_DIM[chave]
    cond_nulos = " ".join(f"AND m.{c} IS NULL" for c in nulos)
    return base.format(join=join) + f" AND {coluna} = '{_escapa(valor)}' {cond_nulos}{ordem}"


def _consultas_pedidos(kpi: str, dimensao: dict[str, str], j: JanelasTemporais) -> dict[str, str]:
    expr = _EXPR_KPI[kpi]
    join, cond = _fragmento_dimensao(dimensao)
    ini = j.inicio_tendencia.isoformat()
    fim = f"{j.ano_alvo:04d}-{j.mes_alvo:02d}-01"  # limite superior exclusivo (1º dia do alvo)
    anos = ", ".join(str(a) for a in j.anos_sazonais)

    tendencia = (
        f"SELECT to_char(date_trunc('month', p.data_pedido), 'YYYY-MM') AS mes, "
        f"{expr} AS valor "
        f"FROM negocio.pedidos p {join} "
        f"WHERE p.status = 'pago'{cond} "
        f"AND p.data_pedido >= DATE '{ini}' AND p.data_pedido < DATE '{fim}' "
        f"GROUP BY 1 ORDER BY 1"
    )
    sazonal = (
        f"SELECT extract(year FROM p.data_pedido)::int AS ano, {expr} AS valor "
        f"FROM negocio.pedidos p {join} "
        f"WHERE p.status = 'pago'{cond} "
        f"AND extract(month FROM p.data_pedido) = {j.mes_alvo} "
        f"AND extract(year FROM p.data_pedido) IN ({anos}) "
        f"GROUP BY 1 ORDER BY 1"
    )
    return {"tendencia": tendencia, "sazonal": sazonal, "meta": _consulta_meta(kpi, dimensao, j)}


def _consultas_conversao(dimensao: dict[str, str], j: JanelasTemporais) -> dict[str, str]:
    """taxa_conversao = pedidos / sessões (denominador em sessoes_diarias).

    Numerador = TODOS os pedidos (não só `status='pago'`), por definição da conversão
    (pedido feito ÷ visita) — alinhado ao golden N3. Difere dos KPIs de faturamento/ticket,
    que medem só pedidos pagos.

    Nota: a conversão não emite resultset `sazonal`, então a saúde depende da `meta` existir
    (o seed sempre tem meta de conversão); sem ela cairia em "estável vs anos anteriores".
    """
    if not dimensao:
        cond = ""
        join_p = join_s = ""
    else:
        ((chave, valor),) = dimensao.items()
        valor = _escapa(valor)
        if chave == "canal":
            join_p = "JOIN negocio.canais d ON d.id = p.canal_id"
            join_s = "JOIN negocio.canais d ON d.id = s.canal_id"
        elif chave == "regiao":
            join_p = "JOIN negocio.regioes d ON d.id = p.regiao_id"
            join_s = "JOIN negocio.regioes d ON d.id = s.regiao_id"
        else:
            raise TemplateNaoSuportadoError(f"Conversão não suporta dimensão {chave!r}.")
        cond = f" AND d.nome = '{valor}'"
    ini = j.inicio_tendencia.isoformat()
    fim = f"{j.ano_alvo:04d}-{j.mes_alvo:02d}-01"
    tendencia = (
        f"SELECT to_char(a.d, 'YYYY-MM') AS mes, "
        f"round(a.ped::numeric / nullif(b.sess, 0), 4) AS valor "
        f"FROM (SELECT date_trunc('month', p.data_pedido) d, count(*) ped "
        f"      FROM negocio.pedidos p {join_p} "
        f"      WHERE p.data_pedido >= DATE '{ini}' AND p.data_pedido < DATE '{fim}'{cond} "
        f"      GROUP BY 1) a "
        f"JOIN (SELECT date_trunc('month', s.data) d, sum(s.sessoes) sess "
        f"      FROM negocio.sessoes_diarias s {join_s} "
        f"      WHERE s.data >= DATE '{ini}' AND s.data < DATE '{fim}'{cond} "
        f"      GROUP BY 1) b USING (d) ORDER BY 1"
    )
    return {"tendencia": tendencia, "meta": _consulta_meta("taxa_conversao", dimensao, j)}


def montar_consultas(
    kpi: str, dimensao: dict[str, str], janelas: JanelasTemporais
) -> dict[str, str]:
    """Monta as consultas nomeadas (tendência/sazonal) para o KPI×dimensão."""
    if kpi == "taxa_conversao":
        return _consultas_conversao(dimensao, janelas)
    if kpi in _EXPR_KPI:
        return _consultas_pedidos(kpi, dimensao, janelas)
    raise TemplateNaoSuportadoError(f"KPI sem template: {kpi!r}.")
