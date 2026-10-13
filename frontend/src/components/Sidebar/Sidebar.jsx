import { NavLink } from 'react-router-dom'
import { Bot, ClipboardCheck, LayoutDashboard, MessageSquareText, Package, Settings2 } from 'lucide-react'
import './Sidebar.css'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard, badge: null },
  { path: '/raw-messages', label: 'Ham Mesajlar', icon: MessageSquareText, badge: null },
  { path: '/extraction', label: 'AI Çözümleme', icon: Bot, badge: null },
  { path: '/orders', label: 'Siparişler', icon: Package, badge: null },
  { path: '/validation', label: 'Doğrulama', icon: ClipboardCheck, badge: null },
  { path: '/workflow', label: 'İş Sırası', icon: Settings2, badge: null },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">W</div>
        <div>
          <div className="sidebar__title">WorkFlow</div>
          <div className="sidebar__subtitle">Lojistik AI Operasyon</div>
        </div>
      </div>

      <nav className="sidebar__nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
            }
          >
            <item.icon className="sidebar__icon" />
            {item.label}
            {item.badge && <span className="sidebar__badge">{item.badge}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__footer">
        PostgreSQL ve model bağlantısına hazır v1
      </div>
    </aside>
  )
}
