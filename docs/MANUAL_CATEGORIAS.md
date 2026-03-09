# Manual de Categorias — Helpdesk Carbon

**Atualizado em:** 09/03/2026
**Para:** Victor, Daniele, Luana, Reinan

---

## As 6 Categorias

| Categoria | Quando usar | Exemplos |
|-----------|------------|----------|
| **Meu Pedido** | Cliente quer SABER sobre o pedido dele | "Cadê meu pedido?", "Qual o rastreio?", "Quando chega?", alteração de endereço |
| **Garantia** | Produto com defeito, troca, mau uso, Carbon Care | "Meu relógio não liga", "Tela parou", "Quero trocar", bateria acabando rápido |
| **Reenvio** | Cliente quer um NOVO ENVIO | Produto errado, item faltante, extravio confirmado, reenvio pendente |
| **Financeiro** | Dinheiro: estorno, cancelamento, NF, arrependimento | "Quero cancelar", "Cadê meu estorno?", "Preciso da nota fiscal", Pix/cartão |
| **Duvida** | Perguntas gerais sobre produto ou empresa | "Qual a diferença do Raptor pro Atlas?", "É à prova d'água?", compatibilidade |
| **Reclamacao** | Cliente insatisfeito, ameaça legal, GUACU | PROCON, Reclame Aqui, advogado, chargeback, "isso é golpe" |

---

## Regra de Ouro: Meu Pedido vs Reenvio

- **Meu Pedido** = quer INFORMACAO ("onde tá?", "quando chega?")
- **Reenvio** = quer PRODUTO NOVO ("veio errado", "faltou item", "extraviou")

Se o cliente começa perguntando do rastreio e depois descobre que extraviou → muda pra **Reenvio**.

---

## Tags Importantes

As tags complementam a categoria. Uma reclamacao pode ter tag `guacu`, `procon`, `chargeback`. Uma garantia pode ter tag `mau_uso`, `defeito`, `carregador`.

| Tag | Significado |
|-----|------------|
| `guacu` | Cliente confundiu Carbon com GUACU (mesma empresa, nomes diferentes) |
| `procon` | Mencionou PROCON |
| `chargeback` | Contestou no cartão |
| `mau_uso` | Dano causado pelo cliente (queda, água quente, carregador errado) |
| `reincidente` | Cliente já abriu ticket antes |
| `revisao_manual` | IA não teve certeza da categoria — REVISAR |

---

## O que a IA faz automaticamente

1. **Categoriza** o ticket numa das 6 categorias
2. **Define prioridade** (baixa/média/alta/urgente)
3. **Gera briefing**: resume o problema e sugere próximo passo
4. **Adiciona tags** relevantes
5. **Marca risco jurídico** se detectar PROCON/advogado/chargeback

Se a tag `revisao_manual` aparecer, a IA não teve certeza. **Verifique a categoria e corrija se necessário.**

---

## Prazos de SLA (pela prioridade)

| Prioridade | Primeira Resposta | Resolução |
|-----------|------------------|-----------|
| Urgente | 2h | 24h |
| Alta | 4h | 48h |
| Média | 8h | 72h |
| Baixa | 24h | 120h |

---

## Duvidas?

Falar com Pedro.
