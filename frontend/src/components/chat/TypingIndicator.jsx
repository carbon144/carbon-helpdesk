export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-2">
      <div className="flex gap-1 rounded-2xl px-4 py-2.5" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <span className="w-2 h-2 rounded-full animate-bounce [animation-delay:0ms]" style={{ background: '#71717A' }} />
        <span className="w-2 h-2 rounded-full animate-bounce [animation-delay:150ms]" style={{ background: '#71717A' }} />
        <span className="w-2 h-2 rounded-full animate-bounce [animation-delay:300ms]" style={{ background: '#71717A' }} />
      </div>
    </div>
  )
}
