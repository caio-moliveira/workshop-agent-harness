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
    """Só uma instrução por chamada (sem ';' interno)."""
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql("SELECT 1; SELECT 2", max_rows=MAX)


def test_rejeita_dml_escondido_em_cte() -> None:
    """WITH é permitido, mas DML dentro de uma CTE (Postgres) é barrado."""
    sql = "WITH x AS (DELETE FROM negocio.pedidos RETURNING id) SELECT * FROM x"
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql(sql, max_rows=MAX)


def test_rejeita_select_into() -> None:
    """SELECT ... INTO cria tabela — barrado pela allowlist de palavras."""
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql("SELECT * INTO nova FROM negocio.pedidos", max_rows=MAX)


def test_rejeita_inicio_invalido() -> None:
    """Só consultas que começam com SELECT ou WITH."""
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql("EXPLAIN SELECT 1", max_rows=MAX)


def test_rejeita_vazio() -> None:
    with pytest.raises(SQLInseguroError):
        validar_e_blindar_sql("   ", max_rows=MAX)


def test_injeta_limit_quando_ausente() -> None:
    """LIMIT é garantido quando a consulta não traz um."""
    out = validar_e_blindar_sql("SELECT id FROM negocio.pedidos", max_rows=MAX)
    assert out.endswith(f"LIMIT {MAX}")


def test_envelopa_garantindo_teto_externo() -> None:
    """O SQL é envelopado numa subconsulta com LIMIT externo (teto de linhas garantido)."""
    out = validar_e_blindar_sql("SELECT id FROM negocio.pedidos LIMIT 5", max_rows=MAX)
    assert out.endswith(f"LIMIT {MAX}")
    assert "_run_sql_sub" in out  # envelope aplicado


def test_limit_interno_em_subconsulta_nao_derrota_o_teto() -> None:
    """LIMIT só em subconsulta/CTE não limita o resultset externo — o envelope garante o teto."""
    sql = "SELECT id FROM negocio.pedidos WHERE id IN (SELECT id FROM negocio.pedidos LIMIT 1)"
    out = validar_e_blindar_sql(sql, max_rows=MAX)
    # o LIMIT externo (de nível superior) é o MAX, independentemente do LIMIT interno
    assert out.rstrip().endswith(f"LIMIT {MAX}")


def test_remove_comentarios_e_ponto_virgula_final() -> None:
    """Comentários e ';' final são removidos antes da análise/execução."""
    out = validar_e_blindar_sql("SELECT 1 -- comentário\n; ", max_rows=MAX)
    assert ";" not in out
    assert "--" not in out
    assert out.endswith(f"LIMIT {MAX}")


def test_permite_with_select() -> None:
    """WITH ... SELECT (consulta analítica legítima) passa e ganha LIMIT externo."""
    sql = "WITH t AS (SELECT 1 AS n) SELECT n FROM t"
    out = validar_e_blindar_sql(sql, max_rows=MAX)
    assert "WITH t AS" in out
    assert out.endswith(f"LIMIT {MAX}")


def test_palavra_chave_dentro_de_string_nao_e_falso_positivo() -> None:
    """'drop' como valor de string (não comando) não bloqueia a consulta."""
    sql = "SELECT id FROM negocio.pedidos WHERE status = 'drop the base'"
    out = validar_e_blindar_sql(sql, max_rows=MAX)
    assert out.endswith(f"LIMIT {MAX}")
