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

export default function useWebSocket(token) {
  const wsRef = useRef(null)
  const pingRef = useRef(null)
  const reconnectRef = useRef(null)
  const [notifications, setNotifications] = useState([])
  const [connected, setConnected] = useState(false)

  const connect = useCallback(() => {
    if (!token) return
    // Prevent duplicate connections
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return

    try {
      const ws = new WebSocket(`${getWsBase()}/ws/${token}`)

      ws.onopen = () => {
        setConnected(true)
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping')
        }, PING_INTERVAL_MS)
      }

      ws.onmessage = (event) => {
        if (event.data === 'pong') return
        try {
          const data = JSON.parse(event.data)
          const notif = {
            id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
            ...data,
            timestamp: new Date(),
            read: false,
          }
          setNotifications(prev => [notif, ...prev].slice(0, MAX_NOTIFICATIONS))
        } catch (e) {
          console.warn('WebSocket: failed to parse message', e)
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (pingRef.current) clearInterval(pingRef.current)
        // Clear previous timer before setting new one
        if (reconnectRef.current) clearTimeout(reconnectRef.current)
        reconnectRef.current = setTimeout(connect, AUTO_RECONNECT_MS)
      }

      ws.onerror = (e) => {
        console.warn('WebSocket error:', e)
        ws.close()
      }

      wsRef.current = ws
    } catch (e) {
      console.warn('WebSocket: failed to connect', e)
    }
  }, [token])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      if (pingRef.current) clearInterval(pingRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  const markRead = useCallback((id) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
  }, [])

  const clearAll = useCallback(() => {
    setNotifications([])
  }, [])

  const unreadCount = notifications.filter(n => !n.read).length

  return { notifications, unreadCount, connected, markRead, clearAll }
}
