'use client'

import { marked } from 'marked'
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
    try {
      return marked.parse(content, { async: false }) as string
    } catch {
      return content
    }
  }, [content])

  return (
    <div
      className={`prose prose-sm max-w-none ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
