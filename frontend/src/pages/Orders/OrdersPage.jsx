import { useMemo, useState } from 'react'
import { Filter, Package, X } from 'lucide-react'
import DetailPanel from '../../components/DetailPanel/DetailPanel'
import MessageCard from '../../components/MessageCard/MessageCard'
import OrderTable from '../../components/OrderTable/OrderTable'
import { getMessageOrders, updateOrderDecisionStatus, useWorkflowData } from '../../services/workflowStore'
import './OrdersPage.css'

export default function OrdersPage() {
  const state = useWorkflowData()
  const [selectedMessage, setSelectedMessage] = useState(null)
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')

  const filteredMessages = useMemo(() => {
    const term = searchTerm.trim().toLowerCase()
    if (!term) return state.messages
    return state.messages.filter((message) =>
      [
        message.gonderen_adi,
        message.firma_adi,
        message.mesaj_metni,
        message.chat_adi,
        message.telefon,
      ]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(term))
    )
  }, [state.messages, searchTerm])

  const displayedOrders = useMemo(() => {
    const orders = selectedMessage
      ? getMessageOrders(selectedMessage.id, state)
      : state.siparisler

    return orders.map((order) => {
      const message = state.messages.find((item) => item.id === order.ham_mesaj_id)
      return {
        ...order,
        gonderen_adi: message?.gonderen_adi,
        firma_adi: message?.firma_adi,
      }
    })
  }, [selectedMessage, state])

  const detailMessage = selectedOrder
    ? state.messages.find((message) => message.id === selectedOrder.ham_mesaj_id)
    : selectedMessage
  const detailOrders = detailMessage ? getMessageOrders(detailMessage.id, state) : []

  const handleMessageClick = (message) => {
    setSelectedMessage(message)
    setSelectedOrder(null)
  }

  const handleOrderSelect = (order) => {
    setSelectedOrder((current) => current?.id === order.id ? null : order)
  }

  const handleClearFilter = () => {
    setSelectedMessage(null)
    setSelectedOrder(null)
  }

  return (
    <div className="orders-page" id="orders-page">
      <div className="orders-page__messages">
        <div className="orders-page__messages-header">
          <div className="orders-page__messages-title">
            Mesajlar
            <span className="orders-page__messages-count">{filteredMessages.length}</span>
          </div>
          <input
            type="text"
            className="orders-page__messages-search"
            placeholder="Mesaj, firma veya grup ara..."
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            id="message-search"
          />
        </div>
        <div className="orders-page__messages-list">
          {filteredMessages.map((message) => (
            <MessageCard
              key={message.id}
              message={message}
              orderCount={getMessageOrders(message.id, state).length}
              isActive={selectedMessage?.id === message.id}
              onClick={handleMessageClick}
            />
          ))}
        </div>
      </div>

      <div className="orders-page__main">
        <div className="orders-page__table-header">
          <div className="orders-page__table-title">
            <Package size={16} />
            Sipariş Tablosu
            <span className="orders-page__table-count">({displayedOrders.length} sipariş)</span>
          </div>
          <div className="orders-page__table-actions">
            {selectedMessage && (
              <button className="orders-page__filter-btn orders-page__filter-btn--active" id="active-filter-badge">
                <Filter size={12} />
                {selectedMessage.firma_adi || selectedMessage.gonderen_adi}
              </button>
            )}
            {selectedMessage && (
              <button className="orders-page__clear-btn" onClick={handleClearFilter} id="clear-filter-btn">
                <X size={12} />
                Filtreyi Temizle
              </button>
            )}
          </div>
        </div>

        <OrderTable
          orders={displayedOrders}
          selectedOrderId={selectedOrder?.id}
          onOrderSelect={handleOrderSelect}
          onStatusChange={updateOrderDecisionStatus}
        />

        {detailMessage && (
          <DetailPanel
            message={detailMessage}
            orders={detailOrders}
            onClose={() => setSelectedOrder(null)}
          />
        )}
      </div>
    </div>
  )
}
