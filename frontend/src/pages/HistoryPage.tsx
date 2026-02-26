import { useQuery } from '@tanstack/react-query'
import { applicationsApi } from '../services/api'
import type { Application } from '../types'
import { formatDistanceToNow } from 'date-fns'
import { ru } from 'date-fns/locale'
import { ExternalLink } from 'lucide-react'

const statusLabels: Record<string, { label: string; className: string }> = {
  sent: { label: 'Отправлено', className: 'bg-blue-100 text-blue-700' },
  viewed: { label: 'Просмотрено', className: 'bg-yellow-100 text-yellow-700' },
  invitation: { label: 'Приглашение', className: 'bg-green-100 text-green-700' },
  rejection: { label: 'Отказ', className: 'bg-red-100 text-red-700' },
  discard: { label: 'Отозвано', className: 'bg-gray-100 text-gray-600' },
}

export default function HistoryPage() {
  const { data: applications = [] } = useQuery<Application[]>({
    queryKey: ['applications'],
    queryFn: () => applicationsApi.list().then((r) => r.data),
  })

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 mb-4">История откликов</h1>

      {applications.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-16">Откликов пока нет</p>
      ) : (
        <div className="space-y-2">
          {applications.map((app) => {
            const s = statusLabels[app.status] ?? statusLabels.sent
            return (
              <div key={app.id} className="bg-white border border-gray-200 rounded-xl p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-gray-900 text-sm">{app.vacancy_title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {app.company_name}
                      {app.salary_display && ` · ${app.salary_display}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${s.className}`}>
                      {s.label}
                    </span>
                    <a
                      href={app.vacancy_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-400 hover:text-red-600"
                    >
                      <ExternalLink size={14} />
                    </a>
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {formatDistanceToNow(new Date(app.applied_at), {
                    addSuffix: true,
                    locale: ru,
                  })}
                </p>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
