"""
Seed script para criar chatbot flows do Carbon Helpdesk — REDESIGN v2.
Baseado na análise de 1870 tickets reais.
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
    {"id": "cancelar", "label": "Cancelar pedido", "description": "Quero cancelar"},
    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Menu principal"},
]

SUBMENU_GARANTIA = [
    {"id": "defeito", "label": "Defeito / Não funciona", "description": "Relógio com problema"},
    {"id": "troca_modelo", "label": "Trocar modelo ou pulseira", "description": "Quero trocar"},
    {"id": "nao_recebi", "label": "Não recebi / Extraviado", "description": "Pedido não chegou"},
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
                    "Olá! Bem-vindo ao suporte da Carbon.\n"
                    "Sou o assistente virtual e vou te ajudar."
                ),
            },
            {
                "type": "send_menu",
                "message": "Como posso te ajudar? Escolha uma opção:",
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
                "type": "send_message",
                "message": "Certo! Vou te ajudar com seu pedido.",
            },
            {
                "type": "send_menu",
                "message": "O que você precisa?",
                "options": SUBMENU_PEDIDO,
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 3. RASTREIO DE PEDIDO
    # 22% do volume — maior demanda. Resolver 100% aqui.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Rastreio de Pedido",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "rastreio", "rastrear", "rastreamento", "entrega", "chegou",
                "onde está", "cadê", "tracking", "código de rastreio",
                "encomenda", "correios", "transportadora", "prazo",
                "previsão", "status", "exceção", "devolvido",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Vou verificar o status do seu pedido.",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": (
                    "Me informe o número do seu pedido ou o e-mail usado na compra.\n"
                    "Exemplo: 128478 ou #128478"
                ),
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não encontrei esse pedido. Verifique o número e tente novamente.\n"
                    "Se preferir, digite *atendente* para falar com a equipe."
                ),
                "found_message": (
                    "Encontrei seu pedido!\n\n"
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
    # Tenta puxar NF automaticamente do sistema Carbon NF.
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
                "message": "Vou buscar a nota fiscal do seu pedido.",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o número do pedido:",
            },
            {
                "type": "lookup_invoice",
                "variable": "order_number",
                "found_message": (
                    "Encontrei a nota fiscal do seu pedido!\n\n"
                    "NFS-e nº {nfse_number}\n"
                    "Valor: R$ {valor_servico}\n\n"
                    "Acesse o PDF aqui: {link_pdf}\n\n"
                    "A NF também foi enviada para o e-mail cadastrado na compra."
                ),
                "not_found_message": (
                    "A nota fiscal desse pedido ainda não está disponível no sistema.\n"
                    "Ela é enviada automaticamente por e-mail após o faturamento.\n\n"
                    "Se você não recebeu, verifique a pasta de spam.\n"
                    "Vou transferir para a equipe verificar."
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
    # Regras claras: antes de faturar = cancela. Depois = recusar/devolver.
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
                    "Entendi que você quer cancelar seu pedido.\n\n"
                    "Como funciona o cancelamento na Carbon:\n"
                    "- Pedido ainda não enviado: cancelamos e fazemos o estorno.\n"
                    "- Pedido já enviado: você pode recusar a entrega ou devolver em até 7 dias após receber.\n\n"
                    "O prazo do estorno é de até 10 dias úteis.\n"
                    "Pix: devolvido direto. Cartão: pode levar até 3 faturas."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o número do pedido que deseja cancelar:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não encontrei esse pedido. Verifique o número e tente novamente."
                ),
                "found_message": (
                    "Pedido localizado:\n\n"
                    "Pedido: {order_name}\n"
                    "Status: {status}\n"
                    "Valor: R$ {total_price}\n\n"
                    "Vou transferir para a equipe processar o cancelamento."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Transferindo para a equipe processar o cancelamento do pedido {order_number}.\n"
                    "Um atendente vai confirmar os próximos passos."
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
                "garantia", "troca", "trocar", "devolução", "devolver",
                "arrependimento", "produto errado",
            ]
        },
        "steps": [
            {
                "type": "send_menu",
                "message": "Certo! Qual a situação?",
                "options": SUBMENU_GARANTIA,
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 7. DEFEITO / NÃO FUNCIONA
    # 5.5% do volume. Coletar dados + direcionar pra troque.app
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Defeito / Não Funciona",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "defeito", "quebrou", "não funciona", "parou", "não liga",
                "não carrega", "travou", "apagou", "esquentando", "tela",
                "bateria", "consertar", "reparo", "assistência",
                "parou de funcionar",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Sinto muito que você esteja tendo problemas com seu Carbon.\n"
                    "Vou coletar algumas informações para analisar seu caso."
                ),
            },
            {
                "type": "collect_input",
                "variable": "modelo",
                "message": (
                    "Qual o modelo do seu relógio?\n"
                    "Carbon Raptor, Atlas, One Max, Aurora ou Quartz?"
                ),
            },
            {
                "type": "collect_input",
                "variable": "problema",
                "message": "Descreva o problema que está acontecendo:",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o número do pedido ou NF para verificar a garantia:",
            },
            {
                "type": "send_message",
                "message": (
                    "Obrigado pelas informações!\n\n"
                    "A Carbon oferece garantia de 1 ano. Para dar andamento à sua solicitação, "
                    "acesse nosso portal de trocas e devoluções:\n\n"
                    "carbonsmartwatch.troque.app.br\n\n"
                    "Lá você consegue abrir a solicitação com fotos e acompanhar o andamento.\n\n"
                    "Importante: atualmente não realizamos reparos nem temos assistência técnica. "
                    "Caso seu produto esteja na garantia, fazemos a troca por um novo."
                ),
            },
            {
                "type": "send_menu",
                "message": "Precisa de mais alguma coisa?",
                "options": [
                    {"id": "atendente", "label": "Falar com atendente", "description": "Se precisar de ajuda com o portal"},
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opções"},
                ],
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
                "pulseira incompatível", "modelo errado", "produto errado",
                "veio errado", "troca_modelo",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Para solicitar troca de modelo ou pulseira, acesse:\n\n"
                    "carbonsmartwatch.troque.app.br\n\n"
                    "Você tem até 7 dias após o recebimento para solicitar a troca.\n"
                    "O produto deve estar sem uso e na embalagem original."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Se precisar de ajuda, informe o número do pedido:",
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Transferindo para a equipe ajudar com a troca do pedido {order_number}.\n"
                    "Aguarde um momento."
                ),
                "department": "garantia",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 9. NÃO RECEBI / REENVIO
    # 11.5% do volume. Lookup + escalar.
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
                "message": "Entendo sua preocupação. Vou verificar a situação do seu pedido.",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o número do pedido ou o e-mail usado na compra:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não encontrei esse pedido. Verifique o número e tente novamente.\n"
                    "Ou digite *atendente* para falar com a equipe."
                ),
                "found_message": (
                    "Pedido localizado:\n\n"
                    "Pedido: {order_name}\n"
                    "Status: {status}\n"
                    "Rastreio: {tracking_number}\n\n"
                    "Vou transferir para a equipe verificar a entrega e as opções disponíveis."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Transferindo para a equipe analisar a situação da entrega "
                    "do pedido {order_number}.\n"
                    "Eles vão verificar as opções (reenvio, estorno) e te retornar."
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
                "financeiro", "reembolso", "estorno", "pix", "boleto",
                "pagamento", "paguei", "cobrado", "valor", "parcela",
                "cartão", "cobrança", "fatura",
            ]
        },
        "steps": [
            {
                "type": "send_menu",
                "message": "Certo! Qual a questão financeira?",
                "options": SUBMENU_FINANCEIRO,
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 11. ESTORNO / REEMBOLSO
    # Script fixo com prazos reais.
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
                    "O prazo para conclusão é de até 10 dias úteis.\n"
                    "- Pix: o valor é devolvido direto após aprovação.\n"
                    "- Cartão de crédito: pode levar até 3 faturas, "
                    "conforme regras da operadora.\n\n"
                    "Você receberá a confirmação por e-mail."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o número do pedido para verificar o status do estorno:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": "Não encontrei esse pedido. Verifique o número.",
                "found_message": (
                    "Pedido localizado:\n\n"
                    "Pedido: {order_name}\n"
                    "Pagamento: {financial_status}\n"
                    "Valor: R$ {total_price}\n\n"
                    "Vou transferir para a equipe financeira verificar o status."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Transferindo para a equipe financeira verificar o estorno do pedido {order_number}."
                ),
                "department": "financeiro",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 12. SUPORTE TÉCNICO
    # Script fixo: sem assist técnica, opções claras.
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
                    "Vou te ajudar com o suporte técnico.\n\n"
                    "Antes de tudo, tente o reset de fábrica:\n"
                    "1. Vá em Configurações no relógio\n"
                    "2. Selecione 'Restaurar padrão de fábrica'\n"
                    "3. Confirme e aguarde reiniciar\n"
                    "4. Reconecte pelo app no celular\n\n"
                    "Se o problema persistir após o reset, vou transferir para a equipe."
                ),
            },
            {
                "type": "collect_input",
                "variable": "problema_tecnico",
                "message": "O reset resolveu? Se não, descreva o que está acontecendo:",
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Transferindo para a equipe técnica.\n\n"
                    "Problema relatado: {problema_tecnico}\n\n"
                    "Aguarde um momento."
                ),
                "department": "garantia",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 13. DÚVIDA GERAL → IA
    # A IA responde com KB + regras. Se não souber, escala.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Dúvida Geral (IA)",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "dúvida", "duvida", "pergunta", "informação", "quero saber",
                "como funciona", "como usar", "preço", "comprar",
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
    # Escalar direto, sem burocracia.
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
                "type": "transfer_to_agent",
                "message": (
                    "Certo! Transferindo para um atendente da Carbon.\n"
                    "Aguarde um momento, por favor."
                ),
                "department": "geral",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 15. PROCON / JURÍDICO / RECLAME AQUI → ESCALAR IMEDIATO
    # NUNCA tentar resolver no bot. Flag urgente.
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
                    "Entendo a gravidade da situação e peço desculpas pelo transtorno.\n"
                    "Vou transferir imediatamente para nossa equipe responsável, "
                    "que vai tratar o seu caso com prioridade total."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "PRIORIDADE ALTA — Transferindo para atendimento imediato.\n"
                    "Um responsável vai entrar em contato o mais rápido possível."
                ),
                "department": "jurídico",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 16. DÚVIDA PRÉ-VENDA
    # Perguntas sobre produto antes de comprar.
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
    # Resposta automática quando cliente questiona o tipo da NF.
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
                    "Entendo sua dúvida em relação à nota fiscal.\n\n"
                    "A Carbon atua como intermediadora comercial. Isso significa que nosso "
                    "CNPJ é enquadrado como empresa de intermediação de negócios, e não como "
                    "comércio varejista tradicional.\n\n"
                    "Por isso, a nota fiscal é emitida nessa modalidade, que é o formato "
                    "correto e legal de acordo com o nosso enquadramento tributário.\n\n"
                    "Não conseguimos emitir a nota de outra forma ou em um modelo diferente, "
                    "porque o nosso CNPJ não permite esse tipo de emissão."
                ),
            },
            {
                "type": "send_message",
                "message": (
                    "Mas não se preocupe!\n\n"
                    "O valor integral da sua compra está devidamente registrado na nota. "
                    "Ela tem a mesma validade fiscal e serve como comprovante oficial para "
                    "todos os fins, incluindo garantia do produto.\n\n"
                    "Se precisar da nota para alguma finalidade específica, me explica o caso "
                    "que eu vejo como posso te ajudar."
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
    # 18. FALLBACK → MENU
    # Quando nenhum flow matcha.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Fallback",
        "trigger_type": "any",
        "trigger_config": {},
        "steps": [
            {
                "type": "send_message",
                "message": "Não entendi o que você precisa.",
            },
            {
                "type": "send_menu",
                "message": "Escolha uma opção para eu te ajudar:",
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
