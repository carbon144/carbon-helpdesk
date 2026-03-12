"""Seed the database with initial data for Carbon Expert Hub."""
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
            content="Raptor: 5ATM (respingos, chuva, banho rápido, piscina com cuidado). Atlas: 3ATM (respingos, chuva, lavar mãos). One Max: 1ATM (respingos leves, suor). Aurora: 1ATM (respingos leves, suor). Quartz: 1ATM (respingos leves, suor). NENHUM modelo é IP68 ou IP67. 1ATM = NÃO usar na água. 3ATM = NÃO nadar. 5ATM = piscina com cuidado, sem mergulho."),
        KBArticle(title="Troubleshooting: Sincronização Bluetooth", category="suporte_tecnico", tags=["bluetooth", "sincronizacao"],
            content="1. Remova o pareamento no telefone. 2. Reinicie o relógio (segurar botão 10s). 3. Abra o app Carbon e pareie novamente. 4. Certifique-se que o app tem permissão de Bluetooth."),
    ]
    db.add_all(articles)

    # ── Macros (aligned with 6 system categories) ──
    macros = [
        # ── meu_pedido ──
        Macro(name="Rastreio do Pedido", category="meu_pedido",
            content="Oi, {{cliente}}! Seu pedido {{numero}} está com o seguinte status de rastreio:\n\nCódigo: {{rastreio}}\nStatus: em trânsito\n\nVocê pode acompanhar em tempo real pelo site dos Correios. Qualquer dúvida, estou aqui!"),
        Macro(name="Pedido a Caminho", category="meu_pedido",
            content="{{cliente}}, boas notícias! Seu pedido já saiu do nosso centro de distribuição e está a caminho.\n\nCódigo de rastreio: {{rastreio}}\nPrevisão: 5 a 12 dias úteis dependendo da sua região.\n\nAcompanhe pelo site dos Correios!"),
        Macro(name="Nota Fiscal", category="meu_pedido",
            content="{{cliente}}, segue em anexo a nota fiscal do seu pedido {{numero}}.\n\nCaso precise de uma segunda via futuramente, é só nos chamar!"),
        Macro(name="Pedido Não Recebido", category="meu_pedido",
            content="{{cliente}}, lamento que seu pedido ainda não chegou. Vou verificar o status agora mesmo.\n\nPode me confirmar o endereço de entrega para eu comparar com o que consta no sistema?"),
        Macro(name="Pedido Incompleto", category="meu_pedido",
            content="{{cliente}}, sinto muito pelo transtorno! Vamos resolver isso.\n\nPode me informar quais itens estão faltando e enviar uma foto do que recebeu? Assim consigo agilizar o reenvio."),
        Macro(name="Cancelar Pedido", category="meu_pedido",
            content="{{cliente}}, entendi que deseja cancelar o pedido {{numero}}.\n\nSe o pedido ainda não foi enviado, consigo cancelar e solicitar o estorno imediato. Caso já tenha sido postado, precisamos aguardar a devolução para processar.\n\nPosso seguir com o cancelamento?"),

        # ── garantia ──
        Macro(name="Garantia - Análise Inicial", category="garantia",
            content="{{cliente}}, vamos analisar seu caso de garantia.\n\nPreciso de algumas informações:\n1. Número do pedido\n2. Descrição detalhada do defeito\n3. Fotos ou vídeo mostrando o problema\n4. O relógio teve contato com água ou calor excessivo?\n\nNossa garantia cobre 12 meses contra defeitos de fabricação."),
        Macro(name="Garantia Aprovada", category="garantia",
            content="{{cliente}}, boa notícia! Analisamos seu caso e a garantia foi aprovada.\n\nPróximos passos:\n1. Vamos gerar sua solicitação no Troque Commerce\n2. Você receberá um e-mail com a etiqueta de postagem (grátis)\n3. Embale o produto e envie pelos Correios\n4. Assim que recebermos, enviamos o novo em até 10 dias úteis\n\nAlguma dúvida?",
            actions=[{"type": "add_tag", "value": "garantia_aprovada"}]),
        Macro(name="Garantia Negada - Mau Uso", category="garantia",
            content="{{cliente}}, após análise técnica, identificamos que o problema não é coberto pela garantia pois se trata de mau uso (contato com água/calor/impacto).\n\nA garantia de 12 meses cobre defeitos de fabricação. Danos por uso inadequado não são cobertos.\n\nSe quiser, posso te ajudar com opções de compra de um novo com desconto especial."),
        Macro(name="Abrir Troque Commerce", category="garantia",
            content="{{cliente}}, para dar andamento à sua troca, preciso que você abra uma solicitação no nosso portal:\n\n1. Acesse troquecommerce.com.br\n2. Informe o número do pedido ou CPF\n3. Selecione o motivo\n4. Aguarde a aprovação (até 48h)\n\nSe já abriu, me passe o número da solicitação que consulto o status pra você!"),
        Macro(name="Assistência Técnica", category="garantia",
            content="{{cliente}}, atualmente não oferecemos assistência técnica com reparo. Nossa política é de troca direta dentro da garantia (12 meses).\n\nSe o defeito for coberto, enviamos um produto novo. Me conta mais sobre o problema para eu avaliar?"),

        # ── reenvio ──
        Macro(name="Reenvio Confirmado", category="reenvio",
            content="{{cliente}}, confirmamos o reenvio do seu pedido! Um novo produto será postado em até 3 dias úteis.\n\nVocê receberá o código de rastreio por e-mail assim que sair. Qualquer dúvida, estou aqui!",
            actions=[{"type": "add_tag", "value": "reenvio"}, {"type": "set_status", "value": "waiting"}]),
        Macro(name="Extraviado - Verificação", category="reenvio",
            content="{{cliente}}, verifiquei que seu pedido consta como extraviado pelos Correios.\n\nVou providenciar o reenvio sem custo. Pode confirmar se o endereço está correto?\n\nEndereço no sistema: (verificar no Shopify)"),

        # ── financeiro ──
        Macro(name="Estorno Solicitado", category="financeiro",
            content="{{cliente}}, o estorno do seu pedido {{numero}} foi solicitado.\n\nPrazos:\n- Pix: até 5 dias úteis\n- Cartão de crédito: até 2 faturas (depende da operadora)\n- Boleto: até 10 dias úteis na conta informada\n\nVocê receberá um e-mail de confirmação.",
            actions=[{"type": "add_tag", "value": "estorno"}, {"type": "set_status", "value": "waiting"}]),
        Macro(name="Dúvida de Pagamento", category="financeiro",
            content="{{cliente}}, sobre sua dúvida de pagamento:\n\nAceitamos: Pix, cartão de crédito (até 12x), boleto bancário e carteiras digitais.\n\nSe o pagamento não foi confirmado, pode levar até 3 dias úteis para compensação (boleto) ou ser instantâneo (Pix/cartão).\n\nPosso te ajudar com algo mais específico?"),

        # ── duvida ──
        Macro(name="Informações do Produto", category="duvida",
            content="{{cliente}}, sobre o Carbon Watch:\n\n- Bluetooth 5.0 para conexão com o celular\n- Monitor cardíaco e oxímetro (SpO2)\n- Resistência à água varia por modelo (1ATM a 5ATM)\n- Bateria: 3 a 5 dias de uso normal\n- Compatível com Android e iOS\n\nTem alguma dúvida específica?"),
        Macro(name="Como Usar o Relógio", category="duvida",
            content="{{cliente}}, para começar a usar seu Carbon Watch:\n\n1. Carregue por 2h antes do primeiro uso\n2. Baixe o app FitCloudPro (Android/iOS)\n3. Ative o Bluetooth e pareie pelo app\n4. Pronto! O app sincroniza dados automaticamente\n\nSe precisar de ajuda com algum passo, me avisa!"),

        # ── reclamacao ──
        Macro(name="GUACU é Carbon", category="reclamacao",
            content="{{cliente}}, entendo sua preocupação! GUACU Negócios Digitais LTDA é a razão social da Carbon Smartwatch. É a mesma empresa, mesmo CNPJ.\n\nIsso aparece na fatura do cartão porque é o nome registrado. Seu pedido é legítimo e estamos aqui para qualquer dúvida!\n\nPosso te ajudar com mais alguma coisa?",
            actions=[{"type": "add_tag", "value": "guacu"}]),
        Macro(name="Reclamação - Acolhimento", category="reclamacao",
            content="{{cliente}}, entendo completamente sua frustração e peço desculpas pelo transtorno. Sua experiência importa muito pra gente.\n\nVou analisar seu caso com prioridade. Pode me contar mais detalhes sobre o que aconteceu?",
            actions=[{"type": "set_priority", "value": "high"}]),
        Macro(name="Escalação para Supervisor", category="reclamacao",
            content="{{cliente}}, entendo a gravidade da situação. Estou encaminhando seu caso diretamente para nosso supervisor, que vai entrar em contato em até 4 horas.\n\nSua satisfação é nossa prioridade e vamos resolver isso.",
            actions=[{"type": "set_status", "value": "escalated"}, {"type": "set_priority", "value": "urgent"}]),

        # ── uso geral (sem categoria específica = duvida) ──
        Macro(name="Solicitar Dados", category="duvida",
            content="{{cliente}}, para dar andamento ao seu caso, preciso de algumas informações:\n\n- Número do pedido ou e-mail de compra\n- Modelo do relógio\n- Descrição do problema\n\nAguardo seu retorno!"),
        Macro(name="Encerramento", category="duvida",
            content="{{cliente}}, fico feliz em ter ajudado! Se precisar de qualquer coisa, é só nos chamar.\n\nTenha um ótimo dia!"),
    ]
    db.add_all(macros)

    await db.commit()
    print("✅ Database seeded with demo data")
