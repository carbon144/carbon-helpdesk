function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

export default function ChatMessageBubble({ message, agentName }) {
  const { sender_type, content, content_type, created_at } = message
  const time = formatTime(created_at)
  const isNote = content_type === 'note'
  const isSystem = sender_type === 'system'
  const isAgent = sender_type === 'agent'
  const isBot = sender_type === 'bot'

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className="rounded-full px-4 py-1.5 text-xs max-w-md text-center"
          style={{ background: 'rgba(255,255,255,0.06)', color: '#71717A' }}>
          {content}
          <span className="ml-2" style={{ color: '#52525B' }}>{time}</span>
        </div>
      </div>
    )
  }

  if (isNote) {
    return (
      <div className="flex justify-end my-1 px-4">
        <div className="max-w-[70%] rounded-2xl rounded-br-md px-4 py-2.5"
          style={{ background: 'rgba(229,168,0,0.1)', border: '1px solid rgba(229,168,0,0.3)' }}>
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-[10px] font-medium uppercase tracking-wide" style={{ color: '#E5A800' }}>Nota interna</span>
          </div>
          <p className="text-sm whitespace-pre-wrap break-words" style={{ color: '#E4E4E7' }}>{content}</p>
          <div className="flex items-center justify-end gap-1 mt-1">
            {agentName && <span className="text-[10px]" style={{ color: 'rgba(229,168,0,0.6)' }}>{agentName}</span>}
            <span className="text-[10px]" style={{ color: 'rgba(229,168,0,0.4)' }}>{time}</span>
          </div>
        </div>
      </div>
    )
  }

  if (isAgent || isBot) {
    return (
      <div className="flex justify-end my-1 px-4">
        <div className="max-w-[70%] rounded-2xl rounded-br-md px-4 py-2.5"
          style={{ background: '#E5A800', color: '#000' }}>
          <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
          <div className="flex items-center justify-end gap-1 mt-1">
            {agentName && <span className="text-[10px]" style={{ color: 'rgba(0,0,0,0.5)' }}>{agentName}</span>}
            {isBot && <span className="text-[10px]" style={{ color: 'rgba(0,0,0,0.5)' }}>Bot</span>}
            <span className="text-[10px]" style={{ color: 'rgba(0,0,0,0.4)' }}>{time}</span>
          </div>
        </div>
      </div>
    )
  }

  // Contact messages — left side
  return (
    <div className="flex justify-start my-1 px-4">
      <div className="max-w-[70%] rounded-2xl rounded-bl-md px-4 py-2.5"
        style={{ background: 'rgba(255,255,255,0.08)' }}>
        <p className="text-sm whitespace-pre-wrap break-words" style={{ color: '#E4E4E7' }}>{content}</p>
        <span className="text-[10px] mt-1 block text-right" style={{ color: '#52525B' }}>{time}</span>
      </div>
    </div>
  )
}
