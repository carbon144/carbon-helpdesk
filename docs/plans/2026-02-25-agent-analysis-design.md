# Design: Analise Profunda de Atendentes

## Resumo

Sistema de analise completa de cada atendente, combinando metricas quantitativas (SQL) com analise qualitativa por IA (Claude). Gera relatorios sob demanda e automaticamente toda semana. Acesso restrito a super_admin.

## Acesso

- Somente usuarios com role `super_admin`
- Endpoint protegido + pagina escondida no frontend para outros roles

## Arquitetura

### Backend

**Model `AgentReport`** — armazena cada relatorio gerado:
- `id` (UUID)
- `agent_id` (FK users)
- `period_start`, `period_end` (datetime)
- `sample_size` (int — 20/50/100/null para todas)
- `quantitative_metrics` (JSONB — metricas SQL)
- `ai_analysis` (Text — parecer IA completo)
- `ai_scores` (JSONB — scores individuais 1-10)
- `generated_by` (FK users — quem solicitou, null se automatico)
- `report_type` (string — "manual" ou "weekly_auto")
- `created_at` (datetime)

**Endpoints:**
- `POST /api/reports/agent-analysis/{agent_id}` — gera relatorio sob demanda. Params: `sample_size` (20/50/100/all), `days` (periodo). Calcula metricas SQL, busca mensagens outbound, envia pro Claude, salva e retorna.
- `GET /api/reports/agent-analysis` — lista relatorios salvos. Filtro por agent_id e periodo.
- `GET /api/reports/agent-analysis/{report_id}` — detalhe de um relatorio.
- `GET /api/reports/agent-analysis/{report_id}/export` — exporta PDF.
- `GET /api/reports/agent-analysis/overview` — resumo de todos agentes (cards com ultimo score).

**Cron semanal** — roda domingo 23h UTC. Gera relatorio pra cada atendente ativo com amostra 50 e periodo 7 dias. Salva no banco.

### Metricas Quantitativas (SQL)

| Metrica | Descricao |
|---|---|
| tickets_resolved | Total resolvidos no periodo |
| tickets_total | Total atribuidos no periodo |
| avg_first_response_h | Tempo medio primeira resposta (horas) |
| avg_resolution_h | Tempo medio de resolucao (horas) |
| sla_compliance_pct | % de SLA cumprido |
| csat_avg | CSAT medio |
| csat_count | Quantidade de avaliacoes CSAT |
| tickets_escalated | Quantos foram escalados |
| tickets_by_category | Distribuicao por categoria (JSON) |
| messages_per_ticket_avg | Media de mensagens outbound por ticket |
| hourly_distribution | Atividade por hora do dia (JSON) |
| daily_volume | Tickets/dia ao longo do periodo (JSON) |
| fcr_rate | First Contact Resolution % |

### Analise Qualitativa (IA)

A IA recebe as N mensagens outbound do atendente e avalia:

**Scores (1-10):**
- `tone_empathy` — Tom e empatia: acolhimento, cordialidade
- `clarity` — Clareza: objetividade, sem ambiguidade
- `playbook_adherence` — Aderencia ao playbook/KB
- `proactivity` — Proatividade: antecipou duvidas, ofereceu solucoes
- `grammar` — Portugues: gramatica, ortografia, formalidade
- `resolution_quality` — Resolucao efetiva: resolveu ou enrolou
- `overall` — Nota geral ponderada

**Texto:**
- Parecer geral (3-5 paragrafos)
- Pontos fortes (lista)
- Pontos de melhoria (lista com exemplos reais)
- Recomendacoes (acoes concretas)

### Prompt da IA

```
Voce e um supervisor de atendimento ao cliente da Carbon (smartwatches).
Analise as mensagens abaixo enviadas pelo atendente "{agent_name}" nos ultimos {days} dias.

Avalie cada criterio de 1 a 10:
1. Tom e empatia
2. Clareza e objetividade
3. Aderencia aos procedimentos (playbook)
4. Proatividade
5. Qualidade do portugues
6. Resolucao efetiva

Retorne em JSON:
{
  "scores": { "tone_empathy": N, "clarity": N, "playbook_adherence": N, "proactivity": N, "grammar": N, "resolution_quality": N, "overall": N },
  "summary": "parecer geral...",
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "recommendations": ["...", "..."]
}

MENSAGENS:
{messages}
```

### Frontend

**Nova pagina `/agent-analysis`** — visivel somente para super_admin no menu lateral (secao "Gestao").

**Layout:**
1. **Visao geral** — cards por atendente com: nome, nota geral, mini-barras dos 6 scores, ultimo relatorio gerado, botao "Analisar"
2. **Detalhe do atendente** — clica no card:
   - Seletor de periodo (7/14/30/60/90 dias) e amostra (20/50/100/todas)
   - Botao "Gerar Nova Analise"
   - Metricas quantitativas com graficos (volume diario, distribuicao horaria, por categoria)
   - Parecer IA completo (scores com barras visuais + texto)
   - Botao "Exportar PDF"
3. **Historico** — lista de relatorios anteriores do atendente, com comparacao de evolucao dos scores ao longo do tempo

**Exportacao PDF:**
- Gera no backend usando HTML template + weasyprint ou similar
- Inclui metricas + parecer IA + graficos basicos

## Retry de IA (fix do erro 529)

Adicionar retry com backoff exponencial no ai_service.py para erros 429 (rate limit) e 529 (overloaded). Max 3 tentativas com delays 2s, 4s, 8s.

## Custo Estimado

- Relatorio com 50 mensagens: ~2000 tokens input + 500 output = ~$0.03
- 6 atendentes x semanal = ~$0.18/semana = ~$0.72/mes
- Sob demanda com 100 mensagens: ~$0.06 por relatorio
