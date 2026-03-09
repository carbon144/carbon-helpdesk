# Carbon Voice AI — Carol

## Visao geral
Numero fixo SP (11) com Voice AI que atende ligacoes usando a mesma logica dos 28 flows do chatbot. Cliente liga, Carol conversa por voz, resolve. Se nao resolver, cria ticket no helpdesk e avisa que retornam por email.

## Arquitetura

```
Cliente liga (11) XXXX-XXXX
        |
    Twilio (numero fixo SP)
        |
    Vapi.ai (Voice AI platform)
    - STT: Deepgram (transcreve fala)
    - LLM: Claude (processa)
    - TTS: ElevenLabs (voz Carol)
        |
    Webhooks -> Backend Helpdesk (FastAPI)
    - Shopify (pedidos)
    - Wonca/tracking (rastreio)
    - TroqueCommerce (garantia)
    - Escalation -> cria ticket + email
```

## Fluxo de uma ligacao

1. Cliente liga -> Twilio encaminha pra Vapi
2. Carol: "Fala! Bem-vinda a Carbon, aqui eh a Carol. Como posso te ajudar?"
3. Cliente fala -> Deepgram transcreve -> Claude processa com system prompt
4. Quando precisa consultar dados (pedido, rastreio, Troque), Vapi chama webhook no backend
5. Claude formula resposta -> ElevenLabs gera audio -> cliente ouve
6. Se nao resolver -> Carol abre ticket no helpdesk, avisa retorno por email

## Componentes backend

- `backend/app/api/vapi_webhook.py` — endpoint pro Vapi chamar (tools: consulta pedido, rastreio, Troque, cria ticket)
- `backend/app/services/voice_service.py` — logica de ferramentas expostas pro Vapi
- Tabela `voice_calls` (id, ticket_id, conversation_id, duration, recording_url, transcript, created_at)

## Componentes frontend

- `VoiceCallPlayer` — player de audio + transcricao dentro do ticket
- Indicador visual de que o ticket veio de ligacao

## Gravacao e transcricao

- Vapi envia webhook `end-of-call` com recording URL + transcript
- Backend salva na tabela `voice_calls` vinculado ao ticket/conversa
- Frontend mostra: player de audio, transcricao completa, duracao

## Servicos externos

| Servico | Funcao | Custo estimado |
|---------|--------|---------------|
| Twilio | Numero fixo SP + minutos | ~R$30/mes + R$0.05/min |
| Vapi.ai | Orquestracao voice AI | ~R$0.05/min |
| Deepgram | Speech-to-text | incluso no Vapi |
| ElevenLabs | Voz Carol (TTS) | ~R$0.08/min |
| Claude API | LLM | ~R$0.01/interacao |

**Custo total estimado: ~R$0.15-0.20/min de ligacao**

## Fora de escopo (fase 2)
- URA com menu por teclas (DTMF)
- Transferencia ao vivo pra agente humano
- Audio no WhatsApp (responder com voz no WA)
