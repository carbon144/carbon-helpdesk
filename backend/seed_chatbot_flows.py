"""
Seed script para criar 7 chatbot flows no Carbon Helpdesk.
Uso: python seed_chatbot_flows.py
"""

import asyncio
from sqlalchemy import select, func

from app.core.database import async_engine, AsyncSessionLocal
from app.models.chatbot_flow import ChatbotFlow


MENU_OPTIONS = [
    {"key": "1", "label": "📦 Rastreio do meu pedido"},
    {"key": "2", "label": "🔧 Garantia / Defeito"},
    {"key": "3", "label": "📬 Não recebi / Reenvio"},
    {"key": "4", "label": "💰 Financeiro (reembolso, cancelamento, NF)"},
    {"key": "5", "label": "❓ Dúvida geral"},
]

FLOWS = [
    # ── 1. Saudação + Menu Principal ──
    {
        "name": "Saudação + Menu Principal",
        "trigger_type": "greeting",
        "trigger_config": {},
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Olá! 👋 Bem-vindo ao suporte Carbon Smartwatch.\n"
                    "Sou o assistente virtual e vou te ajudar no que precisar!"
                ),
            },
            {
                "type": "send_menu",
                "message": "Como posso te ajudar hoje? Escolha uma opção:",
                "options": MENU_OPTIONS,
            },
        ],
        "active": True,
    },
    # ── 2. Rastreio de Pedido ──
    {
        "name": "Rastreio de Pedido",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "rastreio", "rastrear", "rastreamento", "meu pedido", "pedido",
                "entrega", "chegou", "onde esta", "cadê", "tracking",
                "codigo de rastreio", "numero do pedido", "encomenda", "correios",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Certo! Vou verificar o status do seu pedido. 📦"
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": (
                    "Por favor, me informe o número do seu pedido ou o e-mail usado na compra:"
                ),
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não encontrei nenhum pedido com essa informação. "
                    "Verifique o número e tente novamente, ou digite *atendente* "
                    "para falar com a nossa equipe."
                ),
                "found_message": (
                    "Encontrei seu pedido! Aqui estão os detalhes:\n\n"
                    "📋 Pedido: {order_name}\n"
                    "📊 Status: {status}\n"
                    "🚚 Rastreio: {tracking_number}\n\n"
                    "Para acompanhar em tempo real, acesse:\n"
                    "https://brutodeverdade.com.br/pages/rastreio"
                ),
            },
            {
                "type": "send_message",
                "message": (
                    "Precisa de mais alguma coisa? Se sim, é só digitar! 😊\n"
                    "Se quiser falar com um atendente, digite *atendente*."
                ),
            },
        ],
        "active": True,
    },
    # ── 3. Garantia e Defeito ──
    {
        "name": "Garantia e Defeito",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "garantia", "defeito", "quebrou", "nao funciona", "parou",
                "tela", "bateria", "nao liga", "nao carrega", "travou",
                "apagou", "esquentando", "troca", "assistencia", "reparo",
                "consertar",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Sinto muito que esteja tendo problemas com seu relógio! 😔\n"
                    "Vou coletar algumas informações para agilizar seu atendimento."
                ),
            },
            {
                "type": "collect_input",
                "variable": "modelo",
                "message": (
                    "Qual o modelo do seu relógio? "
                    "(Ex: Raptor, Atlas, One Max, Aurora, Quartz)"
                ),
            },
            {
                "type": "collect_input",
                "variable": "problema",
                "message": (
                    "Descreva o problema que está acontecendo com o máximo de detalhes possível:"
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": (
                    "Por favor, informe o número do seu pedido ou o e-mail da compra "
                    "para eu localizar sua garantia:"
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Obrigado pelas informações! Estou transferindo você para um "
                    "especialista da nossa equipe de assistência técnica. 🔧\n\n"
                    "Resumo:\n"
                    "• Modelo: {modelo}\n"
                    "• Problema: {problema}\n"
                    "• Pedido: {order_number}\n\n"
                    "Aguarde um momento, por favor."
                ),
                "department": "garantia",
            },
        ],
        "active": True,
    },
    # ── 4. Não Recebi / Reenvio ──
    {
        "name": "Não Recebi / Reenvio",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "nao recebi", "não recebi", "nao chegou", "atrasado", "atraso",
                "extraviado", "reenvio", "devolvido", "alfandega", "taxado",
                "demora",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Entendo sua preocupação! Vou verificar a situação do seu pedido. 📬"
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": (
                    "Informe o número do pedido ou o e-mail usado na compra:"
                ),
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não localizei o pedido. Verifique o número e tente novamente, "
                    "ou digite *atendente* para falar com a equipe."
                ),
                "found_message": (
                    "Encontrei o pedido!\n\n"
                    "📋 Pedido: {order_name}\n"
                    "📊 Status: {status}\n"
                    "🚚 Rastreio: {tracking_number}\n\n"
                    "Vou transferir para a equipe analisar a situação da entrega."
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Transferindo para um atendente que vai verificar a situação "
                    "da sua entrega e as opções disponíveis (reenvio, estorno etc). "
                    "Aguarde um momento! 🙏"
                ),
                "department": "logistica",
            },
        ],
        "active": True,
    },
    # ── 5. Financeiro ──
    {
        "name": "Financeiro",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "reembolso", "estorno", "cancelar", "cancelamento", "pix",
                "boleto", "pagamento", "paguei", "cobrado", "nota fiscal", "nf",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Certo, vou te ajudar com a questão financeira! 💰"
                ),
            },
            {
                "type": "collect_input",
                "variable": "order_number",
                "message": (
                    "Informe o número do pedido ou o e-mail usado na compra:"
                ),
            },
            {
                "type": "lookup_order",
                "lookup_by": "order_number",
                "variable": "order_number",
                "not_found_message": (
                    "Não localizei o pedido. Verifique o número e tente novamente, "
                    "ou digite *atendente* para falar com a equipe financeira."
                ),
                "found_message": (
                    "Pedido localizado!\n\n"
                    "📋 Pedido: {order_name}\n"
                    "📊 Status: {status}\n"
                    "💳 Valor: {total_price}"
                ),
            },
            {
                "type": "collect_input",
                "variable": "descricao_financeiro",
                "message": (
                    "Descreva o que precisa em relação ao financeiro "
                    "(ex: quero cancelar, solicitar reembolso, pedir nota fiscal, etc):"
                ),
            },
            {
                "type": "transfer_to_agent",
                "message": (
                    "Entendi! Estou transferindo para a equipe financeira. 📋\n\n"
                    "Resumo:\n"
                    "• Pedido: {order_number}\n"
                    "• Solicitação: {descricao_financeiro}\n\n"
                    "Um atendente vai cuidar do seu caso em breve!"
                ),
                "department": "financeiro",
            },
        ],
        "active": True,
    },
    # ── 6. Dúvida Geral (IA) ──
    {
        "name": "Dúvida Geral (IA)",
        "trigger_type": "keyword",
        "trigger_config": {
            "keywords": [
                "duvida", "pergunta", "informacao", "quero saber", "como funciona",
                "como usar", "preco", "valor", "pulseira", "acessorio",
                "bluetooth", "app", "aplicativo", "a prova dagua",
            ]
        },
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Boa pergunta! 🤖 Vou consultar nossa base de conhecimento "
                    "para te responder da melhor forma. Um momento..."
                ),
            },
        ],
        "active": True,
    },
    # ── 7. Fallback ──
    {
        "name": "Fallback",
        "trigger_type": "any",
        "trigger_config": {},
        "steps": [
            {
                "type": "send_message",
                "message": (
                    "Não entendi muito bem o que você precisa. 🤔\n"
                    "Veja as opções abaixo:"
                ),
            },
            {
                "type": "send_menu",
                "message": "Escolha uma das opções para eu te ajudar:",
                "options": MENU_OPTIONS,
            },
        ],
        "active": True,
    },
]


async def seed():
    async with AsyncSessionLocal() as session:
        # Verifica se ja existem flows
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

        # Cria os 7 flows
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
