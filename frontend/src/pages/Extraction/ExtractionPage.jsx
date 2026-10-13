import { AlertTriangle, ArrowLeft, Bot, CheckCircle2, ClipboardList, Loader2, MapPin, Package, Play, RefreshCcw, Truck } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import StatusBadge from '../../components/StatusBadge/StatusBadge'
import { extractMessage, getMessageOrders, getMessageResolution, resetWorkflowState, useWorkflowData } from '../../services/workflowStore'
import './ExtractionPage.css'

export default function ExtractionPage() {
  const state = useWorkflowData()
  const navigate = useNavigate()
  const [extracting, setExtracting] = useState(false)
  const [searchParams] = useSearchParams()
  const selectedMessageId = Number(searchParams.get('messageId'))
  const selectedMessage = state.messages.find((message) => message.id === selectedMessageId)
    || state.messages.find((message) => message.islem_durumu !== 'islendi')
    || state.messages[0]
  const orders = selectedMessage ? getMessageOrders(selectedMessage.id, state) : []
  const cozumleme = selectedMessage ? getMessageResolution(selectedMessage.id, state) : null
  const displayJson = buildDisplayJson(cozumleme, orders)
  const modelResponseText = formatModelResponse(cozumleme, displayJson)
  const canRunExtraction = selectedMessage
    ? ['bekliyor', 'hata'].includes(selectedMessage.islem_durumu)
    : false
  const issues = selectedMessage
    ? state.sorunlar.filter((issue) => issue.ham_mesaj_id === selectedMessage.id && issue.durum === 'acik')
    : []

  return (
    <div className="extraction-page">
      <aside className="extraction-list">
        <div className="extraction-list__header">
          <strong>Çözümleme Kuyruğu</strong>
          <button onClick={resetWorkflowState} title="Mock veriyi sıfırla">
            <RefreshCcw size={14} />
          </button>
        </div>
        {state.messages.map((message) => (
          <button
            type="button"
            onClick={() => navigate(`/extraction?messageId=${message.id}`)}
            className={`extraction-message ${message.id === selectedMessage?.id ? 'extraction-message--active' : ''}`}
            key={message.id}
          >
            <strong>{message.firma_adi || message.gonderen_adi}</strong>
            <span className={`extraction-message__status extraction-message__status--${message.islem_durumu}`}>
              {message.islem_durumu}
            </span>
            <p>{message.mesaj_metni}</p>
          </button>
        ))}
      </aside>

      <main className="extraction-main">
        {selectedMessage && (
          <>
            <div className="extraction-toolbar" id={`message-${selectedMessage.id}`}>
              <div>
                <button className="extraction-back-btn" onClick={() => navigate('/raw-messages')}>
                  <ArrowLeft size={14} />
                  Ham Mesajlara Dön
                </button>
                <h2>{selectedMessage.firma_adi || selectedMessage.gonderen_adi}</h2>
                <p>{selectedMessage.chat_adi}</p>
                <div className="extraction-meta-row">
                  <StatusBadge status={selectedMessage.islem_durumu} />
                  <span>{orders.length} sipariş</span>
                  <span>{issues.length} açık sorun</span>
                </div>
              </div>
              <div className="extraction-toolbar__actions">
                {issues.length > 0 && (
                  <button className="extraction-control-btn" onClick={() => navigate(`/validation?messageId=${selectedMessage.id}`)}>
                    <AlertTriangle size={14} />
                    Manuel Kontrol
                  </button>
                )}
                <button
                  className="extraction-run-btn"
                  disabled={extracting || !canRunExtraction}
                  onClick={async () => {
                    if (!canRunExtraction) return
                    setExtracting(true)
                    try { await extractMessage(selectedMessage.id) }
                    finally { setExtracting(false) }
                  }}
                >
                  {extracting ? (
                    <>
                      <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                      AI işliyor...
                    </>
                  ) : selectedMessage.islem_durumu === 'islendi' ? (
                    <>
                      <CheckCircle2 size={14} />
                      Çözümlendi
                    </>
                  ) : selectedMessage.islem_durumu === 'manuel_kontrol' ? (
                    <>
                      <AlertTriangle size={14} />
                      Manuel Kontrol
                    </>
                  ) : selectedMessage.islem_durumu === 'isleniyor' ? (
                    <>
                      <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                      AI işliyor...
                    </>
                  ) : (
                    <>
                      <Play size={14} />
                      AI ile Çözümle
                    </>
                  )}
                </button>
              </div>
            </div>

            <section className="extraction-grid">
              <div className="extraction-panel extraction-panel--message">
                <div className="extraction-panel__title">
                  <ClipboardList size={14} />
                  Ham Mesaj
                </div>
                <pre>{selectedMessage.mesaj_metni}</pre>
              </div>

              <div className="extraction-panel extraction-panel--model">
                <div className="extraction-panel__title">
                  <Bot size={14} />
                  Model Cevabı
                </div>
                <pre>{modelResponseText}</pre>
              </div>

              <div className="extraction-panel extraction-panel--json">
                <div className="extraction-panel__title">
                  <CheckCircle2 size={14} />
                  Düzeltilmiş JSON
                </div>
                <pre>{displayJson ? JSON.stringify(displayJson, null, 2) : 'Henüz çözümleme yok.'}</pre>
              </div>

              <div className="extraction-panel extraction-panel--orders">
                <div className="extraction-panel__title">
                  <Package size={14} />
                  Oluşan Siparişler
                </div>
                {orders.length === 0 ? (
                  <p className="extraction-empty">Sipariş oluşmadı.</p>
                ) : (
                  <div className="extraction-orders">
                    {orders.map((order) => (
                      <div className="extraction-order-card" key={order.id}>
                        <div className="extraction-order-card__route">
                          <div>
                            <span>Nereden</span>
                            <strong>{order.nereden || 'Belirsiz'}</strong>
                          </div>
                          <MapPin size={16} />
                          <div>
                            <span>Nereye</span>
                            <strong>{order.nereye || 'Belirsiz'}</strong>
                          </div>
                        </div>
                        <div className="extraction-order-card__badges">
                          <InfoBadge icon={Package} label="Yük" value={order.yuk_tipi} type="load" />
                          <InfoBadge icon={Truck} label="Araç" value={order.arac_tipi} type="vehicle" />
                          <InfoBadge icon={Package} label="Kasa" value={order.kasa_tipi} type="case" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

function buildDisplayJson(cozumleme, orders) {
  const json = cozumleme?.duzeltilmis_json
  const jsonOrders = Array.isArray(json?.siparisler) ? json.siparisler : []
  if (jsonOrders.length > 0) return json

  if (orders.length > 0) {
    const siparisler = orders.map((order) => ({
      nereden: order.nereden || '',
      nereye: order.nereye || '',
      yuk_tipi: order.yuk_tipi || '',
      arac_tipi: order.arac_tipi || '',
      kasa_tipi: order.kasa_tipi || '',
    }))
    return {
      siparis_sayisi: siparisler.length,
      siparisler,
    }
  }

  return json || null
}

function formatModelResponse(cozumleme, displayJson) {
  if (!cozumleme) return 'Henüz model cevabı yok.'

  const raw = String(cozumleme.ham_model_cevabi || '').trim()
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed?.siparisler) && parsed.siparisler.length > 0) {
        return JSON.stringify(parsed, null, 2)
      }
    } catch {
      if (raw.includes('siparisler')) return raw
    }
  }

  if (displayJson?.siparisler?.length > 0) {
    return JSON.stringify(displayJson, null, 2)
  }

  return raw || cozumleme.hata_mesaji || 'Henüz model cevabı yok.'
}

function InfoBadge({ icon: Icon, label, value, type }) {
  return (
    <span className={`extraction-info-badge extraction-info-badge--${type}`}>
      <Icon size={13} />
      <span>{label}</span>
      <strong>{value || 'Belirsiz'}</strong>
    </span>
  )
}
