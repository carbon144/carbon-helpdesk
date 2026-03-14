import React, { useState, useEffect } from 'react'
import { Wand2, Loader2, Copy, RefreshCw, Star, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import { getOptions, generateScript, refineScript, rateScript } from '../services/api'
import ScriptResult from '../components/ScriptResult'

const DURATION_LABELS = { 15: '15s (Story)', 30: '30s (Reels)', 45: '45s', 60: '1min', 90: '1min30' }

export default function GeneratorPage() {
  const [options, setOptions] = useState(null)
  const [brief, setBrief] = useState({
    title: '',
    product_name: '',
    product_description: '',
    objective: '',
    target_audience: '',
    tone: 'conversacional',
    script_type: 'teleprompter',
    duration_seconds: 30,
    additional_notes: '',
    use_customer_insights: true,
    tags: [],
  })
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    getOptions().then(r => setOptions(r.data)).catch(() => {})
  }, [])

  const handleGenerate = async () => {
    if (!brief.title || !brief.product_name) {
      setError('Preencha pelo menos o titulo e o nome do produto')
      return
    }
    setGenerating(true)
    setError(null)
    setResult(null)
    try {
      const { data } = await generateScript(brief)
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao gerar roteiro')
    } finally {
      setGenerating(false)
    }
  }

  const handleRefine = async (feedback) => {
    if (!result?.id) return
    setGenerating(true)
    setError(null)
    try {
      const { data } = await refineScript(result.id, { feedback })
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao refinar roteiro')
    } finally {
      setGenerating(false)
    }
  }

  const scriptTypes = options?.script_types || {
    teleprompter: 'Teleprompter',
    ugc: 'UGC',
    founder_ad: 'Founder Ad',
    meta_ad: 'Meta Ad Completo',
  }

  const toneOptions = options?.tone_options || [
    'urgente', 'conversacional', 'autoritario', 'emocional',
    'humoristico', 'educativo', 'aspiracional', 'direto',
  ]

  return (
    <div className="space-y-6">
      {/* Brief Form */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-carbon-100 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-carbon-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Novo Roteiro</h2>
              <p className="text-sm text-gray-500">Preencha o brief e o AI gera o roteiro</p>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-5">
          {/* Tipo de roteiro */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Tipo de Roteiro</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {Object.entries(scriptTypes).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setBrief(b => ({ ...b, script_type: key }))}
                  className={`px-4 py-3 rounded-xl text-sm font-medium border-2 transition-all ${
                    brief.script_type === key
                      ? 'border-carbon-500 bg-carbon-50 text-carbon-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Titulo + Produto */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Titulo do Video *</label>
              <input
                type="text"
                value={brief.title}
                onChange={e => setBrief(b => ({ ...b, title: e.target.value }))}
                placeholder="Ex: Por que esse serum e diferente"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-carbon-500 focus:border-carbon-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Produto *</label>
              <input
                type="text"
                value={brief.product_name}
                onChange={e => setBrief(b => ({ ...b, product_name: e.target.value }))}
                placeholder="Nome do produto"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-carbon-500 focus:border-carbon-500 text-sm"
              />
            </div>
          </div>

          {/* Descricao do produto */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Descricao do Produto</label>
            <textarea
              value={brief.product_description}
              onChange={e => setBrief(b => ({ ...b, product_description: e.target.value }))}
              placeholder="Descreva o produto, beneficios, diferenciais..."
              rows={3}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-carbon-500 focus:border-carbon-500 text-sm"
            />
          </div>

          {/* Objetivo */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Objetivo do Video</label>
            <input
              type="text"
              value={brief.objective}
              onChange={e => setBrief(b => ({ ...b, objective: e.target.value }))}
              placeholder="Ex: Gerar vendas diretas, aumentar awareness, educar sobre o produto"
              className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-carbon-500 focus:border-carbon-500 text-sm"
            />
          </div>

          {/* Duracao + Tom */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Duracao</label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(DURATION_LABELS).map(([val, label]) => (
                  <button
                    key={val}
                    onClick={() => setBrief(b => ({ ...b, duration_seconds: parseInt(val) }))}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                      brief.duration_seconds === parseInt(val)
                        ? 'border-carbon-500 bg-carbon-50 text-carbon-700'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Tom</label>
              <div className="flex flex-wrap gap-2">
                {toneOptions.map(t => (
                  <button
                    key={t}
                    onClick={() => setBrief(b => ({ ...b, tone: t }))}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border capitalize transition-all ${
                      brief.tone === t
                        ? 'border-carbon-500 bg-carbon-50 text-carbon-700'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Advanced */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700"
          >
            {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            Opcoes avancadas
          </button>

          {showAdvanced && (
            <div className="space-y-4 pt-2">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Publico-Alvo</label>
                <input
                  type="text"
                  value={brief.target_audience}
                  onChange={e => setBrief(b => ({ ...b, target_audience: e.target.value }))}
                  placeholder="Ex: Mulheres 25-40 anos, classe AB, interessadas em skincare"
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-carbon-500 focus:border-carbon-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Notas Adicionais</label>
                <textarea
                  value={brief.additional_notes}
                  onChange={e => setBrief(b => ({ ...b, additional_notes: e.target.value }))}
                  placeholder="Qualquer info extra que ajude na criacao do roteiro..."
                  rows={2}
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-carbon-500 focus:border-carbon-500 text-sm"
                />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={brief.use_customer_insights}
                  onChange={e => setBrief(b => ({ ...b, use_customer_insights: e.target.checked }))}
                  className="rounded border-gray-300 text-carbon-500 focus:ring-carbon-500"
                />
                <span className="text-sm text-gray-700">Usar insights de clientes do helpdesk</span>
              </label>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 text-red-700 px-4 py-3 rounded-xl text-sm">{error}</div>
          )}

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className={`w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-white transition-all ${
              generating
                ? 'bg-carbon-400 cursor-wait animate-pulse-gold'
                : 'bg-carbon-500 hover:bg-carbon-600 shadow-lg shadow-carbon-500/20'
            }`}
          >
            {generating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Gerando roteiro...
              </>
            ) : (
              <>
                <Wand2 className="w-5 h-5" />
                Gerar Roteiro
              </>
            )}
          </button>
        </div>
      </div>

      {/* Result */}
      {result && (
        <ScriptResult
          script={result}
          onRefine={handleRefine}
          generating={generating}
        />
      )}
    </div>
  )
}
