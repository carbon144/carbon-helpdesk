# Changelog & Manual — Equipe Carbon Helpdesk

---

## Atualizacao: Respostas Rapidas (Macros) — Novo! (Marco 2026)

### O QUE SAO

Respostas prontas que voce insere com 1 clique (ou digitando `/`). Em vez de escrever a mesma resposta do zero toda vez, a macro ja vem pronta com o nome do cliente, numero do ticket, rastreio — tudo preenchido automaticamente.

**Antes:** digitar resposta inteira de rastreio toda vez (2-3 min)
**Agora:** digitar `/rastreio` e apertar Enter (2 segundos)

---

### COMO USAR

**Metodo 1 — Slash Command (mais rapido)**
1. Na caixa de resposta do ticket, digite `/`
2. Comece a digitar o nome da macro (ex: `/rastreio`, `/garantia`, `/guacu`)
3. Use setas pra navegar e **Enter** ou **Tab** pra selecionar
4. A resposta aparece pronta — revise e envie

**Metodo 2 — Botao Macros**
1. Clique no botao **Macros** (icone de raio) ao lado do botao Enviar
2. Clique na macro = insere o texto (voce revisa antes de enviar)
3. Duplo-clique na macro = envia direto sem revisar

---

### AS 22 MACROS DISPONIVEIS

#### Meu Pedido
| Macro | Quando usar |
|-------|------------|
| Rastreio do Pedido | Cliente pergunta "cade meu pedido?" |
| Pedido a Caminho | Confirmar que o pedido saiu |
| Nota Fiscal | Enviar NF do pedido |
| Pedido Nao Recebido | Cliente diz que nao chegou — pedir endereco |
| Pedido Incompleto | Faltou item — pedir foto |
| Cancelar Pedido | Cliente quer cancelar |

#### Garantia
| Macro | Quando usar |
|-------|------------|
| Garantia - Analise Inicial | Pedir fotos/video do defeito + perguntas |
| Garantia Aprovada | Defeito confirmado, iniciar troca *(muda tag automaticamente)* |
| Garantia Negada - Mau Uso | Agua, calor, impacto — nao cobre |
| Abrir Troque Commerce | Orientar cliente a abrir no portal de trocas |
| Assistencia Tecnica | Explicar que nao tem reparo, so troca |

#### Reenvio
| Macro | Quando usar |
|-------|------------|
| Reenvio Confirmado | Produto extraviado, vamos enviar de novo *(muda status)* |
| Extraviado - Verificacao | Confirmar endereco antes de reenviar |

#### Financeiro
| Macro | Quando usar |
|-------|------------|
| Estorno Solicitado | Confirmar estorno com prazos por forma de pagamento *(muda status)* |
| Duvida de Pagamento | Formas aceitas, prazos de compensacao |

#### Duvida
| Macro | Quando usar |
|-------|------------|
| Informacoes do Produto | Specs do Carbon Watch (Bluetooth, bateria, IP67) |
| Como Usar o Relogio | Primeiro uso, app FitCloudPro, pareamento |
| Solicitar Dados | Pedir numero de pedido + modelo + descricao |
| Encerramento | Fechar atendimento |

#### Reclamacao
| Macro | Quando usar |
|-------|------------|
| GUACU e Carbon | Cliente acha que eh golpe — explicar que GUACU = Carbon *(add tag guacu)* |
| Reclamacao - Acolhimento | Acolher cliente insatisfeito *(sobe prioridade)* |
| Escalacao para Supervisor | Caso grave, escalar *(muda pra urgente + escalated)* |

---

### ACOES AUTOMATICAS

Algumas macros fazem coisas alem de inserir texto. Voce reconhece elas pelo icone de engrenagem:

- **Garantia Aprovada** — adiciona tag `garantia_aprovada`
- **Reenvio Confirmado** — adiciona tag `reenvio` + muda status pra "Aguardando"
- **Estorno Solicitado** — adiciona tag `estorno` + muda status pra "Aguardando"
- **GUACU e Carbon** — adiciona tag `guacu`
- **Reclamacao - Acolhimento** — muda prioridade pra ALTA
- **Escalacao para Supervisor** — muda status pra ESCALADO + prioridade URGENTE

**Voce nao precisa fazer nada** — as acoes acontecem sozinhas quando voce usa a macro.

---

### VARIAVEIS

As macros usam variaveis que sao substituidas automaticamente:

| Variavel | Vira... |
|----------|---------|
| `{{cliente}}` | Nome do cliente (ex: "Maria Santos") |
| `{{agente}}` | Seu nome (ex: "Ana Silva") |
| `{{numero}}` | Numero do ticket (ex: "#1234") |
| `{{email}}` | Email do cliente |
| `{{rastreio}}` | Codigo de rastreio do ticket |
| `{{assunto}}` | Assunto do ticket |

**IMPORTANTE:** Sempre revise antes de enviar! As variaveis preenchem automaticamente, mas confira se o conteudo faz sentido pro caso.

---

### COMO CRIAR NOVAS MACROS

1. Acesse **Respostas Rapidas** no menu lateral
2. Clique em **Nova Macro**
3. Preencha: nome, categoria, texto (use as variaveis!)
4. Opcional: adicione acoes automaticas (mudar status, tag, etc)
5. Confira o preview e salve

**Dica:** nomeie suas macros de forma curta e descritiva. O slash command busca pelo nome — "Rastreio do Pedido" funciona melhor que "Resposta padrao sobre o status de entrega do produto".

---

### REGRAS

1. **SEMPRE revise** a macro antes de enviar. Ela e um ponto de partida, nao a resposta final.
2. **Personalize** se necessario. Se o caso tem nuances, adapte o texto.
3. **Nao invente informacao.** Se a macro diz algo que voce nao sabe se eh verdade pro caso, apague essa parte.
4. **Use a macro certa.** "Garantia Aprovada" so depois de confirmar que o defeito e coberto.
5. **Escalacao** so pra casos reais (Procon, advogado, chargeback, reincidente grave). Nao escale duvida simples.

---

---

## Atualizacao: IA Auto-Reply por Email (Marco 2026)

---

### O QUE MUDOU

A partir de agora, quando um cliente envia um email para o suporte, a IA da Carbon responde automaticamente:

**1. Tickets Simples (rastreio, duvida, status do pedido)**
- A IA le o email, entende o problema e responde direto
- O ticket fica como "Aguardando Cliente" (amarelo)
- Se o cliente responder, o ticket volta pra fila normalmente
- Tag no ticket: `auto_reply`

**2. Tickets que precisam de analise (garantia, financeiro, reclamacao)**
- A IA envia um ACK automatico: "Recebemos sua mensagem, retornaremos em ate 24h"
- O email inclui links uteis (rastreio, portal trocas, FAQ)
- O ticket fica "Aberto" na fila do agente — voces resolvem normalmente
- Tag no ticket: `ack`

**3. Tickets urgentes (Procon, advogado, chargeback)**
- A IA NAO responde nada. Esses vao direto pro agente com prioridade URGENTE
- Slack eh notificado automaticamente

---

### O QUE MUDA PRA VOCES

| Antes | Agora |
|-------|-------|
| Cliente esperava 58h por resposta | Cliente recebe resposta em <5 min |
| 393 tickets sem agente | Todo ticket tem dono automaticamente |
| Segunda: avalanche de 205 tickets | IA resolve FDS, segunda chega filtrada |
| 73% tickets = 1 msg simples | IA resolve esses automaticamente |
| "Peco desculpas pela demora" em toda msg | Nao precisa mais — IA respondeu na hora |

---

### COMO IDENTIFICAR TICKETS DA IA

Na inbox, os tickets da IA tem tags visiveis:
- **`auto_reply`** — IA respondeu completamente. So revisar se o cliente responder.
- **`ack`** — IA enviou confirmacao. Voces precisam resolver.
- Tickets sem tag = nunca passaram pela IA.

---

### REGRAS IMPORTANTES

1. **NAO desabilitar a IA** sem falar com Pedro. Se algo parecer errado, reportem.
2. **Revisem tickets `auto_reply`** se o cliente responder — a IA pode ter errado.
3. **Foco nos tickets `ack`** — esses sao os que precisam de voces de verdade.
4. **Tickets urgentes** (Procon, advogado, etc) continuam chegando direto pra voces. A IA nao toca neles.

---

### PRIORIDADE DE ATENDIMENTO

1. **URGENTE** (vermelho) — Procon, advogado, chargeback. SLA: 1h resposta.
2. **ALTA** (laranja) — Defeito grave, reincidente, reclamacao forte. SLA: 4h.
3. **MEDIA** (amarelo) — Trocas, problemas tecnicos, entrega. SLA: 8h.
4. **BAIXA** (verde) — Duvidas simples, elogios, feedback. SLA: 24h.

---

### CATEGORIAS DOS TICKETS

| Categoria | O que eh | Exemplo |
|-----------|----------|---------|
| meu_pedido | Quer saber onde esta o pedido | "Cade meu rastreio?" |
| garantia | Defeito, troca, devolucao | "Meu relogio nao liga" |
| reenvio | Nao chegou, quer novo envio | "Extraviou, enviem de novo" |
| financeiro | Estorno, reembolso, chargeback | "Quero meu dinheiro de volta" |
| duvida | Pre-venda, como usar, elogio | "Qual app uso pro Raptor?" |
| reclamacao | Insatisfacao, golpe, GUACU | "Isso eh golpe?" |

---

### ESCALA E COBERTURA

- **Todo ticket agora tem um agente atribuido automaticamente** (round-robin por carga)
- Se nenhum agente ta online, o sistema distribui entre todos os ativos
- **Daniele e Tauane** = modelo de efetividade. Menos mensagens, mais resolucoes.
- **Foco em FECHAR tickets**, nao em responder. Uma resposta completa > 5 respostas parciais.

---

### DUVIDAS FREQUENTES

**P: A IA pode responder errado?**
R: Ela foi programada pra NUNCA inventar informacao. Se nao sabe, manda o ACK generico. Mas revisem se algo parecer estranho.

**P: O cliente vai saber que eh IA?**
R: O email vem de "Equipe Carbon", nao de "IA" ou "Bot". O tom eh profissional e natural.

**P: E se a IA responder e o cliente nao gostar?**
R: O ticket continua na fila. Quando o cliente responde, volta pra "Aberto" e o agente assume.

**P: Funciona no final de semana?**
R: SIM. A IA responde 24/7, inclusive feriados. Eh o principal beneficio.
