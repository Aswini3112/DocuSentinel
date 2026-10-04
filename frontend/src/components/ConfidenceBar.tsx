import clsx from 'clsx'

interface ConfidenceBarProps {
  percent: number
  reason?: string
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
}

function getColor(percent: number) {
  if (percent >= 75) return { bar: 'bg-sentinel-green',  text: 'text-sentinel-green',  glow: 'shadow-green-glow' }
  if (percent >= 45) return { bar: 'bg-sentinel-amber',  text: 'text-sentinel-amber',  glow: 'shadow-amber-glow' }
  return              { bar: 'bg-red-400',               text: 'text-red-400',          glow: 'shadow-red-glow' }
}

export default function ConfidenceBar({
  percent,
  reason,
  showLabel = true,
  size = 'md',
}: ConfidenceBarProps) {
  const color = getColor(percent)
  const clamped = Math.max(0, Math.min(100, percent))

  const heightCls = { sm: 'h-1', md: 'h-2', lg: 'h-3' }[size]

  return (
    <div className="w-full space-y-1.5">
      {showLabel && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-sentinel-gray">Evidence Confidence</span>
          <span className={clsx('text-sm font-bold font-mono', color.text)}>
            {clamped}%
          </span>
        </div>
      )}
      <div className={clsx('confidence-bar', heightCls)}>
        <div
          className={clsx('confidence-fill', color.bar)}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {reason && (
        <details className="group">
          <summary className="text-xs text-sentinel-gray cursor-pointer hover:text-sentinel-text transition-colors list-none flex items-center gap-1">
            <span className="group-open:rotate-90 transition-transform inline-block">›</span>
            Why this score?
          </summary>
          <div className="mt-2 pl-3 border-l border-sentinel-border space-y-1">
            {reason.split('\n').filter(Boolean).map((line, i) => (
              <p key={i} className="text-xs text-sentinel-text-dim leading-relaxed">{line}</p>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}
