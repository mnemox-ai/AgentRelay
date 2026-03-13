"use client";

import Link from "next/link";
import { PageShell } from "@/components/layout/page-shell";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAgents, useReputations, useLedger, useTasks } from "@/hooks/use-api";

// ─── Pass rate bar ──────────────────────────────────────────────────────────

function PassRateBar({ rate }: { rate: number }) {
  const pct = rate * 100;
  const color =
    pct >= 80
      ? "bg-[var(--success)]"
      : pct >= 50
        ? "bg-amber-500"
        : "bg-[var(--error)]";

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-20 rounded-full bg-neutral-100">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-xs text-[var(--text-primary)]">
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-neutral-200 ${className ?? ""}`}
    />
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const { data: agents, isLoading, error } = useAgents();
  const { data: reputations } = useReputations();
  const { data: ledger } = useLedger();
  const { data: tasks } = useTasks();

  if (error) {
    return (
      <PageShell title="Agents" description="Registered agents and performance overview">
        <Card>
          <p className="text-[var(--error)]">Failed to load agents: {error.message}</p>
        </Card>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell title="Agents" description="Registered agents and performance overview">
        <Card>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        </Card>
      </PageShell>
    );
  }

  // Build lookup maps
  const repMap = new Map(reputations?.map((r) => [r.agent_id, r.metrics]) ?? []);

  const balanceMap = new Map<string, number>();
  ledger?.forEach((e) => {
    balanceMap.set(e.agent_id, (balanceMap.get(e.agent_id) ?? 0) + e.amount);
  });

  const completedMap = new Map<string, number>();
  tasks?.forEach((t) => {
    if (t.status === "completed" && t.claimed_by) {
      completedMap.set(t.claimed_by, (completedMap.get(t.claimed_by) ?? 0) + 1);
    }
  });

  return (
    <PageShell title="Agents" description="Registered agents and performance overview">
      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--text-tertiary)]">
              <th className="pb-3 font-medium">Name</th>
              <th className="pb-3 font-medium">Provider</th>
              <th className="pb-3 font-medium">Model</th>
              <th className="pb-3 font-medium">Status</th>
              <th className="pb-3 font-medium">Pass Rate</th>
              <th className="pb-3 font-medium text-right">Quality</th>
              <th className="pb-3 font-medium text-right">Completed</th>
              <th className="pb-3 font-medium text-right">Balance</th>
            </tr>
          </thead>
          <tbody>
            {agents?.map((agent) => {
              const metrics = repMap.get(agent.id);
              const balance = balanceMap.get(agent.id) ?? 0;
              const completed = completedMap.get(agent.id) ?? 0;
              const provider = (agent.quota_profile as Record<string, string>).provider ?? "—";
              const model = (agent.quota_profile as Record<string, string>).model ?? "—";

              return (
                <tr
                  key={agent.id}
                  className="border-b border-[var(--border)] last:border-0 hover:bg-neutral-50 transition-colors cursor-pointer"
                >
                  <td className="py-3">
                    <Link
                      href={`/dashboard/agents/${agent.id}`}
                      className="font-medium text-[var(--text-primary)] hover:text-[var(--accent)]"
                    >
                      {agent.name}
                    </Link>
                  </td>
                  <td className="py-3 text-[var(--text-secondary)] capitalize">
                    {provider}
                  </td>
                  <td className="py-3">
                    <span className="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-mono text-[var(--text-secondary)]">
                      {model}
                    </span>
                  </td>
                  <td className="py-3">
                    <Badge status={agent.status} />
                  </td>
                  <td className="py-3">
                    {metrics ? (
                      <PassRateBar rate={metrics.pass_rate} />
                    ) : (
                      <span className="text-[var(--text-tertiary)]">—</span>
                    )}
                  </td>
                  <td className="py-3 text-right font-mono text-[var(--text-primary)]">
                    {metrics
                      ? `${(metrics.quality_score * 100).toFixed(0)}%`
                      : "—"}
                  </td>
                  <td className="py-3 text-right font-mono text-[var(--text-primary)]">
                    {completed}
                  </td>
                  <td className="py-3 text-right font-mono text-[var(--text-primary)]">
                    ${balance.toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </PageShell>
  );
}
