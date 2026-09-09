'use client'

import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import {
  createContext,
  useCallback,
  useContext,
  useId,
  useState,
  type ReactNode,
} from 'react'

const EASE = [0.16, 1, 0.3, 1] as const
const DURATION = 0.16

export interface AccordionItemData {
  id?: string
  title: ReactNode
  content: ReactNode
}

interface AccordionProps {
  items?: AccordionItemData[]
  children?: ReactNode
  className?: string
  dividerClassName?: string
  itemTitleClassName?: string
  itemContentClassName?: string
  allowMultiple?: boolean
}

interface AccordionItemProps {
  id?: string
  title: ReactNode
  children: ReactNode
  className?: string
  titleClassName?: string
  contentClassName?: string
}

interface AccordionContextValue {
  openIds: Set<string>
  toggle: (id: string) => void
  baseId: string
}

const AccordionContext = createContext<AccordionContextValue | null>(null)

function useAccordionContext() {
  const ctx = useContext(AccordionContext)
  if (!ctx) {
    throw new Error('Accordion.Item must be used within Accordion')
  }
  return ctx
}

export function Accordion({
  items,
  children,
  className = '',
  dividerClassName = 'divide-v2-border',
  itemTitleClassName,
  itemContentClassName,
  allowMultiple = false,
}: AccordionProps) {
  const baseId = useId()
  const [openIds, setOpenIds] = useState<Set<string>>(() => new Set())

  const toggle = useCallback(
    (id: string) => {
      setOpenIds((prev) => {
        const next = new Set(allowMultiple ? prev : [])
        if (prev.has(id)) {
          next.delete(id)
        } else {
          next.add(id)
        }
        return next
      })
    },
    [allowMultiple],
  )

  return (
    <AccordionContext.Provider value={{ openIds, toggle, baseId }}>
      <div className={`divide-y ${dividerClassName} ${className}`}>
        {items?.map((item, index) => (
          <AccordionItem
            key={item.id ?? `${baseId}-${index}`}
            id={item.id ?? `${baseId}-${index}`}
            title={item.title}
            titleClassName={itemTitleClassName}
            contentClassName={itemContentClassName}
          >
            {item.content}
          </AccordionItem>
        ))}
        {children}
      </div>
    </AccordionContext.Provider>
  )
}

export function AccordionItem({
  id: idProp,
  title,
  children,
  className = '',
  titleClassName = 'text-v2-text-primary',
  contentClassName = 'text-v2-text-secondary',
}: AccordionItemProps) {
  const { openIds, toggle, baseId } = useAccordionContext()
  const autoId = useId()
  const id = idProp ?? autoId
  const expanded = openIds.has(id)
  const panelId = `${baseId}-panel-${id}`
  const buttonId = `${baseId}-button-${id}`
  const reduceMotion = useReducedMotion()

  return (
    <div className={className}>
      <h3 className="m-0">
        <button
          type="button"
          id={buttonId}
          aria-expanded={expanded}
          aria-controls={panelId}
          onClick={() => toggle(id)}
          className={`flex w-full items-center justify-between gap-3 py-3 text-left text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus ${titleClassName}`}
        >
          <span>{title}</span>
          <motion.span
            aria-hidden
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={
              reduceMotion
                ? { duration: 0 }
                : { duration: DURATION, ease: EASE }
            }
            className="inline-flex shrink-0 text-v2-text-secondary"
          >
            <ChevronIcon />
          </motion.span>
        </button>
      </h3>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={panelId}
            role="region"
            aria-labelledby={buttonId}
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={
              reduceMotion
                ? { duration: 0 }
                : { duration: DURATION, ease: EASE }
            }
            className="overflow-hidden"
          >
            <div className={`pb-3 text-sm ${contentClassName}`}>{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ChevronIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M4 6l4 4 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

Accordion.Item = AccordionItem

export default Accordion
