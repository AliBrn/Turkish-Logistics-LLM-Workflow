import { useState } from 'react'
import { ArrowRight, Calendar, GripVertical, MapPin, MessageSquare, Package, Phone, Truck, User, X } from 'lucide-react'
import StatusBadge from '../../components/StatusBadge/StatusBadge'
import { STATUS_COLUMNS, formatStatus, updateOrderStatus, useWorkflowData } from '../../services/workflowStore'
import './WorkflowPage.css'

export default function WorkflowPage() {
  const state = useWorkflowData()
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [draggedOrderId, setDraggedOrderId] = useState(null)
  const [dragOverColumn, setDragOverColumn] = useState(null)

  const enrichedOrders = state.siparisler
    .filter((order) => order.durum === 'is_kuyrugunda')
    .map((order) => {
      const message = state.messages.find((item) => item.id === order.ham_mesaj_id)
      return { ...order, operasyon_durumu: order.operasyon_durumu || 'yeni', message }
    })

  const groupedOrders = STATUS_COLUMNS.reduce((acc, column) => {
    acc[column.key] = enrichedOrders.filter((order) => order.operasyon_durumu === column.key)
    return acc
  }, {})

  const handleDragStart = (event, orderId) => {
    setDraggedOrderId(orderId)
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(orderId))
  }

  const handleDrop = (event, targetStatus) => {
    event.preventDefault()
    setDragOverColumn(null)
    if (!draggedOrderId) return
    updateOrderStatus(draggedOrderId, targetStatus)
    setDraggedOrderId(null)
  }

  const handleCloseModal = () => setSelectedOrder(null)
  const selectedMessage = selectedOrder?.message

  return (
    <div className="workflow-page" id="workflow-page">
      <div className="workflow-page__header">
        <p className="workflow-page__title">
          İş kuyruğuna alınan siparişlerin operasyon durumunu takip edin.
        </p>
        <div className="workflow-page__stats">
          <span className="workflow-page__stat-item">
            İş Kuyruğu: <strong>{enrichedOrders.length}</strong>
          </span>
        </div>
      </div>

      <div className="workflow-page__board">
        {STATUS_COLUMNS.map((column) => {
          const columnOrders = groupedOrders[column.key] || []
          const isOver = dragOverColumn === column.key
          return (
            <div
              className={`workflow-column ${isOver ? 'workflow-column--drag-over' : ''}`}
              key={column.key}
              onDragOver={(event) => {
                event.preventDefault()
                setDragOverColumn(column.key)
              }}
              onDragLeave={() => setDragOverColumn(null)}
              onDrop={(event) => handleDrop(event, column.key)}
            >
              <div className="workflow-column__header">
                <div className="workflow-column__title">
                  <span className="workflow-column__dot" style={{ background: column.color }} />
                  {column.label}
                </div>
                <span className="workflow-column__count">{columnOrders.length}</span>
              </div>
              <div className="workflow-column__body">
                {columnOrders.length === 0 ? (
                  <div className="workflow-column__empty">
                    {isOver ? 'Buraya bırak' : 'Sipariş yok'}
                  </div>
                ) : (
                  columnOrders.map((order) => (
                    <div
                      className={`workflow-card ${draggedOrderId === order.id ? 'workflow-card--dragging' : ''}`}
                      key={order.id}
                      draggable
                      onDragStart={(event) => handleDragStart(event, order.id)}
                      onDragEnd={() => {
                        setDraggedOrderId(null)
                        setDragOverColumn(null)
                      }}
                      onClick={() => setSelectedOrder(order)}
                    >
                      <div className="workflow-card__drag-handle">
                        <GripVertical size={14} />
                      </div>
                      <div className="workflow-card__content">
                        <div className="workflow-card__route">
                          {order.nereden}
                          <ArrowRight size={12} className="workflow-card__arrow" />
                          {order.nereye}
                        </div>
                        <div className="workflow-card__meta">{order.message?.firma_adi || order.message?.gonderen_adi}</div>
                        <div className="workflow-card__details">
                          {order.kasa_tipi && <span className="workflow-card__tag">{order.kasa_tipi}</span>}
                          {order.arac_tipi && <span className="workflow-card__tag">{order.arac_tipi}</span>}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )
        })}
      </div>

      {selectedOrder && selectedMessage && (
        <div className="workflow-modal-overlay" onClick={handleCloseModal}>
          <div className="workflow-modal animate-fade-in" onClick={(event) => event.stopPropagation()}>
            <div className="workflow-modal__header">
              <h3 className="workflow-modal__title">Sipariş Detayı</h3>
              <button className="workflow-modal__close" onClick={handleCloseModal} aria-label="Kapat">
                <X size={18} />
              </button>
            </div>

            <div className="workflow-modal__body">
              <div className="workflow-modal__route-card">
                <div className="workflow-modal__route-from">
                  <MapPin size={16} className="workflow-modal__route-icon" />
                  <div>
                    <div className="workflow-modal__route-label">Nereden</div>
                    <div className="workflow-modal__route-value">{selectedOrder.nereden}</div>
                  </div>
                </div>
                <div className="workflow-modal__route-arrow"><ArrowRight size={20} /></div>
                <div className="workflow-modal__route-to">
                  <MapPin size={16} className="workflow-modal__route-icon workflow-modal__route-icon--accent" />
                  <div>
                    <div className="workflow-modal__route-label">Nereye</div>
                    <div className="workflow-modal__route-value">{selectedOrder.nereye}</div>
                  </div>
                </div>
              </div>

              <div className="workflow-modal__grid">
                <InfoField icon={Truck} label="Araç Tipi" value={selectedOrder.arac_tipi || 'Belirtilmedi'} />
                <InfoField icon={Package} label="Yük Tipi" value={selectedOrder.yuk_tipi || 'Belirtilmedi'} />
                <InfoField icon={Package} label="Kasa Tipi" value={selectedOrder.kasa_tipi || 'Belirtilmedi'} />
                <div className="workflow-modal__field">
                  <span className="workflow-modal__field-label">Durum</span>
                  <span className="workflow-modal__field-value"><StatusBadge status={selectedOrder.operasyon_durumu || 'yeni'} /></span>
                </div>
              </div>

              <div className="workflow-modal__section-title">Gönderen Bilgileri</div>
              <div className="workflow-modal__grid">
                <InfoField icon={User} label="Firma" value={selectedMessage.firma_adi || selectedMessage.gonderen_adi} />
                <InfoField icon={Phone} label="Numara" value={selectedMessage.telefon} mono />
                <InfoField icon={MessageSquare} label="Grup" value={selectedMessage.chat_adi} />
                <InfoField icon={Calendar} label="Tarih" value={new Date(selectedMessage.mesaj_tarihi).toLocaleString('tr-TR')} />
              </div>

              <div className="workflow-modal__section-title">Ham Mesaj</div>
              <div className="workflow-modal__message-body">{selectedMessage.mesaj_metni}</div>

              <div className="workflow-modal__section-title">Durum Değiştir</div>
              <div className="workflow-modal__status-row">
                <div className="workflow-modal__current-status">
                  <span className="workflow-modal__field-label">Mevcut:</span>
                  <StatusBadge status={selectedOrder.operasyon_durumu || 'yeni'} />
                </div>
                <select
                  className="workflow-modal__status-select"
                  value={selectedOrder.operasyon_durumu || 'yeni'}
                  onChange={(event) => updateOrderStatus(selectedOrder.id, event.target.value)}
                  id="status-select"
                >
                  {STATUS_COLUMNS.map((column) => (
                    <option key={column.key} value={column.key}>
                      {formatStatus(column.key)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function InfoField({ icon: Icon, label, value, mono }) {
  return (
    <div className="workflow-modal__field">
      <Icon size={14} className="workflow-modal__field-icon" />
      <span className="workflow-modal__field-label">{label}</span>
      <span className={`workflow-modal__field-value ${mono ? 'workflow-modal__field-value--mono' : ''}`}>{value}</span>
    </div>
  )
}
