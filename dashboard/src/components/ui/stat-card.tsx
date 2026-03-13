import { Card } from "./card";

interface StatCardProps {
  label: string;
  value: string | number;
  delta?: string;
}

export function StatCard({ label, value, delta }: StatCardProps) {
  return (
    <Card>
      <p className="text-sm text-[var(--text-secondary)]">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-tight font-mono text-[var(--text-primary)]">
        {value}
      </p>
      {delta && (
        <p className="mt-1 text-xs text-[var(--text-tertiary)]">{delta}</p>
      )}
    </Card>
  );
}
