import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { searchApi, applicationsApi, resumesApi } from '../services/api'
import type { Vacancy, Resume, SearchTemplate, SearchParams, HHArea, HHRole } from '../types'
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Search,
  Save,
  BookmarkPlus,
  Trash2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

// ─── helpers ────────────────────────────────────────────────────────────────

function formatSalary(salary: Vacancy['salary']): string {
  if (!salary) return 'З/п не указана'
  const parts = []
  if (salary.from) parts.push(`от ${salary.from.toLocaleString('ru')}`)
  if (salary.to) parts.push(`до ${salary.to.toLocaleString('ru')}`)
  const gross = salary.gross ? ' до вычета налогов' : ''
  return parts.join(' ') + ' ' + salary.currency + gross
}

const DEFAULT_FILTERS: SearchParams = {
  text: '',
  search_field: ['name'],
  excluded_text: '',
  area: [],
  experience: '',
  employment: [],
  schedule: [],
  salary: '',
  currency_code: 'RUR',
  only_with_salary: false,
  label: [],
  professional_role: [],
  industry: [],
  date_from: '',
  date_to: '',
  order_by: 'publication_time',
  per_page: 20,
}

function filtersToApiParams(f: SearchParams, page = 0): Record<string, unknown> {
  return {
    text: f.text || undefined,
    search_field: f.search_field.length ? f.search_field : undefined,
    excluded_text: f.excluded_text || undefined,
    area: f.area.length ? f.area : undefined,
    experience: f.experience || undefined,
    employment: f.employment.length ? f.employment : undefined,
    schedule: f.schedule.length ? f.schedule : undefined,
    salary: f.salary ? parseInt(f.salary) : undefined,
    currency_code: f.salary ? f.currency_code : undefined,
    only_with_salary: f.only_with_salary || undefined,
    label: f.label.length ? f.label : undefined,
    professional_role: f.professional_role.length ? f.professional_role : undefined,
    industry: f.industry.length ? f.industry : undefined,
    date_from: f.date_from || undefined,
    date_to: f.date_to || undefined,
    order_by: f.order_by || undefined,
    per_page: f.per_page,
    page,
  }
}

function paramsFromTemplate(raw: string): SearchParams {
  try {
    const p = JSON.parse(raw)
    return {
      text: p.text ?? '',
      search_field: p.search_field ?? ['name'],
      excluded_text: p.excluded_text ?? '',
      area: p.area ?? [],
      experience: p.experience ?? '',
      employment: p.employment ?? [],
      schedule: p.schedule ?? [],
      salary: p.salary != null ? String(p.salary) : '',
      currency_code: p.currency_code ?? 'RUR',
      only_with_salary: p.only_with_salary ?? false,
      label: p.label ?? [],
      professional_role: p.professional_role ?? [],
      industry: p.industry ?? [],
      date_from: p.date_from ?? '',
      date_to: p.date_to ?? '',
      order_by: p.order_by ?? 'publication_time',
      per_page: p.per_page ?? 20,
    }
  } catch {
    return { ...DEFAULT_FILTERS }
  }
}

// ─── sub-components ──────────────────────────────────────────────────────────

interface PillCheckProps {
  label: string
  checked: boolean
  onChange: () => void
}

function PillCheck({ label, checked, onChange }: PillCheckProps) {
  return (
    <label
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-xs cursor-pointer select-none transition-colors ${
        checked
          ? 'bg-red-50 border-red-400 text-red-700 font-medium'
          : 'border-gray-300 text-gray-600 hover:border-gray-400'
      }`}
    >
      <input type="checkbox" className="hidden" checked={checked} onChange={onChange} />
      {label}
    </label>
  )
}

interface CheckGroupProps {
  label: string
  options: { value: string; label: string }[]
  value: string[]
  onChange: (v: string[]) => void
}

function CheckGroup({ label, options, value, onChange }: CheckGroupProps) {
  const toggle = (v: string) =>
    onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v])
  return (
    <div>
      <p className="text-xs font-medium text-gray-600 mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => (
          <PillCheck
            key={o.value}
            label={o.label}
            checked={value.includes(o.value)}
            onChange={() => toggle(o.value)}
          />
        ))}
      </div>
    </div>
  )
}

interface AreaSelectProps {
  areas: HHArea[]
  value: string[]
  onChange: (v: string[]) => void
}

function AreaSelect({ areas, value, onChange }: AreaSelectProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = areas.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()),
  )
  const toggle = (id: string) =>
    onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id])
  const selectedNames = areas.filter((a) => value.includes(a.id)).map((a) => a.name)
  const label =
    value.length === 0
      ? 'Все регионы'
      : selectedNames.slice(0, 2).join(', ') + (value.length > 2 ? ` +${value.length - 2}` : '')

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:border-gray-400 bg-white"
      >
        <span className="truncate">{label}</span>
        <ChevronDown size={14} className="text-gray-400 flex-shrink-0 ml-1" />
      </button>
      {open && (
        <div className="absolute z-30 top-full mt-1 left-0 min-w-full w-64 bg-white border border-gray-200 rounded-lg shadow-xl">
          <div className="p-2 border-b">
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск региона..."
              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-red-500"
            />
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filtered.map((area) => (
              <label
                key={area.id}
                className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={value.includes(area.id)}
                  onChange={() => toggle(area.id)}
                  className="accent-red-600"
                />
                <span className="text-sm text-gray-700">{area.name}</span>
              </label>
            ))}
            {filtered.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-3">Не найдено</p>
            )}
          </div>
          {value.length > 0 && (
            <div className="px-3 py-2 border-t">
              <button
                onClick={() => onChange([])}
                className="text-xs text-red-600 hover:underline"
              >
                Сбросить ({value.length})
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface RoleSelectProps {
  roles: HHRole[]
  value: string[]
  onChange: (v: string[]) => void
}

function RoleSelect({ roles, value, onChange }: RoleSelectProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = roles.filter((r) =>
    r.name.toLowerCase().includes(search.toLowerCase()) ||
    r.category.toLowerCase().includes(search.toLowerCase()),
  )
  const toggle = (id: string) =>
    onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id])
  const label =
    value.length === 0
      ? 'Все специализации'
      : `Выбрано: ${value.length}`

  // Group by category for display
  const grouped = filtered.reduce<Record<string, HHRole[]>>((acc, r) => {
    if (!acc[r.category]) acc[r.category] = []
    acc[r.category].push(r)
    return acc
  }, {})

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:border-gray-400 bg-white"
      >
        <span className="truncate">{label}</span>
        <ChevronDown size={14} className="text-gray-400 flex-shrink-0 ml-1" />
      </button>
      {open && (
        <div className="absolute z-30 top-full mt-1 left-0 min-w-full w-72 bg-white border border-gray-200 rounded-lg shadow-xl">
          <div className="p-2 border-b">
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск специализации..."
              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-red-500"
            />
          </div>
          <div className="max-h-60 overflow-y-auto">
            {Object.entries(grouped).map(([cat, items]) => (
              <div key={cat}>
                <p className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide bg-gray-50">
                  {cat}
                </p>
                {items.map((r) => (
                  <label
                    key={r.id}
                    className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={value.includes(r.id)}
                      onChange={() => toggle(r.id)}
                      className="accent-red-600"
                    />
                    <span className="text-sm text-gray-700">{r.name}</span>
                  </label>
                ))}
              </div>
            ))}
            {filtered.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-3">Не найдено</p>
            )}
          </div>
          {value.length > 0 && (
            <div className="px-3 py-2 border-t">
              <button
                onClick={() => onChange([])}
                className="text-xs text-red-600 hover:underline"
              >
                Сбросить ({value.length})
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── main component ──────────────────────────────────────────────────────────

export default function SearchPage() {
  const qc = useQueryClient()

  const [filters, setFilters] = useState<SearchParams>({ ...DEFAULT_FILTERS })
  const [activeFilters, setActiveFilters] = useState<SearchParams | null>(null)
  const [page, setPage] = useState(0)
  const [showFilters, setShowFilters] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [applying, setApplying] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const [showSaveTemplate, setShowSaveTemplate] = useState(false)

  const set = (patch: Partial<SearchParams>) => setFilters((f) => ({ ...f, ...patch }))

  // Data queries
  const { data: resumes } = useQuery<Resume[]>({
    queryKey: ['resumes'],
    queryFn: () => resumesApi.list().then((r) => r.data),
  })

  const { data: areas = [] } = useQuery<HHArea[]>({
    queryKey: ['hh-areas'],
    queryFn: () => searchApi.getAreas().then((r) => r.data),
    staleTime: Infinity,
    retry: false,
  })

  const { data: roles = [] } = useQuery<HHRole[]>({
    queryKey: ['hh-roles'],
    queryFn: () => searchApi.getProfessionalRoles().then((r) => r.data),
    staleTime: Infinity,
    retry: false,
  })

  const { data: templates = [] } = useQuery<SearchTemplate[]>({
    queryKey: ['search-templates'],
    queryFn: () => searchApi.listTemplates().then((r) => r.data),
  })

  const activeResume = resumes?.find((r) => r.is_active)

  const { data, isFetching } = useQuery<{
    items: Vacancy[]
    found: number
    pages: number
    page: number
  }>({
    queryKey: ['vacancies', activeFilters, page],
    queryFn: () =>
      searchApi.search(filtersToApiParams(activeFilters!, page)).then((r) => r.data),
    enabled: activeFilters !== null,
  })

  // Mutations
  const saveTemplateMut = useMutation({
    mutationFn: () =>
      searchApi.createTemplate(templateName.trim(), {
        text: filters.text,
        search_field: filters.search_field,
        excluded_text: filters.excluded_text,
        area: filters.area,
        experience: filters.experience,
        employment: filters.employment,
        schedule: filters.schedule,
        salary: filters.salary ? parseInt(filters.salary) : null,
        currency_code: filters.currency_code,
        only_with_salary: filters.only_with_salary,
        label: filters.label,
        professional_role: filters.professional_role,
        industry: filters.industry,
        date_from: filters.date_from,
        date_to: filters.date_to,
        order_by: filters.order_by,
        per_page: filters.per_page,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['search-templates'] })
      toast.success('Шаблон сохранён')
      setShowSaveTemplate(false)
      setTemplateName('')
    },
    onError: () => toast.error('Ошибка сохранения шаблона'),
  })

  const deleteTemplateMut = useMutation({
    mutationFn: (id: number) => searchApi.deleteTemplate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['search-templates'] })
      toast.success('Шаблон удалён')
    },
  })

  // Actions
  const handleSearch = () => {
    setPage(0)
    setSelected(new Set())
    setActiveFilters({ ...filters })
  }

  const handleReset = () => {
    setFilters({ ...DEFAULT_FILTERS })
  }

  const loadTemplate = (tmpl: SearchTemplate) => {
    setFilters(paramsFromTemplate(tmpl.params))
    toast.success(`Загружен шаблон «${tmpl.name}»`)
  }

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const toggleAll = () => {
    if (!data) return
    setSelected(
      selected.size === data.items.length ? new Set() : new Set(data.items.map((v) => v.id)),
    )
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

  // ─── options ────────────────────────────────────────────────────────────

  const SEARCH_FIELD_OPTS = [
    { value: 'name', label: 'Название' },
    { value: 'company_name', label: 'Компания' },
    { value: 'description', label: 'Описание' },
  ]
  const EXPERIENCE_OPTS = [
    { value: '', label: 'Любой' },
    { value: 'noExperience', label: 'Нет опыта' },
    { value: 'between1And3', label: '1–3 года' },
    { value: 'between3And6', label: '3–6 лет' },
    { value: 'moreThan6', label: 'Более 6 лет' },
  ]
  const EMPLOYMENT_OPTS = [
    { value: 'full', label: 'Полная' },
    { value: 'part', label: 'Частичная' },
    { value: 'project', label: 'Проектная' },
    { value: 'volunteer', label: 'Волонтёрство' },
    { value: 'probation', label: 'Стажировка' },
  ]
  const SCHEDULE_OPTS = [
    { value: 'fullDay', label: 'Полный день' },
    { value: 'shift', label: 'Сменный' },
    { value: 'flexible', label: 'Гибкий' },
    { value: 'remote', label: 'Удалённая работа' },
    { value: 'flyInFlyOut', label: 'Вахта' },
  ]
  const LABEL_OPTS = [
    { value: 'not_from_agency', label: 'Без агентств' },
    { value: 'accredited_it', label: 'Аккредит. IT' },
    { value: 'with_address', label: 'Есть адрес' },
    { value: 'accept_handicapped', label: 'Для людей с инвалидностью' },
    { value: 'internship', label: 'Стажировки' },
  ]
  const ORDER_OPTS = [
    { value: 'publication_time', label: 'По дате' },
    { value: 'relevance', label: 'По соответствию' },
    { value: 'salary_desc', label: 'По убыванию з/п' },
    { value: 'salary_asc', label: 'По возрастанию з/п' },
  ]
  const CURRENCY_OPTS = ['RUR', 'USD', 'EUR']
  const PER_PAGE_OPTS = [10, 20, 50, 100]

  // ─── render ─────────────────────────────────────────────────────────────

  return (
    <div className="max-w-4xl">
      <h1 className="text-xl font-semibold text-gray-900 mb-4">Поиск вакансий</h1>

      {/* ── Search bar ── */}
      <div className="flex gap-2 mb-2">
        <input
          value={filters.text}
          onChange={(e) => set({ text: e.target.value })}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Ключевые слова, должность..."
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
        />
        <button
          onClick={handleSearch}
          disabled={isFetching}
          className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
        >
          <Search size={14} />
          {isFetching ? 'Поиск...' : 'Найти'}
        </button>
      </div>

      {/* ── Templates strip ── */}
      {templates.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {templates.map((t) => (
            <div key={t.id} className="flex items-center gap-0.5">
              <button
                onClick={() => loadTemplate(t)}
                className="text-xs px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full"
              >
                {t.name}
              </button>
              <button
                onClick={() => deleteTemplateMut.mutate(t.id)}
                className="text-gray-400 hover:text-red-500 p-0.5"
                title="Удалить шаблон"
              >
                <Trash2 size={11} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── Toggle filters ── */}
      <button
        onClick={() => setShowFilters((v) => !v)}
        className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 mb-3"
      >
        {showFilters ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        {showFilters ? 'Скрыть фильтры' : 'Расширенные фильтры'}
      </button>

      {/* ── Filters panel ── */}
      {showFilters && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4 space-y-4">

          {/* Row: where to search + exclude words */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <CheckGroup
              label="Искать в"
              options={SEARCH_FIELD_OPTS}
              value={filters.search_field}
              onChange={(v) => set({ search_field: v })}
            />
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1.5">Исключить слова</p>
              <input
                value={filters.excluded_text}
                onChange={(e) => set({ excluded_text: e.target.value })}
                placeholder="junior, intern..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>
          </div>

          {/* Row: region + specialization */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1.5">Регион</p>
              <AreaSelect areas={areas} value={filters.area} onChange={(v) => set({ area: v })} />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1.5">Специализация</p>
              <RoleSelect
                roles={roles}
                value={filters.professional_role}
                onChange={(v) => set({ professional_role: v })}
              />
            </div>
          </div>

          {/* Row: experience */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1.5">Опыт работы</p>
            <div className="flex flex-wrap gap-1.5">
              {EXPERIENCE_OPTS.map((o) => (
                <label
                  key={o.value}
                  className={`inline-flex items-center px-2.5 py-1 rounded-full border text-xs cursor-pointer select-none transition-colors ${
                    filters.experience === o.value
                      ? 'bg-red-50 border-red-400 text-red-700 font-medium'
                      : 'border-gray-300 text-gray-600 hover:border-gray-400'
                  }`}
                >
                  <input
                    type="radio"
                    className="hidden"
                    checked={filters.experience === o.value}
                    onChange={() => set({ experience: o.value })}
                  />
                  {o.label}
                </label>
              ))}
            </div>
          </div>

          {/* Row: employment + schedule */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <CheckGroup
              label="Тип занятости"
              options={EMPLOYMENT_OPTS}
              value={filters.employment}
              onChange={(v) => set({ employment: v })}
            />
            <CheckGroup
              label="График работы"
              options={SCHEDULE_OPTS}
              value={filters.schedule}
              onChange={(v) => set({ schedule: v })}
            />
          </div>

          {/* Row: salary */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1.5">Зарплата</p>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-500">от</span>
              <input
                type="number"
                value={filters.salary}
                onChange={(e) => set({ salary: e.target.value })}
                placeholder="0"
                min={0}
                className="w-28 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-red-500"
              />
              <select
                value={filters.currency_code}
                onChange={(e) => set({ currency_code: e.target.value })}
                className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-red-500"
              >
                {CURRENCY_OPTS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.only_with_salary}
                  onChange={(e) => set({ only_with_salary: e.target.checked })}
                  className="accent-red-600"
                />
                Только с з/п
              </label>
            </div>
          </div>

          {/* Row: date range */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1.5">Дата публикации</p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">с</span>
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => set({ date_from: e.target.value })}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-red-500"
              />
              <span className="text-xs text-gray-500">по</span>
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => set({ date_to: e.target.value })}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>
          </div>

          {/* Row: labels */}
          <CheckGroup
            label="Метки"
            options={LABEL_OPTS}
            value={filters.label}
            onChange={(v) => set({ label: v })}
          />

          {/* Row: sorting + per_page */}
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1.5">Сортировка</p>
              <select
                value={filters.order_by}
                onChange={(e) => set({ order_by: e.target.value })}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-red-500"
              >
                {ORDER_OPTS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1.5">Показывать</p>
              <select
                value={filters.per_page}
                onChange={(e) => set({ per_page: Number(e.target.value) })}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-red-500"
              >
                {PER_PAGE_OPTS.map((n) => (
                  <option key={n} value={n}>
                    {n} вакансий
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-2 ml-auto">
              <button
                onClick={handleReset}
                className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:border-gray-400"
              >
                Сбросить
              </button>
              <button
                onClick={() => setShowSaveTemplate((v) => !v)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:border-gray-400"
              >
                <BookmarkPlus size={14} />
                Сохранить шаблон
              </button>
            </div>
          </div>

          {/* Save template form */}
          {showSaveTemplate && (
            <div className="flex gap-2 pt-1 border-t">
              <input
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && templateName.trim() && saveTemplateMut.mutate()}
                placeholder="Название шаблона..."
                className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-red-500"
              />
              <button
                onClick={() => saveTemplateMut.mutate()}
                disabled={!templateName.trim() || saveTemplateMut.isPending}
                className="flex items-center gap-1 px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
              >
                <Save size={13} />
                Сохранить
              </button>
              <button
                onClick={() => setShowSaveTemplate(false)}
                className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700"
              >
                Отмена
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Results header ── */}
      {data && (
        <div className="mb-3 flex items-center justify-between flex-wrap gap-2">
          <p className="text-sm text-gray-500">
            Найдено: <span className="font-medium text-gray-800">{data.found.toLocaleString('ru')}</span>
            {data.pages > 1 && (
              <span className="ml-2 text-gray-400">
                · страница {data.page + 1} из {data.pages}
              </span>
            )}
          </p>
          <div className="flex gap-2 items-center">
            <button onClick={toggleAll} className="text-sm text-red-600 hover:underline">
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

      {/* ── Vacancy list ── */}
      <div className="space-y-2">
        {data?.items.map((vacancy) => (
          <div
            key={vacancy.id}
            className={`bg-white border rounded-xl p-4 cursor-pointer transition-colors ${
              selected.has(vacancy.id) ? 'border-red-400 bg-red-50' : 'border-gray-200 hover:border-gray-300'
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
                <div className="flex flex-wrap gap-2 mt-1 items-center">
                  <p className="text-xs font-medium text-green-700">
                    {formatSalary(vacancy.salary)}
                  </p>
                  {vacancy.experience && (
                    <span className="text-xs text-gray-400">{vacancy.experience.name}</span>
                  )}
                  {vacancy.schedule && (
                    <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                      {vacancy.schedule.name}
                    </span>
                  )}
                  {vacancy.employment && vacancy.employment.id !== 'full' && (
                    <span className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-500 rounded">
                      {vacancy.employment.name}
                    </span>
                  )}
                </div>
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

      {/* ── Pagination ── */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <button
            onClick={() => setPage((p) => p - 1)}
            disabled={page === 0 || isFetching}
            className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:border-gray-400 disabled:opacity-40"
          >
            <ChevronLeft size={14} />
            Назад
          </button>
          <span className="text-sm text-gray-500">
            {page + 1} / {data.pages}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= data.pages - 1 || isFetching}
            className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:border-gray-400 disabled:opacity-40"
          >
            Вперёд
            <ChevronRight size={14} />
          </button>
        </div>
      )}

      {/* ── Empty states ── */}
      {activeFilters && !isFetching && data?.items.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-12">
          Вакансии не найдены. Попробуйте изменить фильтры.
        </p>
      )}
      {!activeFilters && (
        <p className="text-sm text-gray-400 text-center py-12">
          Введите запрос и нажмите «Найти»
        </p>
      )}
    </div>
  )
}
