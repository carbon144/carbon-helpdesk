import { useState, useRef, useCallback } from 'react'
import { Send, StickyNote } from 'lucide-react'

export default function ChatInput({ onSendMessage, onSendNote, disabled }) {
  const [text, setText] = useState('')
  const [isNote, setIsNote] = useState(false)
  const textareaRef = useRef(null)

  const handleSend = useCallback(() => {
    const trimmed = text.trim()
    if (!trimmed) return

    if (isNote) {
      onSendNote(trimmed)
    } else {
      onSendMessage(trimmed)
    }

    setText('')
    setIsNote(false)
    textareaRef.current?.focus()
  }, [text, isNote, onSendMessage, onSendNote])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="p-3" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
      {isNote && (
        <div className="flex items-center gap-1.5 mb-2 px-1">
          <StickyNote className="w-3.5 h-3.5" style={{ color: '#E5A800' }} />
          <span className="text-xs font-medium" style={{ color: '#E5A800' }}>Nota interna (apenas atendentes)</span>
          <button
            onClick={() => { setIsNote(false); setText('') }}
            className="text-xs ml-auto cursor-pointer" style={{ color: '#71717A' }}>
            Cancelar
          </button>
        </div>
      )}

      <div className={`flex items-end gap-2 rounded-xl px-3 py-2`}
        style={{
          border: isNote ? '1px solid rgba(229,168,0,0.3)' : '1px solid rgba(255,255,255,0.1)',
          background: isNote ? 'rgba(229,168,0,0.05)' : 'rgba(255,255,255,0.04)',
        }}>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={isNote ? 'Escreva uma nota interna...' : 'Escreva uma mensagem...'}
          rows={1}
          className="flex-1 bg-transparent resize-none text-sm placeholder-zinc-500 focus:outline-none max-h-32 min-h-[20px]"
          style={{ color: '#E4E4E7' }}
          onInput={(e) => {
            e.target.style.height = 'auto'
            e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px'
          }}
        />

        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => { setIsNote(!isNote); setText('') }}
            className="p-1.5 rounded-lg transition cursor-pointer"
            style={{ color: isNote ? '#E5A800' : '#71717A' }}
            title="Nota interna">
            <StickyNote className="w-4 h-4" />
          </button>
          <button
            onClick={handleSend}
            disabled={disabled || !text.trim()}
            className="p-1.5 rounded-lg transition cursor-pointer disabled:opacity-30"
            style={{ background: '#E5A800', color: '#000' }}
            title="Enviar">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
