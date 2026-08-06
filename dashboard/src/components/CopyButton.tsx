'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Check, Copy } from 'lucide-react'

interface CopyButtonProps {
  text: string
}

export function CopyButton({ text }: CopyButtonProps) {
  const tc = useTranslations('common')
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard unavailable — leave state untouched
    }
  }

  return (
    <button
      onClick={handleCopy}
      title={copied ? tc('copied') : tc('copy')}
      aria-label={copied ? tc('copied') : tc('copy')}
      className={`p-2 rounded-lg transition-colors shrink-0 ${
        copied
          ? 'bg-v2-accent text-v2-inverted'
          : 'bg-v2-accent/10 text-v2-accent hover:bg-v2-accent/20'
      }`}
    >
      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
    </button>
  )
}