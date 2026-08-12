'use client'

import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useMemo } from 'react'

// Configure marked for safe output
marked.setOptions({
  breaks: true,
  gfm: true,
})

interface MarkdownRendererProps {
  content: string
  className?: string
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  const html = useMemo(() => {
    if (!content) return ''
    const raw = (() => {
      try {
        return marked.parse(content, { async: false }) as string
      } catch {
        return content
      }
    })()
    return DOMPurify.sanitize(raw)
  }, [content])

  return (
    <div
      className={`prose prose-sm max-w-none ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
