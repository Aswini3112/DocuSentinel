import clsx from 'clsx'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  label?: string
  className?: string
}

export default function LoadingSpinner({ size = 'md', label, className }: LoadingSpinnerProps) {
  const sizeCls = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-10 h-10 border-[3px]',
  }[size]

  return (
    <div className={clsx('flex flex-col items-center justify-center gap-3', className)}>
      <div
        className={clsx(
          sizeCls,
          'rounded-full border-sentinel-border border-t-sentinel-cyan animate-spin'
        )}
      />
      {label && (
        <p className="text-sm text-sentinel-gray animate-pulse">{label}</p>
      )}
    </div>
  )
}

export function PageLoader({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center h-64">
      <LoadingSpinner size="lg" label={label} />
    </div>
  )
}
