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
  meu_pedido: 'Meu Pedido',
  garantia: 'Garantia',
  reenvio: 'Reenvio',
  financeiro: 'Financeiro',
  duvida: 'Dúvida',
  reclamacao: 'Reclamação',
}

export const CATEGORY_COLORS = {
  meu_pedido: 'bg-blue-500/10 text-blue-300',
  garantia: 'bg-orange-500/10 text-orange-300',
  reenvio: 'bg-purple-500/10 text-purple-300',
  financeiro: 'bg-green-500/10 text-green-300',
  duvida: 'bg-gray-500/10 text-gray-300',
  reclamacao: 'bg-red-500/10 text-red-300',
}

export const SENTIMENT_LABELS = {
  positive: 'Positivo', neutral: 'Neutro', negative: 'Negativo', angry: 'Irritado',
}

export const TAG_COLORS = {
  guacu: 'bg-red-900/30 text-red-300',
  procon: 'bg-red-900/30 text-red-300',
  advogado: 'bg-red-900/30 text-red-300',
  reclame_aqui: 'bg-red-900/30 text-red-300',
  chargeback: 'bg-pink-900/30 text-pink-300',
  mau_uso: 'bg-orange-900/30 text-orange-300',
  carregador: 'bg-cyan-900/30 text-cyan-300',
  defeito: 'bg-orange-900/30 text-orange-300',
  troca: 'bg-purple-900/30 text-purple-300',
  nf: 'bg-blue-900/30 text-blue-300',
  reembolso: 'bg-green-900/30 text-green-300',
  reincidente: 'bg-yellow-900/30 text-yellow-300',
  revisao_manual: 'bg-yellow-500/10 text-yellow-300',
  ai_auto_reply: 'bg-cyan-500/10 text-cyan-300',
  ai_ack: 'bg-cyan-500/10 text-cyan-300',
  BLACKLIST: 'bg-red-500/10 text-red-300',
  AUTO_ESCALADO: 'bg-orange-500/10 text-orange-300',
  SLA_ESTOURADO: 'bg-red-500/10 text-red-300',
  SLA_ALERTA: 'bg-yellow-500/10 text-yellow-300',
  chat_whatsapp: 'bg-green-500/15 text-green-300',
  chat_instagram: 'bg-pink-500/15 text-pink-300',
  chat_facebook: 'bg-blue-500/15 text-blue-300',
}

export const TAG_LABELS = {
  guacu: 'GUACU/Golpe', procon: 'PROCON', advogado: 'Advogado',
  reclame_aqui: 'Reclame Aqui', chargeback: 'Chargeback',
  mau_uso: 'Mau Uso', carregador: 'Carregador', defeito: 'Defeito',
  troca: 'Troca', nf: 'Nota Fiscal', reembolso: 'Reembolso',
  reincidente: 'Reincidente', revisao_manual: 'Revisão Manual',
  ai_auto_reply: 'IA Respondeu', ai_ack: 'IA Confirmou',
  BLACKLIST: 'Blacklist', AUTO_ESCALADO: 'Auto-Escalado',
  SLA_ESTOURADO: 'SLA Estourado', SLA_ALERTA: 'Alerta SLA',
  chat_whatsapp: 'Via WhatsApp', chat_instagram: 'Via Instagram', chat_facebook: 'Via Facebook',
}

export const PRIORITY_ORDER = { urgent: 4, high: 3, medium: 2, low: 1 }
export const STATUS_ORDER = { escalated: 9, open: 8, in_progress: 7, analyzing: 6, waiting: 5, waiting_supplier: 4, waiting_resend: 3, resolved: 2, closed: 1, archived: 0 }
