'use client'

import { Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { BookOpen, GraduationCap, Users } from 'lucide-react'
import { StepDots } from '@/components/ui/StepDots'
import { normalizeRole, saveSignupIntent, type SignupRole } from '@/lib/auth/signupIntent'

const ROLES: Array<{ role: SignupRole; icon: typeof GraduationCap; labelKey: string; descKey: string }> = [
  { role: 'student', icon: GraduationCap, labelKey: 'role_learner', descKey: 'role_learner_desc' },
  { role: 'teacher', icon: BookOpen, labelKey: 'role_teacher', descKey: 'role_teacher_desc' },
  { role: 'parent', icon: Users, labelKey: 'role_parent', descKey: 'role_parent_desc' },
]

function RoleSelection() {
  const t = useTranslations('signup')
  const tLogin = useTranslations('login')
  const router = useRouter()
  const params = useSearchParams()
  const preselected = normalizeRole(params.get('role'))

  const choose = (role: SignupRole) => {
    saveSignupIntent({ role })
    if (role === 'student') {
      router.push('/sign-up/learner')
    } else {
      router.push(`/sign-up/account?role=${role}`)
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-display text-2xl text-v2-text-primary">{t('join_title')}</h1>
        <p className="mt-2 text-sm text-v2-text-secondary">{t('join_subtitle')}</p>
      </div>

      <div className="space-y-3">
        {ROLES.map(({ role, icon: Icon, labelKey, descKey }) => (
          <button
            key={role}
            type="button"
            onClick={() => choose(role)}
            aria-current={preselected === role ? 'true' : undefined}
            className={`flex w-full items-center gap-4 rounded-xl border p-4 text-left transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus ${
              preselected === role
                ? 'border-v2-accent bg-v2-accent-muted'
                : 'border-v2-border bg-v2-surface hover:border-v2-accent hover:bg-v2-accent-muted'
            }`}
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-v2-accent-muted text-v2-accent">
              <Icon className="h-6 w-6" aria-hidden />
            </span>
            <span>
              <span className="block text-sm font-semibold text-v2-text-primary">
                {t(labelKey)}
              </span>
              <span className="mt-0.5 block text-xs text-v2-text-secondary">
                {t(descKey)}
              </span>
            </span>
          </button>
        ))}
      </div>

      <StepDots current={1} total={3} label={t('step_of', { current: 1, total: 3 })} />

      <p className="text-center text-xs text-v2-text-secondary">
        {tLogin('already_have_account')}{' '}
        <Link href="/login" className="font-medium text-v2-accent hover:text-v2-accent-hover">
          {tLogin('sign_in')}
        </Link>
      </p>
    </div>
  )
}

export default function SignUpPage() {
  return (
    <Suspense>
      <RoleSelection />
    </Suspense>
  )
}
