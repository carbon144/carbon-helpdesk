"""Product catalog endpoint — static product data from Carbon."""
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/catalog", tags=["catalog"])

PRODUCTS = [
    {
        "id": "raptor",
        "name": "Carbon Raptor",
        "price": 819.97,
        "image": "https://carbonsmartwatch.com.br/cdn/shop/files/raptor_main.webp",
        "color": "#1a1a2e",
        "specs": {
            "tela": "1.96\" AMOLED",
            "bateria": "Até 15 dias",
            "resistencia": "5ATM (à prova d'água real)",
            "bluetooth": "5.2",
            "sensores": "Frequência cardíaca, SpO2, acelerômetro, giroscópio",
            "compatibilidade": "Android 5.0+ / iOS 11+",
            "funcoes": "Chamadas Bluetooth, 100+ modos esporte, Always On Display, assistente de voz, monitoramento sono, controle de música",
        },
        "category": "smartwatch",
        "status": "active",
        "common_issues": ["Carregador", "Pareamento Bluetooth", "Notificações não chegam", "Resistência à água"],
        "url": "https://carbonsmartwatch.com.br/products/raptor",
    },
    {
        "id": "atlas",
        "name": "Carbon Atlas",
        "price": 849.97,
        "image": "https://carbonsmartwatch.com.br/cdn/shop/files/atlas_main.webp",
        "color": "#0d1b2a",
        "specs": {
            "tela": "AMOLED ultra brilhante",
            "bateria": "Mais de 15 dias",
            "resistencia": "100% à prova d'água",
            "bluetooth": "5.2",
            "gps": "GPS integrado",
            "sensores": "Frequência cardíaca, SpO2, acelerômetro, giroscópio, bússola",
            "compatibilidade": "Android 5.0+ / iOS 11+",
            "funcoes": "GPS integrado, chamadas pelo pulso, 100+ modos esporte, monitoramento sono, Always On Display",
        },
        "category": "smartwatch",
        "status": "active",
        "common_issues": ["GPS impreciso", "Bateria descarregando rápido", "Sincronização de dados", "Carregador"],
        "url": "https://carbonsmartwatch.com.br/products/carbonatlas",
    },
    {
        "id": "spark-x",
        "name": "Carbon Spark X",
        "price": 829.97,
        "image": "https://carbonsmartwatch.com.br/cdn/shop/files/sparkx_main.webp",
        "color": "#16213e",
        "specs": {
            "tela": "AMOLED ultra brilhante",
            "bateria": "Até 15 dias",
            "resistencia": "À prova d'água",
            "bluetooth": "5.2",
            "sensores": "Frequência cardíaca, SpO2, acelerômetro, giroscópio",
            "compatibilidade": "Android 5.0+ / iOS 11+",
            "funcoes": "Chamadas Bluetooth, Always On Display, assistente de voz, 100+ modos esporte, monitoramento sono, controle de música",
        },
        "category": "smartwatch",
        "status": "active",
        "common_issues": ["Pareamento Bluetooth", "Notificações não chegam", "Carregador", "Reset de fábrica"],
        "url": "https://carbonsmartwatch.com.br/products/smartwatch-carbon-spark-x",
    },
    {
        "id": "one-max",
        "name": "Carbon One Max",
        "price": 699.97,
        "image": "https://carbonsmartwatch.com.br/cdn/shop/files/onemax_main.webp",
        "color": "#1b2838",
        "specs": {
            "tela": "HD display",
            "bateria": "Até 10 dias",
            "resistencia": "À prova d'água",
            "bluetooth": "5.0",
            "sensores": "Frequência cardíaca, SpO2, acelerômetro",
            "compatibilidade": "Android 5.0+ / iOS 10+",
            "funcoes": "Monitoramento cardíaco, modos esportivos completos, notificações, controle de música",
        },
        "category": "smartwatch",
        "status": "active",
        "common_issues": ["Pareamento", "Notificações", "Bateria", "Carregador"],
        "url": "https://carbonsmartwatch.com.br/products/onemax",
    },
    {
        "id": "scout",
        "name": "Carbon Scout",
        "price": 683.97,
        "image": "https://carbonsmartwatch.com.br/cdn/shop/files/scout_main.webp",
        "color": "#2d3436",
        "specs": {
            "tela": "Display HD",
            "bateria": "Até 10 dias",
            "resistencia": "100% à prova d'água (AquaShield)",
            "bluetooth": "5.0",
            "sensores": "Frequência cardíaca, SpO2, acelerômetro",
            "compatibilidade": "Android 5.0+ / iOS 10+",
            "funcoes": "Chamadas Bluetooth, 100+ modos esporte, Always On Display, monitoramento sono, controle de música",
        },
        "category": "smartwatch",
        "status": "active",
        "common_issues": ["Pareamento Bluetooth", "Resistência à água", "Carregador", "Sincronização"],
        "url": "https://carbonsmartwatch.com.br/products/carbonscout",
    },
    {
        "id": "titan",
        "name": "Carbon Titan",
        "price": 649.97,
        "image": "https://carbonsmartwatch.com.br/cdn/shop/files/titan_main.webp",
        "color": "#2d3748",
        "specs": {
            "tela": "1.71\" HD",
            "bateria": "380mAh",
            "resistencia": "Material ultra resistente",
            "bluetooth": "5.0",
            "sensores": "Frequência cardíaca, acelerômetro",
            "compatibilidade": "Android 5.0+ / iOS 10+",
            "funcoes": "24 modalidades esportivas, notificações, monitoramento sono, controle de música",
        },
        "category": "smartwatch",
        "status": "active",
        "common_issues": ["Pareamento", "Tela não liga", "Bateria", "Reset de fábrica"],
        "url": "https://carbonsmartwatch.com.br/products/carbontitan-1",
    },
    {
        "id": "carregador-magnetico",
        "name": "Carregador Magnético Universal",
        "price": 49.99,
        "image": "https://carbonsmartwatch.com.br/cdn/shop/files/charger_main.webp",
        "color": "#4a5568",
        "specs": {
            "tipo": "Magnético USB",
            "compatibilidade": "Todos modelos Carbon",
            "cabo": "1 metro",
        },
        "category": "acessorio",
        "status": "active",
        "common_issues": ["Não carrega", "Não encaixa magnético"],
    },
    {
        "id": "pulseira-silicone",
        "name": "Pulseira de Silicone Extra",
        "price": 29.99,
        "image": "https://carbonsmartwatch.com.br/cdn/shop/files/strap_main.webp",
        "color": "#636e72",
        "specs": {
            "material": "Silicone hipoalergênico",
            "tamanhos": "S/M/L",
            "compatibilidade": "Todos modelos Carbon",
            "cores": "Preto, Azul, Verde, Vermelho, Rosa",
        },
        "category": "acessorio",
        "status": "active",
        "common_issues": ["Tamanho errado", "Desgaste prematuro"],
    },
]


@router.get("/products")
async def list_products(
    category: str | None = None,
    user: User = Depends(get_current_user),
):
    """List all products in the catalog."""
    products = PRODUCTS
    if category:
        products = [p for p in products if p["category"] == category]
    return products


@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    user: User = Depends(get_current_user),
):
    """Get a specific product by ID."""
    for p in PRODUCTS:
        if p["id"] == product_id:
            return p
    return {"error": "Produto não encontrado"}
