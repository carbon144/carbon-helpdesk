import React, { useState } from 'react'
import { Search, Lightbulb, Loader2, MessageSquare, AlertTriangle, ThumbsUp, HelpCircle } from 'lucide-react'
import { getCustomerInsights } from '../services/api'

export default function InsightsPage() {
  const [productName, setProductName] = useState('')
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const handleSearch = async (e) => {
    e?.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { data: result } = await getCustomerInsights(productName || undefined)
      setData(result)
    } catch (e) {
      setError('Erro ao buscar insights. Verifique a conexao com o helpdesk.')
    }
    setLoading(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Insights dos Clientes</h2>
        <p className="text-sm text-gray-500">Dados reais dos tickets do helpdesk para informar seus roteiros</p>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={productName}
            onChange={e => setProductName(e.target.value)}
            placeholder="Nome do produto (ou vazio para todos)"
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-carbon-500 focus:border-carbon-500 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-carbon-500 text-white font-medium text-sm hover:bg-carbon-600 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lightbulb className="w-4 h-4" />}
          Buscar Insights
        </button>
      </form>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-xl text-sm">{error}</div>
      )}

      {data && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="bg-carbon-50 rounded-xl p-4 flex items-center gap-3">
            <Lightbulb className="w-5 h-5 text-carbon-600" />
            <span className="text-sm text-carbon-700">
              Analisados <strong>{data.insights?.total_tickets_analyzed || 0}</strong> tickets
              {data.insights?.product_filter && <> filtrados por <strong>{data.insights.product_filter}</strong></>}
            </span>
          </div>

          {/* AI Summary */}
          {data.summary && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-carbon-500" />
                Resumo AI
              </h3>
              <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                {data.summary}
              </div>
            </div>
          )}

          {/* Raw subjects */}
          {data.insights?.subjects?.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-blue-500" />
                Assuntos dos Tickets ({data.insights.subjects.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {data.insights.subjects.slice(0, 30).map((s, i) => (
                  <span key={i} className="bg-blue-50 text-blue-700 px-3 py-1 rounded-lg text-xs">{s}</span>
                ))}
              </div>
            </div>
          )}

          {/* Customer messages */}
          {data.insights?.customer_messages?.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-green-500" />
                Mensagens de Clientes (exemplos reais)
              </h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {data.insights.customer_messages.slice(0, 20).map((msg, i) => (
                  <div key={i} className="bg-gray-50 rounded-lg px-4 py-3 text-sm text-gray-700">
                    {msg}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!data && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Lightbulb className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Busque insights dos clientes para criar roteiros mais autenticos.</p>
          <p className="text-gray-400 text-xs mt-1">Os dados vem dos tickets reais do helpdesk da Carbon.</p>
        </div>
      )}
    </div>
  )
}

function Sparkles({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="M5 3v4" /><path d="M19 17v4" /><path d="M3 5h4" /><path d="M17 19h4" />
    </svg>
  )
}
