export const STATUS_COLORS = {
  open: 'bg-blue-500/10 text-blue-300',
  in_progress: 'bg-yellow-500/10 text-yellow-300',
  waiting: 'bg-orange-500/10 text-orange-300',
  waiting_supplier: 'bg-orange-500/10 text-orange-300',
  waiting_resend: 'bg-orange-500/10 text-orange-300',
  analyzing: 'bg-blue-500/10 text-blue-300',
  resolved: 'bg-green-500/10 text-green-300',
  closed: 'bg-gray-500/10 text-gray-300',
  escalated: 'bg-blue-500/10 text-blue-300',
  archived: 'bg-gray-500/10 text-gray-400',
}

export const PRIORITY_COLORS = {
  low: 'bg-gray-500/10 text-gray-300',
  medium: 'bg-blue-500/10 text-blue-300',
  high: 'bg-orange-500/10 text-orange-300',
  urgent: 'bg-red-500/10 text-red-300',
}

export const STATUS_LABELS = {
  open: 'Aberto',
  in_progress: 'Aberto',
  waiting: 'Aguardando Cliente',
  waiting_supplier: 'Aguardando Cliente',
  waiting_resend: 'Aguardando Cliente',
  analyzing: 'Aberto',
  resolved: 'Resolvido',
  closed: 'Fechado',
  escalated: 'Aberto',
  archived: 'Arquivado',
}

export const PRIORITY_LABELS = {
  low: 'Baixa', medium: 'Média', high: 'Alta', urgent: 'Urgente',
}

export const CATEGORY_LABELS = {
  chargeback: 'Chargeback',
  ra_procon_juridico: 'RA/Procon/Jurídico',
  garantia_devolucoes: 'Garantia/Devoluções/Assistência',
  cancelamento: 'Cancelamento',
  entrega_rastreio: 'Entrega/Rastreio',
  pre_venda: 'Pré-Venda',
  // Legacy categories (mapped for backward compat)
  reclame_aqui: 'RA/Procon/Jurídico',
  procon: 'RA/Procon/Jurídico',
  juridico: 'RA/Procon/Jurídico',
  defeito_garantia: 'Garantia/Devoluções/Assistência',
  troca: 'Garantia/Devoluções/Assistência',
  garantia: 'Garantia/Devoluções/Assistência',
  mau_uso: 'Garantia/Devoluções/Assistência',
  reenvio: 'Entrega/Rastreio',
  rastreamento: 'Entrega/Rastreio',
  duvida: 'Pré-Venda',
  sugestao: 'Pré-Venda',
  elogio: 'Pré-Venda',
  outros: 'Pré-Venda',
  carregador: 'Garantia/Devoluções/Assistência',
  reclamacao: 'RA/Procon/Jurídico',
  suporte_tecnico: 'Garantia/Devoluções/Assistência',
  financeiro: 'Cancelamento',
}

export const SENTIMENT_LABELS = {
  positive: 'Positivo', neutral: 'Neutro', negative: 'Negativo', angry: 'Irritado',
}

export const TAG_COLORS = {
  garantia: 'bg-blue-900/30 text-blue-300',
  troca: 'bg-purple-900/30 text-purple-300',
  carregador: 'bg-cyan-900/30 text-cyan-300',
  mau_uso: 'bg-orange-900/30 text-orange-300',
  procon: 'bg-red-900/30 text-red-300',
  chargeback: 'bg-pink-900/30 text-pink-300',
  duvida: 'bg-blue-900/30 text-blue-300',
  reclamacao: 'bg-red-900/30 text-red-300',
  juridico: 'bg-red-900/30 text-red-300',
  suporte_tecnico: 'bg-cyan-900/30 text-cyan-300',
  BLACKLIST: 'bg-red-500/10 text-red-300',
  AUTO_ESCALADO: 'bg-orange-500/10 text-orange-300',
  SLA_ESTOURADO: 'bg-red-500/10 text-red-300',
  SLA_ALERTA: 'bg-yellow-500/10 text-yellow-300',
}

export const TAG_LABELS = {
  garantia: 'Garantia', troca: 'Troca', carregador: 'Carregador',
  mau_uso: 'Mau Uso', procon: 'PROCON', chargeback: 'Chargeback',
  duvida: 'Dúvida', reclamacao: 'Reclamação', juridico: 'Jurídico',
  suporte_tecnico: 'Suporte Técnico',
  BLACKLIST: 'Blacklist', AUTO_ESCALADO: 'Auto-Escalado',
  SLA_ESTOURADO: 'SLA Estourado', SLA_ALERTA: 'Alerta SLA',
}

export const PRIORITY_ORDER = { urgent: 4, high: 3, medium: 2, low: 1 }
export const STATUS_ORDER = { escalated: 9, open: 8, in_progress: 7, analyzing: 6, waiting: 5, waiting_supplier: 4, waiting_resend: 3, resolved: 2, closed: 1, archived: 0 }
