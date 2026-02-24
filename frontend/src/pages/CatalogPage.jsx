import React, { useState, useEffect } from 'react'
import { getProducts } from '../services/api'

const CATS = [
  { id: '', label: 'Todos', icon: 'fa-th' },
  { id: 'smartwatch', label: 'Relógios', icon: 'fa-clock' },
  { id: 'acessorio', label: 'Acessórios', icon: 'fa-plug' },
]

export default function CatalogPage() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    setLoading(true)
    getProducts(category || undefined)
      .then(r => setProducts(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [category])

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white"><i className="fas fa-box-open mr-3 text-cyan-400" />Catálogo de Produtos</h1>
        <p className="text-carbon-400 text-sm mt-1">Consulta rápida de especificações, preços e problemas comuns</p>
      </div>

      {/* Category filter */}
      <div className="flex gap-1.5 bg-carbon-800 rounded-xl p-1.5 mb-6 w-fit">
        {CATS.map(c => (
          <button key={c.id} onClick={() => { setCategory(c.id); setSelected(null) }}
            className={`px-4 py-1.5 rounded-lg text-xs font-medium transition ${category === c.id ? 'bg-cyan-600/20 text-cyan-400' : 'text-carbon-400 hover:text-white hover:bg-carbon-700'}`}>
            <i className={`fas ${c.icon} mr-1.5`} />{c.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-20"><i className="fas fa-spinner animate-spin text-cyan-400 text-2xl" /></div>
      ) : (
        <div className="flex gap-6">
          {/* Product grid */}
          <div className={`grid ${selected ? 'grid-cols-1 w-72' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 flex-1'} gap-4`}>
            {products.map(p => (
              <div key={p.id} onClick={() => setSelected(selected?.id === p.id ? null : p)}
                className={`bg-carbon-700 rounded-xl overflow-hidden border transition cursor-pointer ${
                  selected?.id === p.id ? 'border-cyan-500 ring-1 ring-cyan-500/30' : 'border-carbon-600 hover:border-cyan-500/30'
                }`}>
                <div className="h-32 bg-carbon-800 flex items-center justify-center" style={{ background: p.color || '#1a1a2e' }}>
                  <i className={`fas ${p.category === 'smartwatch' ? 'fa-clock' : 'fa-plug'} text-4xl text-white/20`} />
                </div>
                <div className="p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-white font-semibold text-sm">{p.name}</p>
                    <span className="text-cyan-400 font-bold text-sm">R$ {p.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                      p.status === 'active' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
                    }`}>
                      {p.status === 'active' ? 'Ativo' : 'Inativo'}
                    </span>
                    <span className="text-carbon-400 text-xs">{p.category === 'smartwatch' ? 'Relógio' : 'Acessório'}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Detail panel */}
          {selected && (
            <div className="flex-1 bg-carbon-700 rounded-xl border border-carbon-600 p-6 min-w-[400px]">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-white text-xl font-bold">{selected.name}</h2>
                <button onClick={() => setSelected(null)} className="text-carbon-400 hover:text-white transition">
                  <i className="fas fa-times" />
                </button>
              </div>

              <div className="text-cyan-400 text-2xl font-bold mb-6">R$ {selected.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>

              {/* Specs */}
              <div className="mb-6">
                <h3 className="text-carbon-300 text-xs font-semibold uppercase tracking-wider mb-3">
                  <i className="fas fa-microchip mr-2 text-cyan-400" />Especificações
                </h3>
                <div className="space-y-2">
                  {Object.entries(selected.specs || {}).map(([key, val]) => (
                    <div key={key} className="flex items-start gap-3 bg-carbon-800 rounded-lg px-3 py-2">
                      <span className="text-carbon-400 text-xs capitalize min-w-[90px]">{key}</span>
                      <span className="text-white text-xs">{val}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Common issues */}
              {selected.common_issues?.length > 0 && (
                <div>
                  <h3 className="text-carbon-300 text-xs font-semibold uppercase tracking-wider mb-3">
                    <i className="fas fa-exclamation-triangle mr-2 text-amber-400" />Problemas Comuns
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selected.common_issues.map((issue, i) => (
                      <span key={i} className="px-3 py-1 bg-amber-500/10 text-amber-400 rounded-full text-xs">
                        {issue}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Copy product info */}
              <button onClick={() => {
                const info = `${selected.name} - R$ ${selected.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}\n${Object.entries(selected.specs || {}).map(([k,v]) => `${k}: ${v}`).join('\n')}`
                navigator.clipboard.writeText(info)
              }}
                className="mt-6 w-full bg-cyan-600/20 text-cyan-400 hover:bg-cyan-600/40 py-2.5 rounded-xl text-sm transition">
                <i className="fas fa-copy mr-2" />Copiar Informações
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
