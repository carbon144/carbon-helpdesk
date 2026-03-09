"""
Seed script para criar chatbot flows do Carbon Helpdesk — REDESIGN v3.
Baseado na análise de 1870 tickets reais + doc Reportana.
Tom casual alinhado com WhatsApp. 22 flows.
Uso: python seed_chatbot_flows.py
"""

import asyncio
from sqlalchemy import select, func

from app.core.database import engine, async_session
from app.models.chatbot_flow import ChatbotFlow


# ── Menu Principal ──

MENU_OPTIONS = [
    {"id": "meu_pedido", "label": "Meu Pedido", "description": "Rastreio, status, nota fiscal"},
    {"id": "garantia", "label": "Trocas e Garantia", "description": "Defeito, troca, devolução"},
    {"id": "financeiro", "label": "Financeiro", "description": "Cancelamento, estorno, pagamento"},
    {"id": "duvida_geral", "label": "Dúvida geral", "description": "Sobre produtos, uso, compra"},
]

SUBMENU_PEDIDO = [
    {"id": "rastreio", "label": "Rastreio / Entrega", "description": "Onde está meu pedido"},
    {"id": "nota_fiscal", "label": "Nota Fiscal", "description": "Solicitar NF do pedido"},
    {"id": "nao_recebi", "label": "Não recebi / Extraviado", "description": "Pedido não chegou"},
    {"id": "pedido_incompleto", "label": "Pedido incompleto", "description": "Faltou item no pedido"},
    {"id": "cancelar", "label": "Cancelar pedido", "description": "Quero cancelar"},
]

SUBMENU_GARANTIA = [
    {"id": "consultar_troque", "label": "Consultar solicitação", "description": "Já abri no Troque, quero o status"},
    {"id": "defeito", "label": "Defeito / Não funciona", "description": "Relógio com problema"},
    {"id": "arrependimento", "label": "Arrependimento / Devolução", "description": "Quero devolver"},
    {"id": "produto_errado", "label": "Produto errado", "description": "Veio errado"},
    {"id": "assistencia", "label": "Assistência técnica", "description": "Conserto / reparo"},
    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Menu principal"},
]

SUBMENU_FINANCEIRO = [
    {"id": "cancelar", "label": "Cancelar pedido", "description": "Quero cancelar minha compra"},
    {"id": "estorno", "label": "Estorno / Reembolso", "description": "Quero meu dinheiro de volta"},
    {"id": "pagamento", "label": "Dúvida de pagamento", "description": "Boleto, pix, parcela"},
    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Menu principal"},
]


FLOWS = [
    # ══════════════════════════════════════════════════════════════
    # 1. SAUDAÇÃO + MENU PRINCIPAL
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Saudação + Menu",
        "trigger_type": "greeting",
        "trigger_config": {},
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Fala! Seja bem-vindo(a) à Carbon 👊\n"
                    "Sou o assistente virtual e vou te ajudar."
                ),
            },
            {
                "type": "send_menu",
                "message": "Como posso te ajudar?",
                "options": MENU_OPTIONS,
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 2. MEU PEDIDO (submenu)
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Meu Pedido",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "meu pedido", "pedido", "minha compra", "comprei",
                "status do pedido", "meu_pedido",
            ]
        },
        "steps": [
            {
                "type": "send_menu",
                "message": "Show! O que você precisa sobre o pedido?",
                "options": SUBMENU_PEDIDO,
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 3. RASTREIO DE PEDIDO
    # 22% do volume — maior demanda.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Rastreio de Pedido",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "rastreio", "rastrear", "rastreamento", "entrega", "chegou",
                "onde está", "cadê", "tracking", "código de rastreio",
                "encomenda", "correios", "transportadora", "prazo",
                "previsão", "status", "exceção",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Vou verificar o status do seu pedido 👊",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": (
                    "Me passa o número do pedido ou o e-mail da compra.\n"
                    "Exemplo: 128478 ou #128478"
                ),
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não achei esse pedido. Confere o número e tenta de novo.\n"
                    "Se preferir, digita *atendente* pra falar com a equipe."
                ),
                "found_message": (
                    "Achei seu pedido!\n\n"
                    "Pedido: {order_name}\n"
                    "Status: {status}\n"
                    "Rastreio: {tracking_number}\n\n"
                    "Acompanhe em: carbonsmartwatch.com.br/tracking"
                ),
            },
            {
                "type": "send_menu",
                "message": "Posso te ajudar com mais alguma coisa?",
                "options": [
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opções"},
                    {"id": "atendente", "label": "Falar com atendente", "description": "Atendimento humano"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 4. NOTA FISCAL
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Nota Fiscal",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "nota fiscal", "nf", "nfe", "cupom fiscal", "nota_fiscal",
                "danfe", "nota do pedido",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Vou buscar a nota fiscal do seu pedido 👊",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Me passa o número do pedido:",
            },
            {
                "type": "lookup_invoice",
                "variable": "order_number",
                "found_message": (
                    "Achei a nota fiscal!\n\n"
                    "NFS-e nº {nfse_number}\n"
                    "Valor: R$ {valor_servico}\n\n"
                    "Acesse o PDF aqui: {link_pdf}\n\n"
                    "A NF também foi enviada pro e-mail da compra."
                ),
                "not_found_message": (
                    "A nota fiscal desse pedido ainda não tá disponível.\n"
                    "Ela é enviada automaticamente por e-mail após o faturamento.\n\n"
                    "Confere a pasta de spam. Se não achou, vou encaminhar pro time."
                ),
            },
            {
                "type": "send_menu",
                "message": "Posso te ajudar com mais alguma coisa?",
                "options": [
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opções"},
                    {"id": "atendente", "label": "Falar com atendente", "description": "Atendimento humano"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 5. CANCELAMENTO
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Cancelamento",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "cancelar", "cancelamento", "cancela", "desistir",
                "desistência", "não quero mais", "cancelar pedido",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Entendi que quer cancelar seu pedido.\n\n"
                    "Como funciona:\n"
                    "- Pedido não enviado: cancelamos e fazemos o estorno.\n"
                    "- Pedido já enviado: recuse a entrega ou devolva em até 7 dias.\n\n"
                    "Prazo do estorno: até 10 dias úteis.\n"
                    "Pix: devolvido direto. Cartão: até 3 faturas."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Me passa o número do pedido que quer cancelar:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não achei esse pedido. Confere o número e tenta de novo.\n"
                    "Pode mandar o *e-mail* da compra também.\n\n"
                    "Ou digita *atendente* pra falar com a equipe."
                ),
                "found_message": (
                    "Pedido localizado:\n\n"
                    "Pedido: {order_name}\n"
                    "Status: {status}\n"
                    "Valor: R$ {total_price}\n\n"
                    "Vou encaminhar pro time processar o cancelamento."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Anotado! Já encaminhei pro nosso time 👊\n"
                    "Pedido: {{order_number}}\n"
                    "Nosso time vai responder pelo seu e-mail."
                ),
                "department": "financeiro",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 6. TROCAS E GARANTIA (submenu)
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Trocas e Garantia",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "garantia", "troca", "trocar", "devolução",
            ]
        },
        "steps": [
            {
                "type": "send_menu",
                "message": "Beleza! Qual a situação?",
                "options": SUBMENU_GARANTIA,
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 7. DEFEITO / NÃO FUNCIONA
    # 5.5% do volume. Pergunta se já abriu no Troque primeiro.
    # Se não → questionário 7 perguntas → link Troque → ticket
    # Se sim → redireciona pra consulta Troque
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Defeito / Não Funciona",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "defeito", "quebrou", "não funciona", "parou", "não liga",
                "não carrega", "travou", "apagou", "esquentando", "tela",
                "bateria", "parou de funcionar",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Poxa, sinto muito pelo transtorno!",
            },
            {
                "type": "send_menu",
                "message": "Você já abriu uma solicitação no nosso portal de trocas (Troque)?",
                "options": [
                    {"id": "consultar_troque", "label": "Sim, quero consultar o status", "description": "Já tenho solicitação aberta"},
                    {"id": "defeito_questionario", "label": "Não, quero abrir uma nova", "description": "Ainda não solicitei"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 7b. DEFEITO QUESTIONÁRIO
    # Questionário 7 perguntas quando cliente NÃO abriu no Troque.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Defeito Questionário",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": ["defeito_questionario"],
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Vou precisar te fazer algumas perguntas rápidas pra entender o que tá acontecendo 👊",
            },
            # Q1: Descrição livre do problema
            {
                "type": "collect_input",
                "variable": "descricao_problema",
                "message": "Descreve pra mim o que tá acontecendo com o relógio:",
            },
            # Q2: Contato com água
            {
                "type": "collect_input",
                "variable": "contato_agua",
                "message": "O problema começou após *contato com água*?",
                "options": [
                    {"id": "sim_agua", "label": "Sim, teve contato com água"},
                    {"id": "nao_agua", "label": "Não"},
                ],
            },
            # Q3: Água quente/vapor
            {
                "type": "collect_input",
                "variable": "agua_quente",
                "message": "O produto foi exposto a *chuveiro, vapor, sauna ou água quente*?",
                "options": [
                    {"id": "sim_quente", "label": "Sim"},
                    {"id": "nao_quente", "label": "Não"},
                ],
            },
            # Q4: Botões molhado
            {
                "type": "collect_input",
                "variable": "botoes_molhado",
                "message": "Você pressionou os *botões* do produto enquanto molhado ou submerso?",
                "options": [
                    {"id": "sim_botoes", "label": "Sim"},
                    {"id": "nao_botoes", "label": "Não"},
                ],
            },
            # Q5: Drenagem
            {
                "type": "collect_input",
                "variable": "drenagem",
                "message": "Já fez o procedimento de *drenagem*?",
                "options": [
                    {"id": "sim_drenagem", "label": "Sim, já fiz"},
                    {"id": "nao_drenagem", "label": "Não fiz"},
                    {"id": "nao_aplicavel", "label": "Não se aplica"},
                ],
            },
            # Q6: Reset de fábrica
            {
                "type": "collect_input",
                "variable": "reset",
                "message": "Já fez o *reset de fábrica*?\nConfigurações → Restaurar padrão de fábrica",
                "options": [
                    {"id": "sim_reset", "label": "Sim, já fiz reset"},
                    {"id": "nao_reset", "label": "Não fiz reset"},
                ],
            },
            # Q7: Fonte/carregador
            {
                "type": "collect_input",
                "variable": "carregador",
                "message": "Qual *fonte* você usa pra carregar o produto?",
                "options": [
                    {"id": "notebook", "label": "Notebook / PC"},
                    {"id": "adaptador_comum", "label": "Adaptador comum"},
                    {"id": "adaptador_turbo", "label": "Adaptador turbo"},
                ],
            },
            {
                "type": "send_message",
                "message": (
                    "Anotado! 👊\n\n"
                    "Pra abrir sua solicitação de garantia, acesse:\n"
                    "👉 *carbonsmartwatch.troque.app.br*\n\n"
                    "Também vou abrir um chamado pro nosso time analisar.\n"
                    "Você vai receber retorno pelo *e-mail*.\n\n"
                    "*IMPORTANTE:* Responde o e-mail do chamado com:\n"
                    "- Fotos mostrando o defeito\n"
                    "- Vídeo curto do problema (se possível)\n"
                    "- Foto do carregador com as especificações"
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "SOLICITAÇÃO DE GARANTIA/TROCA\n\n"
                    "Descrição: {{descricao_problema}}\n"
                    "Contato com água: {{contato_agua}}\n"
                    "Água quente/vapor: {{agua_quente}}\n"
                    "Botões molhado: {{botoes_molhado}}\n"
                    "Drenagem: {{drenagem}}\n"
                    "Reset: {{reset}}\n"
                    "Carregador: {{carregador}}\n\n"
                    "Cliente direcionado ao Troque.\n"
                    "Aguardando fotos/vídeo por e-mail."
                ),
                "department": "garantia",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 8. TROCA DE MODELO / PULSEIRA
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Troca de Modelo ou Pulseira",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "trocar modelo", "trocar pulseira", "pulseira errada",
                "pulseira incompatível", "modelo errado", "troca_modelo",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Pra trocar modelo ou pulseira, acesse:\n"
                    "👉 *carbonsmartwatch.troque.app.br*\n\n"
                    "Prazo: até 7 dias após receber.\n"
                    "O produto deve estar sem uso e na embalagem original."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Se precisar de ajuda, me passa o número do pedido:",
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Encaminhando pro time ajudar com a troca do pedido {order_number} 👊"
                ),
                "department": "garantia",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 9. NÃO RECEBI / REENVIO
    # 11.5% do volume.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Não Recebi / Reenvio",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "não recebi", "nao recebi", "não chegou", "nao chegou",
                "atrasado", "atraso", "extraviado", "reenvio", "devolvido",
                "alfândega", "taxado", "demora", "barrado", "fiscalização",
                "nao_recebi",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Entendo sua preocupação. Vou verificar a situação do seu pedido 👊",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Me passa o número do pedido ou o e-mail da compra:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não achei esse pedido. Confere o número e tenta de novo.\n"
                    "Ou digita *atendente* pra falar com a equipe."
                ),
                "found_message": (
                    "Pedido localizado:\n\n"
                    "Pedido: {order_name}\n"
                    "Status: {status}\n"
                    "Rastreio: {tracking_number}\n\n"
                    "Vou encaminhar pro time verificar a entrega."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Encaminhando pro time analisar a entrega do pedido {order_number}.\n"
                    "Vão verificar as opções (reenvio, estorno) e te retornar 👊"
                ),
                "department": "logística",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 10. FINANCEIRO (submenu)
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Financeiro",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "financeiro", "pix", "boleto",
                "pagamento", "paguei", "cobrado", "parcela",
                "cartão", "cobrança", "fatura",
            ]
        },
        "steps": [
            {
                "type": "send_menu",
                "message": "Beleza! Qual a questão financeira?",
                "options": SUBMENU_FINANCEIRO,
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 11. ESTORNO / REEMBOLSO
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Estorno / Reembolso",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "estorno", "reembolso", "dinheiro de volta", "ressarcimento",
                "devolver dinheiro", "meu dinheiro",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Sobre o estorno:\n\n"
                    "Prazo: até 10 dias úteis.\n"
                    "- Pix: devolvido direto.\n"
                    "- Cartão: pode levar até 3 faturas.\n\n"
                    "Você recebe a confirmação por e-mail."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Me passa o número do pedido pra verificar o estorno:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": "Não achei esse pedido. Confere o número.",
                "found_message": (
                    "Pedido localizado:\n\n"
                    "Pedido: {order_name}\n"
                    "Pagamento: {financial_status}\n"
                    "Valor: R$ {total_price}\n\n"
                    "Vou encaminhar pro time financeiro verificar."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Encaminhando pro time financeiro verificar o estorno do pedido {order_number} 👊"
                ),
                "department": "financeiro",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 12. SUPORTE TÉCNICO
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Suporte Técnico",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "bluetooth", "app", "aplicativo", "conectar", "configurar",
                "atualizar", "reset", "resetar", "gps", "sensor",
                "frequência cardíaca", "batimento", "sono", "notificação",
                "liga e desliga", "reiniciando", "travando",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Bora resolver! 👊\n\n"
                    "Primeiro, confere se tá usando o app certo:\n"
                    "- *Raptor* ou *Atlas*: app *GloryFitPro*\n"
                    "- *One Max* ou *Aurora*: app *DaFit*\n\n"
                    "Se o problema continuar, tenta o reset de fábrica:\n"
                    "1. Configurações no relógio\n"
                    "2. Restaurar padrão de fábrica\n"
                    "3. Confirme e aguarde reiniciar\n"
                    "4. Reconecte pelo app no celular\n\n"
                    "Se não resolver, vou encaminhar pro time."
                ),
            },
            {
                "type": "collect_input",
                "variable": "problema_tecnico",
                "message": "O reset resolveu? Se não, descreve o que tá acontecendo:",
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Encaminhando pro time técnico 👊\n\n"
                    "Problema: {problema_tecnico}"
                ),
                "department": "garantia",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 13. DÚVIDA GERAL → IA
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Dúvida Geral (IA)",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "dúvida", "duvida", "pergunta", "informação", "quero saber",
                "como funciona", "como usar",
                "à prova d'água", "resistente", "modelo", "diferença",
                "duvida_geral", "dúvida geral",
            ]
        },
        "steps": [
            {
                "type": "transfer_to_ai",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 14. FALAR COM ATENDENTE
    # Informa que atendimento é por email. Reduz escalações.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Falar com Atendente",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "atendente", "humano", "pessoa", "agente", "falar com alguém",
                "quero falar", "atendimento",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Nosso atendimento funciona por e-mail 👊\n\n"
                    "Manda sua dúvida pra:\n"
                    "📧 *atendimento@carbonsmartwatch.com.br*\n\n"
                    "Prazo de resposta: até 48 horas úteis."
                ),
            },
            {
                "type": "send_menu",
                "message": "Posso te ajudar com mais alguma coisa?",
                "options": [
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opções"},
                    {"id": "preciso_ajuda", "label": "Preciso de mais ajuda", "description": "Abrir chamado"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 14b. PRECISO DE MAIS AJUDA (escala de verdade)
    # Trigger quando cliente insiste após "Falar com Atendente"
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Preciso de Mais Ajuda",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": ["preciso_ajuda", "preciso de mais ajuda"],
        },
        "steps": [
            {
                "type": "transfer_to_agent",
                "message": (
                    "Anotado! Já encaminhei pro nosso time 👊\n"
                    "Vamos responder pelo seu e-mail."
                ),
                "department": "geral",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 15. PROCON / JURÍDICO / RECLAME AQUI → ESCALAR IMEDIATO
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Procon / Jurídico / Reclame Aqui",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "procon", "advogado", "processo", "justiça", "juizado",
                "danos morais", "reclame aqui", "reclameaqui",
                "consumidor.gov", "desacordo comercial", "chargeback",
                "contestação", "disputa",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Entendo a gravidade e peço desculpas pelo transtorno.\n"
                    "Vou encaminhar agora pro time responsável — seu caso vai ser tratado com prioridade total."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "⚠️ PRIORIDADE ALTA — Chamado prioritário.\n"
                    "Nosso time vai analisar e responder pelo seu e-mail.\n\n"
                    "Horário: segunda a sexta, 9h às 18h."
                ),
                "department": "jurídico",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 16. DÚVIDA PRÉ-VENDA → IA
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Pré-Venda",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "comprar", "preço", "valor", "desconto", "cupom",
                "frete", "prazo entrega", "tributo", "imposto", "taxa",
                "produto nacional", "importado",
            ]
        },
        "steps": [
            {
                "type": "transfer_to_ai",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 17. QUESTIONAMENTO NF (serviço vs produto)
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Questionamento Nota Fiscal",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "nota de serviço", "nota de servico", "nf de serviço",
                "nf de servico", "nota errada", "nf errada",
                "nota diferente", "valor da nota", "valor da nf",
                "nota não confere", "nf não confere",
                "nota de produto", "nf de produto",
                "nota com valor", "por que a nota",
                "porque a nota", "nota fiscal errada",
                "intermediação", "intermediacao", "intermediador",
                "nota fiscal de serviço", "nota fiscal de servico",
                "nota fiscal de produto", "pq nota fiscal",
                "pq a nota", "quero nota de produto",
                "quero nf de produto", "nota fiscal errada",
                "por que serviço", "por que servico",
                "pq serviço", "pq servico",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Entendo sua dúvida sobre a nota fiscal.\n\n"
                    "A Carbon atua como intermediadora comercial. Nosso CNPJ é enquadrado "
                    "como empresa de intermediação, e a NF é emitida nessa modalidade — "
                    "formato correto e legal pro nosso enquadramento.\n\n"
                    "Não conseguimos emitir em outro modelo porque o CNPJ não permite."
                ),
            },
            {
                "type": "send_message",
                "message": (
                    "Mas fica tranquilo! 👊\n\n"
                    "O valor integral da compra tá registrado na nota. "
                    "Ela tem validade fiscal normal e serve como comprovante pra tudo, "
                    "incluindo garantia.\n\n"
                    "Se precisa da nota pra algo específico, me explica que vejo como ajudar."
                ),
            },
            {
                "type": "send_menu",
                "message": "Posso te ajudar com mais alguma coisa?",
                "options": [
                    {"id": "atendente", "label": "Falar com atendente", "description": "Se ainda tiver dúvidas sobre a NF"},
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opções"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 18. PEDIDO INCOMPLETO (NOVO)
    # Item faltando no pedido.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Pedido Incompleto",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "faltando", "incompleto", "veio sem", "não veio tudo",
                "nao veio tudo", "faltou", "pedido incompleto",
                "pedido_incompleto",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Poxa, sinto muito! Vou te ajudar com isso 👊",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Me passa o número do pedido:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não achei esse pedido. Confere o número e tenta de novo.\n"
                    "Ou digita *atendente* pra falar com a equipe."
                ),
                "found_message": (
                    "Pedido localizado:\n\n"
                    "Pedido: {order_name}\n"
                    "Status: {status}"
                ),
            },
            {
                "type": "collect_input",
                "variable": "item_faltando",
                "message": "Qual item tá faltando no seu pedido? Descreve pra mim:",
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "PEDIDO INCOMPLETO\n\n"
                    "Pedido: {{order_number}}\n"
                    "Item faltando: {{item_faltando}}\n\n"
                    "Verificar e providenciar envio do item."
                ),
                "department": "logística",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 19. ARREPENDIMENTO / DEVOLUÇÃO (NOVO)
    # Direito de arrependimento — 7 dias CDC.
    # Pergunta se já abriu no Troque primeiro.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Arrependimento / Devolução",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "arrependimento", "devolver", "devolução", "devolucao",
                "não quero", "nao quero", "me arrependi",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Entendi! Sobre devolução por arrependimento:\n\n"
                    "- Prazo: até *7 dias* após receber o produto\n"
                    "- Produto *sem uso* e na *embalagem original*\n"
                    "- Estorno em até 10 dias úteis após receber a devolução"
                ),
            },
            {
                "type": "send_menu",
                "message": "Você já abriu uma solicitação no nosso portal de trocas (Troque)?",
                "options": [
                    {"id": "consultar_troque", "label": "Sim, quero consultar o status", "description": "Já tenho solicitação aberta"},
                    {"id": "abrir_arrependimento", "label": "Não, quero abrir uma nova", "description": "Ainda não solicitei"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 19b. ABRIR ARREPENDIMENTO (direciona pro Troque + escala)
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Abrir Arrependimento",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": ["abrir_arrependimento"],
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Pra abrir sua solicitação de devolução, acesse:\n"
                    "👉 *carbonsmartwatch.troque.app.br*\n\n"
                    "Lá você consegue gerar a etiqueta de devolução."
                ),
            },
            {
                "type": "send_menu",
                "message": "Posso te ajudar com mais alguma coisa?",
                "options": [
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opções"},
                    {"id": "preciso_ajuda", "label": "Preciso de ajuda com a devolução", "description": "Falar com time"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 20. PRODUTO ERRADO (NOVO)
    # Recebeu produto diferente do que comprou.
    # Pergunta se já abriu no Troque primeiro.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Produto Errado",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "produto errado", "veio errado", "errado", "trocado",
                "produto_errado",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Poxa, sinto muito pelo erro!",
            },
            {
                "type": "send_menu",
                "message": "Você já abriu uma solicitação no nosso portal de trocas (Troque)?",
                "options": [
                    {"id": "consultar_troque", "label": "Sim, quero consultar o status", "description": "Já tenho solicitação aberta"},
                    {"id": "abrir_produto_errado", "label": "Não, quero abrir uma nova", "description": "Ainda não solicitei"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 20b. ABRIR PRODUTO ERRADO (coleta dados + Troque + ticket)
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Abrir Produto Errado",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": ["abrir_produto_errado"],
        },
        "steps": [
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Me passa o número do pedido:",
            },
            {
                "type": "collect_input",
                "variable": "produto_recebido",
                "message": "Qual produto você recebeu? (descreve ou manda o nome/modelo)",
            },
            {
                "type": "send_message",
                "message": (
                    "Pra agilizar a troca, acesse:\n"
                    "👉 *carbonsmartwatch.troque.app.br*\n\n"
                    "Também vou abrir um chamado pro time acompanhar."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "PRODUTO ERRADO\n\n"
                    "Pedido: {{order_number}}\n"
                    "Produto recebido: {{produto_recebido}}\n\n"
                    "Cliente direcionado ao Troque. Verificar e providenciar troca."
                ),
                "department": "garantia",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 21. ASSISTÊNCIA TÉCNICA (NOVO)
    # Carbon NÃO tem assistência. Redireciona pra garantia ou cupom.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Assistência Técnica",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "assistência", "assistencia", "conserto", "consertar",
                "reparo", "reparar", "oficina", "técnico",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "A Carbon não possui assistência técnica no momento.\n\n"
                    "Mas temos duas opções pra te ajudar:"
                ),
            },
            {
                "type": "send_menu",
                "message": "Qual se encaixa melhor?",
                "options": [
                    {"id": "defeito", "label": "Tô na garantia", "description": "Abrir solicitação de troca"},
                    {"id": "cupom_assistencia", "label": "Quero um cupom de desconto", "description": "Pra comprar um novo"},
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opções"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 21b. CUPOM ASSISTÊNCIA (escala pra time dar cupom)
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Cupom Assistência",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": ["cupom_assistencia"],
        },
        "steps": [
            {
                "type": "collect_input",
                "variable": "obs_cupom",
                "message": "Me conta um pouco mais sobre a situação do seu relógio:",
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "CUPOM ASSISTÊNCIA\n\n"
                    "Cliente sem garantia, solicitando cupom de desconto.\n"
                    "Observação: {{obs_cupom}}"
                ),
                "department": "garantia",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # CONSULTAR SOLICITAÇÃO TROQUE
    # Busca status da reversa via API TroqueCommerce.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Consultar Solicitação Troque",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "consultar_troque", "consultar solicitação", "consultar solicitacao",
                "status troca", "status devolução", "minha solicitação",
                "minha solicitacao", "status reversa",
            ],
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Vou consultar o status da sua solicitação no Troque 👊",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Me passa o número do pedido ou o e-mail usado na compra:",
            },
            {
                "type": "lookup_troque",
                "variable": "order_number",
                "found_message": "",
                "not_found_message": "",
            },
            {
                "type": "send_menu",
                "message": "Posso te ajudar com mais alguma coisa?",
                "options": [
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opções"},
                    {"id": "preciso_ajuda", "label": "Preciso de mais ajuda", "description": "Falar com time"},
                ],
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # FALLBACK → MENU
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Fallback",
        "trigger_type": "any",
        "trigger_config": {},
        "steps": [
            {
                "type": "send_message",
                "message": "Hmm, não entendi 🤔",
            },
            {
                "type": "send_menu",
                "message": "Escolhe uma opção que eu te ajudo:",
                "options": MENU_OPTIONS,
            },
        ],
        "active": True,
    },
]


async def seed():
    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(ChatbotFlow)
        )
        count = result.scalar()

        if count > 0:
            resp = input(
                f"Já existem {count} chatbot flow(s) no banco. "
                "Deseja deletar e recriar? (s/n): "
            )
            if resp.strip().lower() != "s":
                print("Abortado.")
                return

            await session.execute(
                ChatbotFlow.__table__.delete()
            )
            await session.commit()
            print(f"{count} flow(s) deletado(s).")

        for flow_data in FLOWS:
            flow = ChatbotFlow(
                name=flow_data["name"],
                trigger_type=flow_data["trigger_type"],
                trigger_config=flow_data["trigger_config"],
                steps=flow_data["steps"],
                active=flow_data["active"],
            )
            session.add(flow)
            print(f"  + {flow_data['name']} ({flow_data['trigger_type']})")

        await session.commit()
        print(f"\n{len(FLOWS)} chatbot flows criados com sucesso!")


if __name__ == "__main__":
    asyncio.run(seed())
