import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from '../Sidebar/Sidebar'
import './Layout.css'

const pageTitles = {
  '/': 'Dashboard',
  '/orders': 'Siparişler',
  '/raw-messages': 'Ham Mesajlar',
  '/extraction': 'AI Çözümleme',
  '/validation': 'Doğrulama ve Manuel Kontrol',
  '/workflow': 'İş Sırası Atama',
}

export default function Layout() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'WorkFlow'

  return (
    <div className="layout">
      <Sidebar />
      <div className="layout__content">
        <header className="layout__header">
          <h1 className="layout__header-title">{title}</h1>
          <span className="layout__header-meta">
            {new Date().toLocaleDateString('tr-TR', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </span>
        </header>
        <main className="layout__page">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
