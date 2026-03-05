import React, { useState, useEffect, useRef } from 'react'
import { useToast } from '../components/Toast'
import { getMediaItems, createMediaItem, deleteMediaItem, uploadMedia } from '../services/api'

const CATEGORIES = [
  { id: '', label: 'Todos', icon: 'fa-th' },
  { id: 'video', label: 'Vídeos', icon: 'fa-play-circle', color: 'text-red-400' },
  { id: 'foto', label: 'Fotos', icon: 'fa-image', color: 'text-blue-400' },
  { id: 'instagram', label: 'Instagram', icon: 'fa-instagram', color: 'text-pink-400', brand: true },
  { id: 'link', label: 'Links Úteis', icon: 'fa-link', color: 'text-cyan-400' },
  { id: 'politica', label: 'Políticas', icon: 'fa-file-contract', color: 'text-amber-400' },
  { id: 'manual', label: 'Manuais', icon: 'fa-book', color: 'text-emerald-400' },
  { id: 'outro', label: 'Outros', icon: 'fa-file', color: 'text-carbon-400' },
]

function detectUrlType(url) {
  const lower = (url || '').toLowerCase()
  if (lower.includes('instagram.com') || lower.includes('instagr.am')) return 'instagram'
  if (lower.includes('drive.google.com') || lower.includes('docs.google.com')) return 'drive'
  return 'link'
}

export default function MediaPage() {
  const toast = useToast()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [addMode, setAddMode] = useState('link') // 'link' or 'upload'
  const [form, setForm] = useState({ name: '', drive_url: '', description: '', category: 'video' })
  const [saving, setSaving] = useState(false)
  // Upload state
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef(null)

  useEffect(() => { loadItems() }, [category])

  const loadItems = async () => {
    setLoading(true)
    try {
      const params = {}
      if (category) params.category = category
      const { data } = await getMediaItems(params)
      setItems(data || [])
    } catch (e) { toast.error('Falha ao carregar biblioteca de mídia') }
    finally { setLoading(false) }
  }

  const handleUrlChange = (url) => {
    const detected = detectUrlType(url)
    const newForm = { ...form, drive_url: url }
    if (detected === 'instagram' && form.category !== 'instagram') {
      newForm.category = 'instagram'
    }
    setForm(newForm)
  }

  const handleAdd = async () => {
    if (!form.name || !form.drive_url) return
    setSaving(true)
    try {
      await createMediaItem(form)
      setForm({ name: '', drive_url: '', description: '', category: 'video' })
      setShowAdd(false)
      loadItems()
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao adicionar') }
    finally { setSaving(false) }
  }

  const handleUpload = async () => {
    if (!uploadFile || !form.name) return
    setUploading(true)
    setUploadProgress(10)
    try {
      const fd = new FormData()
      fd.append('file', uploadFile)
      fd.append('name', form.name)
      fd.append('category', form.category)
      fd.append('description', form.description)
      setUploadProgress(30)
      await uploadMedia(fd)
      setUploadProgress(100)
      setForm({ name: '', drive_url: '', description: '', category: 'video' })
      setUploadFile(null)
      setShowAdd(false)
      loadItems()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro no upload')
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Remover este item da biblioteca?')) return
    try {
      await deleteMediaItem(id)
      loadItems()
    } catch (e) { toast.error('Falha ao remover item') }
  }

  const sourceIcon = (sourceType) => {
    if (sourceType === 'instagram') return 'fab fa-instagram text-pink-400'
    if (sourceType === 'drive') return 'fab fa-google-drive text-blue-400'
    return 'fas fa-link text-cyan-400'
  }

  const catIcons = {
    video: 'fa-play-circle text-red-400', foto: 'fa-image text-blue-400',
    instagram: 'fa-instagram text-pink-400',
    link: 'fa-link text-cyan-400', politica: 'fa-file-contract text-amber-400',
    manual: 'fa-book text-emerald-400', outro: 'fa-file text-carbon-400',
  }

  const filtered = items.filter(m => !search || m.name.toLowerCase().includes(search.toLowerCase()) || (m.description || '').toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white"><i className="fas fa-photo-video mr-3 text-pink-400" />Biblioteca de Mídia</h1>
          <p className="text-carbon-400 text-sm mt-1">Vídeos, fotos, Instagram, links e políticas para envio rápido</p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)}
          className="bg-pink-600 hover:bg-pink-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition">
          <i className={`fas ${showAdd ? 'fa-times' : 'fa-plus'} mr-2`} />
          {showAdd ? 'Cancelar' : 'Adicionar Mídia'}
        </button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="bg-carbon-700 rounded-xl p-5 mb-6 border border-carbon-600">
          <div className="flex items-center gap-3 mb-4">
            <h3 className="text-white font-semibold"><i className="fas fa-plus-circle mr-2 text-pink-400" />Nova Mídia</h3>
            <div className="flex bg-carbon-800 rounded-lg p-0.5 ml-auto">
              <button onClick={() => setAddMode('link')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition ${addMode === 'link' ? 'bg-pink-600/20 text-pink-400' : 'text-carbon-400 hover:text-white'}`}>
                <i className="fas fa-link mr-1" />Link
              </button>
              <button onClick={() => setAddMode('upload')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition ${addMode === 'upload' ? 'bg-pink-600/20 text-pink-400' : 'text-carbon-400 hover:text-white'}`}>
                <i className="fas fa-cloud-upload-alt mr-1" />Upload
              </button>
            </div>
          </div>

          {addMode === 'link' ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="Nome do arquivo" className="bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-pink-500" />
                <div className="relative">
                  <input value={form.drive_url} onChange={e => handleUrlChange(e.target.value)}
                    placeholder="Link (Google Drive, Instagram, ou URL)"
                    className="bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-pink-500 w-full pr-10" />
                  {form.drive_url && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2">
                      <i className={sourceIcon(detectUrlType(form.drive_url))} />
                    </span>
                  )}
                </div>
                <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                  placeholder="Descrição (opcional)" className="bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-pink-500" />
                <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}
                  className="bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-pink-500">
                  <option value="video">Vídeo</option>
                  <option value="foto">Foto</option>
                  <option value="instagram">Instagram</option>
                  <option value="link">Link Útil</option>
                  <option value="politica">Política</option>
                  <option value="manual">Manual</option>
                  <option value="outro">Outro</option>
                </select>
              </div>
              <button onClick={handleAdd} disabled={saving || !form.name || !form.drive_url}
                className="mt-4 bg-pink-600 hover:bg-pink-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition disabled:opacity-50">
                <i className={`fas ${saving ? 'fa-spinner animate-spin' : 'fa-save'} mr-2`} />
                {saving ? 'Salvando...' : 'Salvar'}
              </button>
            </>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="Nome do arquivo" className="bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-pink-500" />
                <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}
                  className="bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-pink-500">
                  <option value="video">Vídeo</option>
                  <option value="foto">Foto</option>
                  <option value="manual">Manual</option>
                  <option value="outro">Outro</option>
                </select>
                <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                  placeholder="Descrição (opcional)" className="bg-carbon-800 border border-carbon-600 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-pink-500" />
                <div>
                  <input type="file" ref={fileRef} className="hidden" onChange={e => setUploadFile(e.target.files[0])} />
                  <button onClick={() => fileRef.current?.click()}
                    className="w-full bg-carbon-800 border border-dashed border-carbon-500 rounded-lg px-3 py-2.5 text-sm hover:border-pink-500 transition flex items-center justify-center gap-2">
                    <i className={`fas ${uploadFile ? 'fa-check text-emerald-400' : 'fa-cloud-upload-alt text-carbon-400'}`} />
                    <span className={uploadFile ? 'text-emerald-400' : 'text-carbon-400'}>
                      {uploadFile ? uploadFile.name : 'Escolher arquivo'}
                    </span>
                  </button>
                </div>
              </div>
              {uploading && (
                <div className="mt-3 bg-carbon-800 rounded-full h-2 overflow-hidden">
                  <div className="bg-pink-500 h-full transition-all duration-500" style={{ width: `${uploadProgress}%` }} />
                </div>
              )}
              <button onClick={handleUpload} disabled={uploading || !form.name || !uploadFile}
                className="mt-4 bg-pink-600 hover:bg-pink-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition disabled:opacity-50">
                <i className={`fas ${uploading ? 'fa-spinner animate-spin' : 'fa-cloud-upload-alt'} mr-2`} />
                {uploading ? 'Enviando...' : 'Upload para Google Drive'}
              </button>
            </>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="flex gap-1.5 bg-carbon-800 rounded-xl p-1.5">
          {CATEGORIES.map(c => (
            <button key={c.id} onClick={() => setCategory(c.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${category === c.id ? 'bg-pink-600/20 text-pink-400' : 'text-carbon-400 hover:text-white hover:bg-carbon-700'}`}>
              <i className={`${c.brand ? 'fab' : 'fas'} ${c.icon} mr-1.5`} />{c.label}
            </button>
          ))}
        </div>
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Buscar mídia..."
          className="bg-carbon-800 border border-carbon-600 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-pink-500 flex-1 min-w-[200px]" />
      </div>

      {/* Grid */}
      {loading ? (
        <div className="text-center py-20"><i className="fas fa-spinner animate-spin text-pink-400 text-2xl" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20">
          <i className="fas fa-photo-video text-carbon-600 text-4xl mb-3" />
          <p className="text-carbon-400">Nenhuma mídia encontrada</p>
          <p className="text-carbon-500 text-sm mt-1">Adicione vídeos, fotos, Instagram e links</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(m => (
            <div key={m.id} className="bg-carbon-700 rounded-xl overflow-hidden border border-carbon-600 hover:border-pink-500/30 transition group">
              {/* Thumbnail */}
              {m.thumbnail_url && m.category !== 'link' && m.category !== 'politica' ? (
                <div className="h-40 bg-carbon-800 relative overflow-hidden">
                  <img src={m.thumbnail_url} alt={m.name} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition"
                    onError={e => { e.target.style.display = 'none' }} />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <i className={`${m.source_type === 'instagram' ? 'fab' : 'fas'} ${catIcons[m.category]?.split(' ')[0] || 'fa-file'} text-3xl text-white/50`} />
                  </div>
                </div>
              ) : (
                <div className="h-28 bg-carbon-800 flex items-center justify-center">
                  <i className={`${m.source_type === 'instagram' || m.category === 'instagram' ? 'fab' : 'fas'} ${catIcons[m.category] || 'fa-file text-carbon-400'} text-3xl`} />
                </div>
              )}
              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <i className={`${sourceIcon(m.source_type)} text-xs`} />
                      <p className="text-white font-medium text-sm truncate">{m.name}</p>
                    </div>
                    {m.description && <p className="text-carbon-400 text-xs mt-1 line-clamp-2">{m.description}</p>}
                  </div>
                  <span className="shrink-0 px-2 py-0.5 rounded-full text-xs bg-carbon-600 text-carbon-300">
                    {CATEGORIES.find(c => c.id === m.category)?.label || m.category}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <a href={m.drive_url} target="_blank" rel="noreferrer"
                    className="flex-1 bg-pink-600/20 text-pink-400 hover:bg-pink-600/40 text-center px-3 py-1.5 rounded-lg text-xs transition">
                    <i className="fas fa-external-link-alt mr-1" />Abrir
                  </a>
                  <button onClick={() => { navigator.clipboard.writeText(m.drive_url); }}
                    className="bg-carbon-600 text-carbon-300 hover:text-white px-3 py-1.5 rounded-lg text-xs transition"
                    title="Copiar link">
                    <i className="fas fa-copy" />
                  </button>
                  <button onClick={() => handleDelete(m.id)}
                    className="bg-red-600/20 text-red-400 hover:bg-red-600/40 px-3 py-1.5 rounded-lg text-xs transition"
                    title="Remover">
                    <i className="fas fa-trash" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
