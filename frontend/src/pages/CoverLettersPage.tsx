import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { coverLettersApi } from '../services/api'
import type { CoverLetterTemplate } from '../types'
import { Plus, Trash2, Edit2, Save, X } from 'lucide-react'

const VARIABLES = ['{{company_name}}', '{{vacancy_title}}', '{{skills}}', '{{salary}}', '{{hr_name}}']

export default function CoverLettersPage() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<CoverLetterTemplate | null>(null)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [body, setBody] = useState('')

  const { data: templates = [] } = useQuery<CoverLetterTemplate[]>({
    queryKey: ['cover-letters'],
    queryFn: () => coverLettersApi.list().then((r) => r.data),
  })

  const createMut = useMutation({
    mutationFn: () => coverLettersApi.create(name, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cover-letters'] })
      toast.success('Шаблон создан')
      setCreating(false)
      setName('')
      setBody('')
    },
  })

  const updateMut = useMutation({
    mutationFn: () => coverLettersApi.update(editing!.id, { name, body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cover-letters'] })
      toast.success('Шаблон обновлён')
      setEditing(null)
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => coverLettersApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cover-letters'] })
      toast.success('Удалено')
    },
  })

  const startEdit = (tmpl: CoverLetterTemplate) => {
    setEditing(tmpl)
    setName(tmpl.name)
    setBody(tmpl.body)
    setCreating(false)
  }

  const startCreate = () => {
    setCreating(true)
    setEditing(null)
    setName('')
    setBody('')
  }

  const insertVar = (v: string) => setBody((b) => b + v)

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-gray-900">Сопроводительные письма</h1>
        <button
          onClick={startCreate}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700"
        >
          <Plus size={14} />
          Новый шаблон
        </button>
      </div>

      {(creating || editing) && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            {creating ? 'Новый шаблон' : 'Редактирование'}
          </h2>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Название шаблона"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-2 focus:outline-none focus:ring-2 focus:ring-red-500"
          />
          <div className="flex flex-wrap gap-1 mb-2">
            {VARIABLES.map((v) => (
              <button
                key={v}
                onClick={() => insertVar(v)}
                className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200"
              >
                {v}
              </button>
            ))}
          </div>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Текст письма..."
            rows={8}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 font-mono"
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => (creating ? createMut.mutate() : updateMut.mutate())}
              disabled={!name || !body}
              className="flex items-center gap-1 px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
            >
              <Save size={14} />
              Сохранить
            </button>
            <button
              onClick={() => {
                setCreating(false)
                setEditing(null)
              }}
              className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200"
            >
              <X size={14} />
              Отмена
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {templates.map((tmpl) => (
          <div key={tmpl.id} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-start justify-between">
              <p className="font-medium text-gray-900 text-sm">{tmpl.name}</p>
              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(tmpl)}
                  className="text-gray-400 hover:text-gray-700"
                >
                  <Edit2 size={15} />
                </button>
                <button
                  onClick={() => deleteMut.mutate(tmpl.id)}
                  className="text-gray-400 hover:text-red-600"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-2 line-clamp-3 font-mono whitespace-pre-wrap">
              {tmpl.body}
            </p>
          </div>
        ))}
        {templates.length === 0 && !creating && (
          <p className="text-sm text-gray-400 text-center py-8">
            Нет шаблонов. Создайте первый!
          </p>
        )}
      </div>
    </div>
  )
}
