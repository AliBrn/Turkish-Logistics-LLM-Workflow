import { AlertCircle, Bot, ClipboardCheck, Eye, Hash, Loader2, MessageSquareText } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import StatusBadge from '../../components/StatusBadge/StatusBadge'
import { extractMessage, getMessageOrders, useWorkflowData } from '../../services/workflowStore'
import './RawMessagesPage.css'

export default function RawMessagesPage() {
  const state = useWorkflowData()
  const navigate = useNavigate()
  const totalOrders = state.siparisler.length
  const [loadingId, setLoadingId] = useState(null)
  const [toast, setToast] = useState(null) // { text, tone }

  const showToast = (text, tone = 'success') => {
    setToast({ text, tone })
    setTimeout(() => setToast(null), 3500)
  }

  const handleAction = async (message) => {
    // bekliyor veya hata → AI çalıştır. islendi → sonucu göster.
    if (message.islem_durumu === 'islendi') {
      navigate(`/extraction?messageId=${message.id}`)
      return
    }
    if (message.islem_durumu === 'manuel_kontrol') {
      navigate(`/validation?messageId=${message.id}`)
      return
    }
    setLoadingId(message.id)
    try {
      const result = await extractMessage(message.id)
      const count = result?.siparisler?.length || 0
      if (count > 0) {
        showToast(`AI çözümleme tamamlandı — ${count} sipariş bulundu.`, 'success')
      } else {
        showToast('AI çözümleme tamamlandı.', 'success')
      }
    } catch (err) {
      showToast(`AI çözümleme hatası: ${err.message || err}`, 'danger')
    } finally {
      setLoadingId(null)
    }
  }

  const getAction = (message) => {
    if (loadingId === message.id) {
      return { label: 'AI işliyor...', icon: Loader2, disabled: true, tone: 'muted', spin: true }
    }
    if (message.islem_durumu === 'isleniyor') {
      return { label: 'AI işliyor...', icon: Loader2, disabled: true, tone: 'muted', spin: true }
    }
    if (message.islem_durumu === 'islendi') {
      return { label: 'Sonucu Gör', icon: Eye, disabled: false, tone: 'success' }
    }
    if (message.islem_durumu === 'manuel_kontrol') {
      return { label: 'Manuel Kontrol', icon: ClipboardCheck, disabled: false, tone: 'warning' }
    }
    if (message.islem_durumu === 'hata') {
      return { label: 'Hatalı — Tekrar Dene', icon: AlertCircle, disabled: false, tone: 'danger' }
    }
    return { label: 'AI ile Çözümle', icon: Bot, disabled: false, tone: 'accent' }
  }

  return (
    <div className="raw-messages-page" id="raw-messages-page">
      {toast && (
        <div
          style={{
            position: 'fixed',
            top: 20,
            right: 20,
            zIndex: 9999,
            padding: '12px 18px',
            borderRadius: 8,
            color: '#fff',
            fontWeight: 500,
            boxShadow: '0 6px 18px rgba(0,0,0,.25)',
            background:
              toast.tone === 'danger' ? '#dc2626' :
              toast.tone === 'warning' ? '#d97706' :
              '#16a34a',
          }}
        >
          {toast.text}
        </div>
      )}
      <div className="raw-messages-page__header">
        <p className="raw-messages-page__title">
          Tüm gelen ham mesajların AI çözümleme ve doğrulama ekranı
        </p>
        <div className="raw-messages-page__stats">
          <div className="raw-messages-page__stat">
            <MessageSquareText size={18} style={{ color: 'var(--accent)' }} />
            <div>
              <div className="raw-messages-page__stat-value">{state.messages.length}</div>
              <div className="raw-messages-page__stat-label">Toplam Mesaj</div>
            </div>
          </div>
          <div className="raw-messages-page__stat">
            <Hash size={18} style={{ color: 'var(--success)' }} />
            <div>
              <div className="raw-messages-page__stat-value">{totalOrders}</div>
              <div className="raw-messages-page__stat-label">Toplam Sipariş</div>
            </div>
          </div>
        </div>
      </div>

      <table className="raw-messages-table" id="raw-messages-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Mesaj İçeriği</th>
            <th>Gönderen</th>
            <th>Numara</th>
            <th>Grup Adı</th>
            <th>Tarih</th>
            <th>AI Durumu</th>
            <th>AI Sipariş</th>
            <th>Aksiyon</th>
          </tr>
        </thead>
        <tbody>
          {state.messages.map((message, index) => {
            const date = new Date(message.mesaj_tarihi)
            const orderCount = getMessageOrders(message.id, state).length
            return (
              <tr key={message.id}>
                <td style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>{index + 1}</td>
                <td className="raw-messages-table__body-cell">{message.mesaj_metni}</td>
                <td>{message.firma_adi || message.gonderen_adi}</td>
                <td className="raw-messages-table__number">{message.telefon}</td>
                <td>{message.chat_adi}</td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  {date.toLocaleDateString('tr-TR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                  })}{' '}
                  {date.toLocaleTimeString('tr-TR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </td>
                <td>
                  <StatusBadge status={message.islem_durumu} />
                </td>
                <td>
                  <span className="badge badge--accent">
                    {orderCount > 0 || message.islem_durumu !== 'bekliyor' ? orderCount : '-'}
                  </span>
                </td>
                <td>
                  {(() => {
                    const action = getAction(message)
                    const Icon = action.icon
                    return (
                      <button
                        className={`raw-messages-table__action raw-messages-table__action--${action.tone}`}
                        onClick={() => handleAction(message)}
                        disabled={action.disabled}
                      >
                        <Icon
                          size={13}
                          style={action.spin ? { animation: 'spin 1s linear infinite' } : {}}
                        />
                        {action.label}
                      </button>
                    )
                  })()}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
