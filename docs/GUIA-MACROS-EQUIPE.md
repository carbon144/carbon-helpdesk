# Respostas Rapidas — Guia pra Equipe

---

## Uma coisa muda tudo.

Ate ontem, voces escreviam a mesma resposta de rastreio 30 vezes por dia.
Cada uma levava 2-3 minutos. Multiply por 30. Da quase 1 hora e meia.
Escrevendo. A mesma. Coisa.

Acabou.

---

## O que sao Respostas Rapidas?

Respostas prontas. Ja escritas. Com o nome do cliente, numero do ticket, rastreio — tudo preenchido sozinho.

Voce so digita `/`, escolhe e envia.

**2 segundos. Nao 2 minutos.**

---

## Como usar (tem 2 jeitos)

### Jeito rapido: digite `/`

Na caixa de resposta de qualquer ticket:

```
/rastreio     → resposta com rastreio do pedido
/garantia     → inicia analise de garantia
/guacu        → explica que GUACU = Carbon
/encerr       → fecha o atendimento
```

Funciona igual pesquisa. Digita qualquer parte do nome e aparece.

Setas pra navegar. Enter pra selecionar. Pronto.

### Jeito visual: botao Macros

Do lado do botao Enviar tem um botao com icone de raio. Clica nele.

- **1 clique** = insere o texto (voce revisa antes de enviar)
- **2 cliques rapidos** = envia direto

---

## As 22 macros que voces tem

Organizadas por categoria. Igual os tickets.

### Meu Pedido (6 macros)

| Digita... | Pra que serve |
|-----------|--------------|
| `/rastreio` | "Cade meu pedido?" — responde com codigo e status |
| `/caminho` | Confirmar que o pedido saiu do CD |
| `/nota` | Enviar nota fiscal |
| `/nao receb` | Cliente nao recebeu — pedir endereco pra checar |
| `/incompleto` | Faltou item — pedir foto do que chegou |
| `/cancelar` | Cliente quer cancelar — explica o processo |

### Garantia (5 macros)

| Digita... | Pra que serve |
|-----------|--------------|
| `/analise` | Pedir fotos, video, perguntas sobre o defeito |
| `/aprovada` | Garantia OK — orienta troca. *Ja adiciona tag automatico* |
| `/negada` | Mau uso (agua, calor). Nao cobre |
| `/troque` | Mandar abrir no Troque Commerce |
| `/assistencia` | Explicar que nao tem reparo, so troca direta |

### Reenvio (2 macros)

| Digita... | Pra que serve |
|-----------|--------------|
| `/reenvio` | Confirmar que vamos enviar de novo. *Muda status sozinho* |
| `/extraviado` | Checar endereco antes de reenviar |

### Financeiro (2 macros)

| Digita... | Pra que serve |
|-----------|--------------|
| `/estorno` | Prazos de estorno por forma de pagamento. *Muda status* |
| `/pagamento` | Duvida sobre formas de pagamento e compensacao |

### Duvida (4 macros)

| Digita... | Pra que serve |
|-----------|--------------|
| `/produto` | Specs do relogio (Bluetooth, bateria, IP67) |
| `/como usar` | Primeiro uso, app, pareamento |
| `/solicitar` | Pedir numero do pedido + modelo + descricao |
| `/encerr` | "Fico feliz em ter ajudado!" — fechar atendimento |

### Reclamacao (3 macros)

| Digita... | Pra que serve |
|-----------|--------------|
| `/guacu` | GUACU = Carbon. Mesma empresa. Nao eh golpe. *Adiciona tag* |
| `/acolhimento` | Reclamacao forte — acolher, pedir detalhes. *Sobe prioridade* |
| `/escalar` | Caso grave — mandar pro supervisor. *Status URGENTE automatico* |

---

## O que sao acoes automaticas?

Algumas macros fazem mais do que colar texto. Elas mudam o ticket sozinhas.

Voce reconhece elas pelo icone de engrenagem no dropdown.

Exemplos:
- `/aprovada` → adiciona tag `garantia_aprovada` no ticket
- `/reenvio` → muda status pra "Aguardando" + tag `reenvio`
- `/escalar` → muda pra URGENTE + ESCALADO

**Voce nao precisa clicar em nada.** A macro faz tudo.

---

## O texto se adapta sozinho

As macros usam variaveis. Parecem assim no template:

```
Oi, {{cliente}}! Seu pedido {{numero}} esta com rastreio {{rastreio}}.
```

Mas quando voce usa, vira:

```
Oi, Maria Santos! Seu pedido #5432 esta com rastreio NX123456789BR.
```

O sistema preenche com os dados reais do ticket. Automatico.

---

## 3 regras. So 3.

**1. Sempre revise antes de enviar.**
A macro e um rascunho inteligente, nao uma resposta final. Leia, veja se faz sentido pro caso e envie.

**2. Nao invente.**
Se a macro diz algo que voce nao tem certeza (tipo codigo de rastreio que nao apareceu), apaga essa parte. Melhor resposta incompleta do que resposta errada.

**3. Escalar e serio.**
A macro de escalacao muda pra URGENTE e vai pro supervisor. Use so pra casos reais: Procon, advogado, chargeback, cliente reincidente grave. Duvida simples nao escala.

---

## Voce pode criar as suas

Menu lateral → **Respostas Rapidas** → **Nova Macro**

Se voce perceber que escreve a mesma coisa 3 vezes, cria uma macro.

Dica: nome curto e direto. "Rastreio" funciona melhor que "Resposta padronizada sobre status de entrega do produto ao cliente".

---

## Em resumo

| Antes | Agora |
|-------|-------|
| 2-3 min por resposta de rastreio | 2 segundos |
| Copiar texto de outro ticket | Digita `/` e pronto |
| Esquecer de mudar status | Macro muda sozinha |
| Resposta diferente cada agente | Mesma qualidade, todo mundo |
| 90 min/dia digitando repeticao | 90 min/dia resolvendo de verdade |

---

*Menos tempo digitando. Mais tempo resolvendo.*
