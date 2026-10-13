import { Package } from 'lucide-react'
import { ORDER_STATUS_OPTIONS } from '../../services/workflowStore'
import './OrderTable.css'

export default function OrderTable({ orders, selectedOrderId, onOrderSelect, onStatusChange }) {
  if (!orders || orders.length === 0) {
    return (
      <div className="order-table-wrapper">
        <div className="order-table__empty">
          <Package className="order-table__empty-icon" />
          <div className="order-table__empty-text">Sipariş bulunamadı</div>
          <div className="order-table__empty-sub">
            Sol panelden bir mesaj seçerek siparişleri görüntüleyin.
          </div>
        </div>
      </div>
    )
  }

  const renderCell = (value) => {
    if (!value) {
      return <span className="order-table__cell--dimmed">Belirtilmedi</span>
    }
    return value
  }

  return (
    <div className="order-table-wrapper">
      <div className="order-table-container">
        <table className="order-table" id="orders-main-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Nereden</th>
              <th>Nereye</th>
              <th>Araç Tipi</th>
              <th>Yük Tipi</th>
              <th>Kasa Tipi</th>
              <th>Durum</th>
              <th>Firma</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order, index) => (
              <tr
                key={order.id}
                className={selectedOrderId === order.id ? 'order-row--selected' : ''}
                onClick={() => onOrderSelect(order)}
                id={`order-row-${order.id}`}
              >
                <td>{index + 1}</td>
                <td>{order.nereden}</td>
                <td>{order.nereye}</td>
                <td>{renderCell(order.arac_tipi)}</td>
                <td>{renderCell(order.yuk_tipi)}</td>
                <td>{renderCell(order.kasa_tipi)}</td>
                <td>
                  <div className="order-table__status-cell">
                    {onStatusChange && (
                      <select
                        className={`order-table__status-select order-table__status-select--${order.durum}`}
                        value={order.durum}
                        onClick={(event) => event.stopPropagation()}
                        onChange={(event) => {
                          event.stopPropagation()
                          onStatusChange(order.id, event.target.value)
                        }}
                      >
                        {ORDER_STATUS_OPTIONS.map((status) => (
                          <option key={status.key} value={status.key}>
                            {status.label}
                          </option>
                        ))}
                      </select>
                    )}
                    {!onStatusChange && (
                      <span className={`order-table__status-select order-table__status-select--${order.durum}`}>
                        {ORDER_STATUS_OPTIONS.find((status) => status.key === order.durum)?.label || order.durum}
                      </span>
                    )}
                  </div>
                </td>
                <td className="order-table__cell--firma">{order.firma_adi || order.gonderen_adi || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
