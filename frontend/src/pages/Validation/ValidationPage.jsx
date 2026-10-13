import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, CopyPlus, Minus, Plus, Save, Wrench } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import {
  getMessageOrders,
  saveManualOrdersForMessage,
  useWorkflowData,
} from '../../services/workflowStore'
import './ValidationPage.css'

const LOAD_OPTIONS = ['', 'KOMPLE', 'PARÇA', 'PALETLİ', 'DÖKME', 'YÜKÜSTÜ']
const VEHICLE_OPTIONS = ['', '1360', '860', '10 TEKER', '8 TEKER', '6 TEKER', '4 TEKER', '40 AYAK', 'KAMYONET', 'KIRKAYAK', 'PIKUP']
const CASE_OPTIONS = ['', 'AÇIK', 'KAPALI', 'AÇIK + KAPALI', 'DAMPERLİ', 'FRİGO', 'LOWBED', 'MEGA', 'AÇIK + DAMPERLİ', 'AÇIK + KAPALI + DAMPERLİ', 'AÇIK + KAPALI + LOWBED']

const emptyOrder = () => ({
  nereden: '',
  nereye: '',
  yuk_tipi: '',
  arac_tipi: '',
  kasa_tipi: '',
  durum: 'yeni',
})

export default function ValidationPage() {
  const state = useWorkflowData()
  const [searchParams] = useSearchParams()
  const selectedMessageId = Number(searchParams.get('messageId'))
  const openIssues = state.sorunlar.filter((issue) => issue.durum === 'acik')

  const messagesForControl = useMemo(() => {
    if (selectedMessageId) {
      return state.messages.filter((message) => message.id === selectedMessageId)
    }

    const messageIds = new Set(openIssues.map((issue) => issue.ham_mesaj_id))
    return state.messages.filter((message) => messageIds.has(message.id))
  }, [openIssues, selectedMessageId, state.messages])

  return (
    <div className="validation-page">
      <div className="validation-header">
        <div>
          <h2>Doğrulama ve Manuel Kontrol</h2>
          <p>
            AI çıktısını mesaj bazlı kontrol edin; sipariş sayısını ve her siparişin beş alanını tek ekranda düzeltin.
          </p>
        </div>
        <span>{openIssues.length} açık sorun</span>
      </div>

      <div className="validation-list">
        {messagesForControl.length === 0 ? (
          <div className="validation-empty">
            <CheckCircle2 size={22} />
            Açık doğrulama sorunu yok.
          </div>
        ) : (
          messagesForControl.map((message) => (
            <MessageOrderEditor
              key={message.id}
              message={message}
              orders={getMessageOrders(message.id, state)}
              issues={state.sorunlar.filter((issue) => issue.ham_mesaj_id === message.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

function MessageOrderEditor({ message, orders, issues }) {
  const [draftOrders, setDraftOrders] = useState(() => orders.length ? orders.map(copyOrder) : [emptyOrder()])
  const [saving, setSaving] = useState(false)
  const [saveNotice, setSaveNotice] = useState(null)

  useEffect(() => {
    setDraftOrders(orders.length ? orders.map(copyOrder) : [emptyOrder()])
    setSaveNotice(null)
  }, [message.id])

  const openIssueCount = issues.filter((issue) => issue.durum === 'acik').length

  const setOrderCount = (count) => {
    const nextCount = Math.max(1, Number(count) || 1)
    setDraftOrders((current) => {
      if (nextCount === current.length) return current
      if (nextCount > current.length) {
        return [...current, ...Array.from({ length: nextCount - current.length }, emptyOrder)]
      }
      return current.slice(0, nextCount)
    })
  }

  const updateDraft = (index, field, value) => {
    setDraftOrders((current) =>
      current.map((order, orderIndex) =>
        orderIndex === index ? { ...order, [field]: value } : order
      )
    )
  }

  const addOrder = () => setDraftOrders((current) => [...current, emptyOrder()])
  const removeOrder = (index) => {
    setDraftOrders((current) => current.length === 1 ? current : current.filter((_, itemIndex) => itemIndex !== index))
  }

  const saveOrders = async () => {
    setSaving(true)
    setSaveNotice(null)
    try {
      await saveManualOrdersForMessage(message.id, draftOrders)
      setSaveNotice({ type: 'success', text: 'Kaydedildi. Eksik alan yoksa mesaj Sonucu Gör durumuna geçti.' })
    } catch (error) {
      setSaveNotice({ type: 'error', text: error.message || 'Kaydetme sırasında hata oluştu.' })
    } finally {
      setSaving(false)
    }
  }

  const useAiOrders = () => {
    setDraftOrders(orders.length ? orders.map(copyOrder) : [emptyOrder()])
  }

  return (
    <section className="validation-editor">
      <div className="validation-editor__header">
        <div>
          <div className="validation-editor__title">
            <Wrench size={15} />
            {message.firma_adi || message.gonderen_adi}
          </div>
          <div className="validation-editor__meta">
            {message.chat_adi} · {message.telefon}
          </div>
        </div>
        <div className="validation-editor__issue-count">
          {openIssueCount} açık sorun
        </div>
      </div>

      <div className="validation-editor__body">
        <div className="validation-editor__message">
          <div className="validation-editor__section-title">Ham Mesaj</div>
          <pre>{message.mesaj_metni}</pre>
        </div>

        <div className="validation-ai-result">
          <div className="validation-ai-result__header">
            <div>
              <div className="validation-editor__section-title">AI Çıktısı</div>
              <p>Modelin çıkardığı siparişleri referans olarak kontrol edin.</p>
            </div>
            <button className="validation-editor__secondary-btn" onClick={useAiOrders}>
              AI Çıktısını Taslağa Al
            </button>
          </div>

          {orders.length === 0 ? (
            <div className="validation-ai-result__empty">Bu mesaj için henüz AI siparişi oluşmadı.</div>
          ) : (
            <div className="validation-ai-orders">
              {orders.map((order) => (
                <div className="validation-ai-order" key={order.id}>
                  <strong>{order.siparis_no}. {order.nereden || 'Belirsiz'} → {order.nereye || 'Belirsiz'}</strong>
                  <span>{order.yuk_tipi || 'Yük yok'} · {order.arac_tipi || 'Araç yok'} · {order.kasa_tipi || 'Kasa yok'}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="validation-editor__controls">
          <div className="validation-editor__section-title validation-editor__manual-title">Manuel Düzenleme</div>
          <label className="validation-editor__count">
            Sipariş sayısı
            <input
              type="number"
              min="1"
              value={draftOrders.length}
              onChange={(event) => setOrderCount(event.target.value)}
            />
          </label>
          <button className="validation-editor__secondary-btn" onClick={addOrder}>
            <CopyPlus size={14} />
            Sipariş Ekle
          </button>
          <button className="validation-editor__save-btn" onClick={saveOrders} disabled={saving}>
            <Save size={14} />
            {saving ? 'Kaydediliyor...' : 'Kaydet'}
          </button>
          {saveNotice ? (
            <div className={`validation-editor__save-notice validation-editor__save-notice--${saveNotice.type}`}>
              {saveNotice.text}
            </div>
          ) : null}
        </div>

        <div className="validation-orders">
          {draftOrders.map((order, index) => (
            <div className="validation-order-row" key={`${order.id || 'new'}-${index}`}>
              <div className="validation-order-row__head">
                <strong>{index + 1}. Sipariş</strong>
                <button
                  className="validation-order-row__remove"
                  onClick={() => removeOrder(index)}
                  disabled={draftOrders.length === 1}
                  title="Siparişi kaldır"
                >
                  <Minus size={14} />
                </button>
              </div>

              <label>
                Nereden
                <input value={order.nereden} onChange={(event) => updateDraft(index, 'nereden', event.target.value)} />
              </label>
              <label>
                Nereye
                <input value={order.nereye} onChange={(event) => updateDraft(index, 'nereye', event.target.value)} />
              </label>
              <SelectField label="Yük Tipi" value={order.yuk_tipi} options={LOAD_OPTIONS} onChange={(value) => updateDraft(index, 'yuk_tipi', value)} />
              <SelectField label="Araç Tipi" value={order.arac_tipi} options={VEHICLE_OPTIONS} onChange={(value) => updateDraft(index, 'arac_tipi', value)} />
              <SelectField label="Kasa Tipi" value={order.kasa_tipi} options={CASE_OPTIONS} onChange={(value) => updateDraft(index, 'kasa_tipi', value)} />
            </div>
          ))}
        </div>

        <button className="validation-editor__add-row" onClick={addOrder}>
          <Plus size={14} />
          Bir Sipariş Daha Ekle
        </button>
      </div>
    </section>
  )
}

function SelectField({ label, value, options, onChange }) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option || 'empty'} value={option}>
            {option || 'Seç'}
          </option>
        ))}
      </select>
    </label>
  )
}

function copyOrder(order) {
  return {
    id: order.id,
    nereden: order.nereden || '',
    nereye: order.nereye || '',
    yuk_tipi: order.yuk_tipi || '',
    arac_tipi: order.arac_tipi || '',
    kasa_tipi: order.kasa_tipi || '',
    durum: order.durum || 'inceleniyor',
  }
}
