import React from 'react'

const CHANNEL_CONFIG = {
  whatsapp: { icon: 'fab fa-whatsapp', label: 'WhatsApp', color: 'text-green-400', bg: 'bg-green-500/10' },
  instagram: { icon: 'fab fa-instagram', label: 'Instagram', color: 'text-pink-400', bg: 'bg-pink-500/10' },
  facebook: { icon: 'fab fa-facebook-messenger', label: 'Facebook', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  gmail: { icon: 'fas fa-envelope', label: 'Email', color: 'text-red-400', bg: 'bg-red-500/10' },
  slack: { icon: 'fab fa-slack', label: 'Slack', color: 'text-purple-400', bg: 'bg-purple-500/10' },
  web: { icon: 'fas fa-globe', label: 'Web', color: 'text-gray-400', bg: 'bg-gray-500/10' },
}

const META_SOURCES = ['whatsapp', 'instagram', 'facebook']

export default function MetaBadge({ source, size = 'sm', showLabel = false, aiAutoMode, className = '' }) {
  const config = CHANNEL_CONFIG[source] || CHANNEL_CONFIG.web
  const sizeClass = size === 'lg' ? 'text-base px-2.5 py-1' : 'text-xs px-1.5 py-0.5'
  const isMeta = META_SOURCES.includes(source)

  return (
    <span className={`inline-flex items-center gap-1 rounded ${config.bg} ${config.color} ${sizeClass} ${className}`}>
      <i className={config.icon} />
      {showLabel && <span>{config.label}</span>}
      {isMeta && aiAutoMode === false && (
        <span className="ml-0.5 text-yellow-400" title="IA Pausada">
          <i className="fas fa-pause-circle text-[10px]" />
        </span>
      )}
      {isMeta && aiAutoMode === true && (
        <span className="ml-0.5 text-emerald-400" title="IA Ativa">
          <i className="fas fa-robot text-[10px]" />
        </span>
      )}
    </span>
  )
}

export { CHANNEL_CONFIG, META_SOURCES }
