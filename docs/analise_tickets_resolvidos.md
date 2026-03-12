# Analise de Tickets Resolvidos — Carbon Helpdesk

**Data da analise:** 11 de marco de 2026
**Base de dados:** Producao (143.198.20.6)
**Total de tickets no sistema:** 2.821

---

## 1. Estatisticas Gerais de Resolucao

| Status | Quantidade |
|--------|-----------|
| Closed | 1.021 |
| Resolved | 853 |
| Open | 458 |
| Merged | 252 |
| Waiting | 219 |
| Escalated | 17 |

**Total resolvidos (closed + resolved): 1.874 tickets (66,4% do total)**

### Tempo de Resolucao

| Metrica | Valor |
|---------|-------|
| Media | 97,9 horas (~4,1 dias) |
| Mediana | 76,8 horas (~3,2 dias) |
| P90 | 216,9 horas (~9 dias) |

### SLA nos Tickets Resolvidos

| SLA | Quantidade | % |
|-----|-----------|---|
| Dentro do SLA | 1.255 | 67,0% |
| SLA estourado | 619 | 33,0% |

**1 em cada 3 tickets resolvidos estourou o SLA.** Indicador preocupante.

### Volume Semanal

| Semana | Criados | Resolvidos |
|--------|---------|-----------|
| 09/mar | 844 | 442 (52%) |
| 02/mar | 903 | 494 (55%) |
| 23/fev | 1.005 | 875 (87%) |
| 16/fev | 69 | 63 (91%) |

**Observacao:** Semanas recentes (mar) mostram queda na taxa de resolucao — backlog crescente.

### Por Fonte

| Fonte | Total | Resolvidos | % |
|-------|-------|-----------|---|
| Gmail (email) | 2.376 | 1.462 | 61,5% |
| WhatsApp | 436 | 404 | 92,7% |
| Web | 8 | 8 | 100% |

**WhatsApp tem 92,7% de resolucao** (mas foi desligado como canal de tickets na sessao 27 — agora so autoatendimento).

---

## 2. Resolucao por Categoria

| Categoria | Total | Resolvidos | % Resolucao | Avg Horas | Avg 1a Resp (h) |
|-----------|-------|-----------|-------------|-----------|-----------------|
| cancelamento | 2 | 2 | 100,0% | 183,7 | 183,7 |
| pre_venda | 2 | 2 | 100,0% | 143,3 | 143,3 |
| **reclamacao** | **209** | **156** | **74,6%** | 108,4 | 112,2 |
| **financeiro** | **178** | **131** | **73,6%** | 100,6 | 95,4 |
| **duvida** | **428** | **286** | **66,8%** | 104,8 | 80,4 |
| entrega_rastreio | 15 | 10 | 66,7% | 152,8 | 162,8 |
| **reenvio** | **256** | **156** | **60,9%** | 120,7 | 119,8 |
| **meu_pedido** | **768** | **444** | **57,8%** | 108,4 | 91,4 |
| **garantia** | **335** | **172** | **51,3%** | 106,3 | 141,7 |
| sem categoria | 623 | 515 | 82,7% | 64,8 | 50,4 |

### Destaques:

- **Garantia tem a PIOR taxa de resolucao (51,3%)** — metade dos tickets de garantia nao sao resolvidos. Tempo de primeira resposta altissimo (141,7h = quase 6 dias).
- **Meu Pedido** eh a maior categoria (768 tickets) mas so 57,8% sao resolvidos.
- **Reclamacao** tem a MELHOR taxa entre as grandes categorias (74,6%).
- **Reenvio** demora mais (120,7h media) e tem taxa de resolucao mediana (60,9%).
- **Financeiro** tem boa taxa (73,6%) e o tempo de resolucao mais rapido entre as grandes categorias (100,6h).

---

## 3. Auto-Reply por IA

| Auto-replied | Total | Resolvidos | Abertos |
|-------------|-------|-----------|---------|
| Nao | 2.679 | 1.867 | 423 |
| Sim | 142 | 7 | 35 |

**Apenas 7 de 142 tickets auto-respondidos foram resolvidos (4,9%).** A auto-reply sozinha NAO resolve — ela serve como ACK (confirmacao de recebimento).

### Auto-Reply por Categoria

| Categoria | Auto-replied | Resolvidos |
|-----------|-------------|-----------|
| meu_pedido | 78 | 4 |
| duvida | 48 | 1 |
| financeiro | 6 | 0 |
| garantia | 5 | 1 |
| reenvio | 3 | 0 |
| reclamacao | 1 | 0 |

**Conclusao:** A auto-reply atual funciona como triagem + ACK, nao como resolucao. Para o Carlos IA resolver tickets de fato, precisa de acesso a dados do pedido (Shopify) e capacidade de fornecer informacoes concretas (rastreio, status, prazos).

---

## 4. Padrao de Troca de Mensagens

| Categoria | Media Msgs | Min | Max |
|-----------|-----------|-----|-----|
| entrega_rastreio | 6,1 | 2 | 12 |
| cancelamento | 6,0 | 2 | 10 |
| **reenvio** | **4,2** | 1 | 22 |
| **reclamacao** | **3,9** | 1 | 16 |
| garantia | 3,2 | 1 | 20 |
| financeiro | 3,1 | 1 | 29 |
| duvida | 2,9 | 1 | 17 |
| meu_pedido | 2,7 | 1 | 18 |

### Classificacao por Complexidade

**Simples (1-2 msgs, resolvidos):**

| Categoria | Tickets |
|-----------|---------|
| meu_pedido | 270 |
| duvida | 178 |
| garantia | 91 |
| financeiro | 69 |
| reclamacao | 63 |
| reenvio | 53 |

**Complexos (5+ msgs, resolvidos):**

| Categoria | Tickets |
|-----------|---------|
| meu_pedido | 68 |
| reenvio | 54 |
| duvida | 46 |
| reclamacao | 43 |
| garantia | 27 |
| financeiro | 19 |

**60,8% dos tickets meu_pedido sao resolvidos com 1-2 mensagens** — candidatos ideais para automacao via IA.

---

## 5. Performance dos Agentes

| Agente | Tickets Fechados | Avg Horas Resolucao | Avg 1a Resposta (h) |
|--------|-----------------|--------------------|--------------------|
| **Daniele Marques** | **188** | 160,6 | 149,8 |
| **Tauane Teles** | **161** | 97,6 | 109,8 |
| **Victor Lima** | **133** | 88,5 | 70,1 |
| Reinan Coutinho | 86 | 143,2 | 128,2 |
| Luana | 52 | 156,9 | 116,4 |
| Lyvia Ribeiro | 51 | 67,5 | 30,7 |
| Pedro | 3 | 3,2 | 3,2 |

**Total fechados por agentes: 674 tickets** (dos 1.874 resolvidos, restante fechado por sistema/auto-close/merge).

### Destaques:

- **Daniele** fecha mais tickets (188) mas eh a mais lenta (160,6h media). Alta quantidade, baixa velocidade.
- **Lyvia** eh a mais rapida (67,5h media, 30,7h primeira resposta) mas fecha menos (51). MELHOR eficiencia individual.
- **Victor** tem o melhor equilibrio volume x velocidade (133 tickets, 88,5h media, 70,1h 1a resposta).
- **Tauane** eh a segunda em volume (161) com velocidade decente (97,6h).

---

## 6. Padroes de Escalacao

**Total de tickets escalados: 1.855** (65,7% de todos os tickets)

| Status apos escalacao | Total |
|----------------------|-------|
| Resolved | 716 |
| Closed | 478 |
| Open | 392 |
| Merged | 150 |
| Waiting | 104 |
| Escalated (ainda) | 15 |

**1.194 de 1.855 escalados foram resolvidos (64,4%).**

### Escalacao por Categoria

| Categoria | Escalados | Resolvidos pos-escalacao | % |
|-----------|----------|------------------------|----|
| meu_pedido | 471 | 260 | 55,2% |
| sem categoria | 322 | 268 | 83,2% |
| garantia | 294 | 143 | 48,6% |
| duvida | 274 | 196 | 71,5% |
| reenvio | 204 | 120 | 58,8% |
| reclamacao | 162 | 119 | 73,5% |
| financeiro | 104 | 74 | 71,2% |

**Motivo principal de escalacao:** "Sem resposta ha Xh (limite: Yh)" — escalacao automatica por SLA.

**Garantia tem a pior taxa pos-escalacao (48,6%)** — mesmo escalando, quase metade nao resolve.

---

## 7. Analise de Tags

| Tag | Qty | Significado |
|-----|-----|-------------|
| AUTO_ESCALADO | 1.179 | Escalacao automatica por SLA |
| SLA_ESTOURADO | 945 | SLA ja estourou |
| rastreamento | 451 | Cliente quer rastreio |
| auto_escalado | 404 | (duplicata lowercase) |
| chat_whatsapp | 404 | Veio do WhatsApp |
| SLA_ALERTA | 275 | Proximo de estourar |
| reenvio | 242 | Precisa de reenvio |
| duvida | 202 | Duvida geral |
| reembolso | 118 | Quer dinheiro de volta |
| reclamacao | 115 | Insatisfeito |
| suporte_tecnico | 87 | Problema com produto |
| entrega | 83 | Sobre entrega |
| garantia | 64 | Garantia |
| troca | 62 | Quer trocar |
| defeito | 59 | Produto defeituoso |
| **auto_closed** | **58** | Fechado automaticamente |
| nf | 52 | Nota fiscal |
| reincidente | 42 | Cliente voltou |
| RESGATADO_SPAM | 38 | Recuperado do spam |
| chargeback | 34 | Contestacao cartao |
| procon | 32 | Ameaca/acao Procon |

**Top 3 assuntos reais: rastreamento (451), reenvio (242), reembolso (118).**

---

## 8. Clientes Reincidentes

**491 clientes abriram 2+ tickets, totalizando 1.335 tickets (47,3% do total).**

### Top Reincidentes

| Cliente | Tickets | Resolvidos | Categorias |
|---------|---------|-----------|------------|
| Appmax (chargeback) | 18 | 18 | financeiro |
| Appmax (contato) | 17 | 7 | garantia, reclamacao |
| pedido@contatocliente.store | 16 | 10 | garantia, meu_pedido, reclamacao |
| Mail Delivery Subsystem | 14 | 5 | varias (bounces) |
| Appmax (atendimento) | 10 | 10 | duvida, garantia, reclamacao |
| Jonas Ferreira | 8 | 8 | duvida, financeiro, reclamacao |
| Lyvia (teste?) | 8 | 8 | sem categoria |
| Antonio Carlos | 8 | 6 | duvida, meu_pedido |
| Leonardo Krauel | 8 | 6 | duvida, garantia, reclamacao, reenvio |
| Selmaria Rodrigues | 7 | 1 | garantia (6 nao resolvidos!) |
| Maisa | 7 | 0 | duvida, meu_pedido, reclamacao (NENHUM resolvido!) |

### Observacoes:

- **Appmax** domina reincidentes com 45 tickets entre 3 enderecos — sao chargebacks e notificacoes automaticas. Precisa de filtro/regra.
- **Mail Delivery Subsystem** com 14 tickets = bounces sendo criados como tickets. Precisa de filtro.
- **Selmaria** (7 tickets, 1 resolvido) e **Maisa** (7 tickets, 0 resolvidos) sao clientes em situacao critica de insatisfacao.

---

## 9. EXEMPLOS REAIS DE RESPOSTAS BEM-SUCEDIDAS

Esta eh a secao mais importante — sao respostas reais de agentes que resultaram em resolucao do ticket. Servem como base de treinamento para o Carlos IA.

---

### 9.1 MEU_PEDIDO — Pedido em Processamento (Template Victor)

**Ticket #3749 | Agente: Victor Lima**

```
Ola, Vinicius! Obrigado por entrar em contato com o suporte Carbon.
Meu nome eh Victor e ficarei responsavel pelo seu atendimento.

Verifiquei o status do seu pedido #130071 e ele esta em fase de processamento, que eh a etapa de separacao e preparacao antes do envio. O prazo de processamento eh de ate 5 dias uteis.

Apos a postagem, o codigo de rastreio eh liberado e o prazo de entrega comeca a contar conforme a sua regiao. O codigo eh enviado automaticamente para o e-mail cadastrado na compra — vale conferir tambem as pastas de Spam e Lixo Eletronico.

Com o codigo disponivel, voce podera acompanhar o pedido pelo nosso site: https://carbonsmartwatch.com.br/a/rastreio

Caso o prazo de processamento seja concluido e voce nao receba o codigo de rastreio, basta responder este e-mail que verificamos para voce.
```

**Padrao:** Saudacao pessoal + status concreto do pedido + prazo + link rastreio + orientacao spam + CTA de retorno.

---

### 9.2 MEU_PEDIDO — Pedido Despachado com Rastreio (Template Daniele)

**Ticket #3394 | Agente: Daniele Marques**

```
Ola, Jonilson! Obrigado por entrar em contato com o suporte Carbon.
Meu nome eh Daniele e ficarei responsavel pelo seu atendimento.

Verifiquei que o seu pedido #129332 foi processado e despachado.

Para acompanhar o rastreamento do pedido, voce podera utilizar os seguintes sites:

Rastreamento Oficial Carbon: https://carbonsmartwatch.com.br/pages/rastreio
Rastreamento internacional: https://global.cainiao.com/
Rastreamento pelos Correios (quando o pedido chegar ao Brasil): https://rastreamento.correios.com.br/

Codigo de rastreio: NN114356996BR
Data estimada de entrega: entre 18 de Marco e 4 de Abril

Caso identifique qualquer intercorrencia ou haja novas duvidas, basta nos chamar respondendo a este e-mail.

Estamos a disposicao!
```

**Padrao:** Saudacao + pedido despachado + 3 links de rastreio + codigo + data estimada + CTA.

---

### 9.3 MEU_PEDIDO — Estorno Realizado (Template Luana)

**Ticket #2716 | Agente: Luana**

```
Ola, Jakeline. Tudo bem?

O estorno ja foi realizado de nossa parte conforme os comprovantes anexados, voce consegue verificar a veracidade do estorno com a operadora do cartao e o prazo tambem.

Se possivel quando for realizado, pedimos que avalie a solicitacao no Reclame Aqui.

Agradecemos a compreensao e permaneco a disposicao!
```

**Padrao:** Curta e direta. Estorno + comprovante + pedido de avaliacao RA. Eficiente para financeiro.

---

### 9.4 DUVIDA — Cancelamento e Estorno PIX (Template Luana)

**Ticket #1699 | Agente: Luana**

```
Ola, Adriano.

A solicitacao de cancelamento ja foi registrada. O prazo para conclusao do processo eh de ate 10 dias uteis.

O estorno ocorre conforme a forma de pagamento utilizada na compra:

- Pix: o valor eh devolvido via Pix apos a aprovacao do cancelamento no sistema.

Voce recebera as atualizacoes pelo e-mail cadastrado na compra.

Fico a disposicao!
```

**Padrao:** Confirmacao + prazo + mecanismo de estorno por forma de pagamento + atualizacoes por email.

---

### 9.5 DUVIDA — Pre-venda Tecnica (Template Reinan)

**Ticket #2478 | Agente: Reinan Coutinho**

```
Boa tarde! Tudo bem?

Agradeco pelo seu contato e pelo interesse no Carbon Raptor.

Sim, durante algumas campanhas promocionais o relogio pode ser adquirido com itens adicionais, como pulseiras extras e cabo. Essas ofertas podem variar conforme a promocao ativa no momento da compra.

Sobre suas duvidas tecnicas:

O RAPTOR tem GPS integrado?
Sim. O Carbon Raptor possui GPS integrado, permitindo registrar atividades como corrida, caminhada ou ciclismo diretamente pelo relogio.

Preciso levar o celular para as atividades fisicas?
Nao necessariamente. Como ele possui GPS proprio, o relogio pode registrar distancia e percurso mesmo sem o celular por perto. O celular eh necessario apenas para sincronizacao...
```

**Padrao:** Responde CADA pergunta individualmente + informacao tecnica precisa + tom educado.

---

### 9.6 DUVIDA — Loja Internacional (Template Daniele, em Ingles)

**Ticket #2740 | Agente: Daniele Marques**

```
Hello Camila! Thank you for contacting Carbon Support.
My name is Daniele and I will be responsible for your service.

I inform you that our online store is active and functioning normally. However, at the moment, sales are only available for deliveries within Brazil, and we do not yet offer international shipping.

If you are interested in learning more about our products, you can access our official website: https://carbonsmartwatch.com.br/

Thank you for your contact and interest in Carbon.
We remain at your disposal should you have any questions.
```

**Padrao:** Resposta em ingles quando cliente escreve em ingles. Clara e direta.

---

### 9.7 GARANTIA — Desculpa + Esclarecimento Brinde (Template Luana)

**Ticket #2884 | Agente: Luana**

```
Ola, Iran.

Antes de tudo, peco desculpas pela experiencia que voce teve ate aqui e pela demora no retorno, nos estamos com volume elevado de e-mails no momento. Mas entendo seu ponto e a insatisfacao relatada.

A pulseira preta escolhida eh um brinde adicional, enquanto o relogio ja acompanha a pulseira padrao preta. Os brindes disponiveis sao apresentados no momento da compra para escolha direta do cliente, e por esse motivo nao conseguimos realizar alteracoes posteriormente.

Lamento que essa situacao tenha gerado frustracao. Nosso objetivo eh sempre oferecer uma experiencia positiva e transparente em todo o processo.

Permaneco a disposicao caso precise de qualquer esclarecimento adicional.
```

**Padrao:** Pedido de desculpas genuino + explicacao clara da politica + empatia. Sem solucao tecnica, mas resolve pela comunicacao.

---

### 9.8 GARANTIA — Barrado Alfandega + Retirada Correios (Template Luana)

**Ticket #1567 | Agente: Luana**

```
Ola! Obrigada por entrar em contato com o suporte Carbon.
Meu nome eh Luana e ficarei responsavel pelo seu atendimento.

Eduardo,

Como o endereco estava incorreto, nao foi possivel a entrega do pacote.

Voce pode retirar na agencia dos correios informando o codigo de rastreamento: NN104841043BR

Eh obrigatorio que a retirada seja feita por voce e tenha em maos documento com foto.

O prazo para retirada eh de ate 7 dias a partir de hoje.

Segue informacoes:

Objeto aguardando retirada no endereco indicado

RUA ENGENHEIRO UBATUBA DE FARIA, 296
SARANDI
PORTO ALEGRE - RS

Fico a disposicao!
```

**Padrao:** Instrucao clara de retirada + codigo + endereco da agencia + prazo + documentos necessarios.

---

### 9.9 REENVIO — Pedido Despachado com Rastreio (Template Reinan)

**Ticket #2613 | Agente: Reinan Coutinho**

```
Ola, Gesiel! Tudo bem?
Me chamo Reinan e sou seu agente Carbon.

Peco desculpas pelo tempo de espera na resposta a sua solicitacao. Devido a alta demanda, nosso tempo de atendimento esta um pouco maior que o habitual.

Verifiquei que o seu pedido foi despachado, o senhor pode acompanhar futuras movimentacoes usando o codigo de rastreio abaixo:

Codigo de rastreio: NN114366667BR

Site da transportadora internacional: https://global.cainiao.com/

Apos o seu pedido chegar no Brasil, o senhor pode acompanhar usando o site dos correios.

Site dos correios: https://rastreamento.correios.com.br/app/index.php

Qualquer duvida, nao hesite em me contactar, estou por aqui para te ajudar!
Ate mais!

Atenciosamente,
Reinan.
```

**Padrao:** Desculpa pela demora + rastreio + links. Tom formal ("senhor").

---

### 9.10 REENVIO — Confirmacao de Substituicao (Template Tauane)

**Ticket #2473 | Agente: Tauane Teles**

```
Ola, Douglas. Tudo bem?

Obrigada pela confirmacao. Isso, o modelo para substituicao eh um Carbon Raptor.

O prazo para processamento, separacao e postagem eh de ate 10 dias uteis.

O produto sera enviado para o mesmo endereco confirmado neste e-mail.

Assim que o pedido for despachado, voce recebera automaticamente o codigo de rastreamento no seu e-mail para acompanhar a entrega.

Com o codigo disponivel, voce podera acompanhar o pedido pelo nosso site:
https://rastreamento.correios.com.br/

Caso o prazo de processamento seja concluido e voce nao receba o codigo de rastreio, basta responder a este e-mail que verificaremos para voce.

Qualquer duvida, estamos a disposicao.
```

**Padrao:** Confirma modelo + prazo reenvio 10 dias uteis + endereco + rastreio + CTA.

---

### 9.11 RECLAMACAO — Barrado Alfandega + Opcoes (Template Reinan)

**Ticket #1308 | Agente: Reinan Coutinho**

```
Ola, Cristiano! Tudo bem?
Me chamo Reinan e sou seu agente Carbon.

Verificamos o seu pedido e identificamos que ele foi barrado na fiscalizacao aduaneira.

Isso pode acontecer no processo de importacao e a Carbon cuida de tudo nesses casos — voce nao precisa resolver nada por conta propria.

A melhor forma de seguir eh com o reenvio do produto, sem nenhum custo adicional.

O prazo de entrega sera reiniciado a partir da data do novo envio, seguindo o mesmo prazo estimado do pedido original.

Para darmos sequencia, pedimos que confirme respondendo este e-mail:

(1) se podemos seguir com o reenvio e
(2) se o endereco de entrega permanece o mesmo.

Caso nao esteja de acordo, podemos seguir com a solicitacao de cancelamento estorno do valor pago.

Atenciosamente,
Reinan.
```

**Padrao:** Diagnostico + tranquilizacao + 2 opcoes claras (reenvio ou estorno) + pedido de confirmacao com itens numerados.

---

### 9.12 RECLAMACAO — Rastreio Breve (Template Luana)

**Ticket #2605 | Agente: Luana**

```
Ola, Leonardo!

Voce recebera o rastreio em ate 5 dias uteis. Caso nao receba, me avise e envio por aqui.

Fico a disposicao!
```

**Padrao:** Ultra-curta (3 linhas). Prazo + CTA. Funciona para reclamacoes simples.

---

### 9.13 FINANCEIRO — Confirmacao Pedido + Rastreio (Template Victor)

**Ticket #2793 | Agente: Victor Lima**

```
Ola, Antonio! Obrigado por entrar em contato com o suporte Carbon.
Meu nome eh Victor e ficarei responsavel pelo seu atendimento.

Nao se preocupe, os seus pedidos #129727 e #129728 ja estao com pagamento confirmados.

Seu pedido #129727 ja esta com a transportadora!
Em breve voce podera acompanhar cada etapa pelo codigo de rastreamento abaixo:

Codigo de rastreamento: NN114361143BR

Site da transportadora Global Express: https://global.cainiao.com/newDetail.htm?mailNoList=NN114361143BR

Site da transportadora dos Correios ao chegar no BRASIL: https://rastreamento.correios.com.br/app/index.php

Qualquer duvida, nao hesite em me contactar, estou por aqui para te ajudar!
Ate mais!
```

**Padrao:** Tranquiliza sobre pagamento + confirma envio + rastreio com link direto pre-preenchido.

---

### 9.14 FINANCEIRO — Estorno Cartao (Template Daniele)

**Ticket #2273 | Agente: Daniele Marques**

```
Ola, Junior! Obrigado por entrar em contato com o suporte Carbon.
Meu nome eh Daniele e ficarei responsavel pelo seu atendimento.

Verificamos que o seu pedido #126146 se encontra cancelado.

O prazo para conclusao do processo eh de ate 10 dias uteis.

O estorno ocorre conforme a forma de pagamento utilizada na compra:
- Cartao de credito: o estorno pode aparecer em ate 3 faturas, de acordo com as regras da operadora do cartao.

Voce recebera as atualizacoes pelo e-mail cadastrado na compra.
```

**Padrao:** Status cancelado + prazo estorno + detalhes por forma de pagamento.

---

### 9.15 FINANCEIRO — Carta Estorno + Reclame Aqui (Template Tauane)

**Ticket #3621 | Agente: Tauane Teles**

```
Ola, Ana Paula. Tudo bem?

Como mencionado nos e-mails anteriores, o seu pedido foi cancelado junto a processadora de pagamentos e o comprovante estaria disponivel atraves do App da Pagaleve.

Para sua conferencia e seguranca, a carta de estorno emitida pela processadora segue anexada neste e-mail, confirmando oficialmente o processo de cancelamento e devolucao do valor.

Como o pagamento foi realizado atraves do pix parcelado, o estorno eh processado diretamente pela Pagaleve. As parcelas futuras sao canceladas automaticamente e, caso ja exista algum valor pago, ele sera devolvido ao cliente.

Por gentileza, se possivel, pedimos que avalie sua manifestacao no Reclame Aqui, considerando que sua solicitacao ja foi devidamente solucionada. Sua avaliacao eh muito importante para nos.
```

**Padrao:** Referencia emails anteriores + comprovante anexo + mecanismo estorno Pagaleve + pedido avaliacao RA.

---

### 9.16 AUTO-REPLY IA — Rastreio Pendente (Auto)

**Ticket #3841 | Auto-reply**

```
Ola, Rodrigo!

Entendo sua preocupacao com o codigo de rastreio. As vezes pode acontecer de o codigo ainda nao estar registrado no sistema dos Correios, especialmente quando o produto foi coletado recentemente ou quando ha atraso na atualizacao das informacoes no rastreamento.

Nossa equipe vai verificar imediatamente a situacao do seu pedido e o status do codigo de rastreio para te dar uma posicao precisa sobre a localizacao do seu smartwatch Carbon. Pode acontecer tambem de precisarmos reenviar o codigo correto, se houver alguma inconsistencia.

Vou encaminhar seu protocolo CARBON-2026-00238...
```

**Padrao auto-reply:** Empatia + explicacao generica + promessa de verificacao. NAO resolve — apenas tranquiliza. Precisa de dados concretos pra resolver.

---

### 9.17 AUTO-REPLY IA — Pedido Aprovado Sem Rastreio (Auto)

**Ticket #3836 | Auto-reply**

```
Ola, Anderson!

Obrigada pelo contato. Vejo que seu pedido 130168 foi aprovado mas ainda nao foi processado. Isso significa que o pagamento foi confirmado e agora o pedido esta na etapa de processamento, onde nossa equipe valida as informacoes, prepara a integracao logistica e organiza o envio.

O prazo padrao para processamento eh de ate 5 dias uteis, mas alguns pedidos podem levar ate 10 dias uteis antes do envio. Apos o processamento, voce recebera o codigo de rastreamento por email e SMS.

Nossa equipe vai verificar o status atual do seu pedido e retornar com uma posicao mais especifica...
```

**Padrao auto-reply:** Consegue puxar numero do pedido e status do Shopify. Melhor que a anterior — informa algo concreto. Mas ainda promete "verificar" em vez de resolver.

---

## 10. Padroes Identificados nas Respostas Bem-Sucedidas

### Estrutura Universal de Resposta (funciona em TODAS as categorias):

1. **Saudacao personalizada** — "Ola, [NOME]! Obrigado por entrar em contato..."
2. **Apresentacao do agente** — "Meu nome eh [X] e ficarei responsavel..."
3. **Acao/diagnostico concreto** — "Verifiquei que seu pedido #[X] esta em [STATUS]"
4. **Informacao util** — Links, codigos, prazos, valores
5. **Proximo passo claro** — O que o cliente precisa fazer ou esperar
6. **CTA de retorno** — "Qualquer duvida, basta responder este e-mail"

### Templates Recorrentes por Situacao:

| Situacao | Resposta Padrao |
|----------|----------------|
| Pedido em processamento | Status + prazo 5 dias uteis + checar spam + link rastreio |
| Pedido despachado | Codigo rastreio + 3 links (Carbon, Cainiao, Correios) + data estimada |
| Barrado alfandega | "Carbon cuida de tudo" + opcao reenvio ou estorno + confirmar endereco |
| Cancelamento/estorno | Status cancelado + prazo 10 dias uteis + mecanismo por forma pagamento |
| Estorno Pix | "Devolvido via Pix apos aprovacao" |
| Estorno cartao | "Pode aparecer em ate 3 faturas" |
| Estorno Pagaleve | "Parcelas futuras canceladas automaticamente" |
| Retirada correios | Codigo + endereco agencia + prazo 7 dias + documento com foto |
| Duvida tecnica | Responder cada pergunta individualmente |
| Reclamacao | Desculpas + diagnostico + 2 opcoes (reenvio ou estorno) |

### Links Mais Usados:

- Rastreio Carbon: `https://carbonsmartwatch.com.br/pages/rastreio`
- Cainiao: `https://global.cainiao.com/`
- Correios: `https://rastreamento.correios.com.br/`
- Rastreio com codigo: `https://global.cainiao.com/newDetail.htm?mailNoList=[CODIGO]`

### Prazos Padrao:

- Processamento: 5 dias uteis
- Processamento reenvio: 10 dias uteis
- Estorno: 10 dias uteis
- Estorno cartao: ate 3 faturas
- Retirada correios: 7 dias

---

## 11. Recomendacoes para o Carlos IA

### O que a IA PODE resolver sozinha (alto volume, baixa complexidade):

1. **Meu Pedido — Status** (270 tickets 1-2 msgs): Puxar Shopify + informar status + rastreio
2. **Duvida — Rastreio** (178 tickets 1-2 msgs): Fornecer codigo + links + data estimada
3. **Financeiro — Status estorno** (69 tickets 1-2 msgs): Confirmar cancelamento + prazo + mecanismo

### O que a IA NAO deve resolver sozinha:

1. **Garantia** (51,3% resolucao, 141,7h 1a resposta) — requer analise humana
2. **Reclamacao com ameaca juridica** (tags procon=32, chargeback=34) — escalar imediato
3. **Reenvio** (precisa confirmar endereco e modelo com cliente)

### Melhorias Prioritarias:

1. **Filtrar Appmax/Mail Delivery** — 59 tickets de sistemas automaticos viram tickets falsos
2. **Auto-reply precisa de dados concretos** — puxar Shopify, Wonca, Troque antes de responder
3. **Garantia precisa de atencao** — pior taxa, pior tempo de resposta. Priorizar.
4. **Pedir avaliacao RA** em TODA resolucao de reclamacao (Tauane/Luana ja fazem, padronizar)
5. **SLA estourado em 33%** — reduzir com auto-reply inteligente nos simples
