import React, { useState, useRef, useEffect } from 'react'
import api from '../services/api'

const SUGGESTED_QUESTIONS = [
  'Qual o prazo de garantia dos relógios Carbon?',
  'Como proceder com um pedido de troca?',
  'Quais são os passos para um caso de PROCON?',
  'Como identificar mau uso vs defeito de fábrica?',
  'Qual o processo de chargeback?',
  'Como funciona o reenvio de produto?',
  'Quais problemas comuns com carregadores?',
  'Como escalar um ticket para o jurídico?',
]

export default function AssistantPage({ user }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `Olá ${user?.name?.split(' ')[0] || ''}! Sou o assistente da Carbon. Posso te ajudar com processos, políticas, playbooks e dúvidas sobre atendimento. O que precisa?`,
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return

    const userMsg = { role: 'user', content: text.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const { data } = await api.post('/ai/assistant', {
        message: text.trim(),
        history: messages.slice(-10).map(m => ({ role: m.role, content: m.content })),
      })
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
    } catch (e) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Desculpe, houve um erro ao processar sua pergunta. Tente novamente.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    sendMessage(input)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600/20 flex items-center justify-center">
            <i className="fas fa-robot text-indigo-400 text-lg" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-[var(--text-primary)]">Assistente Carbon</h1>
            <p className="text-[var(--text-secondary)] text-xs">IA treinada com processos, políticas e playbooks da empresa</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-md'
                  : 'bg-[var(--bg-secondary)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-bl-md'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-2 mb-1.5">
                  <i className="fas fa-robot text-indigo-400 text-xs" />
                  <span className="text-indigo-400 text-xs font-medium">Assistente</span>
                </div>
              )}
              <div className="whitespace-pre-wrap">{msg.content}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-2">
                <i className="fas fa-robot text-indigo-400 text-xs" />
                <span className="text-indigo-400 text-xs font-medium">Assistente</span>
              </div>
              <div className="flex gap-1 mt-2">
                <span className="w-2 h-2 bg-[var(--text-tertiary)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-[var(--text-tertiary)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-[var(--text-tertiary)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions (only if no user messages yet) */}
      {messages.length <= 1 && (
        <div className="px-4 pb-3">
          <p className="text-[var(--text-tertiary)] text-xs mb-2">Sugestões:</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q)}
                className="bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs px-3 py-1.5 rounded-full border border-[var(--border-color)] transition"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-[var(--border-color)]">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Pergunte sobre processos, políticas, playbooks..."
            className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl px-4 py-3 text-[var(--text-primary)] text-sm focus:outline-none focus:border-indigo-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-3 rounded-xl text-sm font-medium disabled:opacity-50 transition"
          >
            <i className="fas fa-paper-plane" />
          </button>
        </form>
      </div>
    </div>
  )
}
