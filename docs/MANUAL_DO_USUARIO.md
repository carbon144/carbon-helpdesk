# Manual do Usuario - Carbon Expert Hub v1.0

**Sistema de Atendimento ao Cliente - Carbon Smartwatch**

---

## Sumario

1. [Introducao](#1-introducao)
2. [Acesso ao Sistema](#2-acesso-ao-sistema)
3. [Navegacao Principal](#3-navegacao-principal)
4. [Dashboard](#4-dashboard)
5. [Caixa de Entrada (Tickets)](#5-caixa-de-entrada)
6. [Detalhes do Ticket](#6-detalhes-do-ticket)
7. [Macros e Respostas Rapidas](#7-macros-e-respostas-rapidas)
8. [Inteligencia Artificial](#8-inteligencia-artificial)
9. [Rastreamento de Pacotes](#9-rastreamento-de-pacotes)
10. [Base de Conhecimento](#10-base-de-conhecimento)
11. [Biblioteca de Midia](#11-biblioteca-de-midia)
12. [Catalogo de Produtos](#12-catalogo-de-produtos)
13. [Assistente IA](#13-assistente-ia)
14. [Performance e Gamificacao](#14-performance-e-gamificacao)
15. [Relatorios](#15-relatorios)
16. [Integracoes](#16-integracoes)
17. [Configuracoes](#17-configuracoes)
18. [Regras de SLA](#18-regras-de-sla)
19. [Atalhos de Teclado](#19-atalhos-de-teclado)
20. [Perguntas Frequentes](#20-perguntas-frequentes)

---

## 1. Introducao

O Carbon Expert Hub e o sistema centralizado de atendimento ao cliente da Carbon Smartwatch. Ele reune todos os canais de comunicacao (e-mail, Slack e web) em uma unica plataforma, com recursos de inteligencia artificial, automacao e rastreamento de pedidos.

**Principais recursos:**
- Gestao completa de tickets com SLA automatico
- Triagem automatica por IA (classificacao, prioridade, sentimento)
- Integracao com Gmail, Slack e Shopify
- Rastreamento de pacotes em tempo real (17track)
- Base de conhecimento integrada
- Sistema de macros e respostas rapidas
- Gamificacao e metas de performance
- Relatorios avancados com analise de IA
- Notificacoes em tempo real via WebSocket

---

## 2. Acesso ao Sistema

### 2.1 Login

1. Acesse o sistema pelo navegador
2. Insira seu **e-mail** e **senha** nos campos correspondentes
3. Clique em **"Entrar"**

Caso veja a mensagem "Erro ao fazer login", verifique se o e-mail e a senha estao corretos. Se o problema persistir, contate o administrador do sistema.

### 2.2 Perfis de Acesso

O sistema possui 4 niveis de acesso. Cada perfil tem permissoes diferentes:

| Perfil | Descricao |
|--------|-----------|
| **Super Admin** | Acesso total ao sistema, incluindo gestao de usuarios e integracoes |
| **Administrador** | Acesso administrativo (SLA, horarios, relatorios) |
| **Supervisor** | Supervisao da equipe, relatorios e performance |
| **Agente** | Atendimento de tickets e uso das ferramentas de suporte |

### 2.3 Funcionalidades por Perfil

| Funcionalidade | Super Admin | Admin | Supervisor | Agente |
|---|:---:|:---:|:---:|:---:|
| Dashboard | Sim | Sim | Sim | Sim |
| Caixa de Entrada | Sim | Sim | Sim | Sim |
| Base de Conhecimento | Sim | Sim | Sim | Sim |
| Biblioteca de Midia | Sim | Sim | Sim | Sim |
| Catalogo | Sim | Sim | Sim | Sim |
| Assistente IA | Sim | Sim | Sim | Sim |
| Rastreamento | Sim | Sim | Sim | Sim |
| Performance | Sim | Sim | Sim | - |
| Relatorios | Sim | Sim | Sim | - |
| Integracoes | Sim | - | - | - |
| Gestao de Equipe | Sim | - | - | - |
| Configuracao de SLA | Sim | Sim | - | - |

---

## 3. Navegacao Principal

### 3.1 Barra Lateral (Sidebar)

A barra lateral esta sempre visivel no lado esquerdo da tela. Ela contem:

**Menu de navegacao:**

| Item | Icone | Funcao |
|------|-------|--------|
| Dashboard | Grafico | Painel de metricas e KPIs |
| Caixa de Entrada | Caixa | Lista de tickets (com contador) |
| Base de Conhecimento | Livro | Artigos de suporte |
| Biblioteca de Midia | Camera | Videos, fotos e links |
| Catalogo | Caixa | Produtos e especificacoes |
| Assistente IA | Robo | Chat com IA da empresa |
| Performance | Gamepad | Ranking e metas |
| Rastreamento | Caminhao | Status de entregas |
| Relatorios | Grafico | Analises e exportacao |
| Integracoes | Plug | Slack, Gmail, IA |
| Configuracoes | Engrenagem | Preferencias do sistema |

**Secao do usuario (parte inferior):**
- Seu avatar (primeira letra do nome)
- Seu nome e cargo
- Botao **"Sair"** para encerrar a sessao

### 3.2 Notificacoes em Tempo Real

No canto superior direito, o **sino de notificacoes** mostra alertas em tempo real:

- **Numero vermelho**: quantidade de notificacoes nao lidas
- **Ponto verde**: conexao ativa com o servidor
- **Ponto vermelho**: conexao perdida (as notificacoes serao recebidas quando reconectar)

**Tipos de notificacao:**
- Novo ticket criado
- Ticket atualizado
- Ticket atribuido a voce
- Ticket escalado

Clique em uma notificacao para abrir o ticket correspondente. Use o botao **"Limpar"** para remover todas as notificacoes.

---

## 4. Dashboard

O Dashboard e a tela inicial do sistema. Ele apresenta uma visao geral do atendimento com metricas, graficos e atalhos.

### 4.1 Selecao de Periodo

No topo da pagina, voce pode selecionar o periodo de analise: **7, 14, 30, 60 ou 90 dias**.

### 4.2 Visoes do Dashboard

O Dashboard possui 6 visoes diferentes, acessiveis pelos botoes no topo:

#### Visao Administrador
Para gestores que precisam de uma visao completa do atendimento.

**15 cartoes de KPI:**
- Total de tickets no periodo
- Tickets abertos
- Taxa de conformidade SLA (%)
- Trocas em andamento
- Problemas reportados
- Tickets com risco juridico
- Reclamacoes
- Tickets escalados
- Tempo medio de primeira resposta
- FCR (resolucao no primeiro contato)
- Tickets nao atribuidos
- Resolvidos hoje
- Tempo medio de resolucao
- SLA quebrados
- Resolvidos na primeira resposta

**6 graficos:**
1. Volume diario de tickets (barras)
2. Distribuicao por categoria (pizza)
3. Distribuicao por status (barras horizontais)
4. Distribuicao por prioridade (barras)
5. Distribuicao por canal - Gmail, Slack, Web (pizza)
6. Distribuicao de sentimento do cliente (pizza)

> **Dica:** Clique em qualquer cartao de KPI para navegar diretamente para a lista de tickets com o filtro correspondente ja aplicado.

#### Visao Gestao
Foco em tendencias e resumos por tipo de problema.

- 10 cartoes de KPI
- Grafico de volume diario (linha)
- Grafico de sentimento (pizza)
- Resumo por tipo: Trocas, Problemas Tecnicos, Reclamacoes

#### Visao Agente
Visao pessoal para cada atendente.

**7 cartoes de KPI:**
- Meus tickets abertos
- Meus tickets resolvidos
- Meu tempo medio de resposta
- Meu SLA (%)
- Total dos meus tickets
- Meus SLA quebrados
- Fila geral de tickets

**2 graficos:**
1. Meus tickets por status
2. Meus tickets por categoria

#### Visao Trocas
Dashboard especializado para acompanhamento de trocas de produtos.
- 4 KPIs focados em trocas
- Grafico de status das trocas
- Volume de trocas por dia

#### Visao Problemas
Dashboard focado em problemas tecnicos e defeitos.
- 4 KPIs: Garantia, Mau Uso, Suporte Tecnico, Carregador
- Distribuicao de problemas (pizza)
- Volume por dia (barras)

#### Visao Reclamacoes
Dashboard para monitorar reclamacoes e riscos juridicos.
- 4 KPIs: Reclamacoes, Risco Juridico, Escalados, Chargebacks
- Sentimento dos clientes (pizza)
- Volume de reclamacoes por dia (linha)

---

## 5. Caixa de Entrada

A Caixa de Entrada e onde voce gerencia todos os tickets do sistema.

### 5.1 Cartoes de Contagem

No topo da pagina, 5 cartoes mostram os totais em tempo real:

| Cartao | O que mostra |
|--------|-------------|
| **Privado** | Tickets atribuidos a voce |
| **Equipe** | Tickets atribuidos a qualquer agente |
| **Aguardando** | Tickets sem agente atribuido |
| **Prioridade** | Tickets escalados |
| **Todos** | Total de tickets abertos |

Clique em um cartao para filtrar a lista.

### 5.2 Abas de Visualizacao

| Aba | Conteudo |
|-----|---------|
| **Privado** | Apenas seus tickets (exceto resolvidos) |
| **Equipe** | Tickets de todos os agentes (exceto resolvidos) |
| **Aguardando** | Todos os tickets ativos (exceto resolvidos) |
| **Prioridade** | Tickets com status "Escalado" |
| **Arquivado** | Tickets resolvidos e fechados |
| **Todos** | Todos os tickets sem filtro de status |

### 5.3 Busca

O campo de busca pesquisa em:
- Assunto do ticket
- Numero do ticket
- Nome do cliente
- E-mail do cliente
- Codigo de rastreio
- Conteudo das mensagens

> **Dica:** A busca possui debounce de 400ms -- ou seja, os resultados comecam a aparecer automaticamente enquanto voce digita, sem precisar clicar "Buscar".

### 5.4 Busca Avancada

Clique em **"Avancado"** para abrir o painel com campos adicionais:
- **Nome do Cliente** - busca por nome
- **Data Inicio** - filtra tickets criados a partir desta data
- **Data Fim** - filtra tickets criados ate esta data

### 5.5 Filtros

Clique em **"Filtros"** para abrir o painel de filtros:
- **Status** - Aberto, Em Andamento, Aguardando Cliente, etc.
- **Prioridade** - Baixa, Media, Alta, Urgente
- **Categoria** - Garantia, Troca, Mau Uso, Carregador, etc.
- **Tag** - Garantia, Troca, PROCON, Chargeback, Blacklist, etc.

O botao mostra um contador com a quantidade de filtros ativos. Use **"Limpar"** para remover todos os filtros.

### 5.6 Ordenacao

O menu de ordenacao permite organizar os tickets por:
- **Mais recentes** (padrao)
- **Mais antigos**
- **SLA (urgente primeiro)** - tickets mais proximos de estourar SLA
- **Prioridade** - urgentes primeiro
- **Ultima atualizacao** - alterados mais recentemente

Voce tambem pode clicar no cabecalho de qualquer coluna da tabela para ordenar por aquele campo.

### 5.7 Acoes em Massa

Selecione um ou mais tickets usando as caixas de selecao a esquerda. Uma barra de acoes aparecera com:

- **"Atribuir a..."** - atribui os tickets selecionados a um agente
- **"Mudar status..."** - altera o status de todos os selecionados
- **"Mudar prioridade..."** - altera a prioridade de todos os selecionados
- **"Limpar"** - desfaz a selecao

### 5.8 Edicao Inline

Voce pode editar diretamente na tabela sem abrir o ticket:
- **Status** - clique no badge de status para alterar
- **Prioridade** - clique no badge de prioridade para alterar
- **Agente** - clique no nome do agente para reatribuir
- **Tags** - clique no botao "+" para adicionar, ou no "x" de uma tag para remover

### 5.9 Tabela de Tickets

Cada linha da tabela mostra:

| Coluna | Informacao |
|--------|-----------|
| # | Numero do ticket |
| Assunto | Titulo do ticket + indicadores (juridico, fonte, reincidente, blacklist) |
| Cliente | Nome do cliente |
| Status | Status atual (editavel) |
| Prioridade | Nivel de prioridade (editavel) |
| SLA | Tempo restante ate o SLA ou "Estourado" |
| Recebido | Data e hora de criacao |
| Agente | Agente responsavel (editavel) |
| Tags | Tags aplicadas ao ticket |

**Indicadores visuais:**
- Borda vermelha a esquerda = ticket escalado
- Fundo vermelho claro = SLA estourado
- Icone de balanca = risco juridico
- Icone do Slack = origem Slack
- Icone de envelope = origem Gmail
- Icone de repeticao = cliente reincidente
- Badge "Blacklist" = cliente na lista negra

### 5.10 Botoes de Acao

| Botao | Funcao |
|-------|--------|
| **Atualizar** | Busca novos e-mails do Gmail imediatamente |
| **Historico** | Abre modal para importar e-mails antigos do Gmail |
| **Exportar** | Baixa os tickets filtrados como arquivo CSV |
| **Auto-Atribuir** | Distribui tickets sem agente automaticamente |

### 5.11 Importacao de Historico do Gmail

O modal de importacao permite sincronizar e-mails antigos:
1. Selecione o periodo: **7, 15, 30 ou 60 dias**, ou um valor personalizado
2. Clique em **"Importar X dias"**
3. Aguarde o processamento
4. O resultado mostra: Criados, Atualizados e Ja existentes

### 5.12 Atualizacao Automatica

A lista de tickets e atualizada automaticamente a cada **30 segundos** quando a aba do navegador esta visivel.

---

## 6. Detalhes do Ticket

Ao clicar em um ticket na lista, a pagina de detalhes e aberta com todas as informacoes e ferramentas de atendimento.

### 6.1 Barra Superior

- **Seta de voltar** - retorna a lista de tickets
- **Numero e assunto** do ticket (ex: "#1234 - Problema com relogio")
- **Nome e e-mail** do cliente
- **Badges** de alerta: risco juridico (vermelho), blacklist (vermelho)
- **Cronometro SLA** - contagem regressiva em tempo real (horas, minutos, segundos)
- **Dropdown de status** - clique para alterar o status
- **Dropdown de agente** - clique para reatribuir
- **"Devolver"** - retorna o ticket para a caixa geral (sem agente)
- **"Proximo ticket"** - pula para o proximo ticket mais urgente da sua fila

### 6.2 Deteccao de Colisao

Se outro agente estiver visualizando o mesmo ticket, uma faixa amarela aparecera:

> "Fulano esta vendo este ticket"

Isso evita que dois agentes trabalhem no mesmo ticket simultaneamente.

### 6.3 Informacoes do Ticket

Logo abaixo da barra superior, voce encontra:

- **Protocolo** - numero unico do atendimento
  - Botao **"Gerar"** para criar um protocolo (se ainda nao existe)
  - Botao **"Enviar"** para enviar o protocolo por e-mail ao cliente
  - Check verde indica que o protocolo ja foi enviado
- **Categoria** - classificacao do ticket (editavel ao clicar)
- **Prioridade** - nivel de urgencia (editavel ao clicar)
- **Sentimento** - analise de sentimento do cliente pela IA (Positivo, Neutro, Negativo, Irritado)

### 6.4 Tags

Abaixo das informacoes, as tags sao exibidas como badges coloridos:
- **BLACKLIST** - vermelho
- **AUTO_ESCALADO** - laranja
- **SLA_ESTOURADO** - vermelho
- **SLA_ALERTA** - amarelo
- Demais tags com cores padrao

### 6.5 Resumo da IA

Painel expansivel que mostra o resumo automatico gerado pela IA:
- Se ja existe resumo: texto com botao **"Atualizar resumo"**
- Se nao existe: botao **"Gerar resumo IA"**

O resumo contém no maximo 3 frases com: problema principal, acoes ja tomadas e proximo passo.

### 6.6 Aba Mensagens

A area principal mostra o historico de mensagens:

- **Mensagens do cliente** (entrada) - alinhadas a esquerda, fundo escuro
- **Respostas do agente** (saida) - alinhadas a direita, fundo indigo
- **Notas internas** - alinhadas a direita, fundo amarelo/ambar

Cada mensagem mostra o nome do remetente, data/hora e conteudo.

#### Painel de IA (ao lado das mensagens)

- **"Retriar"** - reclassifica o ticket pela IA
- **"Sugerir"** - solicita uma sugestao de resposta da IA
- Mostra a classificacao da IA: categoria + nivel de confianca (%)
- Quando uma sugestao e gerada, aparece com o botao **"Usar"** para colar no campo de resposta

#### Campo de Resposta

- Alternancia entre **"Responder"** (resposta ao cliente) e **"Nota"** (nota interna)
- Area de texto para compor a mensagem
- **Menu de Macros**: clique para ver a lista de respostas rapidas
  - Clique simples: insere o texto
  - Clique duplo: insere e envia imediatamente
- **Comando de barra**: digite **"/"** no campo de texto para buscar macros
  - Use setas para cima/baixo para navegar
  - Enter ou Tab para selecionar
- **Sugestao inline da IA**: ao digitar 15+ caracteres em modo de resposta, apos 1,5 segundo sem digitar, a IA sugere uma continuacao em texto cinza
  - **Tab** para aceitar a sugestao
  - **Esc** para descartar

#### Botao Enviar (com menu)

O botao **"Enviar"** possui um menu dropdown com opcoes adicionais:

| Opcao | Acao |
|-------|------|
| **Enviar e Resolver** | Envia a resposta e marca como resolvido |
| **Enviar e Aguardar Cliente** | Envia e muda status para "Aguardando Cliente" |
| **Enviar e Aguardar Fornecedor** | Envia e muda status para "Aguardando Fornecedor" |
| **Escalar Ticket** | Envia e escala o ticket |
| **Resolver sem enviar** | Resolve o ticket sem enviar mensagem |

#### Macros Rapidos

Os 4 primeiros macros aparecem como botoes abaixo do campo de resposta para acesso rapido com um clique.

### 6.7 Aba Logistica

#### Rastreamento

- Campo para inserir o codigo de rastreio
- Botao **"Salvar"** para registrar
- Cartao de status mostrando:
  - Status de entrega (Entregue / Em Transito / Devolvido / Falha)
  - Nome da transportadora
  - Dias em transito
  - Localizacao atual
  - Ultima atualizacao
- Linha do tempo com todos os eventos de rastreio
- Link **"Ver no 17track.net"** para consulta externa

#### Notas do Fornecedor

- Area de texto para anotacoes sobre comunicacao com fornecedores
- Botao **"Salvar"**

### 6.8 Barra Lateral Direita

A barra lateral direita possui 5 abas acessiveis por icones:

#### Aba 1: Copiloto (IA)

O Copiloto analisa o ticket e fornece:
- **Alerta de sentimento** - aviso quando cliente esta negativo/irritado
- **Proximo passo** - sugestao de acao recomendada pela IA
- **Dicas** - orientacoes contextuais baseadas na categoria
- **Artigos da base** - artigos relacionados ao problema
- **Acoes sugeridas** - botoes de acao rapida

Clique em **"Atualizar"** para regenerar as sugestoes.

#### Aba 2: Cliente

Informacoes completas do cliente:
- Avatar com badge de nivel (VIP/Problematico/Atencao)
- Nome, telefone, e-mail
- **Dados do Shopify:**
  - Numero de pedidos
  - LTV (valor total gasto, em R$)
  - Numero de tickets abertos
  - Numero de chargebacks
  - Tags do Shopify
  - Endereco
  - Data do ultimo pedido
  - Cliente desde (data)
- **Alertas** de chargeback e muitas devolucoes
- **Pedidos recentes** do Shopify (ate 5)
- **Secao Blacklist**: adicionar/remover da lista negra
- **Info de Escalacao**: motivo e data (se escalado)
- **Historico de tickets** do mesmo cliente

#### Aba 3: Pedidos

3 sub-abas com pedidos de diferentes plataformas:

| Sub-aba | Plataforma | Conteudo |
|---------|-----------|----------|
| Pedidos | Shopify | Pedidos, status de pagamento, itens, rastreio |
| Abandonados | Yampi | Carrinhos abandonados |
| Pagamentos | Appmax | Status de pagamentos |

Cada pedido pode ser expandido para ver detalhes completos. Acoes disponiveis para pedidos Shopify:
- **"Reembolsar"** - processar reembolso
- **"Cancelar"** - cancelar pedido

#### Aba 4: Midia

- Sugestoes de midia pela IA (baseadas na categoria do ticket)
- Upload de arquivo ou link
- Busca na biblioteca
- Grid com todas as midias disponiveis

#### Aba 5: Notas

Notas internas permanentes do ticket (diferentes das notas nas mensagens).

---

## 7. Macros e Respostas Rapidas

Macros sao respostas pre-definidas que economizam tempo no atendimento.

### 7.1 Como Usar Macros

Existem 3 formas de usar macros:

**1. Menu de Macros (no campo de resposta):**
- Clique no botao de macros ao lado do campo de resposta
- Selecione a macro desejada
- Clique simples = insere o texto
- Clique duplo = insere e envia imediatamente

**2. Comando de Barra:**
- No campo de resposta, digite **/**
- Um menu de busca aparecera
- Digite para filtrar as macros
- Use setas para navegar, Enter/Tab para selecionar

**3. Botoes Rapidos:**
- Os 4 macros mais usados aparecem como botoes logo abaixo do campo de resposta

### 7.2 Variaveis de Template

Os macros suportam variaveis que sao substituidas automaticamente:

| Variavel | Substituida por |
|----------|----------------|
| `{{cliente}}` | Nome do cliente |
| `{{email}}` | E-mail do cliente |
| `{{numero}}` | Numero do ticket |
| `{{assunto}}` | Assunto do ticket |
| `{{prioridade}}` | Prioridade atual |
| `{{categoria}}` | Categoria do ticket |
| `{{status}}` | Status atual |
| `{{rastreio}}` | Codigo de rastreio |

**Exemplo de macro:**
```
Ola {{cliente}}, tudo bem?

Referente ao seu ticket #{{numero}}, informamos que o codigo de rastreio
do seu novo produto e: {{rastreio}}

Qualquer duvida, estamos a disposicao!
```

### 7.3 Acoes Automatizadas

Alem de inserir texto, macros podem executar acoes automaticas:

| Acao | Efeito |
|------|--------|
| Alterar status | Muda o status do ticket automaticamente |
| Alterar prioridade | Muda a prioridade |
| Alterar categoria | Muda a categoria |
| Adicionar tag | Adiciona uma tag ao ticket |
| Atribuir agente | Reatribui o ticket a outro agente |

### 7.4 Gerenciar Macros

Acesse **Configuracoes > Respostas Rapidas** para:
- Criar novas macros (nome, conteudo, acoes)
- Editar macros existentes
- Excluir macros que nao sao mais necessarias

---

## 8. Inteligencia Artificial

O Carbon Expert Hub utiliza IA (Claude da Anthropic) em diversas funcionalidades.

### 8.1 Triagem Automatica

Quando um novo ticket e criado, a IA automaticamente:
- **Classifica a categoria** (garantia, troca, mau uso, etc.)
- **Define a prioridade** (baixa, media, alta, urgente)
- **Analisa o sentimento** do cliente (positivo, neutro, negativo, irritado)
- **Detecta risco juridico** (mencoes a PROCON, advogado, Reclame Aqui, chargeback)
- **Aplica tags** relevantes
- **Gera um resumo** em uma frase
- **Calcula nivel de confianca** da classificacao (0-100%)

### 8.2 Sugestao de Resposta

Na tela do ticket, clique em **"Sugerir"** ou use o atalho **Alt+S** para receber uma sugestao de resposta profissional e empatica.

A sugestao:
- Cumprimenta o cliente pelo nome
- E empatica e profissional
- Usa portugues brasileiro
- Considera a categoria e o historico
- Sugere escalar para supervisor em casos de risco juridico

Clique em **"Usar"** para copiar a sugestao para o campo de resposta.

### 8.3 Sugestao Inline

Enquanto voce digita uma resposta (15+ caracteres), a IA sugere automaticamente uma continuacao do texto em cinza claro:
- **Tab** para aceitar a sugestao
- **Esc** para descartar
- Continue digitando para ignorar

### 8.4 Resumo do Ticket

O resumo automatico analisa todo o historico de mensagens e gera um texto de ate 3 frases com:
1. O problema principal do cliente
2. O que ja foi feito ou tentado
3. O status atual e proximo passo

O resumo e atualizado automaticamente a cada 3 mensagens, ou manualmente pelo botao **"Atualizar resumo"**.

### 8.5 Copiloto (Barra Lateral)

O Copiloto fornece orientacao contextual em tempo real:
- Alertas de sentimento negativo
- Sugestao de proximo passo
- Dicas baseadas na categoria do ticket
- Artigos relevantes da base de conhecimento
- Botoes de acao sugeridos

### 8.6 Re-Triagem

Se a classificacao automatica estiver incorreta, clique em **"Retriar"** para solicitar uma nova analise da IA. Isso atualiza categoria, prioridade, sentimento e tags.

---

## 9. Rastreamento de Pacotes

### 9.1 Pagina de Rastreamento

Acesse pelo menu **Rastreamento** na barra lateral.

**Cartoes de resumo (topo):**
- Total de rastreios
- Entregas concluidas
- Em transito
- Pendentes
- Problemas detectados
- Taxa de entrega (%)

**Filtros disponiveis:**
- Status: Todos, Pendentes, Em Transito, Entregues, Problemas, Com Erro
- Transportadora: Todas, Correios, Cainiao, 17Track, Generico

**Acoes:**
- **"Sync Shopify"** - sincroniza rastreios do Shopify (7 a 180 dias)
- **"Atualizar Todos"** - consulta status atualizado de todos os rastreios

**Tabela de rastreamentos:**
- Numero do ticket
- Nome do cliente
- Codigo de rastreio
- Transportadora
- Status do rastreio
- Data de entrega
- Botoes de acao (atualizar, abrir ticket)

Clique em uma linha para expandir e ver a linha do tempo completa de eventos do pacote.

### 9.2 Rastreamento no Ticket

Na aba **Logistica** do ticket:
1. Insira o codigo de rastreio
2. Clique em **"Salvar"**
3. O sistema consulta automaticamente a API de rastreio (17track)
4. O status e atualizado em tempo real

### 9.3 Deteccao Automatica de Problemas

O sistema identifica automaticamente palavras-chave que indicam problemas na entrega, como: barrado, extraviado, devolvido, avariado, cancelado, retido, etc.

---

## 10. Base de Conhecimento

Acesse pelo menu **Base de Conhecimento** na barra lateral.

### 10.1 Navegacao

- **Campo de busca** - pesquise artigos por palavras-chave
- **Filtro por categoria:**
  - Todas categorias
  - Garantia
  - Troca
  - Carregador
  - Mau Uso
  - Juridico
  - Especificacoes
  - Suporte Tecnico

### 10.2 Visualizacao

Os artigos sao exibidos em grade com 2 colunas:
- Titulo do artigo
- Badge da categoria
- Preview do conteudo (3 linhas)

Clique em um artigo para expandir e ver o conteudo completo. Clique novamente para recolher.

> **Dica:** A Base de Conhecimento tambem e usada pelo Copiloto da IA para sugerir artigos relevantes ao ticket que voce esta atendendo.

---

## 11. Biblioteca de Midia

Acesse pelo menu **Biblioteca de Midia** na barra lateral.

### 11.1 O que e

Um repositorio centralizado de videos, fotos, links do Instagram, manuais e politicas que podem ser enviados rapidamente aos clientes durante o atendimento.

### 11.2 Categorias

- Todos
- Videos
- Fotos
- Instagram
- Links Uteis
- Politicas
- Manuais
- Outros

### 11.3 Adicionar Midia

1. Clique em **"Adicionar Midia"**
2. Escolha o modo: **Link** (colar URL) ou **Upload** (enviar arquivo)
3. O sistema detecta automaticamente links do Instagram e Google Drive
4. Preencha nome e categoria
5. Salve

### 11.4 Usar no Atendimento

Na tela de detalhes do ticket, na aba **Midia** da barra lateral direita:
- A IA sugere midias relevantes baseadas na categoria
- Voce pode buscar na biblioteca
- Copie o link para enviar ao cliente

---

## 12. Catalogo de Produtos

Acesse pelo menu **Catalogo** na barra lateral.

### 12.1 Navegacao

- Filtro por tipo: **Todos**, **Relogios**, **Acessorios**
- Cartoes de produto mostrando: nome, preco (R$) e status (Ativo/Inativo)

### 12.2 Detalhes do Produto

Clique em um produto para ver:
- Lista completa de especificacoes
- Problemas comuns associados ao produto
- Botao **"Copiar Informacoes"** - copia as especificacoes para a area de transferencia

> **Dica:** Use o catalogo durante o atendimento para consultar rapidamente especificacoes e problemas conhecidos de cada produto.

---

## 13. Assistente IA

Acesse pelo menu **Assistente IA** na barra lateral.

### 13.1 O que e

Um chat com a IA da Carbon, treinada com processos, politicas e playbooks internos da empresa. Use para tirar duvidas sobre procedimentos sem sair do sistema.

### 13.2 Como Usar

1. Digite sua pergunta no campo de texto
2. A IA responde com base no conhecimento da empresa
3. O historico da conversa e mantido durante a sessao

### 13.3 Perguntas Sugeridas

Na tela inicial, 8 perguntas frequentes sao sugeridas como botoes de acesso rapido:
- Como funciona a garantia?
- Qual o processo de troca?
- Como lidar com caso de PROCON?
- Como diferenciar mau uso de defeito?
- Processo de chargeback?
- Como reenviar um produto?
- Problemas com carregador?
- Quando escalar para juridico?

---

## 14. Performance e Gamificacao

Acesse pelo menu **Performance** na barra lateral (disponivel para supervisores e acima).

### 14.1 Aba Performance

**Meus numeros (cartoes):**
- Resolvidos hoje
- Resolvidos na semana
- Na fila
- SLA urgente

**Barras de progresso:**
- Meta diaria (percentual da meta atingido)
- Meta semanal

**Sequencia (streak):** Mostra quantos dias consecutivos voce foi produtivo.

**Ranking da Equipe:**

| Coluna | Informacao |
|--------|-----------|
| Posicao | 1o, 2o, 3o (com medalhas de ouro, prata, bronze) |
| Nome | Nome do agente |
| Resolvidos | Tickets resolvidos no periodo |
| Pendentes | Tickets pendentes |
| SLA | Taxa de conformidade (%) |
| Score | Pontuacao de performance |

**Seletor de periodo:** 7 dias, 14 dias, 30 dias

### 14.2 Aba Premiacoes

- Exibicao de **"Meus Pontos"** acumulados
- Cartoes de recompensas disponiveis:
  - Nome e descricao
  - Custo em pontos
  - Botao **"Resgatar"** (quando voce tem pontos suficientes)
  - Indicacao de pontos faltantes (quando nao tem)

**Para administradores:** formulario para criar novas recompensas:
- Nome, descricao, icone, cor, pontos
- Categoria: geral, semanal, mensal

### 14.3 Aba Resgates (somente admin)

Lista de solicitacoes de resgate de recompensas pendentes:
- Nome do agente
- Recompensa solicitada
- Botoes: **Aprovar** / **Rejeitar**

---

## 15. Relatorios

Acesse pelo menu **Relatorios** na barra lateral (disponivel para supervisores e acima).

### 15.1 Seletor de Periodo

Disponivel em todos os relatorios: **7, 14, 30, 60, 90, 180 ou 365 dias**.

### 15.2 Visao Geral

**6 cartoes de KPI:**
- Total de tickets
- Conformidade SLA (%)
- Tempo medio de resposta
- Tempo medio de resolucao
- Tickets com risco juridico
- SLA estourados

**Graficos de distribuicao:** por status, prioridade, canal + sentimento e categoria.

### 15.3 Tendencias

- Grafico de volume diario (barras)
- Tempo medio de resposta por dia (linha)
- Tempo medio de resolucao por dia (linha)
- 4 KPIs: total no periodo, resolvidos, SLA estourados, media por dia

### 15.4 Agentes

Tabela de desempenho de cada agente:
- Tickets atendidos
- Taxa de resolucao
- Tempo medio de resposta
- Tempo medio de resolucao
- Conformidade SLA
- Satisfacao media

Botao **"Analisar"** para cada agente gera uma analise completa pela IA:
- Nota geral (0 a 10)
- Resumo do desempenho
- Pontos fortes
- Areas de melhoria
- Recomendacoes

### 15.5 Satisfacao (CSAT)

- Media CSAT (de 1 a 5 estrelas)
- Score NPS
- Contagem de promotores e detratores
- Distribuicao de estrelas (grafico)
- Tendencia diaria (grafico)
- Comentarios recentes dos clientes

### 15.6 Padroes

- Taxa de escalacao
- Percentual de risco juridico
- Clientes reincidentes
- Tabela de **hotspots**: categoria, prioridade, quantidade, SLA estourados, tempo de resolucao
- Top tags mais usadas (ranking)
- Lista de clientes reincidentes

### 15.7 Clientes

Tabela de risco por cliente:
- Nome
- E-mail
- Quantidade de tickets
- Score de risco (%)

### 15.8 Analise IA

Botao **"Gerar Analise"** que produz um relatorio completo de IA:
- Nota operacional (0 a 10)
- Resumo executivo
- Indicadores criticos
- Padroes identificados
- Erros recorrentes
- Analise da equipe (destaques, pontos de atencao, treinamento)
- Analise de clientes (reclamacoes, churn, oportunidades)
- Plano de acao priorizado com prazos e impacto esperado

### 15.9 Exportar

Filtros para exportacao:
- Status
- Prioridade
- Categoria
- Data inicio / Data fim

Botao **"Baixar CSV"** para download do arquivo.

---

## 16. Integracoes

Acesse pelo menu **Integracoes** na barra lateral (somente Super Admin).

### 16.1 Slack

- Recebe mensagens de clientes diretamente no helpdesk via canal do Slack
- Respostas do agente sao enviadas de volta ao Slack
- Status: Conectado / Erro / Nao Configurado
- Mostra: nome do bot, workspace, canal

### 16.2 Gmail

- Busca automatica de novos e-mails a cada 60 segundos
- Cria tickets automaticamente a partir de e-mails recebidos
- Respostas do agente sao enviadas como resposta ao e-mail original
- Botao **"Buscar Emails Agora"** para sincronizacao manual
- Botao **"Autorizar Gmail"** para configurar a integracao

### 16.3 Claude AI

- Motor de triagem, sugestao e analise do sistema
- Status: Conectado / Erro / Nao Configurado
- Recursos ativos:
  - Classificacao automatica
  - Deteccao de prioridade e risco juridico
  - Analise de sentimento
  - Sugestao de resposta
  - Resumo de tickets
  - Copiloto
  - Analise operacional

---

## 17. Configuracoes

Acesse pelo menu **Configuracoes** na barra lateral.

### 17.1 Meu Perfil

- **Nome** - seu nome no sistema
- **E-mail** - somente leitura
- **Cargo** - somente leitura
- **Assinatura de E-mail** - texto que sera adicionado as suas respostas por e-mail

### 17.2 Tickets

| Configuracao | Descricao |
|---|---|
| Tickets por Pagina | 10, 20, 30, 50 ou 100 |
| Aba Padrao | Qual aba abrir por padrao |
| Atualizacao Automatica | Intervalo em segundos (0 a 120) |
| Preview ao Passar o Mouse | Mostrar preview do ticket ao passar o mouse |
| Mostrar Timer | Exibir cronometro de SLA |
| Sugestoes de IA | Ativar/desativar sugestoes automaticas |
| Auto-Atribuir ao Criar | Atribuir automaticamente novos tickets (admin) |

### 17.3 SLA (admin+)

Configure os prazos de SLA por prioridade:

| Prioridade | Tempo de Resposta | Tempo de Resolucao |
|---|---|---|
| Urgente | Configuravel (horas) | Configuravel (horas) |
| Alta | Configuravel (horas) | Configuravel (horas) |
| Media | Configuravel (horas) | Configuravel (horas) |
| Baixa | Configuravel (horas) | Configuravel (horas) |

### 17.4 Horario de Atendimento (admin+)

- Configuracao dia a dia: Segunda a Domingo
- Para cada dia: ativo/inativo, hora de inicio, hora de fim
- Selecao de fuso horario (cidades brasileiras)
- Resposta automatica fora do horario (ativar/desativar)
- Mensagem personalizavel com variaveis: `{{cliente}}`, `{{horario_abertura}}`, `{{proximo_dia}}`

### 17.5 Equipe (somente Super Admin)

**Adicionar membro:**
- Nome, e-mail, senha, cargo

**Gerenciar membros:**
- Alterar cargo (role)
- Definir especialidade: Juridico, Tecnico, Logistica, Geral
- Definir maximo de tickets simultaneos
- Ativar/desativar usuario
- Remover usuario

### 17.6 Respostas Rapidas (Macros)

Veja a secao [7. Macros e Respostas Rapidas](#7-macros-e-respostas-rapidas) para detalhes completos.

### 17.7 Atalhos de Teclado

Lista de referencia dos atalhos disponiveis (somente leitura). Veja a secao [19. Atalhos de Teclado](#19-atalhos-de-teclado).

### 17.8 Seguranca

- **Alterar senha:** senha atual, nova senha, confirmar nova senha
- **Zona de Perigo** (somente Super Admin): botao para resetar o banco de dados

---

## 18. Regras de SLA

O SLA (Service Level Agreement) define os prazos maximos para primeira resposta e resolucao de cada ticket.

### 18.1 SLA por Categoria

| Categoria | Resposta | Resolucao | Prioridade Auto |
|---|---|---|---|
| Chargeback | 1 hora | 24 horas | Urgente |
| Reclame Aqui | 2 horas | 48 horas | Urgente |
| PROCON | 2 horas | 48 horas | Urgente |
| Defeito/Garantia | 4 horas | 72 horas | Alta |
| Troca | 4 horas | 72 horas | Alta |
| Reenvio | 4 horas | 72 horas | Alta |
| Rastreamento | 4 horas | 48 horas | Media |
| Mau Uso | 8 horas | 120 horas | Media |
| Duvida | 8 horas | 48 horas | Media |
| Elogio | 24 horas | 168 horas | Baixa |
| Sugestao | 24 horas | 168 horas | Baixa |
| Outros | 8 horas | 72 horas | Media |

### 18.2 SLA por Prioridade (quando nao ha categoria)

| Prioridade | Resposta | Resolucao |
|---|---|---|
| Urgente | 1 hora | 24 horas |
| Alta | 4 horas | 72 horas |
| Media | 8 horas | 120 horas |
| Baixa | 24 horas | 168 horas |

### 18.3 Escalacao Automatica

O sistema escala tickets automaticamente quando os prazos sao atingidos:

| Prioridade | Alerta em | Escalacao em |
|---|---|---|
| Urgente | 1 hora | 2 horas |
| Alta | 2 horas | 4 horas |
| Media | 4 horas | 8 horas |
| Baixa | 8 horas | 24 horas |

### 18.4 Regras de Blacklist Automatica

O sistema adiciona automaticamente clientes a blacklist quando:
- **3+ chargebacks** registrados
- **2+ reenvios** solicitados
- **3+ flags de abuso** registrados

### 18.5 Roteamento por Especialidade

Tickets sao automaticamente direcionados a equipes especializadas:

| Categoria | Equipe |
|---|---|
| Chargeback, PROCON, Reclame Aqui | Juridico |
| Defeito/Garantia, Mau Uso | Tecnico |
| Troca, Reenvio, Rastreamento | Logistica |

---

## 19. Atalhos de Teclado

Os atalhos funcionam na tela de detalhes do ticket:

| Atalho | Acao |
|--------|------|
| **Alt + R** | Resolver ticket |
| **Alt + E** | Escalar ticket |
| **Alt + W** | Mudar para "Aguardar Cliente" |
| **Alt + N** | Ir para o proximo ticket da fila |
| **Alt + S** | Solicitar sugestao de resposta da IA |
| **Alt + F** | Focar no campo de resposta |
| **Ctrl + Enter** (ou Cmd + Enter no Mac) | Enviar resposta |
| **Tab** | Aceitar sugestao inline da IA |
| **Esc** | Descartar sugestao inline da IA |
| **/** | Abrir menu de macros (no campo de resposta) |

---

## 20. Perguntas Frequentes

### Como criar um novo ticket manualmente?
Na Caixa de Entrada, novos tickets sao criados automaticamente via e-mail, Slack ou pela API. Para criar manualmente, utilize o botao de criacao (se disponivel) ou envie um e-mail para o endereco de suporte configurado.

### O que fazer quando o SLA esta proximo de estourar?
O cronometro na tela do ticket muda para laranja quando falta menos de 1 hora. Priorize esse atendimento. Se nao conseguir resolver a tempo, escale o ticket (Alt+E) para que um supervisor assuma.

### Como funciona a auto-atribuicao?
Ao clicar em **"Auto-Atribuir"** na Caixa de Entrada, o sistema distribui automaticamente os tickets sem agente. Ele considera:
1. Especialidade do agente vs. categoria do ticket
2. Carga atual de cada agente (tickets abertos)
3. Limite maximo de tickets por agente

### O que significa o badge "Risco Juridico"?
Indica que a IA detectou mencoes a PROCON, advogado, Reclame Aqui, chargeback ou danos morais. Esses tickets devem ser tratados com cuidado extra e, se necessario, escalados para o time juridico.

### Como exportar dados para planilha?
Na Caixa de Entrada, clique em **"Exportar"**. Ou na aba **Exportar** dos Relatorios, aplique os filtros desejados e clique em **"Baixar CSV"**. O arquivo pode ser aberto no Excel ou Google Sheets.

### O que acontece quando resolvo um ticket?
Ao resolver um ticket (status "Resolvido" ou "Fechado"), o sistema automaticamente:
1. Registra a data de resolucao
2. Envia uma pesquisa de satisfacao (CSAT) por e-mail ao cliente
3. O ticket aparece na aba "Arquivado"

### Como funciona a deteccao de colisao?
Se dois agentes abrirem o mesmo ticket simultaneamente, ambos verao uma faixa amarela informando quem mais esta visualizando. Isso evita trabalho duplicado.

### O que e o protocolo?
O protocolo e um numero unico de atendimento gerado pelo sistema. Voce pode envia-lo ao cliente por e-mail como comprovante de registro do chamado.

### Como a IA aprende sobre nossa empresa?
A IA utiliza como contexto: a base de conhecimento, os playbooks de atendimento, as politicas da empresa e o historico de mensagens do ticket. Ela nao tem acesso a dados de outros clientes.

### Posso trabalhar offline?
Nao. O Carbon Expert Hub e um sistema web que requer conexao com a internet. Se a conexao cair, o indicador de WebSocket ficara vermelho e as notificacoes serao recebidas quando a conexao for restabelecida.

---

**Carbon Expert Hub v1.0** | Sistema de Atendimento ao Cliente | Carbon Smartwatch
