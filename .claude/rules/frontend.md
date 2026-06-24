---
# Convenções do frontend React + Vite. Carrega ao tocar frontend/.
paths:
  - "frontend/**"
---

# Frontend — React + Vite (TypeScript)

UI de chat que consome o backend via nginx. Simples, tipada, com estados explícitos.

- **React + Vite + TypeScript.** Componentes funcionais + hooks. Sem class components.
- **Tipos explícitos** nas props e no contrato da API (`src/api/`). Nada de `any`.
- **Streaming:** o chat consome SSE do `/chat`. Renderize o relatório **incrementalmente** conforme
  os eventos chegam; não espere a resposta inteira.
- **Estados de UI sempre tratados:** carregando, erro, vazio e sucesso — cada um com seu componente
  (`Estados.tsx`). Nunca deixe a tela "morta" durante uma requisição.
- **Fontes e SQL inspecionáveis:** o analista precisa ver as fontes citadas e o SQL executado. Não
  esconda o rastro — exponha o que o agente usou.
- **Chamadas à API isoladas em `src/api/`**, não espalhadas pelos componentes.
- **Sem segredo no bundle.** A única origem é o nginx (mesma porta); não aponte para serviços
  internos direto.
