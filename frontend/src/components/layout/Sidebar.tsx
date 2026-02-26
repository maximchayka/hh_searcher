import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Search,
  FileText,
  History,
  Bot,
  Settings,
  LogOut,
} from 'lucide-react'
import { useAuthStore } from '../../store/auth'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/search', label: 'Поиск вакансий', icon: Search },
  { to: '/cover-letters', label: 'Сопр. письма', icon: FileText },
  { to: '/history', label: 'История откликов', icon: History },
  { to: '/auto-tasks', label: 'Авто-задачи', icon: Bot },
  { to: '/settings', label: 'Настройки', icon: Settings },
]

export default function Sidebar() {
  const logout = useAuthStore((s) => s.logout)

  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
      <div className="px-4 py-5 border-b border-gray-200">
        <h1 className="text-lg font-bold text-red-600">JobAutoApply</h1>
        <p className="text-xs text-gray-500 mt-0.5">hh.ru автоотклик</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-red-50 text-red-600'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-gray-200">
        <button
          onClick={logout}
          className="flex items-center gap-2.5 px-3 py-2 w-full rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
        >
          <LogOut size={16} />
          Выйти
        </button>
      </div>
    </aside>
  )
}
