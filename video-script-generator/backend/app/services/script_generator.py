"""Gerador de roteiros de video usando Claude AI.

Tipos de roteiro:
- teleprompter: texto corrido pra ler direto, sem instrucoes visuais
- ugc: roteiro estilo UGC com marcacoes de cena informais
- founder_ad: roteiro pra founder falar direto pra camera, persuasivo
- meta_ad: roteiro completo com hook, body, CTA, instrucoes visuais
"""
from __future__ import annotations
import asyncio
import json
import logging
import random
from anthropic import Anthropic

from app.config import settings
from app.services.helpdesk_client import extract_customer_insights

logger = logging.getLogger(__name__)

client: Anthropic | None = None


def _get_client() -> Anthropic:
    global client
    if client is None:
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return client


async def _call_claude(system: str, user_msg: str, max_tokens: int = 4096) -> str:
    """Chama Claude com retry."""
    for attempt in range(3):
        try:
            c = _get_client()
            response = await asyncio.to_thread(
                c.messages.create,
                model=settings.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
            return response.content[0].text
        except Exception as e:
            if attempt == 2:
                raise
            delay = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Claude retry {attempt+1}/3 after {delay:.1f}s: {str(e)[:80]}")
            await asyncio.sleep(delay)


# ─── System prompts por tipo de roteiro ──────────────────────────────

SYSTEM_BASE = """Voce e um copywriter especialista em roteiros de video para e-commerce.
Voce cria roteiros de anuncios para Meta Ads (Facebook/Instagram) que vendem produtos fisicos.
Voce conhece as melhores praticas de direct response, UGC e founder ads.
Voce escreve em portugues brasileiro, informal mas profissional.
Sempre use dados reais dos clientes quando fornecidos para criar roteiros mais autenticos."""

SYSTEM_TELEPROMPTER = SYSTEM_BASE + """

FORMATO: TELEPROMPTER
- Escreva APENAS o texto que sera lido no teleprompter
- SEM instrucoes de cena, SEM marcacoes visuais
- Use frases curtas e diretas, faceis de ler em voz alta
- Marque pausas com [...]
- Destaque palavras-chave com **negrito**
- Estrutura: HOOK (primeiros 3s) > PROBLEMA > SOLUCAO > PROVA > CTA

Responda em JSON com esta estrutura:
{
  "script": "texto completo do teleprompter",
  "hook_options": ["hook alternativo 1", "hook alternativo 2", "hook alternativo 3"],
  "cta_options": ["cta alternativo 1", "cta alternativo 2"],
  "estimated_duration_seconds": 30,
  "thumbnail_suggestions": ["sugestao 1", "sugestao 2"]
}"""

SYSTEM_UGC = SYSTEM_BASE + """

FORMATO: UGC (User Generated Content)
- Roteiro que parece natural, como se fosse uma pessoa real falando
- Use linguagem super informal, como stories do Instagram
- Inclua marcacoes de cena entre [COLCHETES]
- Estrutura tipica: [UNBOXING/REACAO] > [MOSTRANDO O PRODUTO] > [USANDO] > [RESULTADO] > [RECOMENDACAO]
- O tom deve parecer uma recomendacao genuina, NAO um anuncio

Responda em JSON com esta estrutura:
{
  "script": "roteiro completo com marcacoes de cena",
  "scenes": [
    {"scene": 1, "visual": "descricao visual", "dialogue": "fala", "duration": "Xs"}
  ],
  "hook_options": ["hook alternativo 1", "hook alternativo 2", "hook alternativo 3"],
  "cta_options": ["cta alternativo 1", "cta alternativo 2"],
  "estimated_duration_seconds": 30,
  "thumbnail_suggestions": ["sugestao 1", "sugestao 2"],
  "notes": "dicas de gravacao"
}"""

SYSTEM_FOUNDER = SYSTEM_BASE + """

FORMATO: FOUNDER AD
- Roteiro para o fundador/CEO falar direto pra camera
- Tom: autoridade + vulnerabilidade + paixao pelo produto
- Comece com um hook forte (historia pessoal, dado chocante, ou pergunta provocativa)
- Inclua elementos de storytelling (por que criou o produto, desafios, missao)
- Use dados reais dos clientes como prova social quando disponivel
- Estrutura: HOOK PESSOAL > HISTORIA/PROBLEMA > SOLUCAO (o produto) > PROVA SOCIAL > CTA DIRETO

Responda em JSON com esta estrutura:
{
  "script": "roteiro completo do founder ad",
  "scenes": [
    {"scene": 1, "visual": "descricao visual", "dialogue": "fala", "duration": "Xs"}
  ],
  "hook_options": ["hook alternativo 1", "hook alternativo 2", "hook alternativo 3"],
  "cta_options": ["cta alternativo 1", "cta alternativo 2"],
  "estimated_duration_seconds": 45,
  "thumbnail_suggestions": ["sugestao 1", "sugestao 2"],
  "notes": "dicas de gravacao pro founder"
}"""

SYSTEM_META_AD = SYSTEM_BASE + """

FORMATO: META AD COMPLETO
- Roteiro completo com todas as instrucoes de producao
- Inclua: hook visual, texto de overlay, falas, transicoes, musica sugerida
- Pense em formato vertical (9:16) para Reels/Stories e quadrado (1:1) para feed
- Estrutura detalhada: HOOK (0-3s) > PROBLEMA (3-8s) > AGITACAO (8-15s) > SOLUCAO (15-22s) > PROVA (22-28s) > CTA (28-30s)
- Cada cena deve ter: visual, audio, texto na tela, duracao

Responda em JSON com esta estrutura:
{
  "script": "roteiro resumido (versao teleprompter)",
  "scenes": [
    {
      "scene": 1,
      "timestamp": "0:00-0:03",
      "visual": "descricao do que aparece na tela",
      "dialogue": "o que a pessoa fala",
      "text_overlay": "texto que aparece na tela",
      "audio_note": "musica/efeito sonoro",
      "duration": "3s"
    }
  ],
  "hook_options": ["hook alternativo 1", "hook alternativo 2", "hook alternativo 3"],
  "cta_options": ["cta alternativo 1", "cta alternativo 2"],
  "estimated_duration_seconds": 30,
  "thumbnail_suggestions": ["sugestao 1", "sugestao 2"],
  "ad_copy": {
    "primary_text": "texto principal do anuncio",
    "headline": "titulo do anuncio",
    "description": "descricao do anuncio"
  },
  "format_notes": "notas sobre formato 9:16 vs 1:1"
}"""

SYSTEM_PROMPTS = {
    "teleprompter": SYSTEM_TELEPROMPTER,
    "ugc": SYSTEM_UGC,
    "founder_ad": SYSTEM_FOUNDER,
    "meta_ad": SYSTEM_META_AD,
}


async def generate_script(
    title: str,
    product_name: str,
    script_type: str,
    product_description: str | None = None,
    objective: str | None = None,
    target_audience: str | None = None,
    tone: str | None = None,
    duration_seconds: int | None = None,
    additional_notes: str | None = None,
    use_customer_insights: bool = True,
    top_performing_scripts: list[dict] | None = None,
) -> dict:
    """Gera um roteiro de video completo.

    Returns:
        dict com script_content, scenes, hook_options, cta_options, etc.
    """
    system = SYSTEM_PROMPTS.get(script_type, SYSTEM_TELEPROMPTER)

    # Montar o brief
    brief_parts = [f"TITULO DO VIDEO: {title}", f"PRODUTO: {product_name}"]

    if product_description:
        brief_parts.append(f"DESCRICAO DO PRODUTO: {product_description}")
    if objective:
        brief_parts.append(f"OBJETIVO: {objective}")
    if target_audience:
        brief_parts.append(f"PUBLICO-ALVO: {target_audience}")
    if tone:
        brief_parts.append(f"TOM: {tone}")
    if duration_seconds:
        brief_parts.append(f"DURACAO ALVO: {duration_seconds} segundos")
    if additional_notes:
        brief_parts.append(f"NOTAS ADICIONAIS: {additional_notes}")

    # Puxar insights do helpdesk
    customer_insights = None
    if use_customer_insights:
        try:
            insights = await extract_customer_insights(product_name)
            if insights.get("total_tickets_analyzed", 0) > 0:
                customer_insights = insights
                brief_parts.append("\n--- INSIGHTS REAIS DOS CLIENTES (do helpdesk) ---")
                if insights.get("subjects"):
                    brief_parts.append(f"ASSUNTOS DOS TICKETS (ultimos 60 dias): {'; '.join(insights['subjects'][:20])}")
                if insights.get("customer_messages"):
                    brief_parts.append(f"MENSAGENS DE CLIENTES (exemplos reais): {'; '.join(insights['customer_messages'][:10])}")
                brief_parts.append(f"Total de tickets analisados: {insights['total_tickets_analyzed']}")
                brief_parts.append("Use essas informacoes reais para criar um roteiro mais autentico e que aborda as duvidas/dores reais dos clientes.")
        except Exception as e:
            logger.warning(f"Erro ao buscar customer insights: {e}")

    # Adicionar referencia de roteiros que performaram bem
    if top_performing_scripts:
        brief_parts.append("\n--- ROTEIROS QUE PERFORMARAM BEM (referencia) ---")
        for i, script in enumerate(top_performing_scripts[:3], 1):
            brief_parts.append(f"\nREFERENCIA {i} (ROAS: {script.get('roas', 'N/A')}, CTR: {script.get('ctr', 'N/A')}%):")
            brief_parts.append(script.get("script_content", "")[:500])
        brief_parts.append("\nUse esses roteiros como referencia de estilo e estrutura, mas crie algo original.")

    user_msg = "\n".join(brief_parts)

    # Chamar Claude
    raw_response = await _call_claude(system, user_msg)

    # Parsear JSON da resposta
    result = _parse_json_response(raw_response)
    result["customer_insights"] = customer_insights

    return result


async def refine_script(
    original_script: str,
    script_type: str,
    feedback: str,
    keep_structure: bool = True,
) -> dict:
    """Refina um roteiro existente com base no feedback."""
    system = SYSTEM_PROMPTS.get(script_type, SYSTEM_TELEPROMPTER)

    user_msg = f"""ROTEIRO ORIGINAL:
{original_script}

FEEDBACK DO USUARIO:
{feedback}

{"Mantenha a estrutura geral mas melhore conforme o feedback." if keep_structure else "Pode reescrever completamente se necessario."}

Gere a versao refinada no mesmo formato JSON."""

    raw_response = await _call_claude(system, user_msg)
    return _parse_json_response(raw_response)


async def generate_insights_summary(insights: dict) -> str:
    """Gera um resumo dos insights dos clientes para exibir no frontend."""
    if not insights or insights.get("total_tickets_analyzed", 0) == 0:
        return "Nenhum dado de cliente disponivel."

    system = """Voce analisa dados de atendimento ao cliente e gera resumos concisos.
Responda em portugues brasileiro, em formato de bullet points."""

    user_msg = f"""Analise esses dados de tickets de suporte e gere um resumo dos principais insights para criacao de conteudo:

Assuntos dos tickets: {'; '.join(insights.get('subjects', [])[:30])}
Mensagens dos clientes: {'; '.join(insights.get('customer_messages', [])[:15])}
Total de tickets: {insights.get('total_tickets_analyzed', 0)}

Gere:
1. Top 5 duvidas/perguntas mais frequentes
2. Top 3 dores/reclamacoes dos clientes
3. Top 3 elogios ou pontos positivos mencionados
4. Sugestoes de angulos para anuncios baseado nesses dados"""

    return await _call_claude(system, user_msg, max_tokens=2000)


def _parse_json_response(raw: str) -> dict:
    """Extrai JSON da resposta do Claude, mesmo se tiver texto extra."""
    # Tentar parsear direto
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Procurar JSON dentro de markdown code block
    import re
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Procurar primeiro { ate ultimo }
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    # Fallback: retornar como texto puro
    logger.warning("Nao conseguiu parsear JSON da resposta do Claude")
    return {"script": raw, "parse_error": True}
