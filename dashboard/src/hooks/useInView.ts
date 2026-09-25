'use client'

import { useEffect, useRef, useState } from 'react'

/**
 * Fire once when an element scrolls into view (marketing scroll reveals).
 *
 * One-shot by design: the observer disconnects on first intersection, so
 * reveals replay neither on scroll-back nor on resize. Pair with the
 * `Reveal` component in `components/landing/Reveal.tsx`, which drives the
 * framer-motion transition (the CSS-keyframe reveals were dropped in favour
 * of the dashboard's motion convention).
 */
export function useInView<T extends HTMLElement>(threshold = 0.2) {
  const ref = useRef<T>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setInView(true)
          io.disconnect()
        }
      },
      { threshold },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [threshold])

  return { ref, inView }
}
