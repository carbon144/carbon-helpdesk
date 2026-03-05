/**
 * Carbon Chat Widget — Embed on any website
 *
 * Usage:
 *   <script src="https://helpdesk.brutodeverdade.com.br/widget.js" data-server="https://helpdesk.brutodeverdade.com.br"></script>
 *
 * Optional attributes:
 *   data-color="#E5A800"     — accent color
 *   data-greeting="Ola!"    — initial greeting message
 *   data-position="right"   — button position (left|right)
 */
;(function () {
  'use strict'
  if (window.__carbonChatLoaded) return
  window.__carbonChatLoaded = true

  // Config from script tag
  var script = document.currentScript || document.querySelector('script[data-server]')
  var SERVER = (script && script.getAttribute('data-server')) || ''
  var ACCENT = (script && script.getAttribute('data-color')) || '#E5A800'
  var GREETING = (script && script.getAttribute('data-greeting')) || 'Ola! Como posso ajudar?'
  var POSITION = (script && script.getAttribute('data-position')) || 'right'

  if (!SERVER) {
    console.error('[Carbon Chat] data-server is required')
    return
  }

  // Remove trailing slash
  SERVER = SERVER.replace(/\/$/, '')

  // Visitor ID (persistent across sessions)
  var VISITOR_KEY = 'carbon_chat_visitor_id'
  var visitorId = localStorage.getItem(VISITOR_KEY)
  if (!visitorId) {
    visitorId = 'v_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8)
    localStorage.setItem(VISITOR_KEY, visitorId)
  }

  var conversationId = null
  var ws = null
  var isOpen = false
  var messages = []
  var reconnectTimer = null

  // ─── Styles ────────────────────────────────────────────────

  var css = document.createElement('style')
  css.textContent = [
    '#carbon-chat-widget *{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}',
    '#carbon-chat-btn{position:fixed;bottom:20px;' + POSITION + ':20px;width:60px;height:60px;border-radius:30px;background:' + ACCENT + ';color:#000;border:none;cursor:pointer;box-shadow:0 4px 20px rgba(0,0,0,0.3);z-index:99998;display:flex;align-items:center;justify-content:center;transition:transform .2s}',
    '#carbon-chat-btn:hover{transform:scale(1.08)}',
    '#carbon-chat-btn svg{width:28px;height:28px}',
    '#carbon-chat-btn .badge{position:absolute;top:-2px;right:-2px;width:20px;height:20px;border-radius:10px;background:#EF4444;color:#fff;font-size:11px;font-weight:700;display:none;align-items:center;justify-content:center}',
    '#carbon-chat-window{position:fixed;bottom:90px;' + POSITION + ':20px;width:380px;max-width:calc(100vw - 32px);height:520px;max-height:calc(100vh - 120px);border-radius:16px;background:#18181B;box-shadow:0 8px 40px rgba(0,0,0,0.5);z-index:99999;display:none;flex-direction:column;overflow:hidden;border:1px solid rgba(255,255,255,0.08)}',
    '#carbon-chat-window.open{display:flex}',
    '.ccw-header{background:#1F1F23;padding:16px;display:flex;align-items:center;gap:12px;border-bottom:1px solid rgba(255,255,255,0.06)}',
    '.ccw-header .logo{width:36px;height:36px;border-radius:18px;background:' + ACCENT + ';display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;color:#000;flex-shrink:0}',
    '.ccw-header .info h3{color:#E4E4E7;font-size:14px;font-weight:600}',
    '.ccw-header .info p{color:#71717A;font-size:12px}',
    '.ccw-header .close-btn{margin-left:auto;background:none;border:none;color:#71717A;cursor:pointer;padding:4px}',
    '.ccw-header .close-btn:hover{color:#E4E4E7}',
    '.ccw-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px}',
    '.ccw-msg{max-width:80%;padding:10px 14px;border-radius:12px;font-size:13px;line-height:1.5;word-break:break-word}',
    '.ccw-msg.contact{background:#27272A;color:#E4E4E7;align-self:flex-end;border-bottom-right-radius:4px}',
    '.ccw-msg.agent,.ccw-msg.bot{background:rgba(229,168,0,0.12);color:#E4E4E7;align-self:flex-start;border-bottom-left-radius:4px}',
    '.ccw-msg.system{background:transparent;color:#52525B;align-self:center;font-size:11px;font-style:italic}',
    '.ccw-typing{padding:0 16px 8px;color:#52525B;font-size:12px;font-style:italic;display:none}',
    '.ccw-typing.active{display:block}',
    '.ccw-input{padding:12px;border-top:1px solid rgba(255,255,255,0.06);display:flex;gap:8px}',
    '.ccw-input input{flex:1;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:10px 14px;color:#E4E4E7;font-size:13px;outline:none}',
    '.ccw-input input:focus{border-color:' + ACCENT + '}',
    '.ccw-input input::placeholder{color:#52525B}',
    '.ccw-input button{background:' + ACCENT + ';color:#000;border:none;border-radius:8px;padding:0 16px;font-weight:600;font-size:13px;cursor:pointer;flex-shrink:0}',
    '.ccw-input button:hover{opacity:0.9}',
    '.ccw-input button:disabled{opacity:0.4;cursor:not-allowed}',
    '@media(max-width:480px){#carbon-chat-window{bottom:0;right:0;left:0;width:100%;max-width:100%;height:100%;max-height:100%;border-radius:0}}',
  ].join('\n')
  document.head.appendChild(css)

  // ─── DOM ───────────────────────────────────────────────────

  var container = document.createElement('div')
  container.id = 'carbon-chat-widget'

  // Button
  var btn = document.createElement('button')
  btn.id = 'carbon-chat-btn'
  btn.setAttribute('aria-label', 'Abrir chat')
  btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg><span class="badge">0</span>'
  var badge = btn.querySelector('.badge')

  // Window
  var win = document.createElement('div')
  win.id = 'carbon-chat-window'
  win.innerHTML = [
    '<div class="ccw-header">',
    '  <div class="logo">C</div>',
    '  <div class="info"><h3>Carbon</h3><p>Atendimento</p></div>',
    '  <button class="close-btn" aria-label="Fechar"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>',
    '</div>',
    '<div class="ccw-messages"></div>',
    '<div class="ccw-typing">Digitando...</div>',
    '<div class="ccw-input">',
    '  <input type="text" placeholder="Digite sua mensagem..." maxlength="2000" />',
    '  <button type="button" disabled>Enviar</button>',
    '</div>',
  ].join('')

  container.appendChild(btn)
  container.appendChild(win)

  var messagesEl = win.querySelector('.ccw-messages')
  var typingEl = win.querySelector('.ccw-typing')
  var inputEl = win.querySelector('.ccw-input input')
  var sendBtn = win.querySelector('.ccw-input button')
  var closeBtn = win.querySelector('.close-btn')

  // ─── WebSocket ─────────────────────────────────────────────

  function connectWS() {
    if (ws && ws.readyState === WebSocket.OPEN) return

    var proto = SERVER.startsWith('https') ? 'wss' : 'ws'
    var host = SERVER.replace(/^https?:\/\//, '')
    ws = new WebSocket(proto + '://' + host + '/ws/chat/' + visitorId)

    ws.onopen = function () {
      // Initialize conversation
      ws.send(JSON.stringify({
        event: 'init',
        name: 'Visitante',
      }))
    }

    ws.onmessage = function (e) {
      try {
        var data = JSON.parse(e.data)
        if (data.event === 'init_ok') {
          conversationId = data.conversation_id
          sendBtn.disabled = false
          // Show greeting if no messages yet
          if (messages.length === 0) {
            addMessage('bot', GREETING)
          }
        } else if (data.event === 'new_message') {
          addMessage(data.sender_type, data.content)
          typingEl.classList.remove('active')
          if (!isOpen) {
            var count = parseInt(badge.textContent || '0') + 1
            badge.textContent = count
            badge.style.display = 'flex'
          }
        } else if (data.event === 'typing' && data.sender_type === 'agent') {
          typingEl.classList.add('active')
          setTimeout(function () { typingEl.classList.remove('active') }, 4000)
        }
      } catch (err) {
        console.warn('[Carbon Chat] WS parse error:', err)
      }
    }

    ws.onclose = function () {
      sendBtn.disabled = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      reconnectTimer = setTimeout(connectWS, 3000)
    }

    ws.onerror = function () { ws.close() }
  }

  function sendMessage(text) {
    if (!text.trim() || !conversationId || !ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({
      event: 'new_message',
      conversation_id: conversationId,
      content: text.trim(),
    }))
    addMessage('contact', text.trim())
    inputEl.value = ''
  }

  // ─── UI Helpers ────────────────────────────────────────────

  function addMessage(type, content) {
    if (!content) return
    messages.push({ type: type, content: content })
    var el = document.createElement('div')
    el.className = 'ccw-msg ' + type
    el.textContent = content
    messagesEl.appendChild(el)
    messagesEl.scrollTop = messagesEl.scrollHeight
  }

  // ─── Events ────────────────────────────────────────────────

  btn.addEventListener('click', function () {
    isOpen = !isOpen
    if (isOpen) {
      win.classList.add('open')
      badge.style.display = 'none'
      badge.textContent = '0'
      inputEl.focus()
      if (!ws || ws.readyState !== WebSocket.OPEN) connectWS()
    } else {
      win.classList.remove('open')
    }
  })

  closeBtn.addEventListener('click', function () {
    isOpen = false
    win.classList.remove('open')
  })

  sendBtn.addEventListener('click', function () {
    sendMessage(inputEl.value)
  })

  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(inputEl.value)
    }
    // Send typing indicator
    if (ws && ws.readyState === WebSocket.OPEN && conversationId) {
      ws.send(JSON.stringify({ event: 'typing', conversation_id: conversationId }))
    }
  })

  // ─── Mount ─────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { document.body.appendChild(container) })
  } else {
    document.body.appendChild(container)
  }
})()
