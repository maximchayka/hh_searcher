import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// Auth
export const authApi = {
  register: (email: string, password: string) =>
    api.post<{ message: string }>('/auth/register', { email, password }),
  verifyOtp: (email: string, otp: string) =>
    api.post('/auth/verify-otp', { email, otp }),
  login: (email: string, password: string) =>
    api.post<{ access_token: string }>('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  hhAuthUrl: () => api.get<{ url: string }>('/auth/hh/url'),
  hhCallback: (code: string) => api.post('/auth/hh/callback', { code }),
}

// Resumes
export const resumesApi = {
  list: () => api.get('/resumes/'),
  sync: () => api.post('/resumes/sync'),
  setActive: (resume_id: number) => api.post('/resumes/set-active', { resume_id }),
}

// Cover letters
export const coverLettersApi = {
  list: () => api.get('/cover-letters/'),
  create: (name: string, body: string) => api.post('/cover-letters/', { name, body }),
  update: (id: number, data: { name?: string; body?: string }) =>
    api.put(`/cover-letters/${id}`, data),
  delete: (id: number) => api.delete(`/cover-letters/${id}`),
  generate: (vacancy_id: string, tone = 'formal', length = 'short') =>
    api.post<{ text: string }>('/cover-letters/generate', { vacancy_id, tone, length }),
}

// Search
export const searchApi = {
  search: (params: Record<string, unknown>) =>
    api.get('/search/vacancies', {
      params,
      // axios serializes arrays as foo[]=1&foo[]=2 by default; we need foo=1&foo=2
      paramsSerializer: (p) => {
        const parts: string[] = []
        for (const [key, val] of Object.entries(p)) {
          if (val === undefined || val === null || val === '') continue
          if (Array.isArray(val)) {
            val.forEach((v) => parts.push(`${key}=${encodeURIComponent(v)}`))
          } else {
            parts.push(`${key}=${encodeURIComponent(String(val))}`)
          }
        }
        return parts.join('&')
      },
    }),
  getAreas: () => api.get<{ id: string; name: string }[]>('/search/dictionaries/areas'),
  getProfessionalRoles: () =>
    api.get<{ id: string; name: string; category: string }[]>(
      '/search/dictionaries/professional-roles',
    ),
  listTemplates: () => api.get('/search/templates'),
  createTemplate: (name: string, params: Record<string, unknown>) =>
    api.post('/search/templates', { name, params }),
  updateTemplate: (id: number, data: Record<string, unknown>) =>
    api.put(`/search/templates/${id}`, data),
  deleteTemplate: (id: number) => api.delete(`/search/templates/${id}`),
}

// Applications
export const applicationsApi = {
  list: (status?: string) => api.get('/applications/', { params: status ? { status } : {} }),
  apply: (data: {
    vacancy_ids: string[]
    resume_hh_id: string
    cover_letter_template_id?: number
    ai_cover_letter?: boolean
  }) => api.post('/applications/apply', data),
  stats: () => api.get('/applications/stats'),
}

// Job tasks
export const jobTasksApi = {
  list: () => api.get('/job-tasks/'),
  get: (id: number) => api.get(`/job-tasks/${id}`),
  create: (data: Record<string, unknown>) => api.post('/job-tasks/', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/job-tasks/${id}`, data),
  delete: (id: number) => api.delete(`/job-tasks/${id}`),
  runNow: (id: number) => api.post(`/job-tasks/${id}/run`),
  logs: (id: number) => api.get(`/job-tasks/${id}/logs`),
}
