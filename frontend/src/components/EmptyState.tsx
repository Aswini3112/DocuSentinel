import { LucideIcon } from 'lucide-react'
import clsx from 'clsx'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={clsx(
      'flex flex-col items-center justify-center text-center py-16 px-6',
      className
    )}>
      <div className="w-16 h-16 rounded-2xl bg-sentinel-border/50 border border-sentinel-border flex items-center justify-center mb-4">
        <Icon className="w-7 h-7 text-sentinel-gray" />
      </div>
      <h3 className="text-base font-semibold text-sentinel-text mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-sentinel-gray max-w-xs leading-relaxed mb-4">{description}</p>
      )}
      {action}
    </div>
  )
}
