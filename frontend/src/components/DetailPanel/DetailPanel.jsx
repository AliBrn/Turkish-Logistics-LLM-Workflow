import { X, Info } from 'lucide-react'
import './DetailPanel.css'

export default function DetailPanel({ message, orders = [], onClose }) {
  if (!message) return null

  const date = new Date(message.mesaj_tarihi)
  const formattedDate = date.toLocaleDateString('tr-TR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className="detail-panel animate-slide-down" id="detail-panel">
      <div className="detail-panel__header">
        <div className="detail-panel__title">
          <Info className="detail-panel__title-icon" />
          Mesaj Detayları
        </div>
        <button
          className="detail-panel__close"
          onClick={onClose}
          aria-label="Detay panelini kapat"
          id="detail-panel-close"
        >
          <X size={16} />
        </button>
      </div>

      <div className="detail-panel__body">
        <div className="detail-panel__field">
          <span className="detail-panel__label">Gönderen</span>
          <span className="detail-panel__value">{message.gonderen_adi}</span>
        </div>

        <div className="detail-panel__field">
          <span className="detail-panel__label">Telefon</span>
          <span className="detail-panel__value detail-panel__value--mono">
            {message.telefon}
          </span>
        </div>

        <div className="detail-panel__field">
          <span className="detail-panel__label">Grup Adı</span>
          <span className="detail-panel__value">{message.chat_adi}</span>
        </div>

        <div className="detail-panel__field">
          <span className="detail-panel__label">Tarih</span>
          <span className="detail-panel__value">{formattedDate}</span>
        </div>

        <div className="detail-panel__field">
          <span className="detail-panel__label">Sipariş Sayısı</span>
          <span className="detail-panel__value">
            {orders.length} sipariş
          </span>
        </div>

        <div className="detail-panel__field">
          <span className="detail-panel__label">İşlem Durumu</span>
          <span className="detail-panel__value">{message.islem_durumu}</span>
        </div>

        <div className="detail-panel__field" style={{ gridColumn: '1 / -1' }}>
          <span className="detail-panel__label">Ham Mesaj</span>
          <div className="detail-panel__message-body">
            {message.mesaj_metni}
          </div>
        </div>
      </div>
    </div>
  )
}
