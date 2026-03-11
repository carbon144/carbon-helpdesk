import { useEffect, useRef, useState, useCallback } from 'react'

const AUTO_RECONNECT_MS = 3000
const PING_INTERVAL_MS = 30000
const MAX_NOTIFICATIONS = 50

function getWsBase() {
  const envUrl = import.meta.env.VITE_WS_URL
  if (envUrl) return envUrl
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}`
}

// Singleton WS connection shared across all hook consumers
let _ws = null
let _pingInterval = null
let _reconnectTimeout = null
let _token = null
let _listeners = new Set()
let _connected = false

function _connect() {
  if (!_token) return
  if (_ws && _ws.readyState === WebSocket.OPEN) return

  try {
    const ws = new WebSocket(`${getWsBase()}/ws/${_token}`)

    ws.onopen = () => {
      _connected = true
      _pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, PING_INTERVAL_MS)
      _listeners.forEach(fn => fn({ _type: '_connected' }))
    }

    ws.onmessage = (event) => {
      if (event.data === 'pong') return
      try {
        const data = JSON.parse(event.data)
        _listeners.forEach(fn => fn(data))
      } catch (e) {
        console.warn('WebSocket: failed to parse message', e)
      }
    }

    ws.onclose = () => {
      _connected = false
      if (_pingInterval) clearInterval(_pingInterval)
      if (_reconnectTimeout) clearTimeout(_reconnectTimeout)
      _reconnectTimeout = setTimeout(_connect, AUTO_RECONNECT_MS)
      _listeners.forEach(fn => fn({ _type: '_disconnected' }))
    }

    ws.onerror = () => ws.close()
    _ws = ws
  } catch (e) {
    console.warn('WebSocket: failed to connect', e)
  }
}

function _ensureConnection(token) {
  if (_token !== token) {
    _token = token
    if (_reconnectTimeout) { clearTimeout(_reconnectTimeout); _reconnectTimeout = null }
    if (_ws) {
      const oldWs = _ws
      _ws = null
      oldWs.onclose = () => {} // prevent auto-reconnect from old socket
      oldWs.close()
    }
    _connect()
  } else if (!_ws || _ws.readyState !== WebSocket.OPEN) {
    _connect()
  }
}

function _send(data) {
  if (_ws && _ws.readyState === WebSocket.OPEN) {
    _ws.send(typeof data === 'string' ? data : JSON.stringify(data))
  }
}

export default function useWebSocket(token) {
  const [notifications, setNotifications] = useState([])
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    _ensureConnection(token)

    const handler = (data) => {
      if (data._type === '_connected') { setConnected(true); return }
      if (data._type === '_disconnected') { setConnected(false); return }

      const notif = {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        ...data,
        timestamp: new Date(),
        read: false,
      }
      setNotifications(prev => [notif, ...prev].slice(0, MAX_NOTIFICATIONS))
    }

    _listeners.add(handler)
    setConnected(_connected)

    return () => {
      _listeners.delete(handler)
    }
  }, [token])

  const markRead = useCallback((id) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
  }, [])

  const clearAll = useCallback(() => setNotifications([]), [])

  const unreadCount = notifications.filter(n => !n.read).length

  return { notifications, unreadCount, connected, markRead, clearAll, send: _send }
}

/**
 * Lightweight hook to subscribe to specific WS event types.
 * Usage: useChatEvents(token, 'chat_event', (data) => { ... })
 */
export function useChatEvents(token, onChatEvent) {
  useEffect(() => {
    _ensureConnection(token)

    const handler = (data) => {
      if (data._type) return // internal events
      if (data.type === 'chat_event' && onChatEvent) {
        onChatEvent(data)
      }
    }

    _listeners.add(handler)
    return () => _listeners.delete(handler)
  }, [token, onChatEvent])
}
