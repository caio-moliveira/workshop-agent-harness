"""seed/generate.py — gerador determinístico do dataset sintético.

E-commerce de varejo, ~5 anos de histórico, com SAZONALIDADE + TENDÊNCIA e as
NARRATIVAS PLANTADAS (lado quantitativo) descritas em `seed/NARRATIVAS.md`.

Princípios:
  - Determinístico (RNF-05): mesma SEED -> mesmo dataset.
  - Sem agente / sem LLM (invariante #1: ingestão é offline e determinística).
  - As narrativas não são ruído: são padrões plantados, rastreáveis por SQL, que
    depois casam com os documentos de `diagnostico`/`prescricao` e com o golden
    dataset (EDD). Aqui geramos só o lado Postgres.

Escreve um CSV por tabela em `seed/data/`. Carregue com `seed/load.py`.

Uso:
    uv run python seed/generate.py
"""

from __future__ import annotations

import calendar
import csv
import random
from datetime import date
from pathlib import Path

from faker import Faker

# ============================ Configuração ===================================
SEED = 42
ANO_INICIO, MES_INICIO = 2021, 7   # 60 meses -> jun/2026 (hoje=2026-06-16; "próximo mês"=jul/2026)
ANO_FIM, MES_FIM = 2026, 6
PEDIDOS_MES_BASE = 1800            # volume médio/mês antes dos fatores (escala da POC)
BASE_RECOMPRA = 0.62              # fração de pedidos vinda de clientes recorrentes (regime normal)
CRESC_ANUAL = 0.08               # tendência de crescimento (~8% a.a.)
DATA_DIR = Path(__file__).parent / "data"

rng = random.Random(SEED)
fake = Faker("pt_BR")
fake.seed_instance(SEED)

# ============================ Dimensões ======================================
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
PESO_REGIAO = {"Norte": 0.08, "Nordeste": 0.20, "Centro-Oeste": 0.10, "Sudeste": 0.44, "Sul": 0.18}

CANAIS = ["site_proprio", "marketplace", "loja_fisica"]
PESO_CANAL = {"site_proprio": 0.45, "marketplace": 0.35, "loja_fisica": 0.20}

CATEGORIAS = [
    "Eletrônicos", "Moda", "Casa & Decoração", "Beleza",
    "Esporte & Lazer", "Alimentos & Bebidas", "Livros & Papelaria", "Brinquedos",
]
PESO_CATEGORIA = {
    "Eletrônicos": 0.22, "Moda": 0.20, "Casa & Decoração": 0.14, "Beleza": 0.12,
    "Esporte & Lazer": 0.10, "Alimentos & Bebidas": 0.10,
    "Livros & Papelaria": 0.06, "Brinquedos": 0.06,
}
# faixa de preço base típica (R$) por categoria
FAIXA_PRECO = {
    "Eletrônicos": (120, 4500), "Moda": (40, 400), "Casa & Decoração": (30, 900),
    "Beleza": (20, 250), "Esporte & Lazer": (40, 1200), "Alimentos & Bebidas": (15, 180),
    "Livros & Papelaria": (15, 150), "Brinquedos": (25, 500),
}
# substantivos para nomear produtos de forma crível
NOMES_PRODUTO = {
    "Eletrônicos": ["Smartphone", "Fone Bluetooth", "Smart TV", "Notebook", "Caixa de Som",
                    "Smartwatch", "Tablet", "Carregador Turbo"],
    "Moda": ["Camiseta", "Tênis", "Calça Jeans", "Jaqueta", "Vestido", "Mochila", "Boné"],
    "Casa & Decoração": ["Jogo de Panelas", "Luminária", "Tapete", "Edredom", "Cafeteira",
                          "Conjunto de Toalhas"],
    "Beleza": ["Perfume", "Kit Skincare", "Secador", "Batom", "Shampoo Premium", "Máscara Facial"],
    "Esporte & Lazer": ["Bicicleta", "Halteres", "Tênis de Corrida", "Barraca", "Bola",
                         "Esteira Dobrável"],
    "Alimentos & Bebidas": ["Café Especial", "Kit Vinhos", "Chocolate Belga", "Azeite Extra",
                            "Cesta Gourmet"],
    "Livros & Papelaria": ["Romance Best-seller", "Caderno Premium", "Box de Livros",
                            "Caneta Tinteiro", "Agenda 2026"],
    "Brinquedos": ["Lego City", "Boneca Articulada", "Carrinho de Controle", "Quebra-cabeça",
                    "Jogo de Tabuleiro"],
}
LINHAS = ["Essential", "Pro", "Max", "Lite", "Plus", "Eco", "Prime", "Studio", "Air", "Ultra"]

SAZONAL = {1: 0.85, 2: 0.80, 3: 0.95, 4: 0.97, 5: 1.10, 6: 0.95, 7: 0.96,
           8: 0.98, 9: 1.00, 10: 1.08, 11: 1.50, 12: 1.32}

CONV_BASE = {"site_proprio": 0.028, "marketplace": 0.022, "loja_fisica": 0.120}

# id estável = índice + 1
RID = {nome: i + 1 for i, nome in enumerate(REGIOES)}
CID = {nome: i + 1 for i, nome in enumerate(CANAIS)}
CATID = {nome: i + 1 for i, nome in enumerate(CATEGORIAS)}


# ============================ Narrativas plantadas ===========================
# Cada função devolve um MULTIPLICADOR aplicado sobre a baseline. Ver NARRATIVAS.md.
def mult_volume(regiao: str, canal: str, ano: int, mes: int) -> float:
    m = 1.0
    # N5 — loja física em declínio estrutural (~-11% a.a.)
    if canal == "loja_fisica":
        m *= max(0.45, 1 - 0.11 * (ano - ANO_INICIO))
    # N1 — leve queda de volume no Sul no 1º semestre de 2026 (o forte é a recompra)
    if regiao == "Sul" and ano == 2026 and 1 <= mes <= 6:
        m *= 0.96
    return m


def mult_recompra(regiao: str, ano: int, mes: int) -> float:
    # N1 — recompra no Sul cai ~18-20% no 1º semestre de 2026
    if regiao == "Sul" and ano == 2026 and 1 <= mes <= 6:
        return 0.80
    return 1.0


def mult_conversao(canal: str, ano: int, mes: int) -> float:
    m = 1.0
    ym = ano * 12 + mes
    # N3 — conversão do site próprio fraca no inverno (jun-ago)...
    if canal == "site_proprio" and mes in (6, 7, 8):
        m *= 0.72
    # ...até o redesign de checkout em fev/2026, que reverte o quadro
    if canal == "site_proprio" and ym >= 2026 * 12 + 2:
        m *= 1.28
    return m


def mult_categoria(categoria: str, canal: str, regiao: str, ano: int, mes: int) -> float:
    m = 1.0
    ym = ano * 12 + mes
    # N2 — Eletrônicos no marketplace despencam no 4º tri/2025
    if categoria == "Eletrônicos" and canal == "marketplace" and ano == 2025 and mes in (10, 11, 12):
        m *= 0.55
    # N4 — Beleza no Nordeste em alta saudável a partir de 2025
    if categoria == "Beleza" and regiao == "Nordeste" and ym >= 2025 * 12 + 1:
        m *= min(1 + 0.02 * (ym - 2025 * 12), 1.9)
    return m


def mult_ticket(ano: int, mes: int) -> float:
    # N6 — ticket médio sobe no Q4 (Black Friday / Natal): sazonal saudável
    return 1.18 if mes in (11, 12) else 1.0


# ============================ Utilidades =====================================
def meses():
    """Itera (ano, mes) de início a fim, inclusive."""
    ano, mes = ANO_INICIO, MES_INICIO
    while (ano, mes) <= (ANO_FIM, MES_FIM):
        yield ano, mes
        mes += 1
        if mes > 12:
            mes, ano = 1, ano + 1


def tendencia(ano: int, mes: int) -> float:
    anos = (ano * 12 + mes - (ANO_INICIO * 12 + MES_INICIO)) / 12.0
    return (1 + CRESC_ANUAL) ** anos


def ruido(spread: float = 0.10) -> float:
    return rng.uniform(1 - spread, 1 + spread)


def write_csv(nome: str, header: list[str], linhas: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    caminho = DATA_DIR / f"{nome}.csv"
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(linhas)
    print(f"  {nome:<16} {len(linhas):>8,} linhas -> {caminho.name}")


# ============================ Geração ========================================
def main() -> None:
    print(f"Gerando dataset (SEED={SEED}, {ANO_INICIO}-{MES_INICIO:02d} a {ANO_FIM}-{MES_FIM:02d})...")

    # ---- Produtos -----------------------------------------------------------
    produtos: list[tuple] = []          # (id, categoria_id, sku, nome, preco_base, ativo)
    produtos_por_cat: dict[str, list[tuple]] = {c: [] for c in CATEGORIAS}
    pid = 1
    for cat in CATEGORIAS:
        lo, hi = FAIXA_PRECO[cat]
        for base in NOMES_PRODUTO[cat]:
            for linha in rng.sample(LINHAS, k=2):   # 2 linhas por nome-base
                preco = round(rng.uniform(lo, hi), 2)
                sku = f"{cat[:3].upper()}-{pid:05d}"
                nome = f"{base} {linha}"
                row = (pid, CATID[cat], sku, nome, preco, "true")
                produtos.append(row)
                produtos_por_cat[cat].append((pid, preco))
                pid += 1

    # ---- Estado de clientes e agregados -------------------------------------
    clientes: list[tuple] = []                       # (id, nome, email, regiao_id, canal_aq_id, data_cadastro)
    clientes_por_regiao: dict[int, list[int]] = {RID[r]: [] for r in REGIOES}
    next_cliente = 1

    pedidos: list[tuple] = []
    itens: list[tuple] = []
    next_pedido = 1
    next_item = 1

    # contagem de pedidos por (regiao_id, canal_id, ano, mes) -> base das sessões
    pedidos_cel: dict[tuple, int] = {}

    # agregados para as metas (realizado mensal)
    fat_total: dict[tuple, float] = {}        # (ano,mes) -> R$ (pago)
    fat_regiao: dict[tuple, float] = {}       # (regiao_id,ano,mes)
    fat_canal: dict[tuple, float] = {}        # (canal_id,ano,mes)
    fat_categoria: dict[tuple, float] = {}    # (categoria_id,ano,mes) -> receita de itens (pago)
    ped_total: dict[tuple, int] = {}          # (ano,mes) -> qtd pedidos pagos
    ped_canal: dict[tuple, int] = {}          # (canal_id,ano,mes) -> qtd pedidos pagos
    ord_regiao: dict[tuple, int] = {}         # (regiao_id,ano,mes) -> qtd pedidos (todos)
    ret_regiao: dict[tuple, int] = {}         # (regiao_id,ano,mes) -> qtd recompra (todos)
    ord_total: dict[tuple, int] = {}
    ret_total: dict[tuple, int] = {}

    def add(d: dict, k, v=1):
        d[k] = d.get(k, 0) + v

    # ---- Loop de pedidos, mês a mês -----------------------------------------
    for ano, mes in meses():
        dias = calendar.monthrange(ano, mes)[1]
        trend = tendencia(ano, mes)
        for regiao in REGIOES:
            rid = RID[regiao]
            for canal in CANAIS:
                cid = CID[canal]
                n = (PEDIDOS_MES_BASE * PESO_REGIAO[regiao] * PESO_CANAL[canal]
                     * SAZONAL[mes] * trend * mult_volume(regiao, canal, ano, mes) * ruido())
                n = max(0, round(n))
                pedidos_cel[(rid, cid, ano, mes)] = n
                share_recompra = min(0.95, max(0.05, BASE_RECOMPRA * mult_recompra(regiao, ano, mes)))

                # pesos de categoria já com as narrativas N2/N4 deste mês×canal×região
                pesos_cat = [PESO_CATEGORIA[c] * mult_categoria(c, canal, regiao, ano, mes)
                             for c in CATEGORIAS]
                tmult = mult_ticket(ano, mes)

                for _ in range(n):
                    existentes = clientes_por_regiao[rid]
                    recompra = bool(existentes) and rng.random() < share_recompra
                    d = date(ano, mes, rng.randint(1, dias))
                    if recompra:
                        cliente_id = rng.choice(existentes)
                    else:
                        cliente_id = next_cliente
                        next_cliente += 1
                        clientes.append((cliente_id, fake.name(), fake.email(),
                                         rid, cid, d.isoformat()))
                        existentes.append(cliente_id)

                    # itens do pedido
                    cat_primaria = rng.choices(CATEGORIAS, weights=pesos_cat, k=1)[0]
                    n_itens = rng.choices([1, 2, 3, 4, 5], weights=[40, 30, 18, 8, 4], k=1)[0]
                    bruto = 0.0
                    itens_deste: list[tuple] = []
                    for i in range(n_itens):
                        cat = cat_primaria if (i == 0 or rng.random() < 0.8) \
                            else rng.choices(CATEGORIAS, weights=pesos_cat, k=1)[0]
                        prod_id, preco_base = rng.choice(produtos_por_cat[cat])
                        preco = round(preco_base * rng.uniform(0.92, 1.08) * tmult, 2)
                        qtd = rng.choices([1, 2, 3], weights=[72, 21, 7], k=1)[0]
                        bruto += preco * qtd
                        itens_deste.append((prod_id, qtd, preco, CATID[cat]))

                    bruto = round(bruto, 2)
                    desc_pct = rng.uniform(0, 0.08) + (0.12 if mes == 11 else 0.0)
                    desconto = round(bruto * desc_pct, 2)
                    if canal == "loja_fisica":
                        frete = 0.0
                    elif bruto > 200:
                        frete = 0.0                      # frete grátis acima de R$200
                    else:
                        frete = rng.choice([9.90, 14.90, 19.90])
                    status = rng.choices(["pago", "cancelado", "devolvido"],
                                         weights=[92, 5, 3], k=1)[0]
                    total = round(bruto - desconto + frete, 2)

                    pedido_id = next_pedido
                    next_pedido += 1
                    pedidos.append((pedido_id, cliente_id, cid, rid, d.isoformat(),
                                    status, bruto, desconto, frete, total))
                    for prod_id, qtd, preco, catid in itens_deste:
                        itens.append((next_item, pedido_id, prod_id, qtd, preco))
                        next_item += 1
                        if status == "pago":
                            add(fat_categoria, (catid, ano, mes), preco * qtd)

                    # agregados
                    add(ord_regiao, (rid, ano, mes)); add(ord_total, (ano, mes))
                    if recompra:
                        add(ret_regiao, (rid, ano, mes)); add(ret_total, (ano, mes))
                    if status == "pago":
                        add(fat_total, (ano, mes), total)
                        add(fat_regiao, (rid, ano, mes), total)
                        add(fat_canal, (cid, ano, mes), total)
                        add(ped_total, (ano, mes)); add(ped_canal, (cid, ano, mes))

    # ---- Sessões diárias (denominador da conversão) -------------------------
    sessoes: list[tuple] = []
    sess_canal: dict[tuple, int] = {}     # (canal_id,ano,mes) -> sessões
    sess_total: dict[tuple, int] = {}     # (ano,mes) -> sessões
    for (rid, cid, ano, mes), n_ped in pedidos_cel.items():
        canal = CANAIS[cid - 1]
        conv = CONV_BASE[canal] * mult_conversao(canal, ano, mes)
        mes_sessoes = round(n_ped / max(conv, 0.005)) if n_ped else round(50 * ruido())
        dias = calendar.monthrange(ano, mes)[1]
        restante = mes_sessoes
        for dia in range(1, dias + 1):
            s = round(mes_sessoes / dias * ruido(0.25)) if dia < dias else max(0, restante)
            restante -= s
            sessoes.append((date(ano, mes, dia).isoformat(), cid, rid, max(0, s)))
        add(sess_canal, (cid, ano, mes), mes_sessoes)
        add(sess_total, (ano, mes), mes_sessoes)

    # ---- Metas / OKRs -------------------------------------------------------
    # Regra: meta = mesmo mês do ano anterior * (1 + alvo de crescimento). Onde uma
    # narrativa deprimiu o realizado, ele cai abaixo dessa meta (= "abaixo da meta").
    # Conversão usa alvo ABSOLUTO por canal (o vale de inverno fica abaixo dele).
    metas: list[tuple] = []
    meta_id = 1

    def add_meta(ano, mes, kpi, valor, rid=None, cid=None, catid=None):
        nonlocal meta_id
        metas.append((meta_id, ano, mes, kpi, rid, cid, catid, round(valor, 4)))
        meta_id += 1

    CONV_META = {"site_proprio": 0.030, "marketplace": 0.024, "loja_fisica": 0.130}
    for ano, mes in meses():
        py = (ano - 1, mes)  # mesmo mês, ano anterior
        # faturamento (total, região, canal, categoria) -> ano anterior * 1.08
        base = fat_total.get((ano - 1, mes))
        add_meta(ano, mes, "faturamento", (base or fat_total.get((ano, mes), 0)) * (1.08 if base else 1.05))
        for r in REGIOES:
            b = fat_regiao.get((RID[r], *py))
            cur = fat_regiao.get((RID[r], ano, mes), 0)
            add_meta(ano, mes, "faturamento", (b or cur) * (1.08 if b else 1.05), rid=RID[r])
        for c in CANAIS:
            b = fat_canal.get((CID[c], *py))
            cur = fat_canal.get((CID[c], ano, mes), 0)
            add_meta(ano, mes, "faturamento", (b or cur) * (1.08 if b else 1.05), cid=CID[c])
        for cat in CATEGORIAS:
            b = fat_categoria.get((CATID[cat], *py))
            cur = fat_categoria.get((CATID[cat], ano, mes), 0)
            add_meta(ano, mes, "faturamento", (b or cur) * (1.08 if b else 1.05), catid=CATID[cat])
        # ticket_medio (total, canal) -> ano anterior * 1.03
        bt = fat_total.get((ano - 1, mes))
        pt = ped_total.get((ano - 1, mes))
        cur_t = (fat_total.get((ano, mes), 0) / ped_total.get((ano, mes), 1))
        prev_t = (bt / pt) if (bt and pt) else cur_t
        add_meta(ano, mes, "ticket_medio", prev_t * (1.03 if (bt and pt) else 1.02))
        for c in CANAIS:
            bf = fat_canal.get((CID[c], *py)); pf = ped_canal.get((CID[c], *py))
            cur = (fat_canal.get((CID[c], ano, mes), 0) / ped_canal.get((CID[c], ano, mes), 1))
            prev = (bf / pf) if (bf and pf) else cur
            add_meta(ano, mes, "ticket_medio", prev * (1.03 if (bf and pf) else 1.02), cid=CID[c])
        # taxa_recompra (total, região) -> ano anterior * 1.05
        ot = ord_total.get((ano - 1, mes)); rt = ret_total.get((ano - 1, mes), 0)
        prev = (rt / ot) if ot else BASE_RECOMPRA
        add_meta(ano, mes, "taxa_recompra", prev * 1.05)
        for r in REGIOES:
            o = ord_regiao.get((RID[r], *py)); rr = ret_regiao.get((RID[r], *py), 0)
            prev_r = (rr / o) if o else BASE_RECOMPRA
            add_meta(ano, mes, "taxa_recompra", prev_r * 1.05, rid=RID[r])
        # taxa_conversao (total, canal) -> alvo absoluto
        add_meta(ano, mes, "taxa_conversao", 0.030)
        for c in CANAIS:
            add_meta(ano, mes, "taxa_conversao", CONV_META[c], cid=CID[c])

    # ---- Escrita ------------------------------------------------------------
    print("Escrevendo CSVs:")
    write_csv("regioes", ["id", "nome"], [(RID[r], r) for r in REGIOES])
    write_csv("canais", ["id", "nome"], [(CID[c], c) for c in CANAIS])
    write_csv("categorias", ["id", "nome"], [(CATID[c], c) for c in CATEGORIAS])
    write_csv("produtos", ["id", "categoria_id", "sku", "nome", "preco_base", "ativo"], produtos)
    write_csv("clientes", ["id", "nome", "email", "regiao_id", "canal_aquisicao_id", "data_cadastro"], clientes)
    write_csv("pedidos", ["id", "cliente_id", "canal_id", "regiao_id", "data_pedido", "status",
                          "valor_bruto", "desconto", "frete", "valor_total"], pedidos)
    write_csv("itens_pedido", ["id", "pedido_id", "produto_id", "quantidade", "preco_unitario"], itens)
    write_csv("sessoes_diarias", ["data", "canal_id", "regiao_id", "sessoes"], sessoes)
    write_csv("metas", ["id", "ano", "mes", "kpi", "regiao_id", "canal_id", "categoria_id", "valor_meta"], metas)

    print(f"OK. {len(clientes):,} clientes, {len(pedidos):,} pedidos, {len(itens):,} itens, "
          f"{len(sessoes):,} sessões/dia, {len(metas):,} metas.")


if __name__ == "__main__":
    main()
