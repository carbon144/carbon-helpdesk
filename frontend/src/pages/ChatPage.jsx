import { useState, useCallback } from 'react'
import api from '../services/api'
import ChatList from '../components/chat/ChatList'
import ChatView from '../components/chat/ChatView'

export default function ChatPage({ user }) {
  const [selectedConversation, setSelectedConversation] = useState(null)
  const [selectedCustomer, setSelectedCustomer] = useState(null)

  const handleSelectConversation = useCallback(async (conversation, customer) => {
    setSelectedConversation(conversation)
    if (customer) {
      setSelectedCustomer(customer)
    } else {
      setSelectedCustomer(null)
    }
    if (!customer && conversation?.customer_id) {
      try {
        const res = await api.get(`/customers/${conversation.customer_id}`)
        setSelectedCustomer(res.data)
      } catch {
        setSelectedCustomer(null)
      }
    }
  }, [])

  const handleConversationUpdate = useCallback((updated) => {
    setSelectedConversation(updated)
  }, [])

  return (
    <div className="flex h-full overflow-hidden">
      <ChatList
        activeConversationId={selectedConversation?.id}
        onSelectConversation={handleSelectConversation}
      />
      <ChatView
        conversation={selectedConversation}
        customer={selectedCustomer}
        user={user}
        onConversationUpdate={handleConversationUpdate}
      />
    </div>
  )
}
