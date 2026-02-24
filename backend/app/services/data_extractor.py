"""Data extraction utility — extrai dados de identificacao do cliente a partir do corpo de emails.

Usado pelo fluxo de fetch de emails e pela triagem IA para encontrar CPF, telefone,
numero de pedido Shopify e emails secundarios no corpo da mensagem.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns (compilados para performance)
# ---------------------------------------------------------------------------

# CPF: 123.456.789-00 ou 12345678900
CPF_PATTERN = re.compile(r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}')

# Telefone: (11) 98765-4321, 11987654321, (11)98765-4321, 11 98765-4321, etc.
PHONE_PATTERN = re.compile(r'\(?\d{2}\)?\s?\d{4,5}-?\d{4}')

# Pedido Shopify: #1234, #12345, etc.
SHOPIFY_ORDER_PATTERN = re.compile(r'#(\d{4,})')

# Email: padrao RFC simplificado, suficiente para captura em corpo de texto
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
)


# ---------------------------------------------------------------------------
# Helpers de normalizacao e validacao
# ---------------------------------------------------------------------------

def normalize_cpf(cpf: str) -> str:
    """Remove pontos e tracos do CPF, retornando apenas digitos.

    Ex: '123.456.789-00' -> '12345678900'
    """
    return re.sub(r'[.\-]', '', cpf)


def normalize_phone(phone: str) -> str:
    """Remove parenteses, espacos e tracos do telefone, retornando apenas digitos.

    Ex: '(11) 98765-4321' -> '11987654321'
    """
    return re.sub(r'[()\s\-]', '', phone)


def validate_cpf(cpf: str) -> bool:
    """Validacao basica de CPF: verifica se possui exatamente 11 digitos.

    Nao implementa o algoritmo completo de verificacao dos digitos verificadores;
    apenas garante que o formato normalizado tem o tamanho correto.
    """
    digits = normalize_cpf(cpf)
    return len(digits) == 11 and digits.isdigit()


def validate_phone(phone: str) -> bool:
    """Validacao basica de telefone: verifica se possui 10 ou 11 digitos.

    10 digitos = fixo (DDD + 8 digitos), 11 digitos = celular (DDD + 9 digitos).
    """
    digits = normalize_phone(phone)
    return len(digits) in (10, 11) and digits.isdigit()


# ---------------------------------------------------------------------------
# Funcao principal de extracao
# ---------------------------------------------------------------------------

def extract_customer_data(text: str) -> dict:
    """Extrai dados de identificacao do cliente a partir de texto livre (corpo de email).

    Retorna um dicionario com os campos encontrados (ou None se nao encontrado):
        - cpf: str | None         — CPF normalizado (apenas digitos, 11 digitos)
        - phone: str | None       — Telefone normalizado (apenas digitos, 10-11 digitos)
        - shopify_order_id: str | None — Numero do pedido Shopify (ex: '1234')
        - email: str | None       — Email secundario encontrado no corpo
    """
    result: dict = {
        "cpf": None,
        "phone": None,
        "shopify_order_id": None,
        "email": None,
    }

    if not text:
        return result

    # --- CPF ---
    cpf_span = None
    cpf_match = CPF_PATTERN.search(text)
    if cpf_match:
        raw_cpf = cpf_match.group()
        if validate_cpf(raw_cpf):
            result["cpf"] = normalize_cpf(raw_cpf)
            cpf_span = (cpf_match.start(), cpf_match.end())
            logger.debug("CPF extraido: %s", result["cpf"])

    # --- Telefone ---
    # Itera sobre todos os matches para evitar capturar o mesmo trecho do CPF
    for phone_match in PHONE_PATTERN.finditer(text):
        if cpf_span and phone_match.start() < cpf_span[1] and phone_match.end() > cpf_span[0]:
            continue  # pula match que sobrepoe o CPF
        raw_phone = phone_match.group()
        if validate_phone(raw_phone):
            result["phone"] = normalize_phone(raw_phone)
            logger.debug("Telefone extraido: %s", result["phone"])
            break

    # --- Pedido Shopify ---
    order_match = SHOPIFY_ORDER_PATTERN.search(text)
    if order_match:
        result["shopify_order_id"] = order_match.group(1)
        logger.debug("Pedido Shopify extraido: #%s", result["shopify_order_id"])

    # --- Email secundario ---
    email_match = EMAIL_PATTERN.search(text)
    if email_match:
        result["email"] = email_match.group().lower()
        logger.debug("Email extraido: %s", result["email"])

    return result
