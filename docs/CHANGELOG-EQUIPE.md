# Changelog & Manual — Equipe Carbon Helpdesk
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
