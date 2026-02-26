import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '../services/api'

export default function HHCallbackPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    const code = params.get('code')
    if (!code) {
      toast.error('Ошибка авторизации hh.ru')
      navigate('/settings')
      return
    }

    authApi
      .hhCallback(code)
      .then(() => {
        toast.success('hh.ru успешно подключён!')
        navigate('/settings')
      })
      .catch(() => {
        toast.error('Ошибка при подключении hh.ru')
        navigate('/settings')
      })
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-500">Подключение hh.ru...</p>
    </div>
  )
}
