# Triagem Page — Design

## Rota: `/triagem`

## Seções

### 1. Regras de Triagem (topo)
- Header: titulo + botao "Nova Regra"
- Lista de regras estilo builder de filtros, ordenadas por prioridade (maior primeiro)
- Cada regra eh um card horizontal:
  - [Toggle ativo] QUANDO categoria eh [chip colorido] -> Atribuir a [avatar+nome] | Prioridade [badge] | Auto-reply [toggle] [Editar] [Excluir]
- Modal de criar/editar com:
  - Nome (text), Categoria (dropdown fixo 6), Atribuir a (dropdown agentes), Prioridade ticket (dropdown 4), Auto-reply (toggle), Prioridade regra (numero)
- Rodape: texto explicativo sobre fallback round-robin

### 2. Agentes Online (abaixo)
- Cards compactos: nome, avatar, tickets abertos, ultimo acesso
- Indicador verde/cinza (online/offline)

## Visual
- Chips coloridos por categoria
- Badges de prioridade (vermelho=urgente, laranja=alta, azul=media, cinza=baixa)
- Toggle switches para ativo/inativo e auto-reply

## API Endpoints
- GET /api/triage/rules — lista regras
- POST /api/triage/rules — criar regra
- PUT /api/triage/rules/:id — editar regra
- DELETE /api/triage/rules/:id — deletar regra
- GET /api/triage/online-agents — agentes online

## Categorias fixas
meu_pedido, garantia, reenvio, financeiro, duvida, reclamacao
