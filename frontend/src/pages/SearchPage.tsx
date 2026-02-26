import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { searchApi, applicationsApi, resumesApi } from '../services/api'
import type { Vacancy, Resume } from '../types'
import { ExternalLink, Search } from 'lucide-react'

function formatSalary(salary: Vacancy['salary']): string {
  if (!salary) return 'З/п не указана'
  const parts = []
  if (salary.from) parts.push(`от ${salary.from.toLocaleString('ru')}`)
  if (salary.to) parts.push(`до ${salary.to.toLocaleString('ru')}`)
  return parts.join(' ') + ' ' + salary.currency
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [applying, setApplying] = useState(false)

  const { data: resumes } = useQuery<Resume[]>({
    queryKey: ['resumes'],
    queryFn: () => resumesApi.list().then((r) => r.data),
  })

  const activeResume = resumes?.find((r) => r.is_active)

  const { data, refetch, isFetching } = useQuery<{ items: Vacancy[]; found: number }>({
    queryKey: ['vacancies', query],
    queryFn: () => searchApi.search({ text: query, per_page: 50 }).then((r) => r.data),
    enabled: false,
  })

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (!data) return
    if (selected.size === data.items.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(data.items.map((v) => v.id)))
    }
  }

  const applySelected = async () => {
    if (!activeResume) {
      toast.error('Выберите активное резюме в настройках')
      return
    }
    if (selected.size === 0) {
      toast.error('Выберите хотя бы одну вакансию')
      return
    }
    setApplying(true)
    try {
      const res = await applicationsApi.apply({
        vacancy_ids: Array.from(selected),
        resume_hh_id: activeResume.hh_resume_id,
      })
      toast.success(`Откликнулись на ${res.data.applied.length} вакансий`)
      setSelected(new Set())
    } catch {
      toast.error('Ошибка при отправке откликов')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 mb-4">Поиск вакансий</h1>

      <div className="flex gap-2 mb-4">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && refetch()}
          placeholder="Ключевые слова..."
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
        />
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
        >
          <Search size={14} />
          {isFetching ? 'Поиск...' : 'Найти'}
        </button>
      </div>

      {data && (
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm text-gray-500">Найдено: {data.found}</p>
          <div className="flex gap-2">
            <button
              onClick={toggleAll}
              className="text-sm text-red-600 hover:underline"
            >
              {selected.size === data.items.length ? 'Снять все' : 'Выбрать все'}
            </button>
            {selected.size > 0 && (
              <button
                onClick={applySelected}
                disabled={applying}
                className="px-3 py-1 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
              >
                {applying ? 'Отправка...' : `Откликнуться (${selected.size})`}
              </button>
            )}
          </div>
        </div>
      )}

      <div className="space-y-2">
        {data?.items.map((vacancy) => (
          <div
            key={vacancy.id}
            className={`bg-white border rounded-xl p-4 cursor-pointer transition-colors ${
              selected.has(vacancy.id) ? 'border-red-400 bg-red-50' : 'border-gray-200'
            }`}
            onClick={() => toggle(vacancy.id)}
          >
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={selected.has(vacancy.id)}
                onChange={() => toggle(vacancy.id)}
                onClick={(e) => e.stopPropagation()}
                className="mt-1 accent-red-600"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium text-gray-900 text-sm">{vacancy.name}</p>
                  <a
                    href={vacancy.alternate_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-gray-400 hover:text-red-600 flex-shrink-0"
                  >
                    <ExternalLink size={14} />
                  </a>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  {vacancy.employer.name} · {vacancy.area.name}
                </p>
                <p className="text-xs font-medium text-green-700 mt-1">
                  {formatSalary(vacancy.salary)}
                </p>
                {vacancy.snippet.requirement && (
                  <p
                    className="text-xs text-gray-400 mt-1 line-clamp-2"
                    dangerouslySetInnerHTML={{ __html: vacancy.snippet.requirement }}
                  />
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
