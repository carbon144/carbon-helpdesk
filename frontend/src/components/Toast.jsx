import React, { useState, useEffect, useCallback, createContext, useContext } from 'react'

const ToastContext = createContext()

const ICONS = {
  success: 'fa-check-circle',
  error: 'fa-times-circle',
  warning: 'fa-exclamation-triangle',
  info: 'fa-info-circle',
}

const COLORS = {
  success: { bg: 'rgba(22,163,74,0.12)', border: 'rgba(22,163,74,0.25)', text: '#16a34a', icon: '#16a34a' },
  error: { bg: 'rgba(220,38,38,0.12)', border: 'rgba(220,38,38,0.25)', text: '#dc2626', icon: '#dc2626' },
  warning: { bg: 'rgba(234,179,8,0.12)', border: 'rgba(234,179,8,0.25)', text: '#ca8a04', icon: '#ca8a04' },
  info: { bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.25)', text: '#2563eb', icon: '#2563eb' },
}

// Audio feedback using Web Audio API
const playSound = (type) => {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    gain.gain.value = 0.08

    if (type === 'success') {
      osc.frequency.value = 880
      osc.type = 'sine'
      gain.gain.setValueAtTime(0.08, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + 0.15)
      // Second note (higher)
      const osc2 = ctx.createOscillator()
      const gain2 = ctx.createGain()
      osc2.connect(gain2)
      gain2.connect(ctx.destination)
      osc2.frequency.value = 1320
      osc2.type = 'sine'
      gain2.gain.setValueAtTime(0.06, ctx.currentTime + 0.1)
      gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25)
      osc2.start(ctx.currentTime + 0.1)
      osc2.stop(ctx.currentTime + 0.25)
    } else if (type === 'error') {
      // Comic "wah-wah-waaah" trombone fail
      osc.frequency.value = 440
      osc.type = 'sine'
      gain.gain.setValueAtTime(0.07, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + 0.15)
      const osc2 = ctx.createOscillator()
      const gain2 = ctx.createGain()
      osc2.connect(gain2)
      gain2.connect(ctx.destination)
      osc2.frequency.value = 380
      osc2.type = 'sine'
      gain2.gain.setValueAtTime(0.07, ctx.currentTime + 0.13)
      gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.28)
      osc2.start(ctx.currentTime + 0.13)
      osc2.stop(ctx.currentTime + 0.28)
      const osc3 = ctx.createOscillator()
      const gain3 = ctx.createGain()
      osc3.connect(gain3)
      gain3.connect(ctx.destination)
      osc3.frequency.value = 300
      osc3.type = 'sine'
      // Slide down for comic effect
      osc3.frequency.setValueAtTime(300, ctx.currentTime + 0.26)
      osc3.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 0.55)
      gain3.gain.setValueAtTime(0.08, ctx.currentTime + 0.26)
      gain3.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.55)
      osc3.start(ctx.currentTime + 0.26)
      osc3.stop(ctx.currentTime + 0.55)
    } else if (type === 'warning') {
      osc.frequency.value = 660
      osc.type = 'triangle'
      gain.gain.setValueAtTime(0.06, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + 0.2)
    } else {
      osc.frequency.value = 740
      osc.type = 'sine'
      gain.gain.setValueAtTime(0.05, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + 0.12)
    }
  } catch (e) {
    // Audio not available (user hasn't interacted yet or no audio support)
  }
}

function ToastItem({ toast, onRemove }) {
  const [visible, setVisible] = useState(false)
  const [exiting, setExiting] = useState(false)
  const colors = COLORS[toast.type] || COLORS.info

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true))
    const timer = setTimeout(() => {
      setExiting(true)
      setTimeout(() => onRemove(toast.id), 300)
    }, toast.duration || 3000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div
      style={{
        background: colors.bg,
        borderLeft: `3px solid ${colors.border}`,
        transform: visible && !exiting ? 'translateX(0)' : 'translateX(120%)',
        opacity: visible && !exiting ? 1 : 0,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
      }}
      className="flex items-center gap-3 px-4 py-3 rounded-xl mb-2 min-w-[280px] max-w-[400px] pointer-events-auto cursor-pointer"
      onClick={() => { setExiting(true); setTimeout(() => onRemove(toast.id), 300) }}
    >
      <i className={`fas ${ICONS[toast.type]} text-base`} style={{ color: colors.icon }} />
      <div className="flex-1 min-w-0">
        {toast.title && <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{toast.title}</p>}
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{toast.message}</p>
      </div>
      <i className="fas fa-times text-xs opacity-40 hover:opacity-80 transition" style={{ color: 'var(--text-tertiary)' }} />
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((type, message, options = {}) => {
    const id = Date.now() + Math.random()
    const toast = { id, type, message, ...options }
    setToasts(prev => [...prev, toast])
    if (options.sound !== false) playSound(type)
    return id
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const toast = useCallback({
    success: (msg, opts) => addToast('success', msg, opts),
    error: (msg, opts) => addToast('error', msg, opts),
    warning: (msg, opts) => addToast('warning', msg, opts),
    info: (msg, opts) => addToast('info', msg, opts),
  }, [addToast])

  // Fix: useCallback can't wrap an object, use useMemo pattern
  const api = {
    success: (msg, opts) => addToast('success', msg, opts),
    error: (msg, opts) => addToast('error', msg, opts),
    warning: (msg, opts) => addToast('warning', msg, opts),
    info: (msg, opts) => addToast('info', msg, opts),
  }

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col items-end pointer-events-none">
        {toasts.map(t => <ToastItem key={t.id} toast={t} onRemove={removeToast} />)}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast deve ser usado dentro de ToastProvider')
  return ctx
}

export default useToast
