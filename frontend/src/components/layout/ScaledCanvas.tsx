import { useEffect, useRef, useState, type ReactNode } from "react"

interface ScaledCanvasProps {
  children: ReactNode
  designWidth?: number
  designHeight?: number
}

export function ScaledCanvas({ children, designWidth = 1440, designHeight = 1024 }: ScaledCanvasProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const innerRef = useRef<HTMLDivElement | null>(null)
  const [layout, setLayout] = useState({ scale: 1, left: 0 })

  const measureScale = () => {
    if (!wrapRef.current) return
    const rect = wrapRef.current.getBoundingClientRect()
    const availableHeight = Math.max(320, window.innerHeight - rect.top)
    const nextScale = Math.min(1, rect.width / designWidth, availableHeight / designHeight)
    setLayout({
      scale: nextScale,
      left: Math.max(0, (rect.width - designWidth * nextScale) / 2),
    })
  }

  useEffect(() => {
    const ro = new ResizeObserver(measureScale)
    if (wrapRef.current) ro.observe(wrapRef.current)
    window.addEventListener("resize", measureScale)
    measureScale()
    return () => {
      ro.disconnect()
      window.removeEventListener("resize", measureScale)
    }
  }, [designHeight, designWidth])

  const scaledHeight = designHeight * layout.scale

  return (
    <div
      ref={wrapRef}
      data-scaled-wrap
      style={{
        position: "relative",
        width: "100%",
        height: scaledHeight,
        minHeight: scaledHeight,
        overflow: "visible",
      }}
    >
      <div
        ref={innerRef}
        data-scaled-inner
        style={{
          position: "absolute",
          top: 0,
          left: layout.left,
          width: designWidth,
          height: designHeight,
          transformOrigin: "top left",
          transform: `scale(${layout.scale})`,
          overflow: "visible",
        }}
      >
        {children}
      </div>
    </div>
  )
}
