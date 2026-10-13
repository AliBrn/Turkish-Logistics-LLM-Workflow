import { formatStatus } from '../../services/workflowStore'
import './StatusBadge.css'

const statusMap = {
  bekliyor: 'bekliyor',
  isleniyor: 'isleniyor',
  islendi: 'islendi',
  hata: 'hata',
  yeni: 'yeni',
  inceleniyor: 'inceleniyor',
  is_kuyrugunda: 'is-kuyrugunda',
  bekletiliyor: 'bekletiliyor',
  sevkiyatta: 'sevkiyatta',
  arac_bekleniyor: 'arac-bekleniyor',
  sofore_atandi: 'sofore-atandi',
  tamamlandi: 'tamamlandi',
  iptal: 'iptal',
  manuel_kontrol: 'manuel-kontrol',
}

export default function StatusBadge({ status }) {
  const key = statusMap[status] || 'yeni'

  return (
    <span className={`status-badge status-badge--${key}`}>
      <span className="status-badge__dot" />
      {formatStatus(status)}
    </span>
  )
}
