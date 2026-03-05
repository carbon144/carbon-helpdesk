# Design: Aba Produtividade na Analise de Equipe

## Objetivo
Adicionar aba "Produtividade" na AgentAnalysisPage com metricas operacionais de cada agente: tempo medio de resposta, tempo de resolucao, tickets/hora, com graficos diarios e filtro de datas personalizado.

## Metricas por Agente

| Metrica | Calculo |
|---|---|
| Tempo medio de resposta | Media do tempo entre cada msg inbound e a proxima outbound do agente no mesmo ticket |
| Tempo medio de resolucao | Media de resolved_at - created_at dos tickets resolvidos |
| Tickets respondidos/hora | Total tickets com resposta / horas trabalhadas (span first→last msg) |
| Total de tickets | Contagem de tickets atribuidos no periodo |

## Graficos

- **Visao geral**: barras com todos agentes lado a lado por dia (tickets/hora)
- **Detalhe individual**: ao clicar num agente, 3 linhas — tempo resposta, tempo resolucao, tickets/hora

## Filtro de Datas

- Date range picker (data inicio + data fim)
- Presets: Hoje, 7 dias, 30 dias

## Backend

Endpoint: `GET /agent-deep-analysis/productivity?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

Retorna:
```json
{
  "period": { "start": "...", "end": "..." },
  "agents": [
    {
      "agent_id": "...",
      "agent_name": "...",
      "totals": {
        "avg_response_time_min": 45,
        "avg_resolution_time_h": 12.5,
        "tickets_per_hour": 3.2,
        "total_tickets": 150,
        "total_resolved": 130
      },
      "daily": [
        {
          "date": "2026-02-25",
          "avg_response_time_min": 30,
          "avg_resolution_time_h": 10,
          "tickets_responded": 15,
          "hours_worked": 6.5,
          "tickets_per_hour": 2.3
        }
      ]
    }
  ]
}
```

## Frontend

Nova aba "Produtividade" na AgentAnalysisPage usando Recharts.
