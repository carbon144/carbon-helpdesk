#!/usr/bin/env python3
"""
Gerador de Relatório PDF - Diagnóstico Carbon Helpdesk
"""

from fpdf import FPDF
from datetime import datetime


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "Carbon Helpdesk - Relatorio de Diagnostico", align="L")
        self.cell(0, 8, datetime.now().strftime("%d/%m/%Y"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(253, 210, 0)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align="C")

    def cover_page(self):
        self.add_page()
        self.ln(50)

        # Yellow accent bar
        self.set_fill_color(253, 210, 0)
        self.rect(10, 60, 190, 4, "F")

        self.ln(20)
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(29, 29, 31)
        self.cell(0, 15, "CARBON HELPDESK", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "", 18)
        self.set_text_color(99, 99, 102)
        self.cell(0, 12, "Relatorio de Diagnostico Tecnico", align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(10)
        self.set_font("Helvetica", "", 12)
        self.cell(0, 8, f"Data: {datetime.now().strftime('%d de fevereiro de %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, "Versao: 1.0", align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(20)
        self.set_fill_color(245, 245, 247)
        self.rect(30, self.get_y(), 150, 50, "F")
        y = self.get_y() + 5
        self.set_xy(35, y)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(29, 29, 31)
        self.cell(0, 7, "Resumo Executivo", new_x="LMARGIN", new_y="NEXT")
        self.set_x(35)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(99, 99, 102)
        self.multi_cell(140, 6,
            "68 problemas identificados em auditoria completa do sistema.\n"
            "7 criticos | 16 altos | 25 medios | 20 baixos\n"
            "Areas: Seguranca, Performance, Bugs, Arquitetura, UX")

        self.ln(30)

        # Stats boxes
        self.set_font("Helvetica", "B", 10)
        stats = [
            ("65+", "Arquivos Python"),
            ("23", "Arquivos React"),
            ("40+", "Endpoints API"),
            ("9", "Integracoes"),
        ]
        x_start = 25
        for val, label in stats:
            self.set_xy(x_start, self.get_y())
            self.set_fill_color(29, 29, 31)
            self.set_text_color(253, 210, 0)
            self.set_font("Helvetica", "B", 18)
            self.rect(x_start, self.get_y(), 35, 25, "F")
            self.set_xy(x_start, self.get_y() + 3)
            self.cell(35, 8, val, align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_xy(x_start, self.get_y())
            self.set_font("Helvetica", "", 7)
            self.set_text_color(200, 200, 200)
            self.cell(35, 6, label, align="C")
            x_start += 42

    def section_title(self, title, color=(29, 29, 31)):
        self.ln(6)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*color)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(253, 210, 0)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(4)

    def subsection(self, title):
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(29, 29, 31)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text, indent=15):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 60)
        x = self.get_x()
        self.set_x(x + indent)
        # Draw a small filled circle as bullet
        y = self.get_y() + 2.2
        self.set_fill_color(60, 60, 60)
        self.ellipse(x + indent, y, 1.5, 1.5, "F")
        self.set_x(x + indent + 4)
        self.multi_cell(190 - indent - 14, 5.5, text)

    def severity_badge(self, severity, text):
        colors = {
            "CRITICO": (220, 38, 38),
            "ALTO": (234, 88, 12),
            "MEDIO": (202, 138, 4),
            "BAIXO": (37, 99, 235),
        }
        r, g, b = colors.get(severity, (100, 100, 100))

        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        w = self.get_string_width(severity) + 6
        self.cell(w, 5.5, severity, fill=True)
        self.cell(3)
        self.set_text_color(60, 60, 60)
        self.set_font("Helvetica", "B", 9.5)
        self.cell(0, 5.5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def table_header(self, cols, widths):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(29, 29, 31)
        self.set_text_color(255, 255, 255)
        for i, col in enumerate(cols):
            self.cell(widths[i], 7, col, border=0, fill=True, align="C")
        self.ln()

    def table_row(self, cols, widths, fill=False):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(60, 60, 60)
        if fill:
            self.set_fill_color(248, 248, 250)
        for i, col in enumerate(cols):
            self.cell(widths[i], 6.5, col, border=0, fill=fill, align="C" if i > 0 else "L")
        self.ln()


def generate_report():
    pdf = ReportPDF()
    pdf.alias_nb_pages()

    # ==================== COVER ====================
    pdf.cover_page()

    # ==================== VISAO GERAL ====================
    pdf.add_page()
    pdf.section_title("1. Visao Geral do Projeto")
    pdf.body_text(
        "O Carbon Helpdesk e um sistema completo de atendimento ao cliente para a Carbon Smartwatch, "
        "empresa brasileira de smartwatches. O sistema foi construido com FastAPI (backend), React 18 (frontend), "
        "PostgreSQL 16 e Redis 7, implantado via Docker Compose em um droplet DigitalOcean."
    )

    pdf.subsection("Stack Tecnologica")
    widths = [45, 145]
    pdf.table_header(["Camada", "Tecnologia"], widths)
    rows = [
        ("Backend", "FastAPI, SQLAlchemy async, PostgreSQL 16, Redis 7"),
        ("Frontend", "React 18, Vite 5, Tailwind CSS 3, Recharts"),
        ("IA", "Anthropic Claude (triagem, sugestoes, resumo)"),
        ("Deploy", "Docker Compose, Nginx, DigitalOcean"),
        ("Integracoes", "Gmail, Slack, Shopify, Yampi, Appmax, 17track, Notion"),
    ]
    for i, (a, b) in enumerate(rows):
        pdf.table_row([a, b], widths, fill=i % 2 == 0)

    pdf.ln(4)
    pdf.subsection("Funcionalidades Principais")
    features = [
        "Tickets multi-canal: Gmail, Slack, Web com SLA automatico e triagem por IA",
        "E-commerce integrado: Shopify, Yampi, Appmax (pedidos, reembolsos, cancelamentos)",
        "Rastreamento de pacotes: 17track com deteccao automatica de transportadora",
        "Knowledge Base: 17 artigos reais + sistema de macros",
        "AI Copilot: Triagem automatica, sugestoes de resposta, resumo, assistente interno",
        "Gamificacao: Leaderboard de agentes e sistema de recompensas",
        "CSAT: Pesquisa de satisfacao por email com NPS",
        "Relatorios: Dashboard multi-visao, metricas por agente, tendencias",
        "WebSocket: Notificacoes em tempo real e deteccao de colisao",
        "Protocolo automatico: Formato CARBON-YYYY-XXXXXX com envio por email",
    ]
    for f in features:
        pdf.bullet(f)

    # ==================== RESUMO DO DIAGNOSTICO ====================
    pdf.add_page()
    pdf.section_title("2. Resumo do Diagnostico")
    pdf.body_text(
        "Foram identificados 68 problemas no total, distribuidos entre backend (41) e frontend (30), "
        "com sobreposicao em areas compartilhadas. A tabela abaixo mostra a distribuicao por severidade."
    )

    widths = [40, 30, 30, 90]
    pdf.table_header(["Severidade", "Qtd", "Backend", "Exemplos"], widths)
    rows = [
        ("CRITICO", "7", "4 / 3", "Credenciais hardcoded, imports faltando"),
        ("ALTO", "16", "9 / 7", "SLA errado, N+1 queries, memory leaks"),
        ("MEDIO", "25", "16 / 9", "Sem Alembic, sem Error Boundary"),
        ("BAIXO", "20", "9 / 11", "Magic numbers, acessibilidade"),
    ]
    for i, (a, b, c, d) in enumerate(rows):
        pdf.table_row([a, b, c, d], widths, fill=i % 2 == 0)

    pdf.ln(6)
    pdf.subsection("Distribuicao por Categoria")
    widths2 = [50, 25, 115]
    pdf.table_header(["Categoria", "Qtd", "Impacto"], widths2)
    cats = [
        ("Seguranca", "12", "Credenciais expostas, RBAC incompleto, tokens inseguros"),
        ("Performance", "14", "N+1 queries, lazy loading, falta de indices, sem debounce"),
        ("Bugs", "18", "Imports faltando, SLA errado, race conditions, erros silenciosos"),
        ("Arquitetura", "10", "Sem Alembic, sem React Router, migracoes no startup"),
        ("UX", "8", "Tela branca, sem Error Boundary, acessibilidade"),
        ("Code Quality", "6", "Magic numbers, funcoes longas, prop drilling"),
    ]
    for i, (a, b, c) in enumerate(cats):
        pdf.table_row([a, b, c], widths2, fill=i % 2 == 0)

    # ==================== PROBLEMAS CRITICOS ====================
    pdf.add_page()
    pdf.section_title("3. Problemas Criticos", color=(220, 38, 38))
    pdf.body_text("Problemas que devem ser resolvidos imediatamente. Causam crashes, exposicao de dados ou comportamento incorreto em producao.")

    pdf.ln(2)
    pdf.severity_badge("CRITICO", "1. Credenciais hardcoded no codigo-fonte")
    pdf.body_text(
        "Arquivos: backend/app/core/config.py, frontend/src/pages/LoginPage.jsx\n"
        "JWT_SECRET e DATABASE_URL tem valores padrao no codigo. LoginPage exibe email e senha de demo "
        "(pedro@carbonsmartwatch.com.br / carbon2026) visivel para qualquer pessoa.\n"
        "Fix: Remover defaults, usar .env exclusivamente, nunca commitar secrets."
    )

    pdf.severity_badge("CRITICO", "2. Background tasks bloqueando o event loop")
    pdf.body_text(
        "Arquivo: backend/app/main.py\n"
        "Os loops _run_escalation_loop e _run_email_fetch_loop sao sincronos rodando em contexto async. "
        "O fetch de email a cada 60s bloqueia todo o servidor FastAPI.\n"
        "Fix: Usar asyncio.to_thread() ou migrar para Celery/ARQ."
    )

    pdf.severity_badge("CRITICO", "3. Migracoes SQL com except: pass")
    pdf.body_text(
        "Arquivo: backend/app/main.py (linhas 306-310)\n"
        "TODAS as falhas de migracao sao engolidas silenciosamente. Se uma migracao falhar, "
        "o banco fica inconsistente sem nenhum log ou aviso.\n"
        "Fix: Logar erros, falhar loudly. Implementar Alembic."
    )

    pdf.severity_badge("CRITICO", "4. Imports faltando causam NameError")
    pdf.body_text(
        "Arquivos: backend/app/api/tickets.py, backend/app/api/slack.py\n"
        "AuditLog referenciado mas nunca importado em tickets.py - crash ao processar ticket duplicado. "
        "func usado antes de ser importado em slack.py - crash ao processar mensagem.\n"
        "Fix: Adicionar imports no topo dos arquivos."
    )

    pdf.severity_badge("CRITICO", "5. Seed data executado em toda inicializacao")
    pdf.body_text(
        "Arquivo: backend/app/main.py\n"
        "Dados demo com tracking codes e clientes sao inseridos no startup. "
        "Em producao, isso pode sobrescrever dados reais.\n"
        "Fix: Mover para comando manual separado."
    )

    pdf.severity_badge("CRITICO", "6. Error handling vazio no frontend")
    pdf.body_text(
        "Arquivos: useWebSocket.js, Toast.jsx, api.js\n"
        "Blocos catch {} vazios em multiplos lugares silenciam erros criticos. "
        "Debug impossivel em producao.\n"
        "Fix: Logar todos os erros, implementar Sentry."
    )

    pdf.severity_badge("CRITICO", "7. API interceptor faz hard redirect em 401")
    pdf.body_text(
        "Arquivo: frontend/src/services/api.js\n"
        "Em erro 401, faz window.location.href = '/' sem limpar estado React, "
        "causando perda de dados pendentes e inconsistencia.\n"
        "Fix: Emitir evento de logout, limpar estado antes de redirecionar."
    )

    # ==================== PROBLEMAS ALTOS ====================
    pdf.add_page()
    pdf.section_title("4. Problemas de Alta Severidade", color=(234, 88, 12))

    pdf.subsection("Seguranca")
    issues_sec = [
        ("auth.py", "list_users() sem RBAC - qualquer agente ve todos os emails"),
        ("security.py", "Token JWT nao valida expiracao explicitamente"),
        ("useWebSocket.js", "Token exposto na URL do WebSocket (visivel em logs/historico)"),
        ("useWebSocket.js", "URL padrao ws:// (sem criptografia) em vez de wss://"),
        ("App.jsx", "Token do localStorage carregado sem validar se expirou"),
    ]
    for f, desc in issues_sec:
        pdf.severity_badge("ALTO", f"{f}: {desc}")

    pdf.subsection("Bugs")
    issues_bug = [
        ("ai.py:92", "SLA calculado a partir de created_at em vez de now() - SLA quebrado"),
        ("tickets.py", "!= None em vez de .isnot(None) no SQLAlchemy - SQL incorreto"),
        ("tickets.py", "pick_agent() ignora limite de max_tickets quando todos estao cheios"),
        ("tickets.py:558", "SLA recalculado 2x em bulk_update (logica duplicada)"),
        ("useWebSocket.js", "Race condition: multiplos timers de reconnect"),
    ]
    for f, desc in issues_bug:
        pdf.severity_badge("ALTO", f"{f}: {desc}")

    pdf.subsection("Performance")
    issues_perf = [
        ("ticket.py", "lazy='selectin' em TODAS as relationships - carrega mensagens sempre"),
        ("reports.py", "Query CSAT separada por agente dentro de loop - O(n) queries"),
        ("ecommerce.py", "Settings salvos so em memoria, perdem no restart"),
        ("NotificationBell.jsx", "Event listener sem cleanup adequado - memory leak"),
        ("App.jsx", "JSON.parse() sem try/catch - crash se localStorage corrompido"),
        ("App.jsx", "Retorna null enquanto carrega - tela branca sem feedback"),
    ]
    for f, desc in issues_perf:
        pdf.severity_badge("ALTO", f"{f}: {desc}")

    # ==================== PROBLEMAS MEDIOS ====================
    pdf.add_page()
    pdf.section_title("5. Problemas de Media Severidade", color=(202, 138, 4))

    pdf.subsection("Performance")
    items = [
        "Busca de tickets usa ilike sem indice - full table scan em datasets grandes",
        "Search com N+1 queries em mensagens/clientes",
        "JSONB tracking_data['carrier'] sem indice",
        "CSV export carrega TODOS tickets em memoria (risco de OOM)",
        "Modelo Claude hardcoded em multiplos lugares",
        "Auto-refresh de 30s roda mesmo com aba em background",
        "Busca sem debounce - API call a cada keystroke",
    ]
    for item in items:
        pdf.bullet(item)

    pdf.subsection("Arquitetura")
    items2 = [
        "Migracoes misturadas com startup code (deveria usar Alembic)",
        "setattr() direto no ticket bypassa validacao Pydantic",
        "Prop drilling excessivo no Layout (deveria usar React Router)",
        "Sem Error Boundary - crash em componente filho mata o app inteiro",
        "Sem retry logic para requests falhados",
    ]
    for item in items2:
        pdf.bullet(item)

    pdf.subsection("Logica de Negocio")
    items3 = [
        "Deteccao de ticket duplicado usa ilike('%subject[:50]%') - falsos positivos",
        "Agente pode acessar ticket nao-atribuido via ID direto",
        "Tickets 'archived' enviam CSAT email (nao deveriam)",
        "Bot messages do Slack podem ser processadas duplicadas",
        "WebSocket broadcast com except: pass - conexoes mortas silenciosas",
    ]
    for item in items3:
        pdf.bullet(item)

    pdf.subsection("UX")
    items4 = [
        "Toggle de tema no login nao funciona",
        "Modal de import fecha durante operacao em andamento",
        "Sem validacao visual em inputs numericos",
        "Sem atributos de acessibilidade (ARIA labels) na maioria dos botoes",
        "Potencial XSS em notificacoes (conteudo renderizado sem sanitizacao)",
    ]
    for item in items4:
        pdf.bullet(item)

    # ==================== PROBLEMAS BAIXOS ====================
    pdf.add_page()
    pdf.section_title("6. Problemas de Baixa Severidade", color=(37, 99, 235))

    items_low = [
        "_ticket_to_response() com 40 linhas de getattr() repetitivo",
        "Cores duplicadas entre CSS variables e JS constants",
        "Console.error em producao sem logging service",
        "Magic numbers espalhados (30000ms, 50, 3s) sem constantes nomeadas",
        "Formatacao de data inconsistente sem utility centralizada",
        "Deduplica tags com list(set()) que remove ordem",
        "Toast duration hardcoded (3000ms)",
        "Division by zero tratada com max(x, 1) em vez de check explicito",
        "Notificacao ID gerado com Date.now() + Math.random() - nao garante unicidade",
        "Inline style mutations (e.currentTarget.style) bypassa React",
        "ThemeContext implementado mas sem funcionalidade (tema unico)",
        "Falta de cleanup em intervals quando documento perde foco",
    ]
    for item in items_low:
        pdf.bullet(item)

    # ==================== RECOMENDACOES ====================
    pdf.add_page()
    pdf.section_title("7. Plano de Correcao Recomendado")

    pdf.subsection("Fase 1 - Urgente (Seguranca + Crashes)")
    pdf.body_text("Prioridade maxima. Resolver em 1-2 dias.")
    phase1 = [
        "Remover credenciais hardcoded do codigo (LoginPage.jsx, config.py)",
        "Corrigir imports faltando que causam crash (AuditLog, func)",
        "Adicionar tratamento de erros nas migracoes (sair do except: pass)",
        "Corrigir calculo de SLA no AI triage (usar now() em vez de created_at)",
        "Mover seed data para comando manual, nao startup",
        "Validar token JWT ao carregar app no frontend",
        "Adicionar Error Boundary no React",
    ]
    for i, item in enumerate(phase1, 1):
        pdf.bullet(f"{i}. {item}")

    pdf.ln(3)
    pdf.subsection("Fase 2 - Estabilidade")
    pdf.body_text("Resolver em 1 semana. Previne problemas recorrentes.")
    phase2 = [
        "Migrar background tasks para async real (asyncio.to_thread ou Celery)",
        "Implementar Alembic para migracoes de banco de dados",
        "Adicionar Error Boundary no React",
        "Corrigir race conditions no WebSocket reconnect",
        "Adicionar RBAC consistente em todas as rotas",
    ]
    for i, item in enumerate(phase2, 1):
        pdf.bullet(f"{i}. {item}")

    pdf.ln(3)
    pdf.subsection("Fase 3 - Performance")
    pdf.body_text("Resolver em 2 semanas. Melhora experiencia do usuario.")
    phase3 = [
        "Mudar relationships para lazy='select' e fazer join explicito",
        "Adicionar indices no banco (customer.name, ticket.status, tags)",
        "Implementar debounce na busca do frontend",
        "Usar visibility API para pausar refresh em abas inativas",
        "Batch CSAT queries nos relatorios (eliminar O(n) queries)",
        "Implementar streaming para CSV export",
    ]
    for i, item in enumerate(phase3, 1):
        pdf.bullet(f"{i}. {item}")

    pdf.ln(3)
    pdf.subsection("Fase 4 - Qualidade")
    pdf.body_text("Resolver em 1 mes. Melhora manutenibilidade.")
    phase4 = [
        "Implementar React Router real com rotas",
        "Adicionar logging service (Sentry ou similar)",
        "Centralizar formatacao de datas em utility",
        "Adicionar acessibilidade (ARIA labels, keyboard navigation)",
        "Extrair magic numbers para constantes nomeadas",
        "Criar sistema de temas funcional",
    ]
    for i, item in enumerate(phase4, 1):
        pdf.bullet(f"{i}. {item}")

    # ==================== METRICAS DO PROJETO ====================
    pdf.add_page()
    pdf.section_title("8. Metricas do Projeto")

    pdf.subsection("Backend")
    widths3 = [90, 100]
    pdf.table_header(["Metrica", "Valor"], widths3)
    be_metrics = [
        ("Arquivos Python", "65+"),
        ("Modelos de dados", "9 (User, Ticket, Message, Customer, etc.)"),
        ("Rotas API", "40+ endpoints"),
        ("Servicos", "12 (AI, Gmail, Slack, Shopify, etc.)"),
        ("Background tasks", "2 (escalation, email fetch)"),
        ("Integracoes externas", "9 (Gmail, Slack, Shopify, Yampi, etc.)"),
        ("Artigos KB", "17 artigos reais"),
        ("Macros", "6 templates pre-definidos"),
    ]
    for i, (a, b) in enumerate(be_metrics):
        pdf.table_row([a, b], widths3, fill=i % 2 == 0)

    pdf.ln(6)
    pdf.subsection("Frontend")
    fe_metrics = [
        ("Paginas", "12 (Dashboard, Tickets, Detail, KB, etc.)"),
        ("Componentes", "6 principais (Layout, Sidebar, Toast, etc.)"),
        ("API methods", "40+ funcoes no api.js"),
        ("Graficos", "9+ tipos (Bar, Pie, Line via Recharts)"),
        ("WebSocket", "Real-time notifications, collision detection"),
        ("Temas", "1 (Carbon - dark sidebar, yellow accent)"),
    ]
    for i, (a, b) in enumerate(fe_metrics):
        pdf.table_row([a, b], widths3, fill=i % 2 == 0)

    pdf.ln(6)
    pdf.subsection("Infraestrutura")
    infra_metrics = [
        ("Containers Docker", "4 (PostgreSQL, Redis, Backend, Frontend)"),
        ("Reverse Proxy", "Nginx com SSL/Certbot ready"),
        ("Servidor", "DigitalOcean (143.198.20.6)"),
        ("Dominio", "helpdesk.carbonsmartwatch.com.br"),
        ("Scripts de deploy", "5 bash scripts"),
    ]
    for i, (a, b) in enumerate(infra_metrics):
        pdf.table_row([a, b], widths3, fill=i % 2 == 0)

    # ==================== CONCLUSAO ====================
    pdf.add_page()
    pdf.section_title("9. Conclusao")
    pdf.body_text(
        "O Carbon Helpdesk e um sistema robusto e ambicioso, com funcionalidades avancadas de IA, "
        "integracao multi-canal e e-commerce. O codigo esta funcional mas apresenta problemas significativos "
        "de seguranca, performance e estabilidade que devem ser resolvidos antes de escalar para producao."
    )
    pdf.ln(2)
    pdf.body_text(
        "As 7 correcoes criticas devem ser priorizadas imediatamente, pois incluem credenciais expostas "
        "e bugs que causam crashes em runtime. As correcoes de alta severidade (16 itens) afetam "
        "a confiabilidade do sistema e a experiencia do usuario."
    )
    pdf.ln(2)
    pdf.body_text(
        "Com as 4 fases de correcao implementadas, o sistema estara pronto para operacao em producao "
        "com seguranca, performance e manutenibilidade adequadas."
    )

    pdf.ln(10)
    pdf.set_fill_color(253, 210, 0)
    pdf.rect(10, pdf.get_y(), 190, 3, "F")
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, "Relatorio gerado automaticamente via auditoria de codigo.", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C")

    # Save
    output_path = "/Users/pedrocastro/Desktop/carbon-helpdesk/Carbon_Helpdesk_Diagnostico.pdf"
    pdf.output(output_path)
    return output_path


if __name__ == "__main__":
    path = generate_report()
    print(f"Relatorio gerado: {path}")
