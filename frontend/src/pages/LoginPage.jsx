import React, { useState, useEffect } from 'react'
import { login, forgotPassword, resetPasswordWithToken } from '../services/api'

const inputStyle = {
  background: 'var(--bg-input)',
  border: '1px solid var(--border-color)',
  color: 'var(--text-primary)',
}

export default function LoginPage({ onLogin }) {
  // mode: 'login' | 'forgot' | 'reset'
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [hoverBtn, setHoverBtn] = useState(false)

  // Detecta ?reset_token= na URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('reset_token')
    if (token) {
      setResetToken(token)
      setMode('reset')
      // Limpa a URL sem recarregar
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await login(email, password)
      onLogin(data.user, data.access_token)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao fazer login')
    } finally {
      setLoading(false)
    }
  }

  const handleForgot = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)
    try {
      const { data } = await forgotPassword(email)
      setSuccess(data.message)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao enviar email')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (newPassword.length < 6) {
      setError('A senha deve ter pelo menos 6 caracteres')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('As senhas não coincidem')
      return
    }
    setLoading(true)
    try {
      const { data } = await resetPasswordWithToken(resetToken, newPassword)
      setSuccess(data.message)
      setTimeout(() => {
        setMode('login')
        setSuccess('')
        setNewPassword('')
        setConfirmPassword('')
      }, 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao redefinir senha')
    } finally {
      setLoading(false)
    }
  }

  const switchMode = (newMode) => {
    setMode(newMode)
    setError('')
    setSuccess('')
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{ background: 'var(--bg-primary)' }}>
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full opacity-[0.04]"
          style={{ background: 'var(--accent)' }} />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full opacity-[0.04]"
          style={{ background: 'var(--accent)' }} />
      </div>

      {/* Card */}
      <div className="relative z-10 w-full max-w-md px-4">
        <div className="rounded-xl p-8 border"
          style={{
            background: 'var(--bg-secondary)',
            borderColor: 'var(--border-color)',
            boxShadow: 'var(--shadow-lg)',
          }}>
          {/* Logo */}
          <div className="text-center mb-8">
            <img src="/logo-black.png" alt="Carbon Expert Hub" className="h-12 mx-auto mb-4" />
            <p className="text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>
              {mode === 'login' && 'Sistema de Atendimento'}
              {mode === 'forgot' && 'Recuperar Senha'}
              {mode === 'reset' && 'Redefinir Senha'}
            </p>
          </div>

          {/* ── Login ── */}
          {mode === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  E-mail
                </label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg px-4 py-3 text-sm transition login-input" style={inputStyle} required />
              </div>
              <div>
                <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Senha
                </label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg px-4 py-3 text-sm transition login-input" style={inputStyle} required />
              </div>

              {error && (
                <div className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg"
                  style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171' }}>
                  <i className="fas fa-exclamation-circle" />
                  {error}
                </div>
              )}

              <button type="submit" disabled={loading}
                className="w-full font-semibold py-3 rounded-lg transition disabled:opacity-50 text-sm"
                style={{
                  background: !loading && hoverBtn ? 'var(--accent-hover)' : 'var(--accent)',
                  color: 'var(--accent-text)',
                }}
                onMouseEnter={() => setHoverBtn(true)} onMouseLeave={() => setHoverBtn(false)}>
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <i className="fas fa-spinner fa-spin" /> Entrando...
                  </span>
                ) : 'Entrar'}
              </button>

              <button type="button" onClick={() => switchMode('forgot')}
                className="w-full text-xs py-2 transition" style={{ color: 'var(--text-tertiary)' }}
                onMouseEnter={(e) => e.target.style.color = 'var(--accent)'}
                onMouseLeave={(e) => e.target.style.color = 'var(--text-tertiary)'}>
                Esqueci minha senha
              </button>
            </form>
          )}

          {/* ── Esqueci minha senha ── */}
          {mode === 'forgot' && (
            <form onSubmit={handleForgot} className="space-y-4">
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Digite seu e-mail e enviaremos um link para redefinir sua senha.
              </p>
              <div>
                <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  E-mail
                </label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg px-4 py-3 text-sm transition login-input" style={inputStyle}
                  required autoFocus />
              </div>

              {error && (
                <div className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg"
                  style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171' }}>
                  <i className="fas fa-exclamation-circle" />
                  {error}
                </div>
              )}
              {success && (
                <div className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg"
                  style={{ background: 'rgba(34,197,94,0.1)', color: '#4ade80' }}>
                  <i className="fas fa-check-circle" />
                  {success}
                </div>
              )}

              <button type="submit" disabled={loading}
                className="w-full font-semibold py-3 rounded-lg transition disabled:opacity-50 text-sm"
                style={{
                  background: !loading && hoverBtn ? 'var(--accent-hover)' : 'var(--accent)',
                  color: 'var(--accent-text)',
                }}
                onMouseEnter={() => setHoverBtn(true)} onMouseLeave={() => setHoverBtn(false)}>
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <i className="fas fa-spinner fa-spin" /> Enviando...
                  </span>
                ) : 'Enviar link de recuperação'}
              </button>

              <button type="button" onClick={() => switchMode('login')}
                className="w-full text-xs py-2 transition flex items-center justify-center gap-1"
                style={{ color: 'var(--text-tertiary)' }}
                onMouseEnter={(e) => e.target.style.color = 'var(--accent)'}
                onMouseLeave={(e) => e.target.style.color = 'var(--text-tertiary)'}>
                <i className="fas fa-arrow-left text-[10px]" /> Voltar ao login
              </button>
            </form>
          )}

          {/* ── Redefinir Senha (via token do email) ── */}
          {mode === 'reset' && (
            <form onSubmit={handleReset} className="space-y-4">
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Crie uma nova senha para sua conta.
              </p>
              <div>
                <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Nova senha
                </label>
                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-lg px-4 py-3 text-sm transition login-input" style={inputStyle}
                  placeholder="Mínimo 6 caracteres" required autoFocus />
              </div>
              <div>
                <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Confirmar senha
                </label>
                <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-lg px-4 py-3 text-sm transition login-input" style={inputStyle}
                  required />
              </div>

              {error && (
                <div className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg"
                  style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171' }}>
                  <i className="fas fa-exclamation-circle" />
                  {error}
                </div>
              )}
              {success && (
                <div className="flex items-center gap-2 text-sm px-3 py-2 rounded-lg"
                  style={{ background: 'rgba(34,197,94,0.1)', color: '#4ade80' }}>
                  <i className="fas fa-check-circle" />
                  {success}
                </div>
              )}

              <button type="submit" disabled={loading || !!success}
                className="w-full font-semibold py-3 rounded-lg transition disabled:opacity-50 text-sm"
                style={{
                  background: !loading && hoverBtn ? 'var(--accent-hover)' : 'var(--accent)',
                  color: 'var(--accent-text)',
                }}
                onMouseEnter={() => setHoverBtn(true)} onMouseLeave={() => setHoverBtn(false)}>
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <i className="fas fa-spinner fa-spin" /> Redefinindo...
                  </span>
                ) : 'Redefinir Senha'}
              </button>

              <button type="button" onClick={() => switchMode('login')}
                className="w-full text-xs py-2 transition flex items-center justify-center gap-1"
                style={{ color: 'var(--text-tertiary)' }}
                onMouseEnter={(e) => e.target.style.color = 'var(--accent)'}
                onMouseLeave={(e) => e.target.style.color = 'var(--text-tertiary)'}>
                <i className="fas fa-arrow-left text-[10px]" /> Voltar ao login
              </button>
            </form>
          )}

          <p className="text-[11px] text-center mt-6" style={{ color: 'var(--text-tertiary)' }}>
            Carbon Expert Hub v1.0
          </p>
        </div>
      </div>
    </div>
  )
}
