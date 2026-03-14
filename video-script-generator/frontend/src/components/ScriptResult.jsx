import React, { useState } from 'react'
import { Copy, RefreshCw, Star, Check, MessageSquare, Film, Clock, Lightbulb, Type, Image } from 'lucide-react'
import { rateScript } from '../services/api'

export default function ScriptResult({ script, onRefine, generating }) {
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [showRefine, setShowRefine] = useState(false)
  const [rating, setRating] = useState(script.rating || 0)

  const copyScript = () => {
    navigator.clipboard.writeText(script.script_content || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRate = async (value) => {
    setRating(value)
    try {
      await rateScript(script.id, { rating: value })
    } catch {}
  }

  const handleRefine = () => {
    if (!feedback.trim()) return
    onRefine(feedback)
    setFeedback('')
    setShowRefine(false)
  }

  const metadata = script.metadata || {}

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
              <Film className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900">{script.title}</h3>
              <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5">
                <span className="px-2 py-0.5 rounded-full bg-gray-100 font-medium uppercase">{script.script_type}</span>
                {script.duration_seconds && (
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {script.duration_seconds}s</span>
                )}
                {script.version > 1 && <span>v{script.version}</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Rating */}
            <div className="flex items-center gap-0.5">
              {[1, 2, 3, 4, 5].map(v => (
                <button key={v} onClick={() => handleRate(v)} className="p-0.5">
                  <Star className={`w-4 h-4 ${v <= rating ? 'fill-carbon-500 text-carbon-500' : 'text-gray-300'}`} />
                </button>
              ))}
            </div>

            <button onClick={copyScript} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm text-gray-700 transition-colors">
              {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copiado!' : 'Copiar'}
            </button>
          </div>
        </div>
      </div>

      {/* Script Content */}
      <div className="p-6">
        <div className="prose prose-sm max-w-none">
          <div className="bg-gray-50 rounded-xl p-5 whitespace-pre-wrap text-sm text-gray-800 leading-relaxed font-mono">
            {script.script_content}
          </div>
        </div>
      </div>

      {/* Scenes (if any) */}
      {script.scenes && Array.isArray(script.scenes) && script.scenes.length > 0 && (
        <div className="px-6 pb-6">
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Film className="w-4 h-4" /> Cenas
          </h4>
          <div className="space-y-3">
            {script.scenes.map((scene, i) => (
              <div key={i} className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-6 h-6 rounded-full bg-carbon-500 text-white text-xs flex items-center justify-center font-bold">
                    {scene.scene || i + 1}
                  </span>
                  {scene.timestamp && <span className="text-xs text-gray-500 font-mono">{scene.timestamp}</span>}
                  {scene.duration && <span className="text-xs text-gray-400">({scene.duration})</span>}
                </div>
                {scene.visual && (
                  <p className="text-xs text-gray-500 mb-1"><span className="font-semibold">Visual:</span> {scene.visual}</p>
                )}
                {scene.dialogue && (
                  <p className="text-sm text-gray-800"><span className="font-semibold text-gray-500 text-xs">Fala:</span> {scene.dialogue}</p>
                )}
                {scene.text_overlay && (
                  <p className="text-xs text-carbon-600 mt-1"><span className="font-semibold">Texto na tela:</span> {scene.text_overlay}</p>
                )}
                {scene.audio_note && (
                  <p className="text-xs text-gray-400 mt-1"><span className="font-semibold">Audio:</span> {scene.audio_note}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hook Options */}
      {script.hook_options && script.hook_options.length > 0 && (
        <div className="px-6 pb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
            <Lightbulb className="w-4 h-4" /> Opcoes de Hook
          </h4>
          <div className="space-y-2">
            {script.hook_options.map((hook, i) => (
              <div key={i} className="flex items-start gap-2 bg-yellow-50 rounded-lg px-3 py-2 text-sm">
                <span className="text-carbon-600 font-bold">{i + 1}.</span>
                <span className="text-gray-700">{hook}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CTA Options */}
      {script.cta_options && script.cta_options.length > 0 && (
        <div className="px-6 pb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
            <Type className="w-4 h-4" /> Opcoes de CTA
          </h4>
          <div className="flex flex-wrap gap-2">
            {script.cta_options.map((cta, i) => (
              <span key={i} className="bg-green-50 text-green-700 px-3 py-1.5 rounded-lg text-sm">{cta}</span>
            ))}
          </div>
        </div>
      )}

      {/* Thumbnail Suggestions */}
      {script.thumbnail_suggestions && script.thumbnail_suggestions.length > 0 && (
        <div className="px-6 pb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
            <Image className="w-4 h-4" /> Sugestoes de Thumbnail
          </h4>
          <div className="space-y-1">
            {script.thumbnail_suggestions.map((thumb, i) => (
              <p key={i} className="text-sm text-gray-600 bg-purple-50 px-3 py-1.5 rounded-lg">{thumb}</p>
            ))}
          </div>
        </div>
      )}

      {/* Ad Copy (meta_ad type) */}
      {metadata.ad_copy && (
        <div className="px-6 pb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Copy do Anuncio</h4>
          <div className="bg-blue-50 rounded-xl p-4 space-y-2 text-sm">
            <p><span className="font-semibold text-blue-700">Texto principal:</span> {metadata.ad_copy.primary_text}</p>
            <p><span className="font-semibold text-blue-700">Titulo:</span> {metadata.ad_copy.headline}</p>
            <p><span className="font-semibold text-blue-700">Descricao:</span> {metadata.ad_copy.description}</p>
          </div>
        </div>
      )}

      {/* Customer Insights Used */}
      {script.customer_insights && script.customer_insights.total_tickets_analyzed > 0 && (
        <div className="px-6 pb-4">
          <div className="bg-carbon-50 rounded-xl px-4 py-3 flex items-center gap-2 text-sm text-carbon-700">
            <Lightbulb className="w-4 h-4 flex-shrink-0" />
            Roteiro gerado com base em {script.customer_insights.total_tickets_analyzed} tickets reais do helpdesk
          </div>
        </div>
      )}

      {/* Refine */}
      <div className="px-6 pb-6">
        {!showRefine ? (
          <button
            onClick={() => setShowRefine(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Refinar este roteiro
          </button>
        ) : (
          <div className="space-y-3">
            <textarea
              value={feedback}
              onChange={e => setFeedback(e.target.value)}
              placeholder="Descreva o que quer mudar... Ex: 'Mais urgencia no hook', 'CTA mais direto', 'Tom mais casual'"
              rows={3}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-carbon-500 focus:border-carbon-500 text-sm"
            />
            <div className="flex gap-2">
              <button
                onClick={handleRefine}
                disabled={generating || !feedback.trim()}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-carbon-500 text-white font-medium text-sm hover:bg-carbon-600 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} />
                {generating ? 'Refinando...' : 'Refinar'}
              </button>
              <button
                onClick={() => { setShowRefine(false); setFeedback('') }}
                className="px-4 py-2 rounded-xl text-sm text-gray-600 hover:bg-gray-100"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
