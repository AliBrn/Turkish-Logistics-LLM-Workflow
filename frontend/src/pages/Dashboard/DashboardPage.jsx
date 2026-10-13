import { AlertTriangle, Bot, CheckCircle2, ClipboardList, MessageSquareText, Package } from 'lucide-react'
import { getDashboardSummary, useWorkflowData } from '../../services/workflowStore'
import './DashboardPage.css'

const cards = [
  { key: 'totalMessages', label: 'Toplam Mesaj', icon: MessageSquareText, tone: 'info' },
  { key: 'processedMessages', label: 'Islenen Mesaj', icon: CheckCircle2, tone: 'success' },
  { key: 'manualMessages', label: 'Manuel Kontrol', icon: ClipboardList, tone: 'warning' },
  { key: 'errorMessages', label: 'Hata', icon: AlertTriangle, tone: 'danger' },
  { key: 'pendingMessages', label: 'Bekleyen', icon: ClipboardList, tone: 'warning' },
  { key: 'totalOrders', label: 'Toplam Siparis', icon: Package, tone: 'accent' },
  { key: 'openIssues', label: 'Acik Sorun', icon: AlertTriangle, tone: 'danger' },
]

export default function DashboardPage() {
  const state = useWorkflowData()
  const summary = getDashboardSummary(state)
  const modelStatus = state.systemStatus?.model
  const healthStatus = state.systemStatus?.health
  const importStatus = state.systemStatus?.import
  const latestMessages = [...state.messages]
    .sort((a, b) => new Date(b.mesaj_tarihi) - new Date(a.mesaj_tarihi))
    .slice(0, 5)

  return (
    <div className="dashboard-page">
      <div className="dashboard-grid">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <section className={`dashboard-card dashboard-card--${card.tone}`} key={card.key}>
              <Icon size={18} />
              <span>{card.label}</span>
              <strong>{summary[card.key] ?? 0}</strong>
            </section>
          )
        })}
      </div>

      <div className="dashboard-panels">
        <section className="dashboard-panel">
          <div className="dashboard-panel__header">
            <h2>Model ve Sistem</h2>
            <Bot size={18} />
          </div>
          <div className="dashboard-system">
            <div>
              <span>Model istemcisi</span>
              <strong>{modelStatus?.active_client || 'Baglanti bekleniyor'}</strong>
            </div>
            <div>
              <span>LM Studio</span>
              <strong>{modelStatus?.lmstudio_url || '-'}</strong>
            </div>
            <div>
              <span>Veritabani</span>
              <strong>{healthStatus?.database || 'kontrol ediliyor'}</strong>
            </div>
            <div>
              <span>JSON import</span>
              <strong>
                {importStatus
                  ? `${importStatus.next_index}/${importStatus.total_records}`
                  : 'kontrol ediliyor'}
              </strong>
            </div>
            <div>
              <span>Validator</span>
              <strong>Aktif</strong>
            </div>
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="dashboard-panel__header">
            <h2>Son Gelen Mesajlar</h2>
            <MessageSquareText size={18} />
          </div>
          <div className="dashboard-message-list">
            {latestMessages.map((message) => (
              <div className="dashboard-message" key={message.id}>
                <div>
                  <strong>{message.firma_adi || message.gonderen_adi}</strong>
                  <p>{message.mesaj_metni}</p>
                </div>
                <span>{message.islem_durumu}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
