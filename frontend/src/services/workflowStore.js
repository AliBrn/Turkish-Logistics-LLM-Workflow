import { useEffect, useState } from 'react'

const API_BASE = 'http://127.0.0.1:8001/api'
const STORAGE_KEY = 'workflow-lojistik-state-v1'
const STORE_EVENT = 'workflow-store-updated'
const REFRESH_INTERVAL_MS = 30 * 1000

export const STATUS_COLUMNS = [
  { key: 'yeni', label: 'Yeni', color: 'var(--info)' },
  { key: 'arac_bekleniyor', label: 'Araç Bekleniyor', color: '#e09600' },
  { key: 'sofore_atandi', label: 'Şoföre Atandı', color: 'var(--accent)' },
  { key: 'sevkiyatta', label: 'Sevkiyatta', color: '#2dd4bf' },
  { key: 'tamamlandi', label: 'Tamamlandı', color: 'var(--success)' },
]

export const ORDER_STATUS_OPTIONS = [
  { key: 'manuel_kontrol', label: 'Manuel Kontrol', color: '#ff6b35' },
  { key: 'inceleniyor', label: 'İnceleniyor', color: 'var(--warning)' },
  { key: 'is_kuyrugunda', label: 'İş Kuyruğunda', color: 'var(--success)' },
  { key: 'bekletiliyor', label: 'Bekletiliyor', color: '#7c8aa5' },
  { key: 'iptal', label: 'İptal', color: 'var(--danger)' },
]

export const MESSAGE_STATUS_LABELS = {
  bekliyor: 'Bekliyor',
  isleniyor: 'İşleniyor',
  islendi: 'İşlendi',
  manuel_kontrol: 'Manuel Kontrol',
  hata: 'Hata',
}

export const STATUS_LABELS = STATUS_COLUMNS.reduce((acc, item) => {
  acc[item.key] = item.label
  return acc
}, {})

ORDER_STATUS_OPTIONS.forEach((item) => {
  STATUS_LABELS[item.key] = item.label
})

const emptyState = {
  messages: [],
  cozumlemeler: [],
  siparisler: [],
  sorunlar: [],
  durumGecmisi: [],
  dashboardSummary: null,
  systemStatus: null,
  apiConnected: false,
}

const fallbackMessages = [
  {
    id: 1,
    harici_mesaj_id: 'ornek-msg-001',
    telefon: '905425307960',
    gonderen_adi: 'Burak Ozhan',
    firma_adi: 'KYR Tasimacilik',
    chat_id: 'local',
    chat_adi: 'BATI KARADENIZ ISLERI',
    mesaj_metni: 'Mersin -> Batman\nYuk: 20 Ton kasa ici makina\nArac Tipi: Acik 1360',
    mesaj_tarihi: '2026-03-30T21:37:09',
    islem_durumu: 'islendi',
    siparis_sayisi: 1,
  },
]

const fallbackOrders = [
  {
    id: 1,
    ham_mesaj_id: 1,
    cozumleme_id: 1,
    siparis_no: 1,
    nereden: 'Mersin',
    nereye: 'Batman',
    yuk_tipi: 'YÜKÜSTÜ',
    arac_tipi: '1360',
    kasa_tipi: 'AÇIK',
    durum: 'is_kuyrugunda',
    operasyon_durumu: 'yeni',
    manuel_duzenlendi_mi: false,
    gonderen_adi: 'Burak Ozhan',
    firma_adi: 'KYR Tasimacilik',
  },
]

function fallbackState() {
  return {
    ...emptyState,
    messages: fallbackMessages,
    siparisler: fallbackOrders,
    cozumlemeler: [
      {
        id: 1,
        ham_mesaj_id: 1,
        ham_model_cevabi: JSON.stringify({ siparis_sayisi: 1, siparisler: fallbackOrders.map(toJsonOrder) }),
        duzeltilmis_json: { siparis_sayisi: 1, siparisler: fallbackOrders.map(toJsonOrder) },
        basarili_mi: true,
        hata_mesaji: '',
      },
    ],
  }
}

function getStoredState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? { ...emptyState, ...JSON.parse(raw) } : fallbackState()
  } catch {
    return fallbackState()
  }
}

function setStoredState(nextState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState))
  window.dispatchEvent(new Event(STORE_EVENT))
}

async function request(path, options) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `API isteği başarısız: ${response.status}`)
  }

  return response.json()
}

async function loadApiState() {
  const [messages, orders, issues, resolutions, dashboardSummary, healthStatus, modelStatus, importStatus] = await Promise.all([
    request('/messages'),
    request('/orders'),
    request('/validation-issues'),
    request('/resolutions'),
    request('/dashboard/summary'),
    request('/health'),
    request('/model/status'),
    request('/import/status'),
  ])

  return {
    ...emptyState,
    apiConnected: true,
    messages: messages.map(normalizeMessage),
    siparisler: orders.map(normalizeOrder),
    sorunlar: issues.map(normalizeIssue),
    cozumlemeler: resolutions.map(normalizeResolution),
    dashboardSummary,
    systemStatus: {
      health: healthStatus,
      model: modelStatus,
      import: importStatus,
    },
  }
}

async function refreshFromApi() {
  try {
    const nextState = await loadApiState()
    setStoredState(nextState)
    return nextState
  } catch (error) {
    console.warn('API verisi alınamadı, yerel yedek veri kullanılıyor:', error)
    return getStoredState()
  }
}

function normalizeMessage(message) {
  const durum = message.islem_durumu
  return {
    ...message,
    islem_durumu: durum,
    mesaj_metni: String(message.mesaj_metni || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n'),
    siparis_sayisi: Number(message.siparis_sayisi || 0),
  }
}

function normalizeOrder(order) {
  return {
    ...order,
    durum: order.durum || 'inceleniyor',
    operasyon_durumu: order.operasyon_durumu || 'yeni',
    arac_tipi: order.arac_tipi || '',
    kasa_tipi: order.kasa_tipi || '',
    yuk_tipi: order.yuk_tipi || '',
  }
}

function normalizeIssue(issue) {
  return {
    ...issue,
    mevcut_deger: issue.mevcut_deger || '',
    onerilen_deger: issue.onerilen_deger || '',
  }
}

function normalizeResolution(record) {
  return {
    ...record,
    duzeltilmis_json: record.duzeltilmis_json || { siparis_sayisi: 0, siparisler: [] },
  }
}

function toJsonOrder(order) {
  return {
    nereden: order.nereden || '',
    nereye: order.nereye || '',
    yuk_tipi: order.yuk_tipi || '',
    arac_tipi: order.arac_tipi || '',
    kasa_tipi: order.kasa_tipi || '',
  }
}

function createResolutionFromOrders(messageId, orders) {
  const jsonOrders = orders.map(toJsonOrder)
  return {
    id: messageId,
    ham_mesaj_id: messageId,
    ham_model_cevabi: JSON.stringify({ siparis_sayisi: jsonOrders.length, siparisler: jsonOrders }),
    duzeltilmis_json: { siparis_sayisi: jsonOrders.length, siparisler: jsonOrders },
    basarili_mi: true,
    hata_mesaji: '',
  }
}

export function resetWorkflowState() {
  refreshFromApi()
}

export function getWorkflowState() {
  return getStoredState()
}

export function useWorkflowData() {
  const [state, setState] = useState(getStoredState)

  useEffect(() => {
    let cancelled = false

    const sync = () => {
      if (!cancelled) setState(getStoredState())
    }

    refreshFromApi().then((nextState) => {
      if (!cancelled) setState(nextState)
    })
    const intervalId = window.setInterval(() => {
      refreshFromApi().then((nextState) => {
        if (!cancelled) setState(nextState)
      })
    }, REFRESH_INTERVAL_MS)

    window.addEventListener(STORE_EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
      window.removeEventListener(STORE_EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  return state
}

export function getMessageOrders(messageId, state = getStoredState()) {
  return state.siparisler.filter((order) => order.ham_mesaj_id === messageId)
}

export async function extractMessage(messageId) {
  // Backend POST /messages/{id}/extract zaten tam ExtractionOut döndürür.
  // Bu cevabı direkt state'e merge ederiz — 5 ayrı API çağrısı YAPMA.
  const result = await request(`/messages/${messageId}/extract`, { method: 'POST' })
  mergeExtractionResult(messageId, result)
  // Sessizce arka plan senkronu (dashboard sayaçları için) — UI beklemiyor.
  refreshFromApi().catch(() => {})
  return result
}

function mergeExtractionResult(messageId, result) {
  const state = getStoredState()
  const newOrders = (result.siparisler || []).map(normalizeOrder)
  const newIssues = (result.sorunlar || []).map(normalizeIssue)

  const hasOrders = newOrders.length > 0
  const hasOpenIssues = newIssues.some((issue) => issue.durum === 'acik')
  const nextStatus = !hasOrders && result.basarili_mi === false
    ? 'hata'
    : hasOpenIssues || result.basarili_mi === false
      ? 'manuel_kontrol'
      : 'islendi'

  const messages = state.messages.map((m) =>
    m.id === messageId
      ? { ...m, islem_durumu: nextStatus, siparis_sayisi: newOrders.length }
      : m
  )

  // o mesaja ait eski sipariş/sorunları çıkar, yenilerini ekle
  const siparisler = [
    ...state.siparisler.filter((o) => o.ham_mesaj_id !== messageId),
    ...newOrders,
  ]
  const sorunlar = [
    ...state.sorunlar.filter((s) => s.ham_mesaj_id !== messageId),
    ...newIssues,
  ]

  // çözümleme kaydı
  const resolution = normalizeResolution({
    id: result.cozumleme_id || messageId,
    ham_mesaj_id: messageId,
    ham_model_cevabi: JSON.stringify(result.duzeltilmis_json || {}),
    duzeltilmis_json: result.duzeltilmis_json,
    basarili_mi: result.basarili_mi,
    hata_mesaji: result.hata_mesaji || '',
  })
  const cozumlemeler = [
    ...state.cozumlemeler.filter((c) => c.ham_mesaj_id !== messageId),
    resolution,
  ]

  setStoredState({ ...state, messages, siparisler, sorunlar, cozumlemeler })
}

export async function updateOrderStatus(orderId, newStatus, note = '') {
  await request(`/orders/${orderId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({
      operasyon_durumu: newStatus,
      not_metni: note || 'Operasyon durumu arayüzden değiştirildi.',
    }),
  })
  await refreshFromApi()
}

export async function updateOrderDecisionStatus(orderId, newStatus) {
  await request(`/orders/${orderId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({
      durum: newStatus,
      not_metni: 'Sipariş karar durumu arayüzden değiştirildi.',
    }),
  })
  await refreshFromApi()
}

export async function updateOrder(orderId, patch) {
  await request(`/orders/${orderId}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })
  await refreshFromApi()
}

export async function saveManualOrdersForMessage(messageId, draftOrders) {
  await request(`/messages/${messageId}/manual-review`, {
    method: 'PATCH',
    body: JSON.stringify({
      orders: draftOrders.map((order) => ({
        id: order.id || null,
        nereden: order.nereden || '',
        nereye: order.nereye || '',
        yuk_tipi: order.yuk_tipi || '',
        arac_tipi: order.arac_tipi || '',
        kasa_tipi: order.kasa_tipi || '',
        durum: order.durum || 'inceleniyor',
      })),
    }),
  })

  await refreshFromApi()
}

export async function resolveIssue(issueId, patch = {}) {
  await request(`/validation-issues/${issueId}/resolve`, {
    method: 'PATCH',
    body: JSON.stringify({
      onerilen_deger: patch.onerilen_deger,
      not_metni: patch.not_metni,
    }),
  })
  await refreshFromApi()
}

export function getDashboardSummary(state = getStoredState()) {
  if (state.dashboardSummary) return state.dashboardSummary

  const totalMessages = state.messages.length
  const processedMessages = state.messages.filter((item) => item.islem_durumu === 'islendi').length
  const waitingMessages = state.messages.filter((item) => item.islem_durumu === 'bekliyor').length
  const processingMessages = state.messages.filter((item) => item.islem_durumu === 'isleniyor').length
  const manualMessages = state.messages.filter((item) => item.islem_durumu === 'manuel_kontrol').length
  const errorMessages = state.messages.filter((item) => item.islem_durumu === 'hata').length
  const openIssues = state.sorunlar.filter((item) => item.durum === 'acik').length

  return {
    totalMessages,
    processedMessages,
    pendingMessages: waitingMessages + processingMessages,
    waitingMessages,
    processingMessages,
    manualMessages,
    errorMessages,
    totalOrders: state.siparisler.length,
    openIssues,
  }
}

export function getMessageResolution(messageId, state = getStoredState()) {
  const matching = state.cozumlemeler.filter((item) => item.ham_mesaj_id === messageId)
  if (matching.length > 0) {
    return matching.reduce((latest, item) => Number(item.id || 0) > Number(latest.id || 0) ? item : latest)
  }
  return createResolutionFromOrders(messageId, getMessageOrders(messageId, state))
}

export function formatStatus(status) {
  return STATUS_LABELS[status] || MESSAGE_STATUS_LABELS[status] || status || 'Belirtilmedi'
}
