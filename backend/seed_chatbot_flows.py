"""
Seed script para criar chatbot flows do Carbon Helpdesk — REDESIGN v2.
Baseado na analise de 1870 tickets reais.
Uso: python seed_chatbot_flows.py
"""

import asyncio
from sqlalchemy import select, func

from app.core.database import engine, async_session
from app.models.chatbot_flow import ChatbotFlow


# ── Menu Principal ──

MENU_OPTIONS = [
    {"id": "meu_pedido", "label": "Meu Pedido", "description": "Rastreio, status, nota fiscal"},
    {"id": "garantia", "label": "Trocas e Garantia", "description": "Defeito, troca, devolucao"},
    {"id": "financeiro", "label": "Financeiro", "description": "Cancelamento, estorno, pagamento"},
    {"id": "atendente", "label": "Falar com atendente", "description": "Atendimento humano"},
]

SUBMENU_PEDIDO = [
    {"id": "rastreio", "label": "Rastreio / Entrega", "description": "Onde esta meu pedido"},
    {"id": "nota_fiscal", "label": "Nota Fiscal", "description": "Solicitar NF do pedido"},
    {"id": "cancelar", "label": "Cancelar pedido", "description": "Quero cancelar"},
    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Menu principal"},
]

SUBMENU_GARANTIA = [
    {"id": "defeito", "label": "Defeito / Nao funciona", "description": "Relogio com problema"},
    {"id": "troca_modelo", "label": "Trocar modelo ou pulseira", "description": "Quero trocar"},
    {"id": "nao_recebi", "label": "Nao recebi / Extraviado", "description": "Pedido nao chegou"},
    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Menu principal"},
]

SUBMENU_FINANCEIRO = [
    {"id": "cancelar", "label": "Cancelar pedido", "description": "Quero cancelar minha compra"},
    {"id": "estorno", "label": "Estorno / Reembolso", "description": "Quero meu dinheiro de volta"},
    {"id": "pagamento", "label": "Duvida de pagamento", "description": "Boleto, pix, parcela"},
    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Menu principal"},
]


FLOWS = [
    # ══════════════════════════════════════════════════════════════
    # 1. SAUDACAO + MENU PRINCIPAL
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Saudacao + Menu",
        "trigger_type": "greeting",
        "trigger_config": {},
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Ola! Bem-vindo ao suporte da Carbon.\n"
                    "Sou o assistente virtual e vou te ajudar."
                ),
            },
            {
                "type": "send_menu",
                "message": "Como posso te ajudar? Escolha uma opcao:",
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
                "message": "O que voce precisa?",
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
                "onde esta", "cadê", "tracking", "codigo de rastreio",
                "encomenda", "correios", "transportadora", "prazo",
                "previsao", "status", "excecao", "devolvido",
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
                    "Me informe o numero do seu pedido ou o e-mail usado na compra.\n"
                    "Exemplo: 128478 ou #128478"
                ),
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Nao encontrei esse pedido. Verifique o numero e tente novamente.\n"
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
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opcoes"},
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
                "message": (
                    "A nota fiscal e enviada automaticamente para o e-mail "
                    "cadastrado na compra apos o faturamento do pedido.\n\n"
                    "Se voce nao recebeu, verifique a pasta de spam.\n"
                    "Caso ainda nao tenha encontrado, vou transferir para a equipe."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o numero do pedido para eu verificar:",
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Transferindo para a equipe verificar a nota fiscal do pedido {order_number}.\n"
                    "Aguarde um momento."
                ),
                "department": "financeiro",
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
                "desistencia", "nao quero mais", "cancelar pedido",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Entendi que voce quer cancelar seu pedido.\n\n"
                    "Como funciona o cancelamento na Carbon:\n"
                    "- Pedido ainda nao enviado: cancelamos e fazemos o estorno.\n"
                    "- Pedido ja enviado: voce pode recusar a entrega ou devolver em ate 7 dias apos receber.\n\n"
                    "O prazo do estorno e de ate 10 dias uteis.\n"
                    "Pix: devolvido direto. Cartao: pode levar ate 3 faturas."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o numero do pedido que deseja cancelar:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Nao encontrei esse pedido. Verifique o numero e tente novamente."
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
                    "Um atendente vai confirmar os proximos passos."
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
                "garantia", "troca", "trocar", "devolucao", "devolver",
                "arrependimento", "produto errado",
            ]
        },
        "steps": [
            {
                "type": "send_menu",
                "message": "Certo! Qual a situacao?",
                "options": SUBMENU_GARANTIA,
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 7. DEFEITO / NAO FUNCIONA
    # 5.5% do volume. Coletar dados + direcionar pra troque.app
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Defeito / Nao Funciona",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "defeito", "quebrou", "nao funciona", "parou", "nao liga",
                "nao carrega", "travou", "apagou", "esquentando", "tela",
                "bateria", "consertar", "reparo", "assistencia",
                "parou de funcionar",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Sinto muito que voce esteja tendo problemas com seu Carbon.\n"
                    "Vou coletar algumas informacoes para analisar seu caso."
                ),
            },
            {
                "type": "collect_input",
                "variable": "modelo",
                "message": (
                    "Qual o modelo do seu relogio?\n"
                    "Carbon Raptor, Atlas, One Max, Aurora ou Quartz?"
                ),
            },
            {
                "type": "collect_input",
                "variable": "problema",
                "message": "Descreva o problema que esta acontecendo:",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o numero do pedido ou NF para verificar a garantia:",
            },
            {
                "type": "send_message",
                "message": (
                    "Obrigado pelas informacoes!\n\n"
                    "A Carbon oferece garantia de 1 ano. Para dar andamento a sua solicitacao, "
                    "acesse nosso portal de trocas e devolucoes:\n\n"
                    "carbonsmartwatch.troque.app.br\n\n"
                    "La voce consegue abrir a solicitacao com fotos e acompanhar o andamento.\n\n"
                    "Importante: atualmente nao realizamos reparos nem temos assistencia tecnica. "
                    "Caso seu produto esteja na garantia, fazemos a troca por um novo."
                ),
            },
            {
                "type": "send_menu",
                "message": "Precisa de mais alguma coisa?",
                "options": [
                    {"id": "atendente", "label": "Falar com atendente", "description": "Se precisar de ajuda com o portal"},
                    {"id": "voltar_menu", "label": "Voltar ao menu", "description": "Ver outras opcoes"},
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
                "pulseira incompativel", "modelo errado", "produto errado",
                "veio errado", "troca_modelo",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Para solicitar troca de modelo ou pulseira, acesse:\n\n"
                    "carbonsmartwatch.troque.app.br\n\n"
                    "Voce tem ate 7 dias apos o recebimento para solicitar a troca.\n"
                    "O produto deve estar sem uso e na embalagem original."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Se precisar de ajuda, informe o numero do pedido:",
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
    # 9. NAO RECEBI / REENVIO
    # 11.5% do volume. Lookup + escalar.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Nao Recebi / Reenvio",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "nao recebi", "não recebi", "nao chegou", "atrasado", "atraso",
                "extraviado", "reenvio", "devolvido", "alfandega", "taxado",
                "demora", "barrado", "fiscalizacao", "nao_recebi",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": "Entendo sua preocupacao. Vou verificar a situacao do seu pedido.",
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o numero do pedido ou o e-mail usado na compra:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Nao encontrei esse pedido. Verifique o numero e tente novamente.\n"
                    "Ou digite *atendente* para falar com a equipe."
                ),
                "found_message": (
                    "Pedido localizado:\n\n"
                    "Pedido: {order_name}\n"
                    "Status: {status}\n"
                    "Rastreio: {tracking_number}\n\n"
                    "Vou transferir para a equipe verificar a entrega e as opcoes disponiveis."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Transferindo para a equipe analisar a situacao da entrega "
                    "do pedido {order_number}.\n"
                    "Eles vao verificar as opcoes (reenvio, estorno) e te retornar."
                ),
                "department": "logistica",
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
                "cartao", "cobranca", "fatura",
            ]
        },
        "steps": [
            {
                "type": "send_menu",
                "message": "Certo! Qual a questao financeira?",
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
                    "O prazo para conclusao e de ate 10 dias uteis.\n"
                    "- Pix: o valor e devolvido direto apos aprovacao.\n"
                    "- Cartao de credito: pode levar ate 3 faturas, "
                    "conforme regras da operadora.\n\n"
                    "Voce recebera a confirmacao por e-mail."
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": "Informe o numero do pedido para verificar o status do estorno:",
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": "Nao encontrei esse pedido. Verifique o numero.",
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
    # 12. SUPORTE TECNICO
    # Script fixo: sem assist tecnica, opcoes claras.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Suporte Tecnico",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "bluetooth", "app", "aplicativo", "conectar", "configurar",
                "atualizar", "reset", "resetar", "gps", "sensor",
                "frequencia cardiaca", "batimento", "sono", "notificacao",
                "liga e desliga", "reiniciando", "travando",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Vou te ajudar com o suporte tecnico.\n\n"
                    "Antes de tudo, tente o reset de fabrica:\n"
                    "1. Va em Configuracoes no relogio\n"
                    "2. Selecione 'Restaurar padrao de fabrica'\n"
                    "3. Confirme e aguarde reiniciar\n"
                    "4. Reconecte pelo app no celular\n\n"
                    "Se o problema persistir apos o reset, vou transferir para a equipe."
                ),
            },
            {
                "type": "collect_input",
                "variable": "problema_tecnico",
                "message": "O reset resolveu? Se nao, descreva o que esta acontecendo:",
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Transferindo para a equipe tecnica.\n\n"
                    "Problema relatado: {problema_tecnico}\n\n"
                    "Aguarde um momento."
                ),
                "department": "garantia",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 13. DUVIDA GERAL → IA
    # A IA responde com KB + regras. Se nao souber, escala.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Duvida Geral (IA)",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "duvida", "pergunta", "informacao", "quero saber",
                "como funciona", "como usar", "preco", "comprar",
                "a prova dagua", "resistente", "modelo", "diferenca",
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
                "atendente", "humano", "pessoa", "agente", "falar com alguem",
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
    # 15. PROCON / JURIDICO / RECLAME AQUI → ESCALAR IMEDIATO
    # NUNCA tentar resolver no bot. Flag urgente.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Procon / Juridico / Reclame Aqui",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "procon", "advogado", "processo", "justica", "juizado",
                "danos morais", "reclame aqui", "reclameaqui",
                "consumidor.gov", "desacordo comercial", "chargeback",
                "contestacao", "disputa",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Entendo a gravidade da situacao e peco desculpas pelo transtorno.\n"
                    "Vou transferir imediatamente para nossa equipe responsavel, "
                    "que vai tratar o seu caso com prioridade total."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "PRIORIDADE ALTA - Transferindo para atendimento imediato.\n"
                    "Um responsavel vai entrar em contato o mais rapido possivel."
                ),
                "department": "juridico",
            },
        ],
        "active": True,
    },

    # ══════════════════════════════════════════════════════════════
    # 16. DUVIDA PRE-VENDA
    # Perguntas sobre produto antes de comprar.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Pre-Venda",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "comprar", "preco", "valor", "desconto", "cupom",
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
    # 17. FALLBACK → MENU
    # Quando nenhum flow matcha.
    # ══════════════════════════════════════════════════════════════
    {
        "name": "Fallback",
        "trigger_type": "any",
        "trigger_config": {},
        "steps": [
            {
                "type": "send_message",
                "message": "Nao entendi o que voce precisa.",
            },
            {
                "type": "send_menu",
                "message": "Escolha uma opcao para eu te ajudar:",
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
                f"Ja existem {count} chatbot flow(s) no banco. "
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
