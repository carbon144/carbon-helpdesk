#!/usr/bin/env python3
"""
Simulacao automatizada de chat ao vivo para screencast Meta App Review.

Simula conversas WhatsApp reais injetando via webhook com assinatura HMAC.
O webhook cria customers e conversas automaticamente (mesmo fluxo de producao).
Depois atualiza o nome do customer pra ficar bonito no painel.

Uso:
  python scripts/simulate_chat_demo.py --auto-reply    # demo completa automatica
  python scripts/simulate_chat_demo.py --fast           # teste rapido (delays curtos)
  python scripts/simulate_chat_demo.py                  # manual (voce responde no painel)
"""

import argparse
import hashlib
import hmac
import json
import requests
import time
import sys

# --- Config ---
SERVER = "https://helpdesk.brutodeverdade.com.br"
LOGIN_EMAIL = "pedro@carbonsmartwatch.com.br"
LOGIN_PASS = "OdysseY144.-a"
META_APP_SECRET = "59693c0c179df248d7e9af778dea1281"

# Telefones fake (usados como sender_id no webhook)
CONTACTS = [
    {"phone": "5511987654321", "name": "Fernanda Oliveira"},
    {"phone": "5521912345678", "name": "Lucas Mendes"},
    {"phone": "5531998765432", "name": "Juliana Costa"},
    {"phone": "5541955551234", "name": "Rafael Santos"},
]

# Cenarios — cada um gera 1 conversa WhatsApp
SCENARIOS = [
    {
        "contact_idx": 0,
        "messages": [
            {"text": "Oi, boa tarde! Comprei um Carbon Raptor ha 10 dias e ainda nao recebi o codigo de rastreio. Podem me ajudar?", "delay": 2},
            {"text": "Meu pedido eh o #148523", "delay": 8},
            {"text": "Ja olhei no site e nao aparece nada", "delay": 5},
        ],
        "agent_responses": [
            {"text": "Oi Fernanda! Tudo bem? Vou verificar o status do seu pedido agora mesmo.", "delay": 6},
            {"text": "Encontrei seu pedido #148523. O codigo de rastreio ja foi gerado: NX123456789BR. Voce pode acompanhar pelo site dos Correios ou pelo nosso link: carbonsmartwatch.com.br/a/rastreio", "delay": 8},
            {"text": "A previsao de entrega eh para os proximos 3-5 dias uteis. Qualquer duvida, estou por aqui!", "delay": 4},
        ],
    },
    {
        "contact_idx": 1,
        "messages": [
            {"text": "Opa, tudo bem? To pensando em comprar o Carbon Atlas. Ele tem GPS integrado?", "delay": 15},
            {"text": "Vi uns comentarios dizendo que so o Raptor tem GPS, queria confirmar", "delay": 6},
        ],
        "agent_responses": [
            {"text": "Oi Lucas! O Carbon Atlas SIM tem GPS integrado! Tanto o Raptor quanto o Atlas possuem GPS nativo.", "delay": 8},
            {"text": "Com o GPS voce consegue rastrear corridas e pedaladas com precisao, e conectar com o Strava tambem. Quer saber mais alguma coisa?", "delay": 5},
        ],
    },
    {
        "contact_idx": 2,
        "messages": [
            {"text": "Boa noite, meu Carbon One Max parou de carregar do nada. Comprei faz 3 meses.", "delay": 25},
            {"text": "Ja tentei com outro cabo USB e nao foi", "delay": 7},
            {"text": "Ele esta na garantia ne? Como faco pra trocar?", "delay": 5},
        ],
        "agent_responses": [
            {"text": "Oi Juliana! Sinto muito pelo inconveniente. Sim, seu relogio esta dentro da garantia de 12 meses.", "delay": 8},
            {"text": "Vou abrir um chamado de troca pra voce. Preciso que envie um video mostrando que o relogio nao carrega, pode ser?", "delay": 6},
            {"text": "Assim que recebermos o video, enviamos um codigo de postagem pra voce enviar pelos Correios sem custo. A troca leva em media 10 dias uteis.", "delay": 5},
        ],
    },
    {
        "contact_idx": 3,
        "messages": [
            {"text": "Fala pessoal! So passando pra agradecer, recebi meu Raptor ontem e to AMANDO. Qualidade absurda!", "delay": 40},
            {"text": "Ja configurei tudo, conectei no Strava, sensacional", "delay": 5},
        ],
        "agent_responses": [
            {"text": "Opa Rafael, que bacana!! Ficamos muito felizes que voce curtiu o Raptor!", "delay": 6},
            {"text": "Qualquer duvida sobre funcionalidades ou configuracoes, estamos por aqui. Aproveite!", "delay": 4},
        ],
    },
]


def send_webhook(phone: str, text: str, server: str) -> bool:
    """Envia mensagem simulada via webhook WhatsApp com assinatura HMAC valida."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "DEMO",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "DEMO"},
                    "contacts": [{"profile": {"name": "Demo"}, "wa_id": phone}],
                    "messages": [{
                        "id": f"demo_{phone}_{int(time.time() * 1000)}",
                        "from": phone,
                        "timestamp": str(int(time.time())),
                        "type": "text",
                        "text": {"body": text},
                    }],
                },
                "field": "messages",
            }],
        }],
    }
    body = json.dumps(payload).encode("utf-8")
    sig = "sha256=" + hmac.HMAC(META_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()

    resp = requests.post(
        f"{server}/api/webhooks/whatsapp",
        data=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        timeout=15,
    )
    return resp.status_code == 200


def update_customer_name(session: requests.Session, server: str, phone: str, name: str):
    """Encontra customer criado pelo webhook e atualiza o nome."""
    resp = session.get(f"{server}/api/customers", params={"search": phone, "limit": 5})
    if resp.status_code != 200:
        return
    customers = resp.json()
    if isinstance(customers, dict):
        customers = customers.get("items", [])
    for c in customers:
        if c.get("phone") == phone or (c.get("name") or "").endswith(phone):
            try:
                session.put(f"{server}/api/customers/{c['id']}", json={"name": name})
            except Exception:
                pass
            return


def find_conversation(session: requests.Session, server: str, phone: str) -> str | None:
    """Encontra a conversa aberta mais recente pro telefone dado."""
    resp = session.get(f"{server}/api/chat/conversations", params={"channel": "whatsapp", "status": "open", "limit": 50})
    if resp.status_code != 200:
        return None
    convs = resp.json()
    # A conversa mais recente eh a do nosso contato
    if convs:
        return convs[0]["id"]
    return None


def cleanup(session: requests.Session, server: str):
    """Resolve todas as conversas abertas."""
    print("[*] Limpando conversas anteriores...")
    resp = session.get(f"{server}/api/chat/conversations", params={"limit": 200})
    if resp.status_code != 200:
        return
    convs = resp.json()
    resolved = 0
    for conv in convs:
        if conv["status"] not in ("resolved", "closed"):
            try:
                session.put(f"{server}/api/chat/conversations/{conv['id']}/resolve")
                resolved += 1
            except Exception:
                pass
    if resolved:
        print(f"    {resolved} conversa(s) resolvida(s)")
    else:
        print("    Nenhuma conversa pendente")


def main():
    parser = argparse.ArgumentParser(description="Simulacao de chat WhatsApp para screencast Meta")
    parser.add_argument("--server", default=SERVER)
    parser.add_argument("--auto-reply", action="store_true", help="Agente responde automaticamente")
    parser.add_argument("--fast", action="store_true", help="Delays reduzidos (max 2s)")
    args = parser.parse_args()

    server = args.server.rstrip("/")

    if args.fast:
        for s in SCENARIOS:
            for m in s["messages"]:
                m["delay"] = min(m["delay"], 2)
            for r in s.get("agent_responses", []):
                r["delay"] = min(r["delay"], 2)

    # Login
    print(f"[*] Login em {server}...")
    session = requests.Session()
    resp = session.post(f"{server}/api/auth/login", json={"email": LOGIN_EMAIL, "password": LOGIN_PASS})
    resp.raise_for_status()
    token = resp.json().get("access_token") or resp.json().get("token")
    session.headers["Authorization"] = f"Bearer {token}"
    print(f"[+] Logado como {resp.json()['user']['name']}")

    # Cleanup
    cleanup(session, server)

    mode = "AUTO-REPLY" if args.auto_reply else "MANUAL"
    print(f"\n[*] Modo: {mode}")
    print(f"[*] {len(SCENARIOS)} cenarios preparados")
    print(f"[*] Abra o Chat ao Vivo no helpdesk e comece a gravar!\n")
    input(">>> Pressione ENTER para comecar... ")

    for i, scenario in enumerate(SCENARIOS, 1):
        contact = CONTACTS[scenario["contact_idx"]]
        print(f"\n{'='*60}")
        print(f"CENARIO {i}: {contact['name']} via WhatsApp")
        print(f"{'='*60}")

        conv_id = None

        # Enviar mensagens do cliente via webhook
        for j, msg in enumerate(scenario["messages"]):
            delay = msg["delay"]
            print(f"  (aguardando {delay}s...)")
            time.sleep(delay)

            ok = send_webhook(contact["phone"], msg["text"], server)
            if ok:
                print(f"  <- {contact['name']}: {msg['text'][:70]}{'...' if len(msg['text']) > 70 else ''}")
            else:
                print(f"  [!] FALHOU: {msg['text'][:50]}")
                continue

            # Apos primeira mensagem, atualiza nome do customer
            if j == 0:
                time.sleep(1)  # espera o webhook processar
                update_customer_name(session, server, contact["phone"], contact["name"])

        # Encontrar conversa criada
        time.sleep(1)
        conv_id = find_conversation(session, server, contact["phone"])

        if args.auto_reply and conv_id:
            for resp_data in scenario.get("agent_responses", []):
                delay = resp_data["delay"]
                print(f"  (agente responde em {delay}s...)")
                time.sleep(delay)
                try:
                    session.post(f"{server}/api/chat/conversations/{conv_id}/messages", json={
                        "content": resp_data["text"],
                        "content_type": "text",
                    })
                    print(f"  -> Agente: {resp_data['text'][:70]}{'...' if len(resp_data['text']) > 70 else ''}")
                except Exception as e:
                    print(f"  [!] Erro ao enviar resposta: {e}")
        elif not args.auto_reply:
            print(f"  [MANUAL] Responda no painel!")

    print(f"\n{'='*60}")
    print(f"SIMULACAO CONCLUIDA! {len(SCENARIOS)} conversas criadas.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
