import type { SVGProps } from 'react'

export function DnaIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" {...props}>
      <path d="M4 4c4 4 4 12 0 16" opacity="0.6" />
      <path d="M20 4c-4 4-4 12 0 16" opacity="0.6" />
      <path d="M8 8h8" />
      <path d="M8 16h8" />
      <path d="M6 12h12" />
      <circle cx="4" cy="4" r="1.5" fill="currentColor" stroke="none" opacity="0.4" />
      <circle cx="20" cy="20" r="1.5" fill="currentColor" stroke="none" opacity="0.4" />
      <circle cx="20" cy="4" r="1.5" fill="currentColor" stroke="none" opacity="0.4" />
      <circle cx="4" cy="20" r="1.5" fill="currentColor" stroke="none" opacity="0.4" />
    </svg>
  )
}

export function MicroscopeIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" {...props}>
      <path d="M6 20h12" />
      <path d="M12 20v-4" />
      <path d="M10 4h4l2 8h-8l2-8Z" />
      <circle cx="12" cy="14" r="2" />
      <path d="M8 10c-2 0-3 1-3 3s1 3 3 3" opacity="0.4" />
      <path d="M16 10c2 0 3 1 3 3s-1 3-3 3" opacity="0.4" />
    </svg>
  )
}

export function NeuronIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 9v-4" opacity="0.5" />
      <path d="M12 15v4" opacity="0.5" />
      <path d="M9 12H5" opacity="0.5" />
      <path d="M15 12h4" opacity="0.5" />
      <path d="M10 10l-3-3" opacity="0.4" />
      <path d="M14 10l3-3" opacity="0.4" />
      <path d="M10 14l-3 3" opacity="0.4" />
      <path d="M14 14l3 3" opacity="0.4" />
    </svg>
  )
}

export function CellIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" {...props}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" opacity="0.4" />
      <circle cx="12" cy="12" r="2" fill="currentColor" opacity="0.6" stroke="none" />
      <circle cx="17" cy="7" r="1" fill="currentColor" opacity="0.3" stroke="none" />
      <circle cx="7" cy="17" r="1" fill="currentColor" opacity="0.3" stroke="none" />
      <circle cx="7" cy="7" r="0.8" fill="currentColor" opacity="0.3" stroke="none" />
      <circle cx="17" cy="17" r="0.8" fill="currentColor" opacity="0.3" stroke="none" />
    </svg>
  )
}

export function LeafIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" {...props}>
      <path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.78 10-10 10Z" />
      <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
    </svg>
  )
}

export function GenomeIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" {...props}>
      <circle cx="12" cy="12" r="10" opacity="0.3" />
      <path d="M12 2v20" opacity="0.4" />
      <path d="M2 12h20" opacity="0.4" />
      <path d="M5 5l14 14" opacity="0.2" />
      <path d="M19 5L5 19" opacity="0.2" />
      <circle cx="12" cy="12" r="3" opacity="0.5" />
      <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" opacity="0.7" />
    </svg>
  )
}

const ICON_MAP: Record<string, React.ElementType> = {
  dna: DnaIcon,
  microscope: MicroscopeIcon,
  neuron: NeuronIcon,
  cell: CellIcon,
  leaf: LeafIcon,
  genome: GenomeIcon,
}

export function getBioIcon(id: string): React.ElementType {
  return ICON_MAP[id] || DnaIcon
}

export const BIO_ICON_IDS = Object.keys(ICON_MAP)
