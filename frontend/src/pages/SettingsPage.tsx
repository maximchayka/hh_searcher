import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { authApi, resumesApi } from '../services/api'
import type { User, Resume } from '../types'
import { RefreshCw, CheckCircle } from 'lucide-react'

export default function SettingsPage() {
  const qc = useQueryClient()

  const { data: user } = useQuery<User>({
    queryKey: ['me'],
    queryFn: () => authApi.me().then((r) => r.data),
  })

  const { data: resumes = [] } = useQuery<Resume[]>({
    queryKey: ['resumes'],
    queryFn: () => resumesApi.list().then((r) => r.data),
  })

  const syncMut = useMutation({
    mutationFn: () => resumesApi.sync(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['resumes'] })
      toast.success('Резюме синхронизированы')
    },
    onError: () => toast.error('Ошибка синхронизации'),
  })

  const setActiveMut = useMutation({
    mutationFn: (id: number) => resumesApi.setActive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['resumes'] }),
  })

  const connectHH = async () => {
    try {
      const res = await authApi.hhAuthUrl()
      window.location.href = res.data.url
    } catch {
      toast.error('Ошибка получения URL авторизации')
    }
  }

  const hhConnected = !!user?.hh_token_expires_at

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Настройки</h1>

      {/* hh.ru Integration */}
      <section className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Интеграция с hh.ru</h2>
        {hhConnected ? (
          <div className="flex items-center gap-2 text-green-700 text-sm">
            <CheckCircle size={16} />
            Аккаунт подключён
            {user?.hh_token_expires_at && (
              <span className="text-xs text-gray-400 ml-1">
                (до {new Date(user.hh_token_expires_at).toLocaleDateString('ru')})
              </span>
            )}
          </div>
        ) : (
          <button
            onClick={connectHH}
            className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700"
          >
            Подключить hh.ru
          </button>
        )}
      </section>

      {/* Resumes */}
      <section className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-800">Резюме</h2>
          <button
            onClick={() => syncMut.mutate()}
            disabled={syncMut.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={13} className={syncMut.isPending ? 'animate-spin' : ''} />
            Синхронизировать
          </button>
        </div>

        {resumes.length === 0 ? (
          <p className="text-sm text-gray-400">Нет резюме. Синхронизируйте с hh.ru.</p>
        ) : (
          <div className="space-y-2">
            {resumes.map((r) => (
              <div
                key={r.id}
                onClick={() => setActiveMut.mutate(r.id)}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  r.is_active
                    ? 'border-red-400 bg-red-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div
                  className={`w-3 h-3 rounded-full flex-shrink-0 ${
                    r.is_active ? 'bg-red-600' : 'bg-gray-300'
                  }`}
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">{r.title}</p>
                  {(r.first_name || r.last_name) && (
                    <p className="text-xs text-gray-500">
                      {r.first_name} {r.last_name}
                    </p>
                  )}
                </div>
                {r.is_active && (
                  <span className="ml-auto text-xs text-red-600 font-medium">Активное</span>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Account info */}
      <section className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="font-semibold text-gray-800 mb-2">Аккаунт</h2>
        <p className="text-sm text-gray-600">{user?.email}</p>
        <p className="text-xs text-gray-400 mt-1">
          Зарегистрирован: {user && new Date(user.created_at).toLocaleDateString('ru')}
        </p>
      </section>

      {/* Legal notice */}
      <section className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <strong>Правовое уведомление.</strong> Использование автоматических откликов может
        нарушать правила пользования hh.ru и привести к блокировке аккаунта. Используйте
        приложение на свой страх и риск. Убедитесь в соответствии с политикой использования
        API hh.ru.
      </section>
    </div>
  )
}
