from __future__ import annotations

import pytest

from agent.tools.run_sql import SQLInseguroError, validar_e_blindar_sql

MAX = 1000


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO negocio.pedidos (id) VALUES (1)",
        "UPDATE negocio.pedidos SET status='pago'",
        "DELETE FROM negocio.pedidos",
        "DROP TABLE negocio.pedidos",
        "ALTER TABLE negocio.pedidos ADD COLUMN x int",
        "CREATE TABLE t (id int)",
        "TRUNCATE negocio.pedidos",
        "GRANT SELECT ON negocio.pedidos TO outro",
    ],
)
def test_rejeita_escrita_e_ddl(sql: str) -> None:
    """Nenhuma operação de escrita/DDL passa — `negocio` é somente-leitura."""
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql(sql, max_rows=MAX)


def test_rejeita_multiplas_instrucoes() -> None:
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql("SELECT 1; SELECT 2", max_rows=MAX)


def test_rejeita_dml_escondido_em_cte() -> None:
    sql = "WITH x AS (DELETE FROM negocio.pedidos RETURNING id) SELECT * FROM x"
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql(sql, max_rows=MAX)


def test_rejeita_select_into() -> None:
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql("SELECT * INTO nova FROM negocio.pedidos", max_rows=MAX)


def test_rejeita_inicio_invalido() -> None:
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql("EXPLAIN SELECT 1", max_rows=MAX)


def test_rejeita_vazio() -> None:
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql("   ", max_rows=MAX)


def test_envelopa_garantindo_teto_externo() -> None:
    """O SQL é envelopado numa subconsulta com LIMIT externo (teto de linhas garantido)."""
    out = validar_e_blindar_sql("SELECT id FROM negocio.pedidos LIMIT 5", max_rows=MAX)
    assert out.endswith(f"LIMIT {MAX}")
    assert "_run_sql_sub" in out


def test_limit_interno_em_subconsulta_nao_derrota_o_teto() -> None:
    sql = "SELECT id FROM negocio.pedidos WHERE id IN (SELECT id FROM negocio.pedidos LIMIT 1)"
    out = validar_e_blindar_sql(sql, max_rows=MAX)
    assert out.rstrip().endswith(f"LIMIT {MAX}")


def test_remove_comentarios_e_ponto_virgula_final() -> None:
    out = validar_e_blindar_sql("SELECT 1 -- comentário\n; ", max_rows=MAX)
    assert ";" not in out
    assert "--" not in out
    assert out.endswith(f"LIMIT {MAX}")


def test_permite_with_select() -> None:
    out = validar_e_blindar_sql("WITH t AS (SELECT 1 AS n) SELECT n FROM t", max_rows=MAX)
    assert "WITH t AS" in out
    assert out.endswith(f"LIMIT {MAX}")


def test_palavra_chave_dentro_de_string_nao_e_falso_positivo() -> None:
    sql = "SELECT id FROM negocio.pedidos WHERE status = 'drop the base'"
    out = validar_e_blindar_sql(sql, max_rows=MAX)
    assert out.endswith(f"LIMIT {MAX}")
