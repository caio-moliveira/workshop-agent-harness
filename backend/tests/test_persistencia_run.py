"""O run gravado expõe tudo que o avaliador (#26) precisa: tools invocadas
(run_sql + search com coleção/filtros), fontes com score e a saída estruturada.

Captura as chamadas ao repo (sem DB) ao processar um turno pelo chat_service.
"""

from typing import Any

import app.services.chat_service as svc


async def test_run_grava_tools_search_fontes_e_trace(monkeypatch: Any) -> None:
    estado_final = {
        "periodo": "2026-07",
        "premissas": ["p"],
        "relatorio": "Relatorio.",
        "achados": [{"kpi": "faturamento", "dimensao": "regiao=Sul"}],
        "fontes": [
            {"colecao": "diagnostico", "fonte": "minio://diag/sul.md", "score": 0.71},
            {"colecao": "prescricao", "fonte": "minio://presc/frete.md", "score": 0.66},
        ],
        "recomendacoes": [{"kpi": "faturamento", "fonte": "minio://presc/frete.md"}],
        "sql_log": ["SELECT 1", "SELECT 2"],
        "search_log": [
            {"colecao": "diagnostico", "filtros": {"regiao": "Sul"}, "n_hits": 1},
            {"colecao": "prescricao", "filtros": {"kpi_alvo": "faturamento"}, "n_hits": 1},
        ],
    }

    async def fake_stream(pergunta: str, callbacks: Any = None, fontes_excluidas: Any = None):
        yield "final", estado_final

    tool_calls: list[dict[str, Any]] = []
    fontes: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []

    async def cap_tool_call(run_id, ordem, tool, sql_text=None, resultado=None, args=None):  # type: ignore[no-untyped-def]
        tool_calls.append({"ordem": ordem, "tool": tool, "sql_text": sql_text, "args": args})

    async def cap_fonte(run_id, colecao, fonte=None, payload=None, score=None):  # type: ignore[no-untyped-def]
        fontes.append({"colecao": colecao, "fonte": fonte, "score": score})

    async def cap_trace(run_id, evento, dados=None):  # type: ignore[no-untyped-def]
        traces.append({"evento": evento, "dados": dados})

    async def fake_criar_sessao(rotulo: Any = None) -> str:
        return "sess-1"

    async def fake_criar_run(pergunta, sessao_id=None, pergunta_reescrita=None):  # type: ignore[no-untyped-def]
        return "run-1"

    async def fake_noop(*a: Any, **k: Any) -> None:
        return None

    async def fake_persistir(run_id: str, relatorio: str, grafico: Any) -> dict[str, str]:
        return {"relatorio": f"r/{run_id}"}

    monkeypatch.setattr(svc, "run_chat_stream", fake_stream)
    monkeypatch.setattr(svc, "get_langfuse_callbacks", lambda run_id=None: [])
    monkeypatch.setattr(svc, "get_chat_model", lambda tier="rapido": None)
    monkeypatch.setattr(svc.repo, "criar_sessao", fake_criar_sessao)
    monkeypatch.setattr(svc.repo, "criar_run", fake_criar_run)
    monkeypatch.setattr(svc.repo, "registrar_tool_call", cap_tool_call)
    monkeypatch.setattr(svc.repo, "registrar_fonte", cap_fonte)
    monkeypatch.setattr(svc.repo, "registrar_trace", cap_trace)
    monkeypatch.setattr(svc.repo, "finalizar_run", fake_noop)
    monkeypatch.setattr(svc.storage, "persistir_artefatos", fake_persistir)

    preparo = await svc.iniciar("como melhorar vendas?", None)
    # consome o gerador de streaming até o fim
    async for _ in svc.stream(preparo):
        pass

    # Tools invocadas: 2 run_sql (ordem 0,1) + 2 search (ordem 2,3) com coleção + filtros.
    run_sqls = [t for t in tool_calls if t["tool"] == "run_sql"]
    searches = [t for t in tool_calls if t["tool"] == "search"]
    assert len(run_sqls) == 2
    assert len(searches) == 2
    assert [t["ordem"] for t in tool_calls] == [0, 1, 2, 3]  # ordem contínua
    presc = next(t for t in searches if t["args"]["colecao"] == "prescricao")
    assert presc["args"]["filtros"] == {"kpi_alvo": "faturamento"}
    # Nunca data_ingestao nos filtros gravados.
    for s in searches:
        assert "data_ingestao" not in s["args"]["filtros"]

    # Fontes recuperadas com score.
    assert {f["colecao"] for f in fontes} == {"diagnostico", "prescricao"}
    assert all(f["score"] is not None for f in fontes)

    # Saída estruturada (faithfulness): recomendações com fonte.
    saida = next(t for t in traces if t["evento"] == "saida")
    assert saida["dados"]["recomendacoes"][0]["fonte"] == "minio://presc/frete.md"
