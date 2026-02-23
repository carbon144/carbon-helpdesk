"""Seed the database with initial data for Carbon Helpdesk."""
from datetime import datetime, timezone, timedelta
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import hash_password
from app.models.user import User
from app.models.customer import Customer
from app.models.inbox import Inbox
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.kb_article import KBArticle
from app.models.macro import Macro


async def seed_database(db: AsyncSession):
    """Populate with demo data if empty."""
    existing = await db.execute(select(User).limit(1))
    if existing.scalars().first():
        return  # Already seeded

    # ── Users ──
    users = [
        User(name="Pedro", email="pedro@carbonsmartwatch.com.br", password_hash=hash_password("carbon2026"), role="admin"),
        User(name="Ana Silva", email="ana@carbonsmartwatch.com.br", password_hash=hash_password("carbon2026"), role="agent"),
        User(name="Lucas Mendes", email="lucas@carbonsmartwatch.com.br", password_hash=hash_password("carbon2026"), role="agent"),
        User(name="Juliana Costa", email="juliana@carbonsmartwatch.com.br", password_hash=hash_password("carbon2026"), role="supervisor"),
    ]
    db.add_all(users)
    await db.flush()

    # ── Inboxes ──
    inboxes = [
        Inbox(name="Todos os Tickets", type="system", icon="fa-inbox", color="#6366f1", sort_order=0),
        Inbox(name="Não Atribuídos", type="system", icon="fa-user-slash", color="#ef4444", sort_order=1),
        Inbox(name="Meus Tickets - Ana", type="agent", icon="fa-user", color="#8b5cf6", owner_id=users[1].id, sort_order=2),
        Inbox(name="Meus Tickets - Lucas", type="agent", icon="fa-user", color="#3b82f6", owner_id=users[2].id, sort_order=3),
        Inbox(name="Meus Tickets - Juliana", type="agent", icon="fa-user", color="#10b981", owner_id=users[3].id, sort_order=4),
        Inbox(name="Garantias", type="custom", icon="fa-shield-halved", color="#0ea5e9", filter_tags=["garantia"], sort_order=5),
        Inbox(name="Trocas e Devoluções", type="custom", icon="fa-arrow-rotate-left", color="#a855f7", filter_tags=["troca"], sort_order=6),
        Inbox(name="Jurídico", type="custom", icon="fa-gavel", color="#ef4444", filter_tags=["procon", "chargeback"], sort_order=7),
        Inbox(name="Carregadores", type="custom", icon="fa-bolt", color="#eab308", filter_tags=["carregador"], sort_order=8),
    ]
    db.add_all(inboxes)
    await db.flush()

    # ── Customers ──
    customers = [
        Customer(name="Maria Santos", email="maria.santos@gmail.com", cpf="123.456.789-00", total_tickets=2, is_repeat=False),
        Customer(name="João Oliveira", email="joao.oliveira@hotmail.com", total_tickets=5, is_repeat=True, risk_score=0.7),
        Customer(name="Carla Ferreira", email="carla.f@outlook.com", total_tickets=1),
        Customer(name="Roberto Lima", email="roberto.lima@gmail.com", cpf="987.654.321-00", total_tickets=3, is_repeat=True),
        Customer(name="Fernanda Souza", email="fernanda.s@yahoo.com", total_tickets=1),
        Customer(name="Paulo Mendes", email="paulo.m@gmail.com", total_tickets=4, is_repeat=True, risk_score=0.9),
    ]
    db.add_all(customers)
    await db.flush()

    # ── Tickets ──
    now = datetime.now(timezone.utc)
    tickets_data = [
        {"number": 1001, "subject": "Relógio parou de funcionar após 2 meses", "status": "open", "priority": "high",
         "customer_id": customers[0].id, "assigned_to": users[1].id, "inbox_id": inboxes[5].id,
         "tags": ["garantia"], "category": "garantia", "sentiment": "negative",
         "tracking_code": "NX123456789BR", "tracking_status": "Em trânsito - Saiu para entrega",
         "tracking_data": {"carrier": "Correios", "code": "NX123456789BR", "status": "Em trânsito - Saiu para entrega", "main_status": 10, "delivered": False, "days_in_transit": 4, "location": "São Paulo/SP", "events": [{"date": "2026-02-20T14:30:00", "status": "Objeto saiu para entrega ao destinatário", "location": "São Paulo/SP"}, {"date": "2026-02-19T08:15:00", "status": "Objeto em trânsito", "location": "Curitiba/PR"}, {"date": "2026-02-17T10:00:00", "status": "Objeto postado", "location": "Florianópolis/SC"}]},
         "body": "Olá, comprei o Carbon Watch X1 há 2 meses e ele simplesmente parou de funcionar. A tela não liga mais. Preciso de assistência urgente."},
        {"number": 1002, "subject": "Quero trocar meu relógio por outro modelo", "status": "waiting", "priority": "medium",
         "customer_id": customers[1].id, "assigned_to": users[2].id, "inbox_id": inboxes[6].id,
         "tags": ["troca"], "category": "troca", "sentiment": "neutral",
         "tracking_code": "NX987654321BR", "tracking_status": "Entregue",
         "tracking_data": {"carrier": "Correios", "code": "NX987654321BR", "status": "Entregue", "main_status": 50, "delivered": True, "days_in_transit": 6, "location": "Rio de Janeiro/RJ", "events": [{"date": "2026-02-18T16:45:00", "status": "Objeto entregue ao destinatário", "location": "Rio de Janeiro/RJ"}, {"date": "2026-02-17T09:00:00", "status": "Objeto saiu para entrega", "location": "Rio de Janeiro/RJ"}]},
         "body": "Gostaria de trocar meu Carbon Watch S2 pelo modelo X1. Como faço?"},
        {"number": 1003, "subject": "VOU PROCESSAR VOCÊS NO PROCON", "status": "escalated", "priority": "urgent",
         "customer_id": customers[3].id, "assigned_to": users[3].id, "inbox_id": inboxes[7].id,
         "tags": ["procon", "garantia"], "category": "juridico", "sentiment": "angry", "legal_risk": True,
         "body": "Já é o terceiro relógio que apresenta defeito! Vou abrir reclamação no PROCON e no Reclame Aqui! Meus direitos de consumidor estão sendo violados!"},
        {"number": 1004, "subject": "Carregador não encaixa no relógio", "status": "open", "priority": "medium",
         "customer_id": customers[2].id, "inbox_id": inboxes[8].id,
         "tags": ["carregador"], "category": "carregador", "sentiment": "neutral",
         "tracking_code": "YT2312345678901", "tracking_status": "Em trânsito",
         "tracking_data": {"carrier": "Cainiao", "code": "YT2312345678901", "status": "Em trânsito", "main_status": 10, "delivered": False, "days_in_transit": 12, "location": "Cajamar/SP", "events": [{"date": "2026-02-21T20:00:00", "status": "Pacote em trânsito para o destino", "location": "Cajamar/SP"}, {"date": "2026-02-18T05:00:00", "status": "Pacote chegou no país de destino", "location": "Curitiba/PR"}]},
         "body": "O carregador que veio na caixa não encaixa direito no relógio. Ele fica solto e não carrega."},
        {"number": 1005, "subject": "Tela rachada após queda", "status": "open", "priority": "low",
         "customer_id": customers[4].id, "assigned_to": users[1].id,
         "tags": ["mau_uso"], "category": "mau_uso", "sentiment": "negative",
         "tracking_code": "NX555888222BR", "tracking_status": "Objeto devolvido ao remetente",
         "tracking_data": {"carrier": "Correios", "code": "NX555888222BR", "status": "Objeto devolvido ao remetente", "main_status": 40, "delivered": False, "days_in_transit": 8, "location": "Belo Horizonte/MG", "events": [{"date": "2026-02-22T10:00:00", "status": "Objeto devolvido ao remetente", "location": "Belo Horizonte/MG"}, {"date": "2026-02-21T14:00:00", "status": "Destinatário ausente - 3ª tentativa", "location": "Belo Horizonte/MG"}]},
         "body": "O relógio caiu do meu pulso e a tela rachou. Isso está na garantia?"},
        {"number": 1006, "subject": "Contestação de cobrança duplicada", "status": "open", "priority": "urgent",
         "customer_id": customers[5].id, "assigned_to": users[3].id, "inbox_id": inboxes[7].id,
         "tags": ["chargeback"], "category": "financeiro", "sentiment": "angry", "legal_risk": True,
         "body": "Fui cobrado duas vezes pelo mesmo pedido. Se não resolverem, vou contestar no cartão e abrir processo."},
        {"number": 1007, "subject": "Dúvida sobre resistência à água", "status": "resolved", "priority": "low",
         "customer_id": customers[0].id, "assigned_to": users[2].id,
         "tags": [], "category": "duvida", "sentiment": "positive",
         "body": "Posso usar o Carbon Watch X1 para nadar? Qual a resistência à água?"},
        {"number": 1008, "subject": "Relógio não sincroniza com iPhone", "status": "in_progress", "priority": "medium",
         "customer_id": customers[1].id, "assigned_to": users[1].id,
         "tags": ["carregador"], "category": "suporte_tecnico", "sentiment": "neutral",
         "body": "Meu Carbon Watch não está sincronizando com meu iPhone 15. O Bluetooth conecta mas não sincroniza os dados."},
    ]

    for td in tickets_data:
        body = td.pop("body")
        sla_h = {"urgent": 4, "high": 8, "medium": 24, "low": 48}[td["priority"]]
        td["sla_deadline"] = now + timedelta(hours=sla_h)
        td["created_at"] = now - timedelta(hours=random.randint(1, 72))
        td["legal_risk"] = td.get("legal_risk", False)

        if td["status"] == "resolved":
            td["resolved_at"] = now - timedelta(hours=2)
            td["first_response_at"] = td["created_at"] + timedelta(hours=1)

        ticket = Ticket(**td)
        db.add(ticket)
        await db.flush()

        msg = Message(
            ticket_id=ticket.id, type="inbound",
            sender_email=next(c.email for c in customers if c.id == td["customer_id"]),
            sender_name=next(c.name for c in customers if c.id == td["customer_id"]),
            body_text=body,
        )
        db.add(msg)

    # ── KB Articles ──
    articles = [
        KBArticle(title="Política de Garantia Carbon", category="garantia", tags=["garantia", "prazo"],
            content="Todos os produtos Carbon possuem garantia de 12 meses contra defeitos de fabricação. A garantia não cobre danos por mau uso, quedas ou contato com água além do especificado."),
        KBArticle(title="Processo de Troca e Devolução", category="troca", tags=["troca", "devolução", "cdc"],
            content="O cliente tem 7 dias para arrependimento (CDC). Para trocas por defeito, o prazo é de 30 dias. O produto deve estar na embalagem original."),
        KBArticle(title="Carregadores Compatíveis", category="carregador", tags=["carregador", "bateria"],
            content="Carbon Watch X1: carregador magnético modelo CX1-CHG. Carbon Watch S2: carregador USB-C modelo CS2-CHG. Não use carregadores de terceiros."),
        KBArticle(title="O que é Mau Uso?", category="mau_uso", tags=["mau_uso", "garantia"],
            content="Mau uso inclui: quedas, contato com água salgada, tentativa de abertura, uso de acessórios não oficiais, exposição a temperaturas extremas."),
        KBArticle(title="Direitos do Consumidor - CDC", category="juridico", tags=["cdc", "procon", "juridico"],
            content="Art. 18 CDC: fornecedor responde por vícios de qualidade em 30 dias. Art. 49: direito de arrependimento em 7 dias para compras online."),
        KBArticle(title="Resistência à Água dos Modelos", category="especificacoes", tags=["agua", "especificacoes"],
            content="Carbon Watch X1: IP68, até 1.5m por 30min. Carbon Watch S2: IP67, respingos apenas. Carbon Watch Pro: 5ATM, natação."),
        KBArticle(title="Troubleshooting: Sincronização Bluetooth", category="suporte_tecnico", tags=["bluetooth", "sincronizacao"],
            content="1. Remova o pareamento no telefone. 2. Reinicie o relógio (segurar botão 10s). 3. Abra o app Carbon e pareie novamente. 4. Certifique-se que o app tem permissão de Bluetooth."),
    ]
    db.add_all(articles)

    # ── Macros ──
    macros = [
        Macro(name="Saudação Inicial", category="geral",
            content="Olá! Obrigado por entrar em contato com o suporte Carbon. Meu nome é {agente} e ficarei responsável pelo seu atendimento. Como posso ajudar?"),
        Macro(name="Solicitar Informações", category="geral",
            content="Para dar andamento ao seu caso, precisamos das seguintes informações:\n- Número do pedido\n- Modelo do relógio\n- Fotos do problema\n\nAguardamos seu retorno!"),
        Macro(name="Garantia Aprovada", category="garantia",
            content="Boa notícia! Analisamos seu caso e a garantia foi aprovada. Segue as instruções para envio:\n\n1. Embale o produto na caixa original\n2. Cole a etiqueta de postagem (em anexo)\n3. Envie pelos Correios\n\nPrazo de troca: até 10 dias úteis após recebermos o produto."),
        Macro(name="Procedimento de Troca", category="troca",
            content="Para realizar a troca, siga os passos:\n\n1. Acesse carbonsmartwatch.com.br/troca\n2. Informe o número do pedido\n3. Selecione o motivo da troca\n4. Imprima a etiqueta de postagem\n\nDúvidas? Estamos à disposição!"),
        Macro(name="Escalação", category="geral",
            content="Entendo sua situação e peço desculpas pelo transtorno. Estou encaminhando seu caso para um especialista que poderá ajudá-lo melhor. Você receberá um retorno em até 4 horas."),
        Macro(name="Encerramento", category="geral",
            content="Ficamos felizes em ter ajudado! Se precisar de mais alguma coisa, não hesite em nos procurar. Tenha um ótimo dia! 😊"),
    ]
    db.add_all(macros)

    await db.commit()
    print("✅ Database seeded with demo data")
