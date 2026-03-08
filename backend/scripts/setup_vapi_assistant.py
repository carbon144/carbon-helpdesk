"""
Setup script for Vapi.ai Voice Assistant — Carol (Carbon Voice AI).

Run once to create the assistant on Vapi's platform:
    cd backend && python -m scripts.setup_vapi_assistant
"""

import json
import sys

import requests

# ---------------------------------------------------------------------------
# System Prompt — Carol, a assistente de voz da Carbon
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Voce eh a Carol, assistente virtual da Carbon por telefone.
Seu tom eh casual, amigavel e direto — como uma amiga que manja de relogios.
Use "voce", nunca "senhor/senhora". Fale de forma natural e descontraida.
Sempre se refira a marca apenas como "Carbon", nunca "Carbon Smartwatch".

## Modelos
- Carbon Raptor
- Carbon Atlas
- Carbon One Max
- Carbon Aurora
- Carbon Quartz

## Aplicativos
- Raptor e Atlas: GloryFitPro
- One Max e Aurora: DaFit

## Garantia
- Legal: 90 dias (defeito de fabricacao)
- Contratual: 12 meses (defeito de fabricacao)
- Carbon Care: estende a garantia para 24 meses
- Dentro da garantia: troca por produto novo
- Fora da garantia: cupom de desconto para nova compra
- A Carbon NAO faz assistencia tecnica — so troca ou cupom
- Portal de trocas: carbonsmartwatch.troque.app.br

## Prazos de entrega (dias uteis apos envio)
- Sudeste: 7 a 12
- Sul: 7 a 14
- Centro-Oeste: 8 a 16
- Nordeste: 10 a 20
- Norte: 12 a 25

## Regras importantes
- NUNCA mencione importacao, China, alfandega ou qualquer referencia a origem do produto.
- NUNCA sugira Procon, Reclame Aqui, advogado ou acoes legais.
- Se o cliente mencionar Procon, advogado, chargeback, pedir reembolso, estiver muito irritado \
ou voce nao conseguir resolver um problema tecnico: use a ferramenta create_ticket para \
escalar para um atendente humano. Diga que um atendente vai entrar em contato em ate 48h.
- Seja objetiva. Nao enrole. Se nao souber, diga que vai escalar.
"""

# ---------------------------------------------------------------------------
# Tools — OpenAI function-calling format (Vapi compatible)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": (
                "Busca informacoes de um pedido pelo numero do pedido. "
                "Retorna status, itens, rastreio e datas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {
                        "type": "string",
                        "description": "Numero do pedido (ex: #12345 ou 12345)",
                    },
                },
                "required": ["order_number"],
            },
        },
        "server": {"url": "WILL_BE_SET"},
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_tracking",
            "description": (
                "Consulta o status de rastreio de uma encomenda pelo codigo de rastreamento."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_code": {
                        "type": "string",
                        "description": "Codigo de rastreamento (Correios ou transportadora)",
                    },
                },
                "required": ["tracking_code"],
            },
        },
        "server": {"url": "WILL_BE_SET"},
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_troque",
            "description": (
                "Consulta solicitacoes de troca no TroqueCommerce. "
                "Pode buscar por numero do pedido ou telefone do cliente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {
                        "type": "string",
                        "description": "Numero do pedido para buscar troca",
                    },
                    "phone": {
                        "type": "string",
                        "description": "Telefone do cliente para buscar troca",
                    },
                },
                "required": [],
            },
        },
        "server": {"url": "WILL_BE_SET"},
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": (
                "Cria um ticket de suporte para escalar o atendimento para um humano. "
                "Usar quando: Procon/advogado mencionado, pedido de reembolso, "
                "problema tecnico nao resolvido ou cliente muito irritado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Assunto resumido do ticket",
                    },
                    "description": {
                        "type": "string",
                        "description": "Descricao detalhada do problema e contexto da ligacao",
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Nome do cliente, se informado",
                    },
                    "caller_phone": {
                        "type": "string",
                        "description": "Telefone de quem ligou",
                    },
                },
                "required": ["subject", "description"],
            },
        },
        "server": {"url": "WILL_BE_SET"},
    },
]

# ---------------------------------------------------------------------------
# Assistant creation
# ---------------------------------------------------------------------------

VAPI_API_URL = "https://api.vapi.ai/assistant"


def create_assistant() -> None:
    """Create the Carol voice assistant on Vapi."""

    # Import settings (requires the backend package to be importable)
    try:
        from app.core.config import settings
    except ImportError:
        print(
            "ERRO: Nao foi possivel importar settings. "
            "Execute a partir da pasta backend/:\n"
            "  cd backend && python -m scripts.setup_vapi_assistant"
        )
        sys.exit(1)

    api_key = settings.VAPI_API_KEY
    if not api_key:
        print("ERRO: VAPI_API_KEY nao configurada no .env")
        sys.exit(1)

    server_secret = settings.VAPI_SERVER_SECRET
    if not server_secret:
        print("AVISO: VAPI_SERVER_SECRET nao configurada — webhook nao tera autenticacao.")

    # Prompt for webhook URL
    webhook_url = input(
        "Digite a URL do webhook para tool calls\n"
        "(ex: https://helpdesk.brutodeverdade.com.br/api/v1/vapi/tool-call): "
    ).strip()

    if not webhook_url:
        print("ERRO: URL do webhook eh obrigatoria.")
        sys.exit(1)

    # Set server URL on all tools
    tools = json.loads(json.dumps(TOOLS))  # deep copy
    for tool in tools:
        tool["server"]["url"] = webhook_url

    # Build assistant payload
    payload = {
        "name": "Carol - Carbon Voice AI",
        "model": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
            ],
            "tools": tools,
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "XB0fDUnXU5powFXDhCwa",  # Charlotte
            "stability": 0.6,
            "similarityBoost": 0.8,
        },
        "firstMessage": "Fala! Bem-vindo a Carbon, aqui eh a Carol. Como posso te ajudar?",
        "serverUrl": webhook_url,
        "serverUrlSecret": server_secret,
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 600,
        "language": "pt-BR",
    }

    # Create assistant via Vapi API
    print("\nCriando assistente no Vapi...")
    response = requests.post(
        VAPI_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        print(f"ERRO {response.status_code}: {response.text}")
        sys.exit(1)

    data = response.json()
    assistant_id = data.get("id", "???")

    print(f"\nAssistente criado com sucesso!")
    print(f"  ID: {assistant_id}")
    print(f"  Nome: {data.get('name')}")
    print(f"\nProximos passos:")
    print(f"  1. Adicione VAPI_ASSISTANT_ID={assistant_id} no .env")
    print(f"  2. Configure o numero de telefone no dashboard Vapi")
    print(f"  3. Teste com uma ligacao!")


if __name__ == "__main__":
    create_assistant()
