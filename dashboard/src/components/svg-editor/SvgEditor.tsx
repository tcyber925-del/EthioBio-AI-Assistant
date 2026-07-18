'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Download, Edit3, Move, Palette, Type } from 'lucide-react'
import DOMPurify from 'dompurify'

interface DiagramLabel {
  id: string
  text: string
  x: number
  y: number
}

interface SvgEditorProps {
  svg: string
  labels: DiagramLabel[]
  viewBox: { width: number; height: number } | null
  onLabelsChange: (labels: DiagramLabel[]) => void
}

const COLORS = [
  '#22c55e', '#3b82f6', '#ef4444', '#f59e0b', '#a855f7',
  '#ec4899', '#14b8a6', '#ffffff', '#94a3b8', '#1e293b',
]

const SVG_TAGS = [
  'use', 'svg', 'g', 'path', 'circle', 'rect', 'line', 'polygon',
  'polyline', 'text', 'tspan', 'defs', 'clipPath', 'mask',
  'linearGradient', 'radialGradient', 'stop', 'marker', 'image',
  'filter', 'feGaussianBlur', 'feOffset', 'feMerge', 'feMergeNode',
  'feColorMatrix', 'animate', 'animateTransform', 'set',
]
const SVG_ATTRS = [
  'viewBox', 'xmlns', 'd', 'cx', 'cy', 'r', 'rx', 'ry', 'x', 'y',
  'width', 'height', 'fill', 'stroke', 'stroke-width', 'stroke-linecap',
  'transform', 'clip-path', 'mask', 'fill-opacity', 'stroke-opacity',
  'opacity', 'font-family', 'font-size', 'font-weight', 'text-anchor',
  'dominant-baseline', 'dx', 'dy', 'href', 'target', 'id', 'class',
  'style', 'points', 'filter', 'stop-color', 'stop-opacity', 'offset',
  'marker-end', 'marker-start', 'marker-mid', 'refX', 'refY',
  'markerWidth', 'markerHeight', 'orient',
]

export default function SvgEditor({ svg, labels, viewBox, onLabelsChange }: SvgEditorProps) {
  const svgRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [editMode, setEditMode] = useState(false)
  const [dragId, setDragId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')
  const [colorMode, setColorMode] = useState<'fill' | 'stroke' | null>(null)
  const [selectedColor, setSelectedColor] = useState(COLORS[0])

  const vb = viewBox ?? { width: 800, height: 600 }
  const containerRect = containerRef.current?.getBoundingClientRect()

  const toSvgCoords = useCallback(
    (clientX: number, clientY: number) => {
      if (!containerRect) return { x: 0, y: 0 }
      const scaleX = vb.width / containerRect.width
      const scaleY = vb.height / containerRect.height
      return {
        x: (clientX - containerRect.left) * scaleX,
        y: (clientY - containerRect.top) * scaleY,
      }
    },
    [containerRect, vb],
  )

  const handlePointerDown = useCallback(
    (labelId: string, e: React.PointerEvent) => {
      if (!editMode) return
      e.preventDefault()
      e.stopPropagation()
      ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
      setDragId(labelId)
    },
    [editMode],
  )

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragId || !editMode) return
      const coords = toSvgCoords(e.clientX, e.clientY)
      const updated = labels.map((l) =>
        l.id === dragId ? { ...l, x: Math.round(coords.x), y: Math.round(coords.y) } : l,
      )
      onLabelsChange(updated)
    },
    [dragId, editMode, labels, onLabelsChange, toSvgCoords],
  )

  const handlePointerUp = useCallback(() => {
    setDragId(null)
  }, [])

  const handleDoubleClick = useCallback(
    (labelId: string, currentText: string) => {
      if (!editMode) return
      setEditingId(labelId)
      setEditText(currentText)
    },
    [editMode],
  )

  const finishEdit = useCallback(() => {
    if (editingId && editText.trim()) {
      const updated = labels.map((l) =>
        l.id === editingId ? { ...l, text: editText.trim() } : l,
      )
      onLabelsChange(updated)
    }
    setEditingId(null)
    setEditText('')
  }, [editingId, editText, labels, onLabelsChange])

  const handleSvgClick = useCallback(
    (e: React.MouseEvent) => {
      if (!colorMode || !svgRef.current) return
      const target = (e.target as HTMLElement).closest('svg *:not(text)')
      if (!target || target.tagName === 'svg') return
      target.setAttribute(colorMode, selectedColor)
    },
    [colorMode, selectedColor],
  )

  const downloadSvg = useCallback(() => {
    let modified = svg
    const vbMatch = svg.match(/viewBox=["']([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)["']/)
    const svgW = vbMatch ? parseFloat(vbMatch[3]) : 800
    const svgH = vbMatch ? parseFloat(vbMatch[4]) : 600

    labels.forEach((label) => {
      const textEl = `<text x="${label.x}" y="${label.y}" text-anchor="middle" dominant-baseline="middle" font-family="Arial, sans-serif" font-size="14" fill="#22c55e" font-weight="bold">${label.text}</text>`
      const insertBefore = '</svg>'
      modified = modified.replace(insertBefore, `${textEl}\n${insertBefore}`)
    })

    const xmlns = modified.includes('xmlns') ? '' : ' xmlns="http://www.w3.org/2000/svg"'
    if (xmlns) {
      modified = modified.replace('<svg', `<svg${xmlns}`)
    }

    const blob = new Blob([modified], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'diagram.svg'
    a.click()
    URL.revokeObjectURL(url)
  }, [svg, labels])

  useEffect(() => {
    if (!editMode && svgRef.current) {
      setEditingId(null)
      setDragId(null)
      setColorMode(null)
    }
  }, [editMode])

  return (
    <div>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setEditMode(!editMode)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors ${
            editMode
              ? 'bg-primary text-white'
              : 'border border-border text-foreground hover:bg-background-secondary'
          }`}
        >
          <Move className="w-4 h-4" /> {editMode ? 'Editing On' : 'Edit Labels'}
        </button>

        {editMode && (
          <>
            <button
              onClick={() => setColorMode(colorMode === 'fill' ? null : 'fill')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors ${
                colorMode === 'fill'
                  ? 'bg-primary text-white'
                  : 'border border-border text-foreground hover:bg-background-secondary'
              }`}
            >
              <Palette className="w-4 h-4" /> Fill
            </button>
            <button
              onClick={() => setColorMode(colorMode === 'stroke' ? null : 'stroke')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors ${
                colorMode === 'stroke'
                  ? 'bg-primary text-white'
                  : 'border border-border text-foreground hover:bg-background-secondary'
              }`}
            >
              <Palette className="w-4 h-4" /> Stroke
            </button>
          </>
        )}

        <button
          onClick={downloadSvg}
          className="ml-auto px-3 py-1.5 rounded-lg border border-border text-foreground text-sm font-medium hover:bg-background-secondary transition-colors flex items-center gap-1.5"
        >
          <Download className="w-4 h-4" /> Download SVG
        </button>
      </div>

      {colorMode && (
        <div className="flex items-center gap-2 mb-4 p-3 bg-background rounded-lg border border-border">
          <span className="text-xs text-foreground-muted mr-1">
            {colorMode === 'fill' ? 'Fill' : 'Stroke'}:
          </span>
          {COLORS.map((c) => (
            <button
              key={c}
              onClick={() => setSelectedColor(c)}
              className={`w-7 h-7 rounded-full border-2 transition-all ${
                selectedColor === c ? 'border-primary scale-110' : 'border-transparent'
              }`}
              style={{ backgroundColor: c }}
              title={c}
            />
          ))}
          <span className="text-xs text-foreground-muted ml-2">
            Click an SVG element to apply
          </span>
        </div>
      )}

      <div
        ref={containerRef}
        className="relative w-full overflow-hidden rounded-lg"
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onClick={handleSvgClick}
      >
        <div
          ref={svgRef}
          className="w-full [&_svg]:w-full [&_svg]:h-auto"
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(svg, {
              ADD_TAGS: SVG_TAGS,
              ADD_ATTR: SVG_ATTRS,
            }),
          }}
        />

        <div className="absolute inset-0">
          {labels.map((label, i) => {
            const pctX = (label.x / vb.width) * 100
            const pctY = (label.y / vb.height) * 100
            const isEditing = editingId === label.id

            return (
              <div
                key={label.id}
                className={`absolute ${editMode ? 'cursor-grab' : ''} ${
                  dragId === label.id ? 'cursor-grabbing z-20' : 'z-10'
                }`}
                style={{
                  left: `${pctX}%`,
                  top: `${pctY}%`,
                  transform: 'translate(-50%, -50%)',
                  touchAction: 'none',
                }}
                onPointerDown={(e) => handlePointerDown(label.id, e)}
                onDoubleClick={() => handleDoubleClick(label.id, label.text)}
              >
                {isEditing ? (
                  <input
                    type="text"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    onBlur={finishEdit}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') finishEdit()
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    className="w-32 px-2 py-1 text-sm bg-background border border-primary rounded shadow-lg text-foreground focus:outline-none"
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                      dragId === label.id
                        ? 'bg-primary text-white scale-125 shadow-lg shadow-primary/40'
                        : editMode
                          ? 'bg-primary/80 text-white hover:scale-110'
                          : 'bg-primary/80 text-white shadow-md'
                    } ${editMode ? 'hover:bg-primary' : ''}`}
                  >
                    {i + 1}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {editMode && (
        <div className="mt-3 p-3 bg-background rounded-lg border border-border text-xs text-foreground-muted space-y-1">
          <p className="flex items-center gap-1.5"><Move className="w-3.5 h-3.5" /> Drag label badges to reposition</p>
          <p className="flex items-center gap-1.5"><Type className="w-3.5 h-3.5" /> Double-click a badge to edit label text</p>
          <p className="flex items-center gap-1.5"><Palette className="w-3.5 h-3.5" /> Select a color, then click any SVG element</p>
        </div>
      )}
    </div>
  )
}
