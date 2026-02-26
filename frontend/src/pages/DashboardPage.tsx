import { useQuery } from '@tanstack/react-query'
import { applicationsApi } from '../services/api'
import type { ApplicationStats } from '../types'
import { CheckCircle, Eye, Mail, XCircle, Send } from 'lucide-react'

const statCards = [
  { key: 'total', label: 'Всего откликов', icon: Send, color: 'text-gray-600' },
  { key: 'sent', label: 'Отправлено', icon: Mail, color: 'text-blue-600' },
  { key: 'viewed', label: 'Просмотрено', icon: Eye, color: 'text-yellow-600' },
  { key: 'invitation', label: 'Приглашения', icon: CheckCircle, color: 'text-green-600' },
  { key: 'rejection', label: 'Отказы', icon: XCircle, color: 'text-red-600' },
] as const

export default function DashboardPage() {
  const { data: stats } = useQuery<ApplicationStats>({
    queryKey: ['stats'],
    queryFn: () => applicationsApi.stats().then((r) => r.data),
  })

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 mb-6">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {statCards.map(({ key, label, icon: Icon, color }) => (
          <div key={key} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className={`${color} mb-2`}>
              <Icon size={20} />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats?.[key] ?? '—'}</p>
            <p className="text-xs text-gray-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <strong>Внимание:</strong> Автоматические отклики могут нарушать правила hh.ru.
        Используйте инструмент ответственно.
      </div>
    </div>
  )
}
