import { useState, useEffect, useRef, useCallback } from 'react'
import api from '../../services/api'
import { useChatEvents } from '../../hooks/useWebSocket'
import ChatMessageBubble from './ChatMessageBubble'
import ChatInput from './ChatInput'
import TypingIndicator from './TypingIndicator'
import ChannelIcon from './ChannelIcon'
import VoiceCallPlayer from '../tickets/VoiceCallPlayer'
import {
  Bot,
  CheckCircle2,
  UserPlus,
  Loader2,
  MessageSquare,
} from 'lucide-react'

export default function ChatView({ conversation, customer, user, onConversationUpdate }) {
  const [messages, setMessages] = useState([])
  const [agents, setAgents] = useState([])
  const [voiceCalls, setVoiceCalls] = useState([])
  const [loading, setLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [showTransfer, setShowTransfer] = useState(false)
  const messagesEndRef = useRef(null)
  const typingTimeout = useRef(null)
  const convIdRef = useRef(null)

  // Track current conversation id
  useEffect(() => {
    convIdRef.current = conversation?.id || null
  }, [conversation?.id])

  const fetchMessages = useCallback(async () => {
    if (!conversation) return
    setLoading(true)
    try {
      const res = await api.get(`/chat/conversations/${conversation.id}/messages`, {
        params: { limit: 200 },
      })
      setMessages(res.data || [])
    } catch (err) {
      console.error('Failed to fetch messages:', err)
    } finally {
      setLoading(false)
    }
  }, [conversation?.id])

  useEffect(() => { fetchMessages() }, [fetchMessages])

  // Fetch voice calls for conversation
  useEffect(() => {
    if (!conversation) { setVoiceCalls([]); return }
    api.get(`/chat/conversations/${conversation.id}/voice-calls`)
      .then((res) => setVoiceCalls(res.data || []))
      .catch(() => setVoiceCalls([]))
  }, [conversation?.id])

  useEffect(() => {
    api.get('/auth/users').then((res) => setAgents(res.data || [])).catch(() => {})
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  // Real-time chat events via WebSocket
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('carbon_token') : null

  const handleChatEvent = useCallback((data) => {
    if (!convIdRef.current) return

    if (data.event === 'new_message' && data.conversation_id === convIdRef.current) {
      const newMsg = {
        id: data.message_id || `ws-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        conversation_id: data.conversation_id,
        sender_type: data.sender_type,
        sender_id: data.sender_id,
        content_type: data.content_type || 'text',
        content: data.content,
        created_at: data.created_at || new Date().toISOString(),
      }
      setMessages((prev) => {
        if (data.message_id && prev.some(m => m.id === data.message_id)) return prev
        return [...prev, newMsg]
      })

      // Clear typing indicator on new message
      setIsTyping(false)
      if (typingTimeout.current) clearTimeout(typingTimeout.current)
    }

    if (data.event === 'typing' && data.conversation_id === convIdRef.current && data.sender_type === 'contact') {
      setIsTyping(true)
      if (typingTimeout.current) clearTimeout(typingTimeout.current)
      typingTimeout.current = setTimeout(() => setIsTyping(false), 4000)
    }
  }, [])

  useChatEvents(token, handleChatEvent)

  // Fallback: light polling every 30s for any missed messages (only when visible)
  const fetchMessagesRef = useRef(fetchMessages)
  fetchMessagesRef.current = fetchMessages
  useEffect(() => {
    if (!conversation) return
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') fetchMessagesRef.current()
    }, 30000)
    return () => clearInterval(interval)
  }, [conversation?.id])

  const handleSendMessage = useCallback(async (content) => {
    if (!conversation) return
    try {
      const res = await api.post(`/chat/conversations/${conversation.id}/messages`, {
        content,
        content_type: 'text',
      })
      setMessages((prev) => [...prev, res.data])
    } catch (err) {
      console.error('Failed to send message:', err)
    }
  }, [conversation?.id])

  const handleSendNote = useCallback(async (content) => {
    if (!conversation) return
    try {
      const res = await api.post(`/chat/conversations/${conversation.id}/messages`, {
        content,
        content_type: 'note',
      })
      setMessages((prev) => [...prev, res.data])
    } catch (err) {
      console.error('Failed to send note:', err)
    }
  }, [conversation?.id])

  const handleResolve = useCallback(async () => {
    if (!conversation) return
    try {
      await api.put(`/chat/conversations/${conversation.id}/resolve`)
      if (onConversationUpdate) onConversationUpdate({ ...conversation, status: 'resolved' })
    } catch (err) {
      console.error('Failed to resolve:', err)
    }
  }, [conversation, onConversationUpdate])

  const handleAssign = useCallback(async (agentId) => {
    if (!conversation) return
    try {
      await api.put(`/chat/conversations/${conversation.id}/assign?agent_id=${agentId}`)
      if (onConversationUpdate) onConversationUpdate({ ...conversation, assigned_to: agentId })
      setShowTransfer(false)
    } catch (err) {
      console.error('Failed to assign:', err)
    }
  }, [conversation, onConversationUpdate])

  const handleToggleAI = useCallback(async () => {
    if (!conversation) return
    try {
      const res = await api.post(`/chat/conversations/${conversation.id}/toggle-ai`)
      if (onConversationUpdate) onConversationUpdate({ ...conversation, ...res.data })
    } catch (err) {
      console.error('Failed to toggle AI:', err)
    }
  }, [conversation, onConversationUpdate])

  const getAgentName = (msg) => {
    if (msg.sender_type !== 'agent') return null
    const a = agents.find((ag) => ag.id === msg.sender_id)
    return a?.name || 'Atendente'
  }

  if (!conversation) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center" style={{ color: '#52525B' }}>
        <MessageSquare className="w-16 h-16 mb-4" style={{ color: '#3F3F46' }} />
        <p className="text-lg font-medium">Selecione uma conversa</p>
        <p className="text-sm mt-1">Escolha uma conversa na lista ao lado</p>
      </div>
    )
  }

  const contactName = customer?.name || 'Visitante'
  const statusLabel = { open: 'Aberto', pending: 'Pendente', resolved: 'Resolvido', closed: 'Fechado' }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', background: '#1F1F23' }}>
        <div className="flex items-center gap-3">
          {customer?.avatar_url ? (
            <img src={customer.avatar_url} alt={contactName} className="w-9 h-9 rounded-full object-cover" />
          ) : (
            <div className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold"
              style={{ background: '#E5A800', color: '#000' }}>
              {contactName.charAt(0).toUpperCase()}
            </div>
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm" style={{ color: '#E4E4E7' }}>{contactName}</span>
              <ChannelIcon channel={conversation.channel} size="w-3.5 h-3.5" />
              <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                style={{ background: 'rgba(255,255,255,0.06)', color: '#A1A1AA' }}>
                {statusLabel[conversation.status] || conversation.status}
              </span>
            </div>
            {conversation.number && (
              <span className="text-xs font-mono" style={{ color: '#52525B' }}>#{conversation.number}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 relative">
          <button onClick={handleToggleAI}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer"
            style={{
              background: conversation.ai_enabled ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.06)',
              color: conversation.ai_enabled ? '#34D399' : '#71717A',
            }}
            title={conversation.ai_enabled ? 'IA ativa' : 'IA desativada'}>
            <Bot className="w-3.5 h-3.5" />
            {conversation.ai_enabled ? 'IA Ativa' : 'IA Off'}
          </button>

          {conversation.status !== 'resolved' && (
            <button onClick={handleResolve}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition cursor-pointer"
              style={{ background: 'rgba(16,185,129,0.15)', color: '#34D399' }}>
              <CheckCircle2 className="w-4 h-4" />
              Resolver
            </button>
          )}

          <div className="relative">
            <button onClick={() => setShowTransfer(!showTransfer)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition cursor-pointer"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#A1A1AA' }}>
              <UserPlus className="w-4 h-4" />
              Transferir
            </button>
            {showTransfer && (
              <div className="absolute right-0 top-full mt-1 w-56 rounded-lg shadow-lg z-20"
                style={{ background: '#27272A', border: '1px solid rgba(255,255,255,0.1)' }}>
                <div className="p-2">
                  <p className="text-xs font-medium px-2 py-1" style={{ color: '#71717A' }}>Transferir para:</p>
                  {agents
                    .filter((a) => a.id !== user?.id && a.is_active)
                    .map((a) => (
                      <button key={a.id} onClick={() => handleAssign(a.id)}
                        className="w-full text-left px-2 py-1.5 text-sm rounded cursor-pointer transition"
                        style={{ color: '#E4E4E7' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.06)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        {a.name}
                        <span className={`ml-2 text-xs ${a.status === 'online' ? 'text-green-400' : 'text-zinc-500'}`}>
                          {a.status || 'offline'}
                        </span>
                      </button>
                    ))}
                  {agents.filter((a) => a.id !== user?.id && a.is_active).length === 0 && (
                    <p className="text-xs px-2 py-1" style={{ color: '#52525B' }}>Nenhum outro atendente</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4" style={{ background: '#18181B' }}>
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#52525B' }} />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full" style={{ color: '#3F3F46' }}>
            <MessageSquare className="w-10 h-10 mb-2" />
            <p className="text-sm">Nenhuma mensagem ainda</p>
          </div>
        ) : (
          <>
            {voiceCalls.length > 0 && (
              <div className="px-4 pb-2">
                {voiceCalls.map((vc) => (
                  <VoiceCallPlayer key={vc.id} voiceCall={vc} />
                ))}
              </div>
            )}
            {messages.map((msg) => (
              <ChatMessageBubble key={msg.id} message={msg} agentName={getAgentName(msg)} />
            ))}
            {isTyping && <TypingIndicator />}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <ChatInput
        onSendMessage={handleSendMessage}
        onSendNote={handleSendNote}
        disabled={conversation.status === 'resolved' || conversation.status === 'closed'}
      />
    </div>
  )
}
