import React, { useState, useEffect } from 'react'
import { getArticles } from '../services/api'

import { CATEGORY_LABELS } from '../constants/ticket'
const CATEGORIES = Object.keys(CATEGORY_LABELS)

export default function KBPage() {
  const [articles, setArticles] = useState([])
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    loadArticles()
  }, [category])

  const loadArticles = async () => {
    try {
      const { data } = await getArticles({ category: category || undefined, search: search || undefined })
      setArticles(data)
    } catch (e) {
      console.error('Failed to load KB articles:', e)
    }
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-4">Base de Conhecimento</h1>

      <div className="flex gap-3 mb-6">
        <form onSubmit={(e) => { e.preventDefault(); loadArticles() }} className="flex gap-2 flex-1">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar artigos..."
            className="flex-1 bg-carbon-700 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
          />
          <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm">
            <i className="fas fa-search" />
          </button>
        </form>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="bg-carbon-700 border border-carbon-600 rounded-lg px-3 py-2 text-white text-sm"
        >
          <option value="">Todas categorias</option>
          {CATEGORIES.map(c => <option key={c} value={c}>{CATEGORY_LABELS[c] || c}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {articles.map(article => (
          <div
            key={article.id}
            onClick={() => setSelected(selected?.id === article.id ? null : article)}
            className={`bg-carbon-700 rounded-xl p-4 cursor-pointer transition border
              ${selected?.id === article.id ? 'border-indigo-500' : 'border-transparent hover:border-carbon-500'}`}
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="text-white font-medium text-sm">{article.title}</h3>
              <span className="bg-carbon-600 text-carbon-300 px-2 py-0.5 rounded text-xs">{CATEGORY_LABELS[article.category] || article.category}</span>
            </div>
            <p className="text-carbon-400 text-sm line-clamp-3">{article.content}</p>
            {selected?.id === article.id && (
              <div className="mt-3 pt-3 border-t border-carbon-600">
                <p className="text-carbon-200 text-sm whitespace-pre-wrap">{article.content}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {articles.length === 0 && (
        <div className="text-center text-carbon-400 py-12">
          <i className="fas fa-book text-4xl mb-3" /><br />
          Nenhum artigo encontrado
        </div>
      )}
    </div>
  )
}
