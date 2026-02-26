import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { jobTasksApi, searchApi, coverLettersApi } from '../services/api'
import type { JobTask, SearchTemplate, CoverLetterTemplate } from '../types'
import { Play, Pause, Trash2, Plus, ChevronDown } from 'lucide-react'

const FREQ_LABELS: Record<string, string> = {
  '15min': 'Каждые 15 мин',
  '30min': 'Каждые 30 мин',
  '1h': 'Каждый час',
  daily: 'Ежедневно',
  custom: 'Cron',
}

const STATUS_CLASSES: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  paused: 'bg-gray-100 text-gray-600',
  error: 'bg-red-100 text-red-700',
  completed: 'bg-blue-100 text-blue-700',
  limit_reached: 'bg-yellow-100 text-yellow-700',
}

export default function AutoTasksPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: '',
    search_template_id: '',
    cover_letter_template_id: '',
    frequency: '1h',
    action: 'auto_apply',
    daily_limit: 50,
    per_run_limit: 20,
  })

  const { data: tasks = [] } = useQuery<JobTask[]>({
    queryKey: ['job-tasks'],
    queryFn: () => jobTasksApi.list().then((r) => r.data),
  })

  const { data: searchTemplates = [] } = useQuery<SearchTemplate[]>({
    queryKey: ['search-templates'],
    queryFn: () => searchApi.listTemplates().then((r) => r.data),
  })

  const { data: coverTemplates = [] } = useQuery<CoverLetterTemplate[]>({
    queryKey: ['cover-letters'],
    queryFn: () => coverLettersApi.list().then((r) => r.data),
  })

  const createMut = useMutation({
    mutationFn: () =>
      jobTasksApi.create({
        ...form,
        search_template_id: Number(form.search_template_id),
        cover_letter_template_id: form.cover_letter_template_id
          ? Number(form.cover_letter_template_id)
          : null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['job-tasks'] })
      toast.success('Задача создана')
      setShowForm(false)
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => jobTasksApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['job-tasks'] })
      toast.success('Задача удалена')
    },
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      jobTasksApi.update(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-tasks'] }),
  })

  const runMut = useMutation({
    mutationFn: (id: number) => jobTasksApi.runNow(id),
    onSuccess: () => toast.success('Задача запущена'),
  })

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-gray-900">Авто-задачи</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700"
        >
          <Plus size={14} />
          Новая задача
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4 space-y-3">
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Название задачи"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          />
          <select
            value={form.search_template_id}
            onChange={(e) => setForm({ ...form, search_template_id: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value="">-- Шаблон поиска --</option>
            {searchTemplates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <select
            value={form.cover_letter_template_id}
            onChange={(e) => setForm({ ...form, cover_letter_template_id: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value="">-- Без сопр. письма --</option>
            {coverTemplates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <div className="grid grid-cols-2 gap-2">
            <select
              value={form.frequency}
              onChange={(e) => setForm({ ...form, frequency: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              {Object.entries(FREQ_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <select
              value={form.action}
              onChange={(e) => setForm({ ...form, action: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="auto_apply">Авто-отклик</option>
              <option value="manual_review">Ручной просмотр</option>
              <option value="notify_only">Только уведомление</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs text-gray-600">
              Дневной лимит
              <input
                type="number"
                value={form.daily_limit}
                onChange={(e) => setForm({ ...form, daily_limit: Number(e.target.value) })}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </label>
            <label className="text-xs text-gray-600">
              За запуск
              <input
                type="number"
                value={form.per_run_limit}
                onChange={(e) => setForm({ ...form, per_run_limit: Number(e.target.value) })}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </label>
          </div>
          <button
            onClick={() => createMut.mutate()}
            disabled={!form.name || !form.search_template_id}
            className="w-full py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
          >
            Создать задачу
          </button>
        </div>
      )}

      <div className="space-y-3">
        {tasks.map((task) => (
          <div key={task.id} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium text-gray-900 text-sm">{task.name}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {FREQ_LABELS[task.frequency]} · лимит {task.daily_limit}/день
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    STATUS_CLASSES[task.status] ?? ''
                  }`}
                >
                  {task.status}
                </span>
                <button
                  onClick={() =>
                    toggleMut.mutate({
                      id: task.id,
                      status: task.status === 'active' ? 'paused' : 'active',
                    })
                  }
                  className="text-gray-400 hover:text-gray-700"
                  title={task.status === 'active' ? 'Пауза' : 'Запустить'}
                >
                  {task.status === 'active' ? <Pause size={15} /> : <Play size={15} />}
                </button>
                <button
                  onClick={() => runMut.mutate(task.id)}
                  className="text-gray-400 hover:text-green-600"
                  title="Запустить сейчас"
                >
                  <Play size={15} />
                </button>
                <button
                  onClick={() => deleteMut.mutate(task.id)}
                  className="text-gray-400 hover:text-red-600"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          </div>
        ))}
        {tasks.length === 0 && !showForm && (
          <p className="text-sm text-gray-400 text-center py-16">Нет задач. Создайте первую!</p>
        )}
      </div>
    </div>
  )
}
