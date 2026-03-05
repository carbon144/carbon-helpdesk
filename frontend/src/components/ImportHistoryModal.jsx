import React, { useState } from 'react'
import { fetchGmailHistory } from '../services/api'

export default function ImportHistoryModal({ open, onClose, onSuccess }) {
  const [importDays, setImportDays] = useState(30)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [importError, setImportError] = useState(null)
  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => !importing && onClose()}>
      <div className="bg-[var(--bg-secondary)] rounded-2xl w-full max-w-lg border border-[var(--border-color)] shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-8 py-6 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-purple-600/20 flex items-center justify-center border border-purple-500/30">
              <i className="fas fa-cloud-download-alt text-purple-400 text-lg" />
            </div>
            <div>
              <h2 className="text-[var(--text-primary)] font-semibold text-lg">Importar Histórico</h2>
              <p className="text-[var(--text-secondary)] text-sm">Sincronizar emails do Gmail</p>
            </div>
          </div>
          {!importing && (
            <button onClick={() => { onClose(); setImportResult(null) }} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">
              <i className="fas fa-times text-xl" />
            </button>
          )}
        </div>

        <div className="px-8 py-6">
          <label className="text-[var(--text-primary)] text-sm font-semibold block mb-4">Período de importação</label>
          <div className="grid grid-cols-4 gap-3 mb-6">
            {[{ label: '7 dias', value: 7 }, { label: '15 dias', value: 15 }, { label: '30 dias', value: 30 }, { label: '60 dias', value: 60 }].map(opt => (
              <button key={opt.value} onClick={() => setImportDays(opt.value)} disabled={importing}
                className={`py-3 rounded-xl text-sm font-medium transition-colors ${
                  importDays === opt.value
                    ? 'bg-purple-600 text-white border border-purple-500'
                    : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:text-[var(--text-primary)] hover:border-purple-500/50'
                }`}>{opt.label}</button>
            ))}
          </div>

          <div className="flex items-center gap-3 mb-6 bg-[var(--bg-tertiary)] rounded-xl px-4 py-3 border border-[var(--border-color)]">
            <i className="fas fa-calendar text-[var(--text-secondary)] text-lg" />
            <label className="text-[var(--text-secondary)] text-sm font-medium">Personalizado:</label>
            <input type="number" min="1" max="365" value={importDays}
              onChange={e => setImportDays(Math.max(1, Math.min(365, parseInt(e.target.value) || 1)))}
              disabled={importing}
              className="w-16 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-[var(--text-primary)] text-sm text-center focus:outline-none focus:ring-2 focus:ring-purple-500/50" />
            <span className="text-[var(--text-secondary)] text-sm">dias</span>
          </div>

          {importResult && (
            <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4 mb-4">
              <div className="flex items-center gap-2 mb-3">
                <i className="fas fa-check-circle text-green-400 text-lg" />
                <span className="text-green-400 font-semibold text-sm">Importação concluída com sucesso!</span>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">{importResult.created}</div>
                  <div className="text-xs text-[var(--text-secondary)] mt-1">Criados</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-400">{importResult.updated}</div>
                  <div className="text-xs text-[var(--text-secondary)] mt-1">Atualizados</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-[var(--text-secondary)]">{importResult.skipped}</div>
                  <div className="text-xs text-[var(--text-secondary)] mt-1">Já existentes</div>
                </div>
              </div>
            </div>
          )}

          {importError && (
            <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4 mb-4">
              <div className="flex items-center gap-2 mb-2">
                <i className="fas fa-exclamation-circle text-red-400 text-lg" />
                <span className="text-red-400 font-semibold text-sm">Erro na importação</span>
              </div>
              <p className="text-red-300 text-xs mt-2">{importError}</p>
            </div>
          )}
        </div>

        <div className="flex gap-3 justify-end px-8 py-6 border-t border-[var(--border-color)]">
          <button onClick={() => { onClose(); setImportResult(null); setImportError(null) }} disabled={importing}
            className="px-6 py-2.5 rounded-lg text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors font-medium">
            {importResult ? 'Fechar' : 'Cancelar'}
          </button>
          {!importResult && (
            <button onClick={async () => {
              setImporting(true); setImportResult(null); setImportError(null)
              try {
                const { data } = await fetchGmailHistory(importDays)
                setImportResult(data)
                onSuccess()
              } catch (e) {
                const msg = e.response?.data?.detail || e.message || 'Erro desconhecido'
                setImportError(`Não foi possível importar. ${msg}`)
              } finally { setImporting(false) }
            }} disabled={importing}
              className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2">
              {importing ? <><i className="fas fa-spinner animate-spin" />Importando...</> : <><i className="fas fa-cloud-download-alt" />Importar {importDays} dias</>}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
