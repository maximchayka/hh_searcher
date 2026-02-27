import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '../services/api'

const ALLOWED_DOMAINS = ['infoteq.ru', 'iq-cloud.ru']

const registerSchema = z.object({
  email: z
    .string()
    .email('Введите корректный email')
    .refine(
      (v) => ALLOWED_DOMAINS.some((d) => v.toLowerCase().endsWith(`@${d}`)),
      'Регистрация доступна только для @infoteq.ru и @iq-cloud.ru',
    ),
  password: z.string().min(6, 'Минимум 6 символов'),
})

const otpSchema = z.object({
  otp: z
    .string()
    .length(6, 'Код состоит из 6 цифр')
    .regex(/^\d+$/, 'Только цифры'),
})

type RegisterData = z.infer<typeof registerSchema>
type OTPData = z.infer<typeof otpSchema>

export default function RegisterPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<'register' | 'otp'>('register')
  const [pendingEmail, setPendingEmail] = useState('')

  const registerForm = useForm<RegisterData>({ resolver: zodResolver(registerSchema) })
  const otpForm = useForm<OTPData>({ resolver: zodResolver(otpSchema) })

  const onRegister = async (data: RegisterData) => {
    try {
      await authApi.register(data.email, data.password)
      setPendingEmail(data.email)
      setStep('otp')
      toast.success('Код подтверждения отправлен на email')
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Ошибка регистрации'
      toast.error(msg)
    }
  }

  const onVerifyOtp = async (data: OTPData) => {
    try {
      await authApi.verifyOtp(pendingEmail, data.otp)
      toast.success('Аккаунт создан! Войдите.')
      navigate('/login')
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Неверный код'
      toast.error(msg)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 w-full max-w-md">
        {step === 'register' ? (
          <>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">Регистрация</h1>
            <p className="text-sm text-gray-500 mb-6">Создайте аккаунт JobAutoApply</p>

            <form onSubmit={registerForm.handleSubmit(onRegister)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  {...registerForm.register('email')}
                  type="email"
                  placeholder="you@infoteq.ru"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                />
                {registerForm.formState.errors.email && (
                  <p className="text-xs text-red-500 mt-1">
                    {registerForm.formState.errors.email.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Пароль</label>
                <input
                  {...registerForm.register('password')}
                  type="password"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                />
                {registerForm.formState.errors.password && (
                  <p className="text-xs text-red-500 mt-1">
                    {registerForm.formState.errors.password.message}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={registerForm.formState.isSubmitting}
                className="w-full py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {registerForm.formState.isSubmitting ? 'Отправка кода...' : 'Получить код'}
              </button>
            </form>
          </>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">Подтверждение</h1>
            <p className="text-sm text-gray-500 mb-6">
              Введите 6-значный код, отправленный на{' '}
              <span className="font-medium text-gray-700">{pendingEmail}</span>
            </p>

            <form onSubmit={otpForm.handleSubmit(onVerifyOtp)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Код подтверждения
                </label>
                <input
                  {...otpForm.register('otp')}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="123456"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-center tracking-widest text-lg font-mono focus:outline-none focus:ring-2 focus:ring-red-500"
                />
                {otpForm.formState.errors.otp && (
                  <p className="text-xs text-red-500 mt-1">
                    {otpForm.formState.errors.otp.message}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={otpForm.formState.isSubmitting}
                className="w-full py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {otpForm.formState.isSubmitting ? 'Проверка...' : 'Подтвердить'}
              </button>

              <button
                type="button"
                onClick={() => setStep('register')}
                className="w-full py-2 text-sm text-gray-500 hover:text-gray-700"
              >
                Изменить email
              </button>
            </form>
          </>
        )}

        <p className="text-sm text-center text-gray-500 mt-4">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="text-red-600 hover:underline">
            Войти
          </Link>
        </p>
      </div>
    </div>
  )
}
