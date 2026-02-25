import React, { useState, useEffect, Component } from 'react'
import { ThemeProvider } from './contexts/ThemeContext'
import { ToastProvider } from './components/Toast'
import LoginPage from './pages/LoginPage'
import Layout from './components/Layout'
import { getMe } from './services/api'

// Error Boundary to prevent white screen on crashes
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-primary, #FFFFFF)' }}>
          <div className="text-center p-8 rounded-2xl" style={{ background: 'var(--bg-secondary, #fff)', maxWidth: 400 }}>
            <div className="w-14 h-14 rounded-xl flex items-center justify-center font-black text-xl mx-auto mb-4"
              style={{ background: '#E5A800', color: '#FFFFFF' }}>!</div>
            <h2 className="text-lg font-bold mb-2" style={{ color: 'var(--text-primary, #1a1a2e)' }}>Algo deu errado</h2>
            <p className="text-sm mb-4" style={{ color: 'var(--text-secondary, #636366)' }}>
              Ocorreu um erro inesperado. Tente recarregar a pagina.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 rounded-lg font-semibold text-sm"
              style={{ background: '#E5A800', color: '#FFFFFF' }}>
              Recarregar
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const validateSession = async () => {
      const token = localStorage.getItem('carbon_token')
      const saved = localStorage.getItem('carbon_user')
      if (token && saved) {
        try {
          // Validate token is still valid with backend
          const { data } = await getMe()
          setUser(data)
          // Update cached user data
          localStorage.setItem('carbon_user', JSON.stringify(data))
        } catch {
          // Token expired or invalid — clear session
          localStorage.removeItem('carbon_token')
          localStorage.removeItem('carbon_user')
        }
      }
      setLoading(false)
    }
    validateSession()
  }, [])

  const handleLogin = (userData, token) => {
    localStorage.setItem('carbon_token', token)
    localStorage.setItem('carbon_user', JSON.stringify(userData))
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('carbon_token')
    localStorage.removeItem('carbon_user')
    setUser(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-primary, #FFFFFF)' }}>
        <div className="text-center">
          <div className="w-14 h-14 rounded-xl flex items-center justify-center font-black text-xl mx-auto mb-4 animate-pulse"
            style={{ background: '#E5A800', color: '#FFFFFF' }}>C</div>
          <p className="text-sm" style={{ color: 'var(--text-tertiary, #8e8e93)' }}>Carregando...</p>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <ToastProvider>
          {!user ? <LoginPage onLogin={handleLogin} /> : <Layout user={user} onLogout={handleLogout} />}
        </ToastProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}
