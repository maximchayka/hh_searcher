export interface User {
  id: number
  email: string
  is_active: boolean
  is_verified: boolean
  hh_token_expires_at: string | null
  created_at: string
}

export interface Resume {
  id: number
  hh_resume_id: string
  title: string
  first_name: string | null
  last_name: string | null
  skills: string | null
  is_active: boolean
  updated_at: string
}

export interface CoverLetterTemplate {
  id: number
  name: string
  body: string
  created_at: string
  updated_at: string
}

export interface SearchParams {
  text: string
  search_field: string[]      // name, company_name, description
  excluded_text: string
  area: string[]
  experience: string          // noExperience | between1And3 | between3And6 | moreThan6
  employment: string[]        // full | part | project | volunteer | probation
  schedule: string[]          // fullDay | shift | flexible | remote | flyInFlyOut
  salary: string              // numeric string, empty = not set
  currency_code: string       // RUR | USD | EUR
  only_with_salary: boolean
  label: string[]             // not_from_agency | accredited_it | with_address | accept_handicapped | internship
  professional_role: string[]
  industry: string[]
  date_from: string
  date_to: string
  order_by: string            // relevance | publication_time | salary_desc | salary_asc
  per_page: number
}

export interface SearchTemplate {
  id: number
  name: string
  params: string
  created_at: string
}

export type TaskFrequency = '15min' | '30min' | '1h' | 'daily' | 'custom'
export type TaskAction = 'auto_apply' | 'manual_review' | 'notify_only'
export type TaskStatus = 'active' | 'paused' | 'error' | 'completed' | 'limit_reached'

export interface JobTask {
  id: number
  name: string
  search_template_id: number
  cover_letter_template_id: number | null
  frequency: TaskFrequency
  custom_cron: string | null
  action: TaskAction
  status: TaskStatus
  only_new: boolean
  skip_applied: boolean
  min_ai_match: number | null
  daily_limit: number
  per_run_limit: number
  per_company_limit: number
  created_at: string
}

export interface JobTaskLog {
  id: number
  job_task_id: number
  started_at: string
  finished_at: string | null
  vacancies_found: number
  applied_count: number
  errors_count: number
  status: string
}

export type ApplicationStatus = 'sent' | 'viewed' | 'invitation' | 'rejection' | 'discard'

export interface Application {
  id: number
  vacancy_id: string
  vacancy_title: string
  company_name: string
  salary_display: string | null
  vacancy_url: string
  resume_hh_id: string
  cover_letter_text: string | null
  status: ApplicationStatus
  applied_at: string
  updated_at: string
}

export interface ApplicationStats {
  total: number
  sent: number
  viewed: number
  invitation: number
  rejection: number
}

export interface Vacancy {
  id: string
  name: string
  employer: { name: string; logo_urls?: Record<string, string> }
  salary: { from?: number; to?: number; currency: string; gross?: boolean } | null
  area: { name: string }
  snippet: { requirement?: string; responsibility?: string }
  schedule: { id: string; name: string } | null
  experience: { id: string; name: string } | null
  employment: { id: string; name: string } | null
  published_at: string
  alternate_url: string
}

export interface HHArea {
  id: string
  name: string
}

export interface HHRole {
  id: string
  name: string
  category: string
}
