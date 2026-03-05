import React, { useState, useRef } from 'react'
import { composeEmail, uploadAttachment } from '../services/api'

export default function ComposeEmailModal({ open, onClose, onSuccess, toast }) {
  const [to, setTo] = useState('')
  const [cc, setCc] = useState('')
  const [bcc, setBcc] = useState('')
  const [showCcBcc, setShowCcBcc] = useState(false)
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)
  const [attachments, setAttachments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const attachmentRef = useRef(null)

  if (!open) return null

  const reset = () => { setTo(''); setCc(''); setBcc(''); setShowCcBcc(false); setSubject(''); setBody(''); setAttachments([]) }

  const handleUpload = async (files) => {
    if (!files.length) return
    setUploading(true)
    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const { data } = await uploadAttachment(formData)
        setAttachments(prev => [...prev, data])
      }
    } catch { toast.error('Erro ao fazer upload do anexo') }
    finally { setUploading(false) }
  }

  const handleDrop = (e) => { e.preventDefault(); e.stopPropagation(); setDragging(false); handleUpload(Array.from(e.dataTransfer.files)) }
  const handleDragOver = (e) => { e.preventDefault(); e.stopPropagation(); setDragging(true) }
  const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setDragging(false) }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => !sending && onClose()}>
      <div className="bg-[var(--bg-secondary)] rounded-2xl w-full max-w-2xl shadow-2xl border border-[var(--border-color)]" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 flex items-center justify-center">
              <i className="fas fa-pen-to-square text-blue-400 text-lg" />
            </div>
            <h2 className="text-[var(--text-primary)] font-semibold text-lg">Novo E-mail</h2>
          </div>
          <button onClick={onClose} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">
            <i className="fas fa-times text-lg" />
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[var(--text-secondary)] text-sm font-medium">Para</label>
              <button onClick={() => setShowCcBcc(!showCcBcc)} className="text-xs text-blue-400 hover:text-blue-300 transition">
                {showCcBcc ? 'Ocultar CC/CCO' : 'CC/CCO'}
              </button>
            </div>
            <input type="email" value={to} onChange={e => setTo(e.target.value)} placeholder="email@cliente.com"
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
          </div>
          {showCcBcc && (<>
            <div>
              <label className="text-[var(--text-secondary)] text-sm font-medium block mb-1.5">CC</label>
              <input type="text" value={cc} onChange={e => setCc(e.target.value)} placeholder="email1@example.com, email2@example.com"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-sm font-medium block mb-1.5">CCO</label>
              <input type="text" value={bcc} onChange={e => setBcc(e.target.value)} placeholder="email1@example.com, email2@example.com"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
            </div>
          </>)}
          <div>
            <label className="text-[var(--text-secondary)] text-sm font-medium block mb-1.5">Assunto</label>
            <input type="text" value={subject} onChange={e => setSubject(e.target.value)} placeholder="Assunto do e-mail"
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
          </div>
          <div className={`relative ${dragging ? 'ring-2 ring-emerald-400 ring-dashed rounded-lg' : ''}`} onDrop={handleDrop} onDragOver={handleDragOver} onDragLeave={handleDragLeave}>
            {dragging && (
              <div className="absolute inset-0 bg-emerald-500/10 border-2 border-dashed border-emerald-400 rounded-xl z-10 flex items-center justify-center pointer-events-none">
                <span className="text-emerald-400 font-medium text-sm"><i className="fas fa-cloud-upload-alt mr-2" />Solte os arquivos aqui</span>
              </div>
            )}
            <label className="text-[var(--text-secondary)] text-sm font-medium block mb-1.5">Mensagem</label>
            <textarea value={body} onChange={e => setBody(e.target.value)} placeholder="Escreva sua mensagem..." rows={8}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg px-3 py-2.5 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none" />
          </div>
          <div>
            <button onClick={() => attachmentRef.current?.click()} disabled={uploading}
              className={`text-xs px-3 py-1.5 rounded-lg transition ${attachments.length > 0 ? 'bg-emerald-600/20 text-emerald-400' : 'text-[var(--text-tertiary)] hover:text-emerald-400 hover:bg-[var(--bg-tertiary)] border border-[var(--border-color)]'}`}>
              <i className={`fas ${uploading ? 'fa-spinner animate-spin' : 'fa-paperclip'} mr-1`} />
              {attachments.length > 0 ? `${attachments.length} anexo${attachments.length > 1 ? 's' : ''}` : 'Anexar arquivos'}
            </button>
            <input ref={attachmentRef} type="file" multiple className="hidden" onChange={e => { handleUpload(Array.from(e.target.files)); e.target.value = '' }} />
            {attachments.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {attachments.map((att, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 text-xs px-2.5 py-1 rounded-lg">
                    <i className="fas fa-paperclip text-[10px]" />
                    <span className="max-w-[150px] truncate">{att.name}</span>
                    <span className="text-emerald-600 text-[10px]">({(att.size / 1024).toFixed(0)}KB)</span>
                    <button onClick={() => setAttachments(prev => prev.filter((_, j) => j !== i))} className="hover:text-red-400 transition ml-0.5">
                      <i className="fas fa-times text-[10px]" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="flex justify-end gap-3 p-5 border-t border-[var(--border-color)]">
          <button onClick={() => { reset(); onClose() }}
            className="px-4 py-2.5 rounded-lg text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition">Cancelar</button>
          <button onClick={async () => {
            if (!to || !subject || !body) return
            setSending(true)
            try {
              const ccList = cc ? cc.split(',').map(e => e.trim()).filter(Boolean) : undefined
              const bccList = bcc ? bcc.split(',').map(e => e.trim()).filter(Boolean) : undefined
              const { data } = await composeEmail({ to, subject, body, cc: ccList, bcc: bccList, attachments: attachments.length ? attachments : undefined })
              reset(); onClose(); onSuccess(data)
            } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao enviar e-mail') }
            finally { setSending(false) }
          }} disabled={sending || !to || !subject || !body}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2">
            {sending ? <><i className="fas fa-spinner animate-spin" />Enviando...</> : <><i className="fas fa-paper-plane" />Enviar E-mail</>}
          </button>
        </div>
      </div>
    </div>
  )
}
