# Narrativas plantadas — dataset sintético

> Companion de `seed/generate.py`. Documenta o **enredo** de cada narrativa para
> revisão humana (passo 5 da skill `seed-data`).
>
> **Decisão D3:** o dataset não é ruído aleatório — sua espinha dorsal são 5–8
> narrativas plantadas, cada uma um **triplo rastreável**:
> 1. **padrão quantitativo** no Postgres (gerado aqui);
> 2. documento(s) de **`diagnostico`** no Qdrant que explicam o *porquê*;
> 3. documento(s) de **`prescricao`** com `resultado`, incluindo ≥1 par
>    *funcionou / não-funcionou* para alimentar o contraste da síntese (passo 7).
>
> **Estado:** triplo completo e ingerido. **(1) quantitativo** em `generate.py` →
> Postgres; **(2) diagnóstico** e **(3) prescrição** em `seed/corpus/*` → MinIO +
> Qdrant (`seed/ingest.py`); **golden dataset** em `evals/golden/narrativas.yaml`.
> As anotações "(a criar)" abaixo já correspondem a arquivos existentes em `seed/corpus/`.

## Janela e âncora temporal

- Histórico: **jul/2021 → jun/2026** (60 meses). Hoje = 2026-06-16 ⇒ "próximo
  mês" = **jul/2026**. Janelas do agente (D7): tendência = últimos 6 meses;
  sazonal = mesmo mês nos 2 anos anteriores.
- **Determinístico** (`SEED=42`): regenerar dá exatamente o mesmo dataset (RNF-05).

## Como uma narrativa "fica abaixo da meta"

A tabela `metas` é gerada por regra realista: **meta = mesmo mês do ano anterior ×
(1 + alvo de crescimento)** — faturamento ×1,08; ticket ×1,03; recompra ×1,05.
Onde uma narrativa deprimiu o realizado, ele cai **abaixo** dessa meta. A
**conversão** usa alvo **absoluto** por canal, então o vale de inverno fica abaixo
dele. Algumas narrativas aparecem pela comparação **sazonal (YoY)** mesmo sem
"furar meta" — é assim que o agente as enxerga (tendência + sazonal + meta).

---

## N1 — Recompra no Sul despenca no 1º semestre de 2026  ⟂ *funcionou/não-funcionou*

- **KPI / dimensão:** `taxa_recompra` · região = **Sul**.
- **Quantitativo:** a fração de pedidos de clientes recorrentes no Sul cai ~18–20%
  em jan–jun/2026 vs. os mesmos meses de 2024/2025 → abaixo da meta de recompra.
- **Diagnóstico (a criar):** pico de tickets de atraso de entrega após troca de
  transportadora no Sul (a partir de out/2025).
- **Prescrição (a criar):** *frete grátis acima de R$X no Sul* (2024) →
  `resultado: positivo` **(funcionou)**; *brinde genérico no pedido* (2025) →
  `resultado: nulo` **(não funcionou)**.
- **Sinal p/ o agente:** meta de recompra (Sul) + comparação sazonal.

## N2 — Eletrônicos no marketplace caem no 4º tri/2025  ⟂ *funcionou/não-funcionou*

- **KPI / dimensão:** `faturamento` · categoria = **Eletrônicos** × canal = **marketplace**.
- **Quantitativo:** receita de Eletrônicos no marketplace em out–dez/2025 ~45%
  abaixo do mesmo período de 2024 (a alta de fim de ano "não veio").
- **Diagnóstico (a criar):** mudança na regra de comissão do marketplace +
  guerra de preço com concorrência.
- **Prescrição (a criar):** *cupom agressivo* (2024) → `resultado: negativo`
  (destruiu margem, insustentável) **(não funcionou)**; *kit/bundle de acessórios*
  (2025) → `resultado: positivo` **(funcionou)**.
- **Sinal p/ o agente:** comparação **sazonal YoY** no recorte categoria×canal.

## N3 — Conversão do site próprio fraca no inverno; redesign reverte em 2026

- **KPI / dimensão:** `taxa_conversao` · canal = **site_proprio**.
- **Quantitativo:** conversão sazonalmente baixa em jun–ago (todos os anos),
  abaixo do alvo absoluto (0,030). A partir de fev/2026 sobe ~28% (redesign de
  checkout) e passa a bater a meta. **Relevante para o alvo jul/2026.**
- **Diagnóstico (a criar):** fricção no checkout mobile (NPS/tickets sobre etapas
  de pagamento).
- **Prescrição (a criar):** *redesign de checkout em página única* (início/2026) →
  `resultado: positivo`.
- **Sinal p/ o agente:** meta absoluta de conversão + sazonal (jul fraco em
  2024/2025) + tendência de melhora recente.

## N4 — Beleza no Nordeste em alta  (controle saudável — NÃO deve disparar enriquecimento)

- **KPI / dimensão:** `faturamento` · categoria = **Beleza** × região = **Nordeste**.
- **Quantitativo:** crescimento forte e consistente a partir de 2025, **acima da
  meta**. É um KPI saudável: testa o **roteamento** (passo 4) — o agente não deve
  abrir diagnóstico/prescrição para ele.
- **Triplo:** intencionalmente **sem** documentos de diagnóstico/prescrição.

## N5 — Loja física em declínio estrutural (5 anos)  ⟂ *funcionou/não-funcionou*

- **KPI / dimensão:** `faturamento` · canal = **loja_fisica**.
- **Quantitativo:** queda lenta e contínua (~11% a.a.) ao longo de 2021→2026 —
  migração do consumo para o online. Abaixo da meta de forma persistente.
- **Diagnóstico (a criar):** queda de fluxo nas lojas; público migrando p/ digital.
- **Prescrição (a criar):** *"compre online, retire na loja" (omnichannel)* (2025)
  → `resultado: positivo` (recupera parte do fluxo) **(funcionou)**; *reforma de
  vitrine* (2024) → `resultado: nulo` **(não funcionou)**.
- **Sinal p/ o agente:** tendência de longo prazo + meta de faturamento (canal).

## N6 — Ticket médio sobe no Q4  (controle sazonal saudável)

- **KPI / dimensão:** `ticket_medio` · total (mais visível em Moda/Eletrônicos).
- **Quantitativo:** ticket médio sobe ~18% em nov/dez todo ano (Black Friday /
  Natal). Comportamento **esperado e saudável** — sanidade de que o dataset tem
  sazonalidade real; não vira recomendação.

---

## Próximos passos

Feito: ✅ documentos `diagnostico`/`prescricao` (`seed/corpus/`, contrato §8.3) ·
✅ golden dataset (`evals/golden/narrativas.yaml`) · ✅ ingestão MinIO→Qdrant
(`seed/ingest.py`), sem acionar o agente (invariante #1).

Pendente (fora do escopo do seed):
1. **Runner de EDD** (`evals/run_evals.py`) que consome o golden: execution accuracy
   (compara resultset do SQL) + faithfulness/answer-relevancy (LLM-as-judge).
2. O **agente de runtime** (grafo LangGraph) que produz os runs a avaliar.
3. **Embedding multilíngue** para PT em produção (hoje a POC usa modelo EN local).
