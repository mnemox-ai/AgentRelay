const statusStyles: Record<string, string> = {
  open: "bg-neutral-100 text-[var(--text-secondary)]",
  claimed: "bg-amber-50 text-[var(--accent)]",
  completed: "bg-emerald-50 text-[var(--success)]",
  failed: "bg-red-50 text-[var(--error)]",
  expired: "bg-neutral-50 text-[var(--text-tertiary)]",
};

interface BadgeProps {
  status: string;
  className?: string;
}

export function Badge({ status, className = "" }: BadgeProps) {
  const style = statusStyles[status] ?? statusStyles.open;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style} ${className}`}
    >
      {status}
    </span>
  );
}
