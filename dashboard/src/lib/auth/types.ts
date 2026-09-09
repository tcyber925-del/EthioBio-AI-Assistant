export interface AuthMe {
  user_id: string
  email: string
  role: string
  role_claimed: boolean
  grade_level: number | null
  subject: string | null
  date_of_birth: string | null
  onboarding_completed: boolean
}

export type SignupApiRole = 'student' | 'teacher' | 'parent'

export interface SignupIntentPayload {
  role: SignupApiRole
  dob?: string | null
  tos_accepted: boolean
  parent_email?: string | null
}

export interface SignupIntentResponse {
  ok: boolean
  role: string
  requires_parental_consent: boolean
}

export interface OnboardingPayload {
  grade_level?: number | null
  subject?: string | null
}
