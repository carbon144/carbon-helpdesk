# Analise de Tickets Abertos — Carbon Helpdesk

**Data:** 11/03/2026
**Total de tickets abertos:** 947
**Status:** open (458), merged (252), waiting (219), escalated (17), archived (1)

---

## 1. Volume por Categoria

| Categoria | Qtd | % do Total | Idade Media (dias) |
|-----------|-----|------------|-------------------|
| meu_pedido | 324 | 34.2% | 3.8 |
| garantia | 163 | 17.2% | 6.9 |
| duvida | 142 | 15.0% | 3.5 |
| *(sem categoria)* | 108 | 11.4% | 6.4 |
| reenvio | 100 | 10.6% | 7.4 |
| reclamacao | 53 | 5.6% | 9.0 |
| financeiro | 47 | 5.0% | 5.3 |
| entrega_rastreio | 5 | 0.5% | 9.9 |
| garantia_devolucoes | 4 | 0.4% | 6.6 |
| ra_procon_juridico | 1 | 0.1% | 6.7 |

**Insights:**
- **108 tickets (11.4%) sem categoria** — triagem IA nao classificou. Idade media 6.4 dias = ficam esquecidos. ACAO: rodar reclassificacao em batch.
- **meu_pedido** domina com 34% — maioria eh "cade meu pedido". Automatizavel com rastreio.
- **reclamacao** tem a maior idade media (9.0 dias) — tickets ficam envelhecendo sem resolucao.
- **reenvio** com 7.4 dias de media indica processo lento de reenvio.

---

## 2. Top 20 Padroes de Assunto

Agrupamento manual dos 500 assuntos mais recentes:

| # | Padrao | Qtd estimada | Automatizavel? |
|---|--------|-------------|----------------|
| 1 | **"Cade meu pedido" / entrega / atraso** (nao recebeu, nao chegou, atraso, demora, quando vem) | ~98 | SIM — rastreio automatico |
| 2 | **Respostas a emails marketing** ("por que a Carbon existe", "usando metade do Carbon", "como foi atendimento") | ~68 | SIM — fechar automatico (SPAM) |
| 3 | **Reclame Aqui** (Carbon - Reclame Aqui #XXXXX) | ~58 | NAO — humano obrigatorio |
| 4 | **Defeito / problema tecnico** (defeito, parou, tela preta, trincada, visor, esquentando) | ~56 | PARCIAL — triagem IA, resposta humana |
| 5 | **Rastreio / rastreamento** (rastreio, codigo de rastreio, rastreamento) | ~46 | SIM — consulta Wonca automatica |
| 6 | **SPAM / newsletters / phishing** (OpenAI, Spotify, Bradesco, Meta, SEFAZ, NFe, PVC, TikTok) | ~40 | SIM — fechar automatico |
| 7 | **Pedido #XXXXX** (assunto generico com numero) | ~35 | PARCIAL — consultar Shopify e responder |
| 8 | **WhatsApp convertido** ([WhatsApp] Nome — mensagem) | ~34 | JA desligado como canal |
| 9 | **Estorno / reembolso / devolucao / cancelamento** | ~33 | NAO — humano obrigatorio |
| 10 | **Assunto vazio ou "(Sem assunto)"** | ~108 | RISCO — precisa ler corpo do email |
| 11 | **Entrega generica** ("Entrega", "Entrega do relogio", "Entrega de pedido") | ~25 | SIM — rastreio automatico |
| 12 | **Compra generica** ("Compra", "Compra de relogio", "Confirmacao de compra") | ~20 | SIM — status pedido automatico |
| 13 | **Pulseiras** (pulseira estourada, pulseira metal, pulseiras extras) | ~18 | PARCIAL — template garantia pulseira |
| 14 | **Relogio [modelo]** ("Relogio Carbon One Max", "Carbon Raptor", "Carbon One") | ~15 | PARCIAL — depende do conteudo |
| 15 | **Assistencia tecnica** | ~8 | NAO — encaminhar Troque |
| 16 | **Delivery Status Notification** (bounce emails) | ~8 | SIM — fechar automatico |
| 17 | **CARBON ATENDIMENTO - PEDIDO #XXXXX** | ~6 | PARCIAL — consultar historico |
| 18 | **Informacoes sobre produto/pedido** | ~6 | PARCIAL — FAQ + rastreio |
| 19 | **NF / Nota Fiscal** (NF-e, NFSe, NF 5687) | ~5 | SIM — spam fiscal, fechar |
| 20 | **Parceria / consultoria** | ~3 | SIM — fechar automatico |

---

## 3. Distribuicao de Prioridade

| Categoria | Urgente | Alta | Media | Baixa | Total |
|-----------|---------|------|-------|-------|-------|
| meu_pedido | 2 (0.6%) | 55 (17.0%) | 208 (64.2%) | 59 (18.2%) | 324 |
| garantia | 8 (4.9%) | 91 (55.8%) | 49 (30.1%) | 15 (9.2%) | 163 |
| duvida | 1 (0.7%) | 3 (2.1%) | 19 (13.4%) | 119 (83.8%) | 142 |
| *(sem categoria)* | 7 (6.5%) | — | 101 (93.5%) | — | 108 |
| reenvio | 8 (8.0%) | 74 (74.0%) | 18 (18.0%) | — | 100 |
| reclamacao | 20 (37.7%) | 15 (28.3%) | 13 (24.5%) | 5 (9.4%) | 53 |
| financeiro | 5 (10.6%) | 27 (57.4%) | 12 (25.5%) | 3 (6.4%) | 47 |

**Insights:**
- **reclamacao** tem 37.7% urgente — faz sentido (Reclame Aqui = prazo curto).
- **garantia** com 55.8% alta — volume significativo, Tauane eh responsavel por 107 desses.
- **reenvio** com 74% alta — clientes que nao receberam e ja foram confirmados pra reenvio.
- **duvida** com 83.8% baixa — correto, maioria eh pergunta simples. Mas 40+ sao SPAM classificados errado.

---

## 4. Carga de Trabalho por Agente

| Agente | Tickets | % | Idade Media | Top Categoria |
|--------|---------|---|-------------|---------------|
| Tauane Teles | 232 | 24.5% | 5.6 dias | garantia (107), meu_pedido (42) |
| Luana | 197 | 20.8% | 5.6 dias | meu_pedido (76), reenvio (35) |
| *(nao atribuido)* | 171 | 18.1% | 6.5 dias | meu_pedido (76), duvida (22) |
| Daniele Marques | 163 | 17.2% | 4.4 dias | meu_pedido (60), duvida (27) |
| Reinan Coutinho | 116 | 12.2% | 3.7 dias | meu_pedido (59), duvida (27) |
| Victor Lima | 48 | 5.1% | 7.0 dias | meu_pedido (11), reclamacao (8) |
| Lyvia Ribeiro | 20 | 2.1% | 5.9 dias | duvida (14), reclamacao (3) |

**Insights:**
- **171 tickets (18.1%) NAO ATRIBUIDOS** — round-robin nao pegou, ou foram criados antes do sistema de triagem.
- **Tauane esta sobrecarregada** com 232 tickets, sendo 107 de garantia (quase todos). Gargalo claro.
- **Victor tem poucos tickets (48) mas a maior idade media (7.0 dias)** — tickets dificeis acumulando.
- **Reinan tem a melhor performance** — 116 tickets com idade media 3.7 dias (mais recentes, resolvendo rapido).
- **Lyvia praticamente inativa** — so 20 tickets, maioria duvida.

---

## 5. Analise de Idade dos Tickets

| Faixa | Qtd | % |
|-------|-----|---|
| 0-3 dias | 397 | 41.9% |
| 4-7 dias | 216 | 22.8% |
| 8-14 dias | 288 | 30.4% |
| 15-30 dias | 46 | 4.9% |
| >30 dias | 0 | 0% |

**Total com mais de 7 dias: 334 (35.3%)**
**Total com mais de 14 dias: 46 (4.9%)**

**Insights:**
- **288 tickets entre 8-14 dias** eh o maior problema — sao da semana passada que nao foram resolvidos.
- **46 tickets com 15-30 dias** sao casos criticos que provavelmente precisam de escalonamento.
- Nenhum ticket com +30 dias = cleanup automatico esta funcionando (ou sistema eh recente).

---

## 6. Cobertura do Auto-Reply

| Categoria | Auto-replied | Manual | Taxa Auto-Reply |
|-----------|-------------|--------|-----------------|
| meu_pedido | 74 | 250 | 22.8% |
| duvida | 47 | 95 | 33.1% |
| financeiro | 6 | 41 | 12.8% |
| garantia | 4 | 159 | 2.5% |
| reenvio | 3 | 97 | 3.0% |
| reclamacao | 1 | 52 | 1.9% |
| *(sem categoria)* | 0 | 108 | 0% |
| **TOTAL** | **135** | **812** | **14.3%** |

**Insights:**
- **Apenas 14.3% dos tickets recebem auto-reply** — muito baixo.
- **duvida tem a melhor taxa (33.1%)** — IA consegue responder perguntas simples.
- **garantia quase zero (2.5%)** — correto, precisa de humano.
- **sem categoria ZERO** — IA nao consegue auto-reply sem classificar primeiro.
- **OPORTUNIDADE:** meu_pedido poderia subir de 22.8% pra 60%+ se o auto-reply consultasse rastreio automaticamente.

---

## 7. Complexidade (Mensagens por Ticket)

| Categoria | Media msgs | Max msgs |
|-----------|-----------|----------|
| entrega_rastreio | 8.3 | 12 |
| *(sem categoria)* | 4.3 | 22 |
| reclamacao | 4.2 | 39 |
| ra_procon_juridico | 3.0 | 3 |
| reenvio | 2.7 | 9 |
| garantia_devolucoes | 2.5 | 3 |
| garantia | 2.4 | 12 |
| meu_pedido | 2.2 | 27 |
| financeiro | 2.1 | 8 |
| duvida | 2.0 | 10 |

**Insights:**
- **Reclamacao com media 4.2 e max 39** — clientes insatisfeitos mandam muitas msgs.
- **Tickets sem categoria com media 4.3** — conversas longas sem classificacao = provavel ida e volta sem resolucao.
- **duvida com media 2.0** — perguntas simples, uma resposta resolve. Ideal pra IA.
- **meu_pedido com media 2.2** — cliente pergunta, equipe responde com rastreio. Automatizavel.

---

## 8. SPAM / Lixo Identificado

**Total identificado: ~88 tickets (9.3% dos abertos)**

### Categorias de spam:

| Tipo | Qtd | Acao |
|------|-----|------|
| Respostas a emails marketing ("por que a Carbon existe", "usando metade") | ~33 | Fechar + regra de filtro |
| Reply ao email "Como foi seu atendimento" | ~3 | Fechar + nao criar ticket |
| SPAM puro (OpenAI, Spotify, Bradesco, CapCut, TikTok, PVC, telecom) | ~28 | Fechar + blacklist remetente |
| Delivery Status Notification (bounces) | ~8 | Fechar + filtrar por subject |
| NF/SEFAZ falsos (phishing fiscal) | ~6 | Fechar + filtrar |
| Emails em ingles/espanhol B2B | ~7 | Fechar + filtrar por idioma |
| Parceria/consultoria | ~3 | Fechar + filtrar |

**ACAO IMEDIATA RECOMENDADA:**
1. Fechar em batch os 88 tickets spam identificados
2. Criar filtro no `gmail.py:fetch_emails` para NAO criar ticket quando:
   - Subject contem `{{ first_name }}` (template nao renderizado)
   - Subject contem "Delivery Status Notification"
   - Subject contem "OpenAI", "Spotify", "Bradesco Net", "CapCut", "TikTok"
   - Subject contem "NF-e", "SEFAZ", "NFSe" (a menos que remetente seja fornecedor conhecido)
   - Remetente eh `mailer-daemon@` ou `noreply@`
   - Email em ingles puro sem numero de pedido

---

## 9. Quick Wins — Tickets Resolviveis com Template

**Estimativa: ~250 tickets (26.4%) poderiam ser resolvidos automaticamente**

### Grupo A — Resolvivel com rastreio automatico (~144 tickets)
- "Cade meu pedido" + variantes: ~98
- "Rastreio/rastreamento" explicito: ~46
- **Template:** Consultar Wonca/Correios, responder com status + link rastreio + prazo estimado por regiao.

### Grupo B — Resolvivel com status do pedido Shopify (~35 tickets)
- "Pedido #XXXXX" generico
- "Compra" generico
- **Template:** Consultar Shopify, responder com status (pago/enviado/em transito/entregue).

### Grupo C — Resolvivel com FAQ (~25 tickets)
- Entrega generica
- Informacoes sobre produto
- Contatos
- Pulseiras compativeis
- **Template:** FAQ contextualizado + link KB.

### Grupo D — Duvidas simples (~46 tickets)
- Perguntas basicas sobre produto, natacao, surf, GPS
- **Template:** Resposta FAQ + especificacoes do modelo mencionado.

**ACAO RECOMENDADA pra Carlos IA:**
1. Quando subject contem rastreio/pedido/entrega/compra + numero de pedido:
   - Consultar Shopify (status) + Wonca (rastreio)
   - Responder com informacoes completas
   - Fechar automaticamente se entregue
2. Quando subject contem duvida sobre produto:
   - Consultar KB articles
   - Responder com especificacoes + links

---

## 10. Casos Dificeis — Precisam de Humano

**Estimativa: ~200 tickets (21.1%) precisam de julgamento humano**

### Grupo A — Reclame Aqui (~58 tickets) — URGENCIA MAXIMA
- Prazo de resposta: 10 dias uteis
- Impacto: reputacao publica (nota 6.9/10 = REGULAR)
- **Agente:** Victor Lima (responsavel) — mas so tem 8 de reclamacao atribuidos
- **PROBLEMA:** Muitos RA nao estao atribuidos ou estao com outros agentes

### Grupo B — Garantia/Defeito complexo (~56 tickets)
- Tela preta, trincada, esquentando, parou de funcionar
- Precisa de diagnostico + encaminhar Troque Commerce
- **Agente:** Tauane (107 de garantia)
- **PROBLEMA:** Tauane sobrecarregada, backlog crescendo

### Grupo C — Financeiro sensivel (~33 tickets)
- Estorno, reembolso, devolucao, cancelamento
- Envolve Appmax/gateway de pagamento
- Precisa de aprovacao + processamento manual

### Grupo D — Reenvio (~100 tickets)
- Cliente confirmou que nao recebeu, reenvio autorizado
- Depende de logistica/estoque
- **GARGALO:** idade media 7.4 dias = processo de reenvio lento

### Grupo E — Legal/Procon (~3 tickets)
- Cobranca extrajudicial, advogado, Procon
- **PRIORIDADE ZERO** — responder em 24h ou menos

---

## Resumo Executivo

### Numeros-chave
- **947 tickets abertos** — volume alto
- **171 (18%) nao atribuidos** — perdidos no sistema
- **88 (9.3%) sao spam/lixo** — poluindo a fila
- **~250 (26.4%) resolviveis por IA** — oportunidade imediata
- **~200 (21.1%) precisam de humano** — foco da equipe
- **14.3% taxa de auto-reply** — muito baixa, meta deveria ser 40%+
- **334 (35.3%) com mais de 7 dias** — backlog preocupante

### Top 5 Acoes Imediatas

1. **LIMPAR SPAM (impacto: -88 tickets, tempo: 1h)**
   - Script SQL pra fechar os 88 tickets spam identificados
   - Implementar filtros no gmail.py pra prevenir novos

2. **ATRIBUIR TICKETS ORFAOS (impacto: -171 tickets no limbo)**
   - Rodar triagem em batch nos 171 nao atribuidos
   - Reclassificar os 108 sem categoria

3. **TURBINAR AUTO-REPLY (impacto: +250 tickets resolvidos por IA)**
   - Integrar consulta Shopify + Wonca no auto-reply
   - Quando tem numero de pedido no subject/body → consultar e responder
   - Meta: 40% de auto-reply em meu_pedido

4. **REBALANCEAR EQUIPE**
   - Tauane: 232 tickets (sobrecarregada) → redistribuir garantias simples
   - Victor: 48 tickets mas idade 7.0 dias → focar em RA + legal
   - Lyvia: 20 tickets → pode absorver mais duvidas/meu_pedido

5. **ACELERAR REENVIOS (impacto: -100 tickets, idade media 7.4 dias)**
   - Mapear gargalo: eh logistica? estoque? aprovacao?
   - Automatizar confirmacao de reenvio + novo codigo rastreio

### Otimizacoes para Carlos IA (Auto-Reply)

**Regras a adicionar:**

```python
# 1. SPAM FILTER — nao criar ticket
SPAM_SUBJECTS = [
    '{{ first_name }}',
    'Delivery Status Notification',
    'OpenAI', 'Spotify', 'Bradesco Net', 'CapCut',
    'TikTok', 'NF-e', 'SEFAZ', 'NFSe',
    'Partnership opportunity', 'Special offer',
    'Quick idea', 'PVC card', 'manufacturer',
    'Hello Store', 'Increasing AOV', 'Follow Up',
    'Este es un regalo', 'Este é um presente',
    'Um pequeno gesto', 'Please Check Defective',
    'Security Update', 'Action Needed',
    'Reminder: Please Respond',
]

# 2. AUTO-RESOLVE — consultar e responder
# Se subject tem rastreio/pedido/entrega + numero:
#   → Consultar Shopify + Wonca
#   → Responder com status completo
#   → Se entregue ha +5 dias → fechar automaticamente

# 3. ACK INTELIGENTE — garantia/financeiro
# Se garantia com defeito descrito:
#   → ACK com link TroqueCommerce + instrucoes foto/video
#   → Atribuir Tauane
# Se financeiro com pedido de estorno:
#   → ACK com prazo (7-10 dias uteis) + protocolo
#   → Atribuir Victor

# 4. RECLAME AQUI — deteccao + prioridade
# Se subject contem "Reclame Aqui":
#   → Prioridade URGENTE automatica
#   → Atribuir Victor
#   → NUNCA auto-reply (responder so no site RA)
```

### Metricas pra Acompanhar

| Metrica | Atual | Meta 30 dias |
|---------|-------|-------------|
| Tickets abertos | 947 | <400 |
| Taxa auto-reply | 14.3% | 40% |
| Tickets sem categoria | 108 (11.4%) | <5% |
| Tickets nao atribuidos | 171 (18.1%) | <5% |
| Idade media geral | 5.2 dias | <3 dias |
| Spam na fila | 88 (9.3%) | <1% |
| Tickets >7 dias | 334 (35.3%) | <15% |

---

*Relatorio gerado automaticamente em 11/03/2026. Dados extraidos do banco de producao carbon_helpdesk.*
