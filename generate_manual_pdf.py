#!/usr/bin/env python3
"""Gerador de PDF - Manual do Usuario Carbon Helpdesk."""

from fpdf import FPDF
from datetime import datetime


class ManualPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, "Manual do Usuario - Carbon Helpdesk v1.0", align="L")
            self.ln(4)
            self.set_draw_color(220, 220, 220)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        if self.page_no() > 1:
            self.cell(0, 10, f"Pagina {self.page_no() - 1}", align="C")

    def cover_page(self):
        self.add_page()
        self.ln(60)
        self.set_font("Helvetica", "B", 36)
        self.set_text_color(30, 30, 50)
        self.cell(0, 16, "Carbon Helpdesk", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("Helvetica", "", 18)
        self.set_text_color(100, 100, 120)
        self.cell(0, 12, "Manual do Usuario", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_font("Helvetica", "", 13)
        self.set_text_color(140, 140, 160)
        self.cell(0, 10, "Sistema de Atendimento ao Cliente", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 10, "Carbon Smartwatch", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(30)
        self.set_draw_color(200, 200, 210)
        self.line(60, self.get_y(), 150, self.get_y())
        self.ln(10)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(120, 120, 140)
        self.cell(0, 8, f"Versao 1.0 - {datetime.now().strftime('%d/%m/%Y')}", align="C", new_x="LMARGIN", new_y="NEXT")

    def section_title(self, num, title):
        self.ln(6)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 30, 50)
        self.cell(0, 10, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(80, 80, 200)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 80, self.get_y())
        self.set_line_width(0.2)
        self.ln(6)

    def subsection_title(self, title):
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(50, 50, 80)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 60)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bold_text(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(50, 50, 60)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 60)
        x = self.get_x()
        y = self.get_y()
        self.set_fill_color(80, 80, 200)
        self.ellipse(x + 2, y + 1.8, 2, 2, style="F")
        self.set_x(x + 8)
        w = self.w - self.r_margin - self.get_x()
        self.multi_cell(w, 5.5, text)
        self.ln(1)

    def table_header(self, cols, widths):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(240, 240, 250)
        self.set_text_color(40, 40, 60)
        for i, col in enumerate(cols):
            self.cell(widths[i], 7, col, border=1, fill=True, align="C")
        self.ln()

    def table_row(self, cols, widths):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(60, 60, 70)
        for i, col in enumerate(cols):
            self.cell(widths[i], 6.5, col, border=1, align="C" if i > 0 else "L")
        self.ln()

    def tip_box(self, text):
        self.ln(2)
        self.set_fill_color(235, 245, 255)
        self.set_draw_color(100, 150, 255)
        x = self.get_x()
        y = self.get_y()
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(60, 100, 200)
        self.set_x(x + 2)
        self.cell(0, 6, "DICA:", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(50, 80, 150)
        self.set_x(x + 2)
        self.multi_cell(180, 5, text)
        y2 = self.get_y()
        self.rect(x, y - 1, 186, y2 - y + 3, style="D")
        self.ln(4)


def generate():
    pdf = ManualPDF()
    pdf.cover_page()

    # ── Table of Contents ──
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 50)
    pdf.cell(0, 12, "Sumario", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    toc = [
        "1. Introducao",
        "2. Acesso ao Sistema",
        "3. Navegacao Principal",
        "4. Dashboard",
        "5. Caixa de Entrada (Tickets)",
        "6. Detalhes do Ticket",
        "7. Macros e Respostas Rapidas",
        "8. Inteligencia Artificial",
        "9. Rastreamento de Pacotes",
        "10. Base de Conhecimento",
        "11. Biblioteca de Midia",
        "12. Catalogo de Produtos",
        "13. Assistente IA",
        "14. Performance e Gamificacao",
        "15. Relatorios",
        "16. Integracoes",
        "17. Configuracoes",
        "18. Regras de SLA",
        "19. Atalhos de Teclado",
        "20. Perguntas Frequentes",
    ]
    for item in toc:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(60, 60, 80)
        pdf.cell(0, 7, item, new_x="LMARGIN", new_y="NEXT")

    # ── 1. Introduction ──
    pdf.add_page()
    pdf.section_title("1", "Introducao")
    pdf.body_text(
        "O Carbon Helpdesk e o sistema centralizado de atendimento ao cliente da Carbon Smartwatch. "
        "Ele reune todos os canais de comunicacao (e-mail, Slack e web) em uma unica plataforma, "
        "com recursos de inteligencia artificial, automacao e rastreamento de pedidos."
    )
    pdf.bold_text("Principais recursos:")
    for r in [
        "Gestao completa de tickets com SLA automatico",
        "Triagem automatica por IA (classificacao, prioridade, sentimento)",
        "Integracao com Gmail, Slack e Shopify",
        "Rastreamento de pacotes em tempo real (17track)",
        "Base de conhecimento integrada",
        "Sistema de macros e respostas rapidas",
        "Gamificacao e metas de performance",
        "Relatorios avancados com analise de IA",
        "Notificacoes em tempo real via WebSocket",
    ]:
        pdf.bullet(r)

    # ── 2. Access ──
    pdf.section_title("2", "Acesso ao Sistema")
    pdf.subsection_title("2.1 Login")
    pdf.body_text(
        "1. Acesse o sistema pelo navegador\n"
        "2. Insira seu e-mail e senha nos campos correspondentes\n"
        "3. Clique em \"Entrar\"\n\n"
        "Caso veja a mensagem \"Erro ao fazer login\", verifique se o e-mail e a senha estao corretos. "
        "Se o problema persistir, contate o administrador do sistema."
    )
    pdf.subsection_title("2.2 Perfis de Acesso")
    pdf.body_text("O sistema possui 4 niveis de acesso com permissoes diferentes:")
    w = [40, 150]
    pdf.table_header(["Perfil", "Descricao"], w)
    pdf.table_row(["Super Admin", "Acesso total, incluindo gestao de usuarios e integracoes"], w)
    pdf.table_row(["Administrador", "Acesso administrativo (SLA, horarios, relatorios)"], w)
    pdf.table_row(["Supervisor", "Supervisao da equipe, relatorios e performance"], w)
    pdf.table_row(["Agente", "Atendimento de tickets e ferramentas de suporte"], w)

    pdf.subsection_title("2.3 Funcionalidades por Perfil")
    w2 = [52, 22, 22, 22, 22]
    pdf.table_header(["Funcionalidade", "S.Admin", "Admin", "Superv.", "Agente"], w2)
    perms = [
        ["Dashboard", "Sim", "Sim", "Sim", "Sim"],
        ["Caixa de Entrada", "Sim", "Sim", "Sim", "Sim"],
        ["Base de Conhecimento", "Sim", "Sim", "Sim", "Sim"],
        ["Biblioteca de Midia", "Sim", "Sim", "Sim", "Sim"],
        ["Catalogo", "Sim", "Sim", "Sim", "Sim"],
        ["Assistente IA", "Sim", "Sim", "Sim", "Sim"],
        ["Rastreamento", "Sim", "Sim", "Sim", "Sim"],
        ["Performance", "Sim", "Sim", "Sim", "-"],
        ["Relatorios", "Sim", "Sim", "Sim", "-"],
        ["Integracoes", "Sim", "-", "-", "-"],
        ["Gestao de Equipe", "Sim", "-", "-", "-"],
        ["Configuracao SLA", "Sim", "Sim", "-", "-"],
    ]
    for p in perms:
        pdf.table_row(p, w2)

    # ── 3. Navigation ──
    pdf.add_page()
    pdf.section_title("3", "Navegacao Principal")
    pdf.subsection_title("3.1 Barra Lateral (Sidebar)")
    pdf.body_text(
        "A barra lateral esta sempre visivel no lado esquerdo da tela. "
        "Ela contem o menu de navegacao principal e as informacoes do usuario logado."
    )
    w3 = [42, 100, 48]
    pdf.table_header(["Item", "Funcao", "Acesso"], w3)
    nav = [
        ["Dashboard", "Painel de metricas e KPIs", "Todos"],
        ["Caixa de Entrada", "Lista de tickets (com contador)", "Todos"],
        ["Base Conhecimento", "Artigos de suporte", "Todos"],
        ["Biblioteca Midia", "Videos, fotos e links", "Todos"],
        ["Catalogo", "Produtos e especificacoes", "Todos"],
        ["Assistente IA", "Chat com IA da empresa", "Todos"],
        ["Performance", "Ranking e metas", "Superv.+"],
        ["Rastreamento", "Status de entregas", "Todos"],
        ["Relatorios", "Analises e exportacao", "Superv.+"],
        ["Integracoes", "Slack, Gmail, IA", "S.Admin"],
        ["Configuracoes", "Preferencias do sistema", "Todos"],
    ]
    for n in nav:
        pdf.table_row(n, w3)

    pdf.subsection_title("3.2 Notificacoes em Tempo Real")
    pdf.body_text(
        "No canto superior direito, o sino de notificacoes mostra alertas em tempo real. "
        "O numero vermelho indica notificacoes nao lidas. O ponto verde confirma conexao ativa. "
        "Clique em uma notificacao para abrir o ticket correspondente."
    )
    pdf.bold_text("Tipos de notificacao:")
    pdf.bullet("Novo ticket criado")
    pdf.bullet("Ticket atualizado")
    pdf.bullet("Ticket atribuido a voce")
    pdf.bullet("Ticket escalado")

    # ── 4. Dashboard ──
    pdf.add_page()
    pdf.section_title("4", "Dashboard")
    pdf.body_text(
        "O Dashboard e a tela inicial do sistema. Apresenta uma visao geral do atendimento "
        "com metricas, graficos e atalhos. No topo, selecione o periodo de analise: 7, 14, 30, 60 ou 90 dias."
    )
    pdf.bold_text("O Dashboard possui 6 visoes diferentes:")
    pdf.bullet("Administrador - visao completa com 15 KPIs e 6 graficos")
    pdf.bullet("Gestao - tendencias e resumos por tipo de problema")
    pdf.bullet("Agente - visao pessoal com seus numeros e metas")
    pdf.bullet("Trocas - dashboard especializado para acompanhamento de trocas")
    pdf.bullet("Problemas - focado em problemas tecnicos e defeitos")
    pdf.bullet("Reclamacoes - monitoramento de reclamacoes e riscos juridicos")

    pdf.tip_box(
        "Clique em qualquer cartao de KPI para navegar diretamente para a lista de tickets "
        "com o filtro correspondente ja aplicado."
    )

    pdf.subsection_title("Visao Administrador")
    pdf.body_text(
        "Mostra 15 cartoes de KPI incluindo: total de tickets, abertos, SLA cumprido (%), "
        "trocas, problemas, risco juridico, reclamacoes, escalados, tempo de resposta, "
        "FCR, nao atribuidos, resolvidos hoje, tempo de resolucao, SLA quebrados e resolucao na 1a resposta. "
        "Alem de 6 graficos: volume diario, por categoria, por status, por prioridade, por canal e sentimento."
    )
    pdf.subsection_title("Visao Agente")
    pdf.body_text(
        "Mostra 7 cartoes pessoais: meus abertos, meus resolvidos, meu tempo de resposta, "
        "meu SLA (%), total dos meus tickets, meus SLA quebrados e fila geral. "
        "Alem de graficos por status e categoria dos seus tickets."
    )

    # ── 5. Caixa de Entrada ──
    pdf.add_page()
    pdf.section_title("5", "Caixa de Entrada (Tickets)")

    pdf.subsection_title("5.1 Cartoes de Contagem")
    pdf.body_text(
        "No topo da pagina, 5 cartoes mostram os totais em tempo real: "
        "Privado (seus tickets), Equipe (todos os agentes), Aguardando (sem agente), "
        "Prioridade (escalados) e Todos (total abertos). Clique em um cartao para filtrar."
    )

    pdf.subsection_title("5.2 Abas")
    w4 = [35, 155]
    pdf.table_header(["Aba", "Conteudo"], w4)
    pdf.table_row(["Privado", "Apenas seus tickets (exceto resolvidos)"], w4)
    pdf.table_row(["Equipe", "Tickets de todos os agentes (exceto resolvidos)"], w4)
    pdf.table_row(["Aguardando", "Todos os tickets ativos (exceto resolvidos)"], w4)
    pdf.table_row(["Prioridade", "Tickets com status \"Escalado\""], w4)
    pdf.table_row(["Arquivado", "Tickets resolvidos e fechados"], w4)
    pdf.table_row(["Todos", "Todos os tickets sem filtro"], w4)

    pdf.subsection_title("5.3 Busca e Filtros")
    pdf.body_text(
        "O campo de busca pesquisa em: assunto, numero, nome do cliente, e-mail, "
        "codigo de rastreio e conteudo das mensagens. A busca possui debounce de 400ms."
    )
    pdf.body_text(
        "Clique em \"Avancado\" para buscar por nome do cliente e intervalo de datas. "
        "Clique em \"Filtros\" para filtrar por status, prioridade, categoria e tag."
    )

    pdf.subsection_title("5.4 Ordenacao")
    pdf.body_text(
        "Ordene por: Mais recentes, Mais antigos, SLA (urgente primeiro), "
        "Prioridade ou Ultima atualizacao. Voce tambem pode clicar no cabecalho de qualquer coluna."
    )

    pdf.subsection_title("5.5 Acoes em Massa")
    pdf.body_text(
        "Selecione tickets pelas caixas de selecao. Uma barra de acoes aparece com: "
        "\"Atribuir a...\", \"Mudar status...\", \"Mudar prioridade...\" e \"Limpar\"."
    )

    pdf.subsection_title("5.6 Edicao Inline")
    pdf.body_text(
        "Edite diretamente na tabela sem abrir o ticket: "
        "clique no badge de status ou prioridade para alterar, "
        "no nome do agente para reatribuir, ou no \"+\" para adicionar tags."
    )

    pdf.subsection_title("5.7 Botoes de Acao")
    w5 = [35, 155]
    pdf.table_header(["Botao", "Funcao"], w5)
    pdf.table_row(["Atualizar", "Busca novos e-mails do Gmail imediatamente"], w5)
    pdf.table_row(["Historico", "Importa e-mails antigos do Gmail (7 a 365 dias)"], w5)
    pdf.table_row(["Exportar", "Baixa os tickets filtrados como CSV"], w5)
    pdf.table_row(["Auto-Atribuir", "Distribui tickets sem agente automaticamente"], w5)

    pdf.tip_box("A lista de tickets e atualizada automaticamente a cada 30 segundos.")

    # ── 6. Detalhes do Ticket ──
    pdf.add_page()
    pdf.section_title("6", "Detalhes do Ticket")
    pdf.body_text(
        "Ao clicar em um ticket na lista, a pagina de detalhes abre com todas as informacoes "
        "e ferramentas de atendimento."
    )

    pdf.subsection_title("6.1 Barra Superior")
    pdf.body_text(
        "Contem: seta de voltar, numero e assunto do ticket, nome e e-mail do cliente, "
        "badges de alerta (risco juridico, blacklist), cronometro SLA em tempo real, "
        "dropdown de status, dropdown de agente, botao \"Devolver\" e \"Proximo ticket\"."
    )

    pdf.subsection_title("6.2 Deteccao de Colisao")
    pdf.body_text(
        "Se outro agente estiver vendo o mesmo ticket, uma faixa amarela aparece: "
        "\"Fulano esta vendo este ticket\". Isso evita trabalho duplicado."
    )

    pdf.subsection_title("6.3 Protocolo, Categoria e Sentimento")
    pdf.body_text(
        "Protocolo: numero unico de atendimento. Botao \"Gerar\" para criar, \"Enviar\" para enviar por e-mail. "
        "Categoria e prioridade sao editaveis clicando neles. "
        "O sentimento do cliente e detectado pela IA (Positivo, Neutro, Negativo, Irritado)."
    )

    pdf.subsection_title("6.4 Resumo da IA")
    pdf.body_text(
        "Painel expansivel com resumo automatico: problema principal, acoes ja tomadas e proximo passo. "
        "Botao \"Gerar resumo IA\" ou \"Atualizar resumo\" para (re)gerar."
    )

    pdf.subsection_title("6.5 Mensagens")
    pdf.body_text(
        "Historico completo de mensagens: do cliente (esquerda, fundo escuro), "
        "do agente (direita, fundo indigo) e notas internas (direita, fundo amarelo). "
        "Cada mensagem mostra remetente, data e conteudo."
    )

    pdf.subsection_title("6.6 Campo de Resposta")
    pdf.body_text(
        "Alterne entre \"Responder\" (cliente) e \"Nota\" (interna). "
        "Use macros pelo menu, comando \"/\" ou botoes rapidos. "
        "A IA sugere continuacoes automaticas ao digitar 15+ caracteres (Tab aceita, Esc descarta)."
    )

    pdf.subsection_title("6.7 Opcoes de Envio")
    w6 = [60, 130]
    pdf.table_header(["Opcao", "Acao"], w6)
    pdf.table_row(["Enviar e Resolver", "Envia e marca como resolvido"], w6)
    pdf.table_row(["Enviar e Aguardar", "Envia e muda para \"Aguardando Cliente\""], w6)
    pdf.table_row(["Enviar e Ag. Fornec.", "Envia e muda para \"Aguardando Fornecedor\""], w6)
    pdf.table_row(["Escalar Ticket", "Envia e escala o ticket"], w6)
    pdf.table_row(["Resolver s/ enviar", "Resolve sem enviar mensagem"], w6)

    pdf.subsection_title("6.8 Aba Logistica")
    pdf.body_text(
        "Rastreamento: insira o codigo e clique \"Salvar\". O sistema consulta automaticamente a API do 17track. "
        "Mostra status, transportadora, dias em transito, localizacao e linha do tempo de eventos. "
        "Notas do Fornecedor: area para anotacoes sobre comunicacao com fornecedores."
    )

    pdf.subsection_title("6.9 Barra Lateral Direita")
    pdf.body_text("5 abas acessiveis por icones:")
    pdf.bullet("Copiloto - IA com alertas, sugestoes, dicas e artigos relacionados")
    pdf.bullet("Cliente - dados completos, Shopify, historico, blacklist, escalacao")
    pdf.bullet("Pedidos - Shopify, Yampi (abandonados) e Appmax (pagamentos)")
    pdf.bullet("Midia - sugestoes de midia por IA, upload e biblioteca")
    pdf.bullet("Notas - notas internas permanentes do ticket")

    # ── 7. Macros ──
    pdf.add_page()
    pdf.section_title("7", "Macros e Respostas Rapidas")
    pdf.body_text(
        "Macros sao respostas pre-definidas que economizam tempo. "
        "Use pelo menu de macros, comando \"/\" ou botoes rapidos."
    )
    pdf.subsection_title("Variaveis de Template")
    w7 = [40, 150]
    pdf.table_header(["Variavel", "Substituida por"], w7)
    vars_list = [
        ["{{cliente}}", "Nome do cliente"],
        ["{{email}}", "E-mail do cliente"],
        ["{{numero}}", "Numero do ticket"],
        ["{{assunto}}", "Assunto do ticket"],
        ["{{prioridade}}", "Prioridade atual"],
        ["{{categoria}}", "Categoria do ticket"],
        ["{{status}}", "Status atual"],
        ["{{rastreio}}", "Codigo de rastreio"],
    ]
    for v in vars_list:
        pdf.table_row(v, w7)

    pdf.subsection_title("Acoes Automatizadas")
    pdf.body_text(
        "Alem de inserir texto, macros podem: alterar status, alterar prioridade, "
        "alterar categoria, adicionar tag ou reatribuir agente automaticamente."
    )

    # ── 8. IA ──
    pdf.section_title("8", "Inteligencia Artificial")
    pdf.body_text(
        "O Carbon Helpdesk utiliza IA (Claude da Anthropic) em diversas funcionalidades."
    )
    pdf.bullet("Triagem Automatica: classifica categoria, prioridade, sentimento e risco juridico")
    pdf.bullet("Sugestao de Resposta: gera respostas profissionais e empaticas (Alt+S)")
    pdf.bullet("Sugestao Inline: autocomplete enquanto voce digita (Tab aceita)")
    pdf.bullet("Resumo do Ticket: 3 frases com problema, acoes e proximo passo")
    pdf.bullet("Copiloto: orientacao contextual em tempo real na barra lateral")
    pdf.bullet("Re-Triagem: reclassificacao manual pelo botao \"Retriar\"")
    pdf.bullet("Assistente: chat dedicado para duvidas sobre processos da empresa")
    pdf.bullet("Analise Operacional: relatorio completo nos Relatorios")
    pdf.bullet("Analise de Agentes: avaliacao individual com nota e recomendacoes")

    # ── 9. Rastreamento ──
    pdf.add_page()
    pdf.section_title("9", "Rastreamento de Pacotes")
    pdf.body_text(
        "A pagina de rastreamento mostra cartoes de resumo: total, entregues, em transito, "
        "pendentes, problemas e taxa de entrega. Filtre por status e transportadora. "
        "Use \"Sync Shopify\" para importar rastreios e \"Atualizar Todos\" para consultar status atualizado."
    )
    pdf.body_text(
        "Na aba Logistica do ticket, insira o codigo de rastreio e salve. "
        "O sistema consulta a API do 17track e mostra status, transportadora, "
        "dias em transito, localizacao e linha do tempo de eventos."
    )

    # ── 10. KB ──
    pdf.section_title("10", "Base de Conhecimento")
    pdf.body_text(
        "Repositorio de artigos de suporte organizados por categoria: "
        "Garantia, Troca, Carregador, Mau Uso, Juridico, Especificacoes e Suporte Tecnico. "
        "Use o campo de busca e o filtro de categoria para encontrar artigos. "
        "Clique para expandir o conteudo completo."
    )
    pdf.tip_box("A Base de Conhecimento e usada pelo Copiloto da IA para sugerir artigos relevantes.")

    # ── 11. Media ──
    pdf.section_title("11", "Biblioteca de Midia")
    pdf.body_text(
        "Repositorio de videos, fotos, links do Instagram, manuais e politicas para envio rapido. "
        "Categorias: Videos, Fotos, Instagram, Links Uteis, Politicas, Manuais, Outros. "
        "Adicione por link ou upload. O sistema detecta automaticamente links do Instagram e Google Drive."
    )

    # ── 12. Catalog ──
    pdf.section_title("12", "Catalogo de Produtos")
    pdf.body_text(
        "Consulta rapida de especificacoes, precos e problemas comuns dos produtos Carbon. "
        "Filtre por Relogios ou Acessorios. Clique em um produto para ver detalhes. "
        "Use \"Copiar Informacoes\" para colar especificacoes na resposta ao cliente."
    )

    # ── 13. Assistant ──
    pdf.section_title("13", "Assistente IA")
    pdf.body_text(
        "Chat com a IA da Carbon, treinada com processos, politicas e playbooks da empresa. "
        "Digite sua pergunta e receba respostas contextualizadas. "
        "8 perguntas frequentes sao sugeridas na tela inicial como atalhos."
    )

    # ── 14. Performance ──
    pdf.add_page()
    pdf.section_title("14", "Performance e Gamificacao")
    pdf.subsection_title("Performance")
    pdf.body_text(
        "Cartoes pessoais: resolvidos hoje, na semana, na fila e SLA urgente. "
        "Barras de progresso para meta diaria e semanal. "
        "Ranking da equipe com medalhas para os 3 primeiros. "
        "Selecione periodo: 7, 14 ou 30 dias."
    )
    pdf.subsection_title("Premiacoes")
    pdf.body_text(
        "Veja seus pontos acumulados e troque por recompensas disponiveis. "
        "Clique \"Resgatar\" quando tiver pontos suficientes. "
        "Administradores podem criar novas recompensas (geral, semanal, mensal)."
    )
    pdf.subsection_title("Resgates (admin)")
    pdf.body_text(
        "Lista de solicitacoes de resgate pendentes. Aprove ou rejeite cada solicitacao."
    )

    # ── 15. Reports ──
    pdf.section_title("15", "Relatorios")
    pdf.body_text("8 abas disponiveis com seletor de periodo (7 a 365 dias):")
    pdf.bullet("Visao Geral: 6 KPIs + graficos por status, prioridade, canal e categoria")
    pdf.bullet("Tendencias: volume diario, tempo de resposta e resolucao por dia")
    pdf.bullet("Agentes: tabela de desempenho + analise individual por IA")
    pdf.bullet("Satisfacao: CSAT medio, NPS, distribuicao de estrelas, comentarios")
    pdf.bullet("Padroes: escalacoes, risco juridico, hotspots, top tags, reincidentes")
    pdf.bullet("Clientes: tabela de risco por cliente")
    pdf.bullet("Analise IA: relatorio operacional completo gerado por IA")
    pdf.bullet("Exportar: filtros + download CSV")

    # ── 16. Integrations ──
    pdf.section_title("16", "Integracoes")
    pdf.body_text(
        "Pagina exclusiva para Super Admin. Mostra status de 3 integracoes:"
    )
    pdf.bullet("Slack: recebe e responde mensagens de clientes via Slack")
    pdf.bullet("Gmail: busca e-mails a cada 60s, cria tickets, envia respostas")
    pdf.bullet("Claude AI: triagem, sugestao, resumo, copiloto e analise")

    # ── 17. Settings ──
    pdf.add_page()
    pdf.section_title("17", "Configuracoes")
    pdf.bullet("Meu Perfil: nome, e-mail, cargo e assinatura de e-mail")
    pdf.bullet("Tickets: itens por pagina, aba padrao, atualizacao automatica, toggles de preview/timer/IA")
    pdf.bullet("SLA (admin+): prazos de resposta e resolucao por prioridade")
    pdf.bullet("Horario de Atendimento (admin+): dia a dia, fuso horario, resposta automatica fora do horario")
    pdf.bullet("Equipe (Super Admin): adicionar, editar, desativar e remover membros")
    pdf.bullet("Respostas Rapidas: criar, editar e excluir macros com acoes automatizadas")
    pdf.bullet("Atalhos de Teclado: referencia dos atalhos disponiveis")
    pdf.bullet("Seguranca: alterar senha, zona de perigo (reset de banco)")

    # ── 18. SLA Rules ──
    pdf.section_title("18", "Regras de SLA")
    pdf.subsection_title("SLA por Categoria")
    w8 = [38, 28, 30, 30]
    pdf.table_header(["Categoria", "Resposta", "Resolucao", "Prioridade"], w8)
    sla_cat = [
        ["Chargeback", "1h", "24h", "Urgente"],
        ["Reclame Aqui", "2h", "48h", "Urgente"],
        ["PROCON", "2h", "48h", "Urgente"],
        ["Defeito/Garantia", "4h", "72h", "Alta"],
        ["Troca", "4h", "72h", "Alta"],
        ["Reenvio", "4h", "72h", "Alta"],
        ["Rastreamento", "4h", "48h", "Media"],
        ["Mau Uso", "8h", "120h", "Media"],
        ["Duvida", "8h", "48h", "Media"],
        ["Elogio", "24h", "168h", "Baixa"],
        ["Sugestao", "24h", "168h", "Baixa"],
        ["Outros", "8h", "72h", "Media"],
    ]
    for s in sla_cat:
        pdf.table_row(s, w8)

    pdf.ln(3)
    pdf.subsection_title("Escalacao Automatica")
    w9 = [40, 40, 40]
    pdf.table_header(["Prioridade", "Alerta em", "Escalacao em"], w9)
    pdf.table_row(["Urgente", "1 hora", "2 horas"], w9)
    pdf.table_row(["Alta", "2 horas", "4 horas"], w9)
    pdf.table_row(["Media", "4 horas", "8 horas"], w9)
    pdf.table_row(["Baixa", "8 horas", "24 horas"], w9)

    pdf.ln(3)
    pdf.subsection_title("Roteamento por Especialidade")
    w10 = [80, 50]
    pdf.table_header(["Categoria", "Equipe"], w10)
    pdf.table_row(["Chargeback, PROCON, Reclame Aqui", "Juridico"], w10)
    pdf.table_row(["Defeito/Garantia, Mau Uso", "Tecnico"], w10)
    pdf.table_row(["Troca, Reenvio, Rastreamento", "Logistica"], w10)

    # ── 19. Shortcuts ──
    pdf.add_page()
    pdf.section_title("19", "Atalhos de Teclado")
    pdf.body_text("Os atalhos funcionam na tela de detalhes do ticket:")
    w11 = [50, 140]
    pdf.table_header(["Atalho", "Acao"], w11)
    shortcuts = [
        ["Alt + R", "Resolver ticket"],
        ["Alt + E", "Escalar ticket"],
        ["Alt + W", "Mudar para \"Aguardar Cliente\""],
        ["Alt + N", "Ir para o proximo ticket da fila"],
        ["Alt + S", "Solicitar sugestao de resposta da IA"],
        ["Alt + F", "Focar no campo de resposta"],
        ["Ctrl + Enter", "Enviar resposta (Cmd + Enter no Mac)"],
        ["Tab", "Aceitar sugestao inline da IA"],
        ["Esc", "Descartar sugestao inline da IA"],
        ["/", "Abrir menu de macros (no campo de resposta)"],
    ]
    for s in shortcuts:
        pdf.table_row(s, w11)

    # ── 20. FAQ ──
    pdf.ln(4)
    pdf.section_title("20", "Perguntas Frequentes")

    faqs = [
        ("O que fazer quando o SLA esta proximo de estourar?",
         "O cronometro muda para laranja quando falta menos de 1 hora. "
         "Priorize esse atendimento. Se nao conseguir resolver a tempo, "
         "escale o ticket (Alt+E) para que um supervisor assuma."),
        ("Como funciona a auto-atribuicao?",
         "O sistema distribui tickets sem agente considerando: "
         "especialidade do agente vs. categoria, carga atual e limite maximo de tickets."),
        ("O que significa o badge \"Risco Juridico\"?",
         "A IA detectou mencoes a PROCON, advogado, Reclame Aqui, chargeback ou danos morais. "
         "Trate com cuidado extra e escale para o time juridico se necessario."),
        ("Como exportar dados para planilha?",
         "Na Caixa de Entrada, clique \"Exportar\". Ou na aba Exportar dos Relatorios, "
         "aplique filtros e clique \"Baixar CSV\". O arquivo abre no Excel ou Google Sheets."),
        ("O que acontece quando resolvo um ticket?",
         "O sistema registra a data de resolucao, envia pesquisa CSAT ao cliente "
         "e move o ticket para a aba \"Arquivado\"."),
        ("Como funciona a deteccao de colisao?",
         "Se dois agentes abrirem o mesmo ticket, ambos veem uma faixa amarela "
         "informando quem mais esta visualizando."),
        ("O que e o protocolo?",
         "Numero unico de atendimento. Envie ao cliente por e-mail como comprovante de registro."),
        ("Posso trabalhar offline?",
         "Nao. O sistema requer conexao com a internet. Se a conexao cair, "
         "o indicador de WebSocket ficara vermelho e as notificacoes serao recebidas ao reconectar."),
    ]
    for q, a in faqs:
        pdf.bold_text(q)
        pdf.body_text(a)

    # ── Footer page ──
    pdf.add_page()
    pdf.ln(60)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(30, 30, 50)
    pdf.cell(0, 12, "Carbon Helpdesk v1.0", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 120)
    pdf.cell(0, 8, "Sistema de Atendimento ao Cliente", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "Carbon Smartwatch", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(140, 140, 160)
    pdf.cell(0, 8, f"Documento gerado em {datetime.now().strftime('%d/%m/%Y as %H:%M')}", align="C")

    output_path = "Manual_Usuario_Carbon_Helpdesk.pdf"
    pdf.output(output_path)
    print(f"PDF gerado: {output_path}")
    print(f"Total de paginas: {pdf.page_no()}")


if __name__ == "__main__":
    generate()
