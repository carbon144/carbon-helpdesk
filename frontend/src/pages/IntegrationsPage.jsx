import React, { useState, useEffect } from 'react'
import { useToast } from '../components/Toast'
import { getSlackStatus, getGmailStatus, getGmailAuthUrl, fetchGmailEmails, getAIStatus, getMetaStatus } from '../services/api'

export default function IntegrationsPage() {
  const toast = useToast()
  const [slackStatus, setSlackStatus] = useState(null)
  const [gmailStatus, setGmailStatus] = useState(null)
  const [aiStatus, setAiStatus] = useState(null)
  const [metaStatus, setMetaStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fetching, setFetching] = useState(false)
  const [fetchResult, setFetchResult] = useState(null)

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      const [slack, gmail, ai, meta] = await Promise.allSettled([getSlackStatus(), getGmailStatus(), getAIStatus(), getMetaStatus()])
      setSlackStatus(slack.status === 'fulfilled' ? slack.value.data : { configured: false })
      setGmailStatus(gmail.status === 'fulfilled' ? gmail.value.data : { configured: false })
      setAiStatus(ai.status === 'fulfilled' ? ai.value.data : { configured: false })
      setMetaStatus(meta.status === 'fulfilled' ? meta.value.data : null)
    } catch (e) {
      console.error('Failed to load integration statuses:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleGmailAuth = async () => {
    try {
      const { data } = await getGmailAuthUrl()
      window.open(data.auth_url, '_blank')
    } catch (e) {
      toast.error('Erro: configure GMAIL_CLIENT_ID e GMAIL_CLIENT_SECRET no .env primeiro')
    }
  }

  const handleFetchEmails = async () => {
    setFetching(true)
    setFetchResult(null)
    try {
      const { data } = await fetchGmailEmails()
      setFetchResult(data)
    } catch (e) {
      setFetchResult({ error: 'Falha ao buscar emails' })
    } finally {
      setFetching(false)
    }
  }

  const StatusBadge = ({ status }) => {
    if (loading) return <span className="text-carbon-400 text-sm"><i className="fas fa-spinner animate-spin mr-1" />Verificando...</span>
    if (status?.connected) return <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-sm font-medium"><i className="fas fa-check-circle mr-1" />Conectado</span>
    if (status?.configured) return <span className="bg-yellow-500/20 text-yellow-400 px-3 py-1 rounded-full text-sm font-medium"><i className="fas fa-exclamation-circle mr-1" />Erro</span>
    return <span className="bg-carbon-600 text-carbon-400 px-3 py-1 rounded-full text-sm font-medium"><i className="fas fa-times-circle mr-1" />Não Configurado</span>
  }

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-white mb-6">Integrações</h1>

      {/* Slack */}
      <div className="bg-carbon-700 rounded-xl p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-purple-600/20 rounded-xl flex items-center justify-center">
              <i className="fab fa-slack text-2xl text-purple-400" />
            </div>
            <div>
              <h2 className="text-white font-semibold text-lg">Slack</h2>
              <p className="text-carbon-400 text-sm">Receba e responda tickets diretamente pelo Slack</p>
            </div>
          </div>
          <StatusBadge status={slackStatus} />
        </div>

        {slackStatus?.connected && (
          <div className="bg-carbon-800 rounded-lg p-4 mb-4">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div><span className="text-carbon-400">Bot:</span> <span className="text-white">{slackStatus.bot_name}</span></div>
              <div><span className="text-carbon-400">Workspace:</span> <span className="text-white">{slackStatus.team}</span></div>
              <div><span className="text-carbon-400">Canal:</span> <span className="text-white">{slackStatus.channel || 'Todos'}</span></div>
            </div>
          </div>
        )}

        <div className="border-t border-carbon-600 pt-4">
          <h3 className="text-white text-sm font-medium mb-3">Como configurar:</h3>
          <ol className="text-carbon-400 text-sm space-y-2">
            <li>1. Crie um app no <a href="https://api.slack.com/apps" target="_blank" rel="noopener" className="text-indigo-400 hover:underline">Slack API</a></li>
            <li>2. Ative "Event Subscriptions" e aponte para: <code className="bg-carbon-800 px-2 py-0.5 rounded text-green-400">https://SEU-DOMINIO/api/slack/events</code></li>
            <li>3. Adicione os eventos: <code className="bg-carbon-800 px-1 py-0.5 rounded text-yellow-400">message.channels</code></li>
            <li>4. Em "OAuth & Permissions", adicione: <code className="bg-carbon-800 px-1 py-0.5 rounded text-yellow-400">chat:write</code>, <code className="bg-carbon-800 px-1 py-0.5 rounded text-yellow-400">users:read</code>, <code className="bg-carbon-800 px-1 py-0.5 rounded text-yellow-400">users:read.email</code></li>
            <li>5. Configure no <code className="bg-carbon-800 px-2 py-0.5 rounded text-green-400">.env</code>:</li>
          </ol>
          <pre className="bg-carbon-800 rounded-lg p-3 mt-2 text-sm text-green-400 overflow-x-auto">
{`SLACK_BOT_TOKEN=xoxb-seu-token-aqui
SLACK_SIGNING_SECRET=seu-signing-secret
SLACK_SUPPORT_CHANNEL=C0XXXXXXX`}
          </pre>
        </div>
      </div>

      {/* Gmail */}
      <div className="bg-carbon-700 rounded-xl p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-red-600/20 rounded-xl flex items-center justify-center">
              <i className="fas fa-envelope text-2xl text-red-400" />
            </div>
            <div>
              <h2 className="text-white font-semibold text-lg">Gmail</h2>
              <p className="text-carbon-400 text-sm">Receba e responda tickets por email</p>
            </div>
          </div>
          <StatusBadge status={gmailStatus} />
        </div>

        {gmailStatus?.connected && (
          <div className="bg-carbon-800 rounded-lg p-4 mb-4">
            <div className="flex items-center justify-between">
              <div className="text-sm">
                <span className="text-carbon-400">Email:</span>
                <span className="text-white ml-2">{gmailStatus.email}</span>
              </div>
              <button
                onClick={handleFetchEmails}
                disabled={fetching}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm transition disabled:opacity-50"
              >
                <i className={`fas ${fetching ? 'fa-spinner animate-spin' : 'fa-sync'} mr-2`} />
                {fetching ? 'Buscando...' : 'Buscar Emails Agora'}
              </button>
            </div>
            {fetchResult && !fetchResult.error && (
              <div className="mt-3 text-sm text-green-400">
                <i className="fas fa-check mr-1" />
                {fetchResult.fetched} email(s) encontrado(s), {fetchResult.created} ticket(s) criado(s), {fetchResult.updated} atualizado(s)
              </div>
            )}
            {fetchResult?.error && (
              <div className="mt-3 text-sm text-red-400">
                <i className="fas fa-times mr-1" />{fetchResult.error}
              </div>
            )}
          </div>
        )}

        {!gmailStatus?.connected && gmailStatus?.configured && !gmailStatus?.has_refresh_token && (
          <div className="bg-carbon-800 rounded-lg p-4 mb-4">
            <p className="text-yellow-400 text-sm mb-3">Falta autorizar o acesso ao Gmail.</p>
            <button
              onClick={handleGmailAuth}
              className="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg text-sm transition"
            >
              <i className="fab fa-google mr-2" />Autorizar Gmail
            </button>
          </div>
        )}

        <div className="border-t border-carbon-600 pt-4">
          <h3 className="text-white text-sm font-medium mb-3">Como configurar:</h3>
          <ol className="text-carbon-400 text-sm space-y-2">
            <li>1. Crie um projeto no <a href="https://console.cloud.google.com" target="_blank" rel="noopener" className="text-indigo-400 hover:underline">Google Cloud Console</a></li>
            <li>2. Ative a API do Gmail</li>
            <li>3. Crie credenciais OAuth 2.0 (tipo "Web Application")</li>
            <li>4. Adicione redirect URI: <code className="bg-carbon-800 px-2 py-0.5 rounded text-green-400">http://localhost:8000/api/gmail/callback</code></li>
            <li>5. Configure no <code className="bg-carbon-800 px-2 py-0.5 rounded text-green-400">.env</code>:</li>
          </ol>
          <pre className="bg-carbon-800 rounded-lg p-3 mt-2 text-sm text-green-400 overflow-x-auto">
{`GMAIL_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=seu-client-secret
GMAIL_SUPPORT_EMAIL=suporte@carbonsmartwatch.com.br`}
          </pre>
          <p className="text-carbon-400 text-sm mt-3">
            6. Clique em "Autorizar Gmail" acima, faça login, e copie o <code className="text-yellow-400">refresh_token</code> retornado para o <code className="text-green-400">.env</code> como <code className="text-yellow-400">GMAIL_REFRESH_TOKEN</code>.
          </p>
        </div>
      </div>

      {/* Claude AI */}
      <div className="bg-carbon-700 rounded-xl p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-orange-600/20 rounded-xl flex items-center justify-center">
              <i className="fas fa-brain text-2xl text-orange-400" />
            </div>
            <div>
              <h2 className="text-white font-semibold text-lg">Claude AI</h2>
              <p className="text-carbon-400 text-sm">Triagem automática e sugestões de resposta</p>
            </div>
          </div>
          <StatusBadge status={aiStatus} />
        </div>

        {aiStatus?.connected && (
          <div className="bg-carbon-800 rounded-lg p-4 mb-4">
            <div className="text-sm">
              <span className="text-carbon-400">Modelo:</span>
              <span className="text-white ml-2">{aiStatus.model}</span>
            </div>
            <div className="mt-2 text-carbon-400 text-sm">
              <i className="fas fa-check-circle text-green-400 mr-1" />
              Triagem automática ativa em novos tickets
            </div>
          </div>
        )}

        <div className="border-t border-carbon-600 pt-4">
          <h3 className="text-white text-sm font-medium mb-3">Funcionalidades:</h3>
          <ul className="text-carbon-400 text-sm space-y-2">
            <li><i className="fas fa-tag text-orange-400 mr-2" />Classificação automática de categoria</li>
            <li><i className="fas fa-exclamation-circle text-red-400 mr-2" />Detecção de prioridade e risco jurídico</li>
            <li><i className="fas fa-smile text-yellow-400 mr-2" />Análise de sentimento do cliente</li>
            <li><i className="fas fa-lightbulb text-indigo-400 mr-2" />Sugestão de resposta baseada na KB</li>
          </ul>

          <h3 className="text-white text-sm font-medium mb-3 mt-4">Como configurar:</h3>
          <ol className="text-carbon-400 text-sm space-y-2">
            <li>1. Obtenha uma API key em <a href="https://console.anthropic.com" target="_blank" rel="noopener" className="text-indigo-400 hover:underline">console.anthropic.com</a></li>
            <li>2. Configure no <code className="bg-carbon-800 px-2 py-0.5 rounded text-green-400">.env</code>:</li>
          </ol>
          <pre className="bg-carbon-800 rounded-lg p-3 mt-2 text-sm text-green-400 overflow-x-auto">
{`ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui`}
          </pre>
        </div>
      </div>

      {/* WhatsApp Business */}
      <div className="bg-carbon-700 rounded-xl p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-green-600/20 rounded-xl flex items-center justify-center">
              <i className="fab fa-whatsapp text-2xl text-green-400" />
            </div>
            <div>
              <h2 className="text-white font-semibold text-lg">WhatsApp Business</h2>
              <p className="text-carbon-400 text-sm">Atendimento automático por IA via WhatsApp</p>
            </div>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            metaStatus?.whatsapp?.configured
              ? 'bg-green-500/20 text-green-400'
              : 'bg-carbon-600 text-carbon-400'
          }`}>
            <i className={`fas ${metaStatus?.whatsapp?.configured ? 'fa-check-circle' : 'fa-times-circle'} mr-1`} />
            {metaStatus?.whatsapp?.configured ? 'Configurado' : 'Não Configurado'}
          </span>
        </div>
        <div className="border-t border-carbon-600 pt-4">
          <h3 className="text-white text-sm font-medium mb-3">Como configurar:</h3>
          <ol className="text-carbon-400 text-sm space-y-2">
            <li>1. Acesse o <a href="https://developers.facebook.com" target="_blank" rel="noopener" className="text-indigo-400 hover:underline">Meta for Developers</a></li>
            <li>2. Configure o WhatsApp Business Cloud API no seu App</li>
            <li>3. Registre o webhook: <code className="bg-carbon-800 px-2 py-0.5 rounded text-green-400">https://SEU-DOMINIO/api/meta/webhook</code></li>
            <li>4. Configure no <code className="bg-carbon-800 px-2 py-0.5 rounded text-green-400">.env</code>:</li>
          </ol>
          <pre className="bg-carbon-800 rounded-lg p-3 mt-2 text-sm text-green-400 overflow-x-auto">
{`META_APP_SECRET=seu-app-secret
META_VERIFY_TOKEN=seu-token-verificacao
META_WHATSAPP_TOKEN=seu-whatsapp-token
META_WHATSAPP_PHONE_ID=seu-phone-number-id`}
          </pre>
        </div>
      </div>

      {/* Instagram */}
      <div className="bg-carbon-700 rounded-xl p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-pink-600/20 rounded-xl flex items-center justify-center">
              <i className="fab fa-instagram text-2xl text-pink-400" />
            </div>
            <div>
              <h2 className="text-white font-semibold text-lg">Instagram Direct</h2>
              <p className="text-carbon-400 text-sm">Mensagens do Instagram respondidas por IA</p>
            </div>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            metaStatus?.instagram?.configured
              ? 'bg-green-500/20 text-green-400'
              : 'bg-carbon-600 text-carbon-400'
          }`}>
            <i className={`fas ${metaStatus?.instagram?.configured ? 'fa-check-circle' : 'fa-times-circle'} mr-1`} />
            {metaStatus?.instagram?.configured ? 'Configurado' : 'Não Configurado'}
          </span>
        </div>
        <div className="border-t border-carbon-600 pt-4">
          <p className="text-carbon-400 text-sm">Usa o mesmo Meta Page Access Token do Facebook. Configure a Page no Meta Business Suite e vincule sua conta do Instagram.</p>
          <pre className="bg-carbon-800 rounded-lg p-3 mt-2 text-sm text-green-400 overflow-x-auto">
{`META_PAGE_ACCESS_TOKEN=seu-page-access-token`}
          </pre>
        </div>
      </div>

      {/* Facebook Messenger */}
      <div className="bg-carbon-700 rounded-xl p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center">
              <i className="fab fa-facebook-messenger text-2xl text-blue-400" />
            </div>
            <div>
              <h2 className="text-white font-semibold text-lg">Facebook Messenger</h2>
              <p className="text-carbon-400 text-sm">Mensagens do Messenger respondidas por IA</p>
            </div>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            metaStatus?.facebook?.configured
              ? 'bg-green-500/20 text-green-400'
              : 'bg-carbon-600 text-carbon-400'
          }`}>
            <i className={`fas ${metaStatus?.facebook?.configured ? 'fa-check-circle' : 'fa-times-circle'} mr-1`} />
            {metaStatus?.facebook?.configured ? 'Configurado' : 'Não Configurado'}
          </span>
        </div>
        <div className="border-t border-carbon-600 pt-4">
          <p className="text-carbon-400 text-sm">Usa o mesmo Page Access Token e webhook do Instagram. Ambos são gerenciados pela mesma Facebook Page.</p>
        </div>
      </div>
    </div>
  )
}
