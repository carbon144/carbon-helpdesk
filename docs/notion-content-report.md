# Relatorio Completo — Conteudo Notion Carbon

**Data:** 12 mar 2026
**Notion Token:** `secret_40SAZxVy68EDOorq70A1O8w8Vcd41e9XBUeHowLJSuE` (DEPLOYMENT_GUIDE.md)
**NOTION_DATABASE_ID:** Nao configurado no .env local (auto-criado em prod)

---

## 1. Estrutura do Workspace Notion

### Hub Central (pagina raiz)
**URL:** https://www.notion.so/30ff37148f5380d485dada8850b1e1cc

O workspace esta organizado em 7 setores:

| Setor | ID | Descricao |
|-------|-----|-----------|
| Carbon Core | `316f3714-8f53-8163-b999-f9a60291a5fc` | Admin, financeiro, governanca. Acesso restrito Pedro + Lyvia |
| Carbon Culture Hub | `316f3714-8f53-8174-83cf-e39fc44abc3a` | Gestao de pessoas, cultura, onboarding |
| Carbon Data House | `316f3714-8f53-81d8-9681-c2319795038c` | Dados, metricas, IA, automacao |
| Carbon Expert Hub | `30ff3714-8f53-811c-99c9-fa87adf1fb5b` | Centro de operacoes de atendimento |
| Carbon Financial Office | `30cf3714-8f53-8142-83bc-caf40f264d2b` | Financeiro, contabil, tributario |
| Carbon Labs | `30ff3714-8f53-8178-b75b-d369a9b84203` | Criativo — ads, conteudo, site |
| Carbon Logistics Hub | `30ff3714-8f53-819b-83e9-c4b2589310bb` | Estoque, importacoes, logistica |

---

## 2. Databases Encontrados

### Databases Operacionais (Carbon Expert Hub)
| Database | ID | Tipo |
|----------|-----|------|
| Reenvios | `abf68a5a-e530-46c9-90dd-bc4c99bb4815` | Pedidos reenviados pela fabrica |
| Reenvio: Itens Faltantes | `2a29b532-9de1-43e2-88d8-158b2359ee85` | Itens que nao chegaram |
| Pedidos Taxados | `f055489c-ac0b-4671-b32e-5479ea710da2` | Taxados na alfandega |
| Pedidos em Acompanhamento | `93eabb21-0c00-413a-9596-3112e0a306ab` | Sendo monitorados |
| Notas Fiscais | `c80d4a17-f7ec-4da5-9662-d76b633e40e2` | Registro de NFs |
| Manifestacoes | `2bcdd5f5-048b-4136-aa79-e781c3693bc6` | Reclamacoes e manifestacoes |
| Envios Locais | `a73038a0-a296-4e51-9f9c-8be91a8db751` | Envios do escritorio SP |
| Devolucoes Pagas pelo Cliente | `5872a54f-d31c-407d-8d9d-b316e5216a03` | Frete pago pelo cliente |

### Databases Administrativos
| Database | ID | Tipo |
|----------|-----|------|
| Projetos Carbon | `6df25de6-d0f1-4b88-b1d1-6ebe887cff35` | Roadmap de projetos |
| Backlog de Ideias | `f141dddf-5d54-4006-9149-48749ce0da3e` | Ideias futuras |
| Produtos (Catalogo) | `93f6a0eb-4e38-45b5-94a9-e1ea02ed300d` | Catalogo de produtos |
| Colaboradores | `d51eeda6-29f3-4786-9bb6-b506797630ae` | Equipe |
| Folha de Pagamento | `46ca0f73-d89b-4a0f-9602-708e4e7faadc` | Pagamentos |
| Contas a Pagar/Receber | `8361be9b-ca85-441f-a1c9-0065e9b60153` | Financeiro |
| Fluxo de Caixa | `0310bc8c-000f-4388-a8fd-6f282630bcf3` | Caixa |
| Notas Fiscais e Impostos | `c77db280-b78b-4dbd-b1d8-61e8849b1caf` | Fiscal |

### Databases de Marketing (Carbon Labs)
| Database | ID | Tipo |
|----------|-----|------|
| Calendario Editorial | `61906a13-ef14-4202-9143-767ca307bdb7` | Calendario de conteudo |
| Campanhas Ads | `0013adfa-fdaf-4093-ae13-f830541c49e7` | Campanhas ativas |
| Criativos | `c2c2c5a4-d256-4242-82fa-1c16b289c920` | Banco de criativos |

---

## 3. Paginas de Conteudo — Expert Hub (Atendimento)

### 3.1 Base de Conhecimento (KB)
**URL:** https://www.notion.so/316f37148f53811a82ade805790733e1

Conteudo COMPLETO com toggles por tema:
- **Entrega e Frete:** Prazos por regiao (SE 7-12d, S 7-14d, CO 8-16d, NE 10-20d, N 12-25d), processamento 5 dias uteis, frete gratis, rastreamento
- **Trocas e Devolucoes:** Arrependimento 7d, defeito 30d, garantia 12m, Carbon NÃO possui assistencia tecnica, TroqueCommerce, codigo postagem 15 dias validade
- **Atrasos e Extravios:** Manifestacao Correios, extravio so apos confirmacao oficial
- **Produtos — Modelos Ativos:** Raptor (R$869,97, 5ATM, GPS L1+L5, GloryFitPro), Atlas (R$799,97, 3ATM, GPS Dual, GloryFitPro), One Max (R$749,97, 1ATM, DaFit, 900mAh), Aurora (R$699,97, DaFit, 18mm), Aurora Quartz (R$699,97)
- **Specs detalhadas:** Chipsets, memoria, tela, GPS, bateria, resistencia agua por modelo
- **Pulseiras:** 22mm (Raptor/Atlas/One Max), 18mm (Aurora), 12 cores silicone, metal (Link/Luxe), nylon (NAO recomendar)
- **Saude e Medicoes:** Estimativos, margem 5-15%, sem finalidade medica
- **Agua e Resistencia:** Tabela ATM por modelo, AquaShield, NUNCA banho/sauna/vapor
- **Pagamento:** Cartao 12x, PIX 3% desconto, PagaLeve, boleto, AppMax gateway
- **Marketplaces:** NAO vende em nenhum
- **Garantia:** 12m relogios, 90d acessorios, +12m Carbon Care
- **Linguagem Proibida:** Lista completa
- **Manutencao Caseira:** NAO recomendar
- **Dados da Empresa:** CNPJ 48.769.355/0001-76 (Guacu Negocios Digitais Ltda), Rua Irma Pia 422/905, SP

### 3.2 Manual Completo do Agente
**URL:** https://www.notion.so/316f37148f5381fe9cf2fd14e0e0e2b8

14 secoes cobrindo:
1. Bem-vindo ao Expert Hub
2. Hierarquia (Victor Head, Tauane Coord, Reinan/Natalia/Luana/Daniele Agentes)
3. Ferramentas (Reportana, Helpdesk, Shopify, Yampi, AppMax, TroqueCommerce)
4. Fluxo de trabalho (Cliente → Reportana IA → Escalated → Take Over → Helpdesk → Carteira)
5. Formacao de Carteira (A IMPLEMENTAR)
6. Carbon Care Club — Cupons (5%, 8%, 12%, 18% por nivel)
7. Categorias de ticket (9 categorias)
8. SLAs (Urgente 1h/24h, Alta 4h/48h, Normal 12h/72h, Baixa 24h/5d)
9. Escalonamento (3 niveis)
10. Tom de voz e identidade
11. Linguagem proibida
12. Regras absolutas
13. Erros comuns
14. Planilhas e registros

### 3.3 SOPs & Scripts
**URL:** https://www.notion.so/316f37148f53819fa280d0d5461305bd

12 SOPs completos com scripts copy-paste:
1. Rastreio e Entrega (7 cenarios + scripts)
2. Troca e Devolucao (questionario 7 perguntas + 6 cenarios)
3. Reembolso e Cancelamento (6 cenarios + scripts PIX/Cartao/Boleto)
4. Taxacao Aduaneira (Carbon paga tudo)
5. Reclamacao e Reclame Aqui (escalar N3, Tauane responde RA)
6. Duvida de Produto
7. Garantia (troubleshooting 5 passos + SOP)
8. Alteracao de Endereco
9. Reenvio (local 5-10d, fabrica por regiao, taxa R$15)
10. Marketplace e Concorrencia
11. Manutencao Caseira e Bloqueio Aduaneiro
12. Templates e Scripts Gerais (saudacao, follow-up, encerramento)

### 3.4 Guia de Respostas — Email
**URL:** https://www.notion.so/316f37148f53819d9a36dade5c07c89f

11 secoes com templates copy-paste para email:
1. Saudacao padrao
2. Canais oficiais
3. Pedido nao localizado
4. Rastreamento (5 sub-cenarios incluindo 17track)
5. Taxacao aduaneira (3 sub-cenarios)
6. Cancelamentos (6 sub-cenarios)
7. Garantia (expirada, Carbon Care)
8. Duvidas frequentes (GPS, agua IP67/68, vale troca, juros, cupom)
9. Financeiro (nota fiscal)
10. Feedback positivo
11. Encaminhamento para taxas

### 3.5 Guia de Respostas — WhatsApp
**URL:** https://www.notion.so/316f37148f53811eacd1f3117e6e6c78

5 categorias com scripts numerados msg-a-msg:
1. Processamento/Entrega (6 sub-cenarios)
2. Alteracoes/Cancelamento (5 sub-cenarios)
3. Logistica Critica (barrado, reenvio, item faltante, manifestacao)
4. Garantia (triagem, mau uso, devolucao, envio analise, bateria)
5. Identificacao de Pedido/Pagamento

### 3.6 Respostas Redes Sociais
**URL:** https://www.notion.so/316f37148f538146857ec00f5684bc50

Templates para Instagram/Facebook cobrindo: prazo, GPS/NFC/LTE, Strava, apps, agua, saude, caixa, pulseiras, material, modelos, apps, bateria, garantia, email, precos, taxacao, trocas, loja fisica, marketplace.

### 3.7 Departamento de Trocas & Devolucoes
**URL:** https://www.notion.so/316f37148f5381ed9ba0c916ef7fcdc2

- Fluxo completo (mermaid diagram)
- Rotina diaria Tauane + Reinan
- Estoque de pulseiras
- Volumes: 1.761 cancelamentos, 3.605 analises, 2.012 kanban, 694 envios, 600 trocas, 290 controles entrada, 34 divergencias
- Cancelamentos por ano: 2023=1.192, 2024=982, 2025=2.350
- Processo detalhado de analise tecnica
- Ferramentas: Helpdesk, TroqueCommerce, Google Sheets, Shopify, Yampi, Bling

### 3.8 Protocolo de Teste — Setor de Trocas
**URL:** https://www.notion.so/310f37148f5381cf8706fe0e2f08961e

3 fases (13-17 min por unidade):
- Fase 1 — Check Geral (visual + energia + funcionamento basico)
- Fase 2 — Teste Direcionado (6 rotas: A=Tela, B=Bateria, C=Sensores, D=Conectividade, E=Software, F=Estrutura)
- Fase 3 — Veredicto (D0-D4: sem defeito, software, hardware reparavel, irreparavel, mau uso)

### 3.9 Portal do Agente
**URL:** https://www.notion.so/316f37148f5381a3922fc2f82db478f4

Pagina de quick-access para agentes: guias de resposta, produtos, planilhas, escalonamento, time, links rapidos.

### 3.10 Analise Completa Helpdesk — 1870 Tickets
**URL:** https://www.notion.so/31bf37148f5381bb8904f8f6d43b0b2a

Analise detalhada: volume, distribuicao, performance agentes, intencoes dos clientes, exemplos reais, padroes de resposta, insights para chatbot/IA.

### 3.11 Reembolsos & Cancelamentos (Database Page)
**URL:** https://www.notion.so/30ff37148f5381c2be46cfc56c8b86e5

Pagina com tabela manual (nao e o database automatico da integracao). Contem apenas 1 registro de exemplo (#1001).

---

## 4. Outras Paginas Importantes

### Carbon Core
- **Dados da Empresa** (`317f3714-8f53-81bf-b5ac-ec0c86d993a0`)
- **Marcas** (`30ff3714-8f53-8149-93cb-c88835f39868`)
- **Manual de Comunicacao Carbon** (`316f3714-8f53-8158-a329-d7c64d4f8177`)

### Carbon Culture Hub
- Missao, visao, valores
- Equipe completa com cargos
- Checklist onboarding
- Politicas (horario, comunicacao, conduta, horas extras)

### Carbon Financial Office
- Databases: Contas a Pagar/Receber, Fluxo de Caixa, NFs e Impostos
- Cancelamentos historicos: 2023=1.192, 2024=982, 2025=2.350
- Chave PIX Carbon: CNPJ 48.769.355/0001-76

### Carbon Labs
- Brand Guidelines, SOPs de Criacao, Banco de Assets
- Databases: Calendario Editorial, Campanhas Ads, Criativos

---

## 5. Integracao Notion <> Helpdesk — Estado Atual

### notion_service.py
- **Funcao:** Registrar reembolsos e cancelamentos automaticamente no Notion
- **Database alvo:** "Reembolsos & Cancelamentos" (auto-criado se nao existir)
- **Schema:** Ticket, Tipo, Status, Cliente, Email, Pedido Shopify, Valor, Motivo, Agente, Data, Codigo Rastreio, Observacoes
- **Pagina mae:** "Carbon Expert Hub" (criada automaticamente)
- **Status:** Token NAO configurado no .env local (so em prod via DEPLOYMENT_GUIDE.md)

### KB (Base de Conhecimento) — Helpdesk vs Notion

**No Helpdesk (kb_real_data.py) — 14 artigos hardcoded:**

| # | Titulo | Categoria |
|---|--------|-----------|
| 1 | Atualizacoes, Instabilidades e Comportamento Temporario | duvida |
| 2 | Compatibilidade e Requisitos de Uso | duvida |
| 3 | Brindes, Promocoes e Condicoes Especiais | duvida |
| 4 | Autonomia de Bateria e Padroes de Uso | garantia |
| 5 | Politica de Troca e Garantia | garantia |
| 6 | Como Funciona a Troca na Pratica | garantia |
| 7 | Resistencia a Agua e Cuidados de Uso | garantia |
| 8 | Politica de Cancelamento | financeiro |
| 9 | Alteracao de Endereco Apos a Compra | meu_pedido |
| 10 | Produto ou Acessorio em Desacordo com o Pedido | reenvio |
| 11 | Item Faltante ou Entrega Incompleta | reenvio |
| 12 | Origem da Marca e Fabricacao dos Produtos | duvida |
| 13 | Atraso, Extravio e Perda Logistica | meu_pedido |
| 14 | Politica de Reembolso | garantia |
| 15 | Politica de Frete e Entrega | meu_pedido |
| 16 | Catalogo de Produtos e Precos | duvida |

**No Notion (Base de Conhecimento) — conteudo MUITO mais rico:**
A pagina KB do Notion contem tudo que esta hardcoded no Helpdesk MAIS:
- Specs tecnicas detalhadas por modelo (chipset, memoria, tela, GPS, bateria)
- Pulseiras (compatibilidade por modelo, 12 cores, metal, nylon)
- Strava/apps de esporte
- Acessorios e o que vem na caixa
- Modelos legacy (Odyssey, Stellar Rose, Titan Pro X, etc.)
- Pagamento (formas, NF, PagaLeve, AppMax)
- Marketplaces (NAO vende)
- Dados completos da empresa

---

## 6. Gaps e Inconsistencias

### CRITICOS

1. **Precos desatualizados no Helpdesk KB:**
   - Helpdesk: Raptor R$819,97 | Atlas R$749,97 | Aurora Quartz R$642,97 | One Max R$699,97
   - Notion: Raptor R$869,97 | Atlas R$799,97 | Aurora Quartz R$699,97 | One Max R$749,97
   - **Notion esta atualizado. Helpdesk esta com precos antigos.**

2. **Resistencia a agua — Aurora inconsistente:**
   - Helpdesk kb_real_data: Aurora "1ATM (respingos leves, suor — NAO molhar)"
   - Notion KB: Aurora "—" (sem classificacao ATM, apenas "respingos, suor")
   - Notion Redes Sociais: Aurora "resistencia a respingos e suor do dia a dia"
   - **Notion esta correto — Aurora NAO tem classificacao ATM formal.**

3. **Token Notion nao configurado no .env local:**
   - So configurado no DEPLOYMENT_GUIDE.md (prod)
   - Integracao de reembolsos so funciona em producao

### MODERADOS

4. **KB do Helpdesk e 100% hardcoded (kb_real_data.py):**
   - Nao puxa do Notion
   - Nao tem sync automatico
   - Alteracoes no Notion nao se refletem no Helpdesk

5. **Conteudo do Notion NAO presente no KB do Helpdesk:**
   - SOPs e Scripts (12 procedimentos completos)
   - Guia de Respostas Email (11 secoes de templates)
   - Guia de Respostas WhatsApp (5 categorias com scripts msg-a-msg)
   - Respostas Redes Sociais
   - Protocolo de Teste (3 fases de analise tecnica)
   - Manual do Agente (14 secoes)
   - Departamento de Trocas (fluxos, rotinas, volumes)
   - **A IA do chatbot e auto-reply nao tem acesso a esse conteudo.**

6. **Prazos de entrega levemente diferentes:**
   - Helpdesk KB: Sul 7-14d, CO 8-16d
   - Notion KB: Sul 7-14d, CO 8-16d (OK, consistente)
   - Guia Email antigo: "5-25 dias uteis" (simplificado, OK)

7. **Aurora Quartz ausente da tabela de specs do Notion:**
   - Listado como produto mas sem detalhes tecnicos expandidos
   - Mencionado apenas como "pulseira quartz de fabrica, pulseiras proprias"

### BAIXOS

8. **Database "Reembolsos & Cancelamentos" so tem 1 registro de teste:**
   - A integracao notion_service.py cria registros automaticamente
   - Possivelmente nunca foi usada em prod (token nao configurado?)

9. **Pagina "Carbon Expert Hub" duplicada:**
   - `317f3714...` (sem emoji) — pagina antiga/placeholder
   - `30ff3714...811c` (com emoji) — pagina principal ativa
   - Sem conflito real, mas pode confundir

10. **Email de contato inconsistente nos templates antigos:**
    - Guia Email usa `sac@carbonsmartwatch.com.br` em alguns templates
    - Padrao correto: `atendimento@carbonsmartwatch.com.br`

---

## 7. Recomendacoes

1. **Sincronizar precos:** Atualizar `kb_real_data.py` com precos do Notion (fonte de verdade)
2. **Criar sync Notion → KB:** Implementar endpoint que puxa conteudo da pagina KB do Notion e atualiza o banco do Helpdesk
3. **Alimentar IA com SOPs:** Os SOPs, scripts e guias de resposta do Notion sao conteudo essencial para a IA do chatbot e auto-reply
4. **Configurar NOTION_TOKEN no .env:** Habilitar integracao de reembolsos
5. **Corrigir Aurora ATM:** Remover "1ATM" da kb_real_data.py para Aurora (nao tem classificacao)
6. **Unificar email de contato:** Substituir `sac@` por `atendimento@` em todos os templates
