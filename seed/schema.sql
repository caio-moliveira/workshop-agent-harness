-- =============================================================================
-- Agente Analítico de Vendas · Schema de NEGÓCIO (e-commerce de varejo) — seed/POC
-- =============================================================================
-- Invariantes do projeto (CLAUDE.md):
--   #2/#3 — este schema é SOMENTE LEITURA para o agente em runtime. Só o schema
--   de harness é leitura/escrita. O usuário read-only do agente (run_sql) recebe
--   apenas SELECT aqui; quem cria/popula é o seed (host tool, conexão admin RW).
--
-- ATENÇÃO (regra backend.md): em produção este DDL deve ser promovido a uma
-- migration Alembic em infra/db/migrations/** SOB REVISÃO HUMANA. Mantemos aqui,
-- fora do caminho protegido, porque é o dataset sintético do workshop/POC,
-- aplicado por seed/load.py de forma idempotente.
--
-- Dimensões do dataset (DECISÃO D2): multi-região × multicanal × multicategoria,
-- com clientes recorrentes (recompra é KPI de primeira classe).
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS negocio;
SET search_path TO negocio;

-- ---------------------------------------------------------------------------
-- Dimensões
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regioes (
    id    smallint PRIMARY KEY,
    nome  text     NOT NULL UNIQUE          -- Norte | Nordeste | Centro-Oeste | Sudeste | Sul
);

CREATE TABLE IF NOT EXISTS canais (
    id    smallint PRIMARY KEY,
    nome  text     NOT NULL UNIQUE          -- site_proprio | marketplace | loja_fisica
);

CREATE TABLE IF NOT EXISTS categorias (
    id    smallint PRIMARY KEY,
    nome  text     NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS produtos (
    id            integer       PRIMARY KEY,
    categoria_id  smallint      NOT NULL REFERENCES categorias(id),
    sku           text          NOT NULL UNIQUE,
    nome          text          NOT NULL,
    preco_base    numeric(10,2) NOT NULL CHECK (preco_base > 0),
    ativo         boolean       NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS clientes (
    id                  integer  PRIMARY KEY,
    nome                text     NOT NULL,
    email               text     NOT NULL,
    regiao_id           smallint NOT NULL REFERENCES regioes(id),
    canal_aquisicao_id  smallint NOT NULL REFERENCES canais(id),
    data_cadastro       date     NOT NULL                 -- ≈ data do 1º pedido
);

-- ---------------------------------------------------------------------------
-- Fatos transacionais
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pedidos (
    id           bigint        PRIMARY KEY,
    cliente_id   integer       NOT NULL REFERENCES clientes(id),
    canal_id     smallint      NOT NULL REFERENCES canais(id),
    regiao_id    smallint      NOT NULL REFERENCES regioes(id),  -- denormalizado p/ consulta dimensional
    data_pedido  date          NOT NULL,
    status       text          NOT NULL,                         -- pago | cancelado | devolvido
    valor_bruto  numeric(12,2) NOT NULL CHECK (valor_bruto >= 0),-- soma das mercadorias
    desconto     numeric(12,2) NOT NULL DEFAULT 0 CHECK (desconto >= 0),
    frete        numeric(12,2) NOT NULL DEFAULT 0 CHECK (frete   >= 0),
    valor_total  numeric(12,2) NOT NULL CHECK (valor_total >= 0) -- bruto - desconto + frete
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id              bigint        PRIMARY KEY,
    pedido_id       bigint        NOT NULL REFERENCES pedidos(id),
    produto_id      integer       NOT NULL REFERENCES produtos(id),
    quantidade      integer       NOT NULL CHECK (quantidade > 0),
    preco_unitario  numeric(10,2) NOT NULL CHECK (preco_unitario >= 0)
);

-- Tráfego diário: denominador da taxa de conversão (sessões/visitas por canal×região).
CREATE TABLE IF NOT EXISTS sessoes_diarias (
    data       date     NOT NULL,
    canal_id   smallint NOT NULL REFERENCES canais(id),
    regiao_id  smallint NOT NULL REFERENCES regioes(id),
    sessoes    integer  NOT NULL CHECK (sessoes >= 0),
    PRIMARY KEY (data, canal_id, regiao_id)
);

-- ---------------------------------------------------------------------------
-- Metas / OKRs — definem o que é "abaixo da meta" (PRD §8.1 / RF-06).
-- Dimensões NULL = meta agregada naquele eixo. KPI em texto controlado.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS metas (
    id            integer       PRIMARY KEY,
    ano           integer       NOT NULL,
    mes           integer       NOT NULL CHECK (mes BETWEEN 1 AND 12),
    kpi           text          NOT NULL,   -- faturamento | ticket_medio | taxa_recompra | taxa_conversao
    regiao_id     smallint      REFERENCES regioes(id),
    canal_id      smallint      REFERENCES canais(id),
    categoria_id  smallint      REFERENCES categorias(id),
    valor_meta    numeric(14,4) NOT NULL
);

-- ---------------------------------------------------------------------------
-- Índices para as consultas analíticas (tendência + sazonal por dimensão)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_pedidos_data    ON pedidos (data_pedido);
CREATE INDEX IF NOT EXISTS ix_pedidos_dim     ON pedidos (regiao_id, canal_id, data_pedido);
CREATE INDEX IF NOT EXISTS ix_pedidos_cliente ON pedidos (cliente_id, data_pedido);
CREATE INDEX IF NOT EXISTS ix_itens_pedido    ON itens_pedido (pedido_id);
CREATE INDEX IF NOT EXISTS ix_itens_produto   ON itens_pedido (produto_id);
CREATE INDEX IF NOT EXISTS ix_sessoes_data    ON sessoes_diarias (data);
CREATE INDEX IF NOT EXISTS ix_metas_lookup    ON metas (kpi, ano, mes);
