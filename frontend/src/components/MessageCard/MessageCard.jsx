import StatusBadge from '../StatusBadge/StatusBadge'
import './MessageCard.css'

export default function MessageCard({ message, orderCount = 0, isActive, onClick }) {
  const date = new Date(message.mesaj_tarihi)
  const formattedDate = date.toLocaleDateString('tr-TR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div
      className={`message-card ${isActive ? 'message-card--active' : ''}`}
      onClick={() => onClick(message)}
      id={`message-card-${message.id}`}
    >
      <div className="message-card__header">
        <span className="message-card__sender">{message.firma_adi || message.gonderen_adi}</span>
        <span className="message-card__count">{orderCount}</span>
      </div>
      <div className="message-card__body">
        {message.mesaj_metni}
      </div>
      <div className="message-card__footer">
        <span className="message-card__chat">{message.chat_adi}</span>
        <span className="message-card__date">{formattedDate}</span>
      </div>
      <div className="message-card__status">
        <StatusBadge status={message.islem_durumu === 'manuel_kontrol' ? 'manuel_kontrol' : message.islem_durumu === 'islendi' ? 'tamamlandi' : 'yeni'} />
      </div>
    </div>
  )
}
