'use client'

import { useTranslations } from 'next-intl'
import { useLocaleSwitcher } from '@/hooks/useLocaleSwitcher'
import { LOCALES, type Locale } from '@/lib/i18n-config'

interface LanguageSwitcherProps {
  variant: 'select' | 'toggle'
  className?: string
}

/**
 * The single language switcher. `select` fits the dashboard sidebars,
 * `toggle` fits the marketing header. Locale labels always come from
 * messages (common.english / common.amharic), never hardcoded.
 */
export default function LanguageSwitcher({ variant, className = '' }: LanguageSwitcherProps) {
  const t = useTranslations('common')
  const { locale, switchLocale } = useLocaleSwitcher()

  if (variant === 'toggle') {
    return (
      <div className={className} role="group" aria-label={t('language')}>
        {LOCALES.map((l: Locale) => (
          <button
            key={l}
            type="button"
            onClick={() => switchLocale(l)}
            aria-pressed={locale === l}
            className={`px-2.5 py-1 text-xs font-mono rounded-sm transition-all ${
              locale === l ? 'bg-[#3cffd0] text-black font-bold' : 'text-gray-400 hover:text-white'
            }`}
          >
            {t(l === 'en' ? 'english' : 'amharic')}
          </button>
        ))}
      </div>
    )
  }

  return (
    <select
      value={locale}
      onChange={(e) => switchLocale(e.target.value as Locale)}
      aria-label={t('language')}
      className={className}
    >
      {LOCALES.map((l: Locale) => (
        <option key={l} value={l}>
          {t(l === 'en' ? 'english' : 'amharic')}
        </option>
      ))}
    </select>
  )
}
