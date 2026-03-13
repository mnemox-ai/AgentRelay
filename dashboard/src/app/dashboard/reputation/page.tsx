"use client";

import Link from "next/link";
import { PageShell } from "@/components/layout/page-shell";
import { Card } from "@/components/ui/card";
import { useAgents, useReputations, useTasks } from "@/hooks/use-api";

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1)
    return (
      <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-amber-100 text-sm font-bold text-amber-700">
        1
      </span>
    );
  if (rank === 2)
    return (
      <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-neutral-200 text-sm font-bold text-neutral-600">
        2
      </span>
    );
  if (rank === 3)
    return (
      <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-orange-100 text-sm font-bold text-orange-700">
        3
      </span>
    );
  return (
    <span className="inline-flex h-7 w-7 items-center justify-center text-sm font-medium text-[var(--text-tertiary)]">
      {rank}
    </span>
  );
}

function ProviderBadge({ provider }: { provider: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium capitalize text-[var(--text-secondary)]">
      {provider}
    </span>
  );
}

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-neutral-200 ${className ?? ""}`}
    />
  );
}

export default function ReputationPage() {
  const { data: agents, isLoading: agentsLoading, error: agentsError } = useAgents();
  const { data: reputations, isLoading: repLoading } = useReputations();
  const { data: tasks } = useTasks();

  const isLoading = agentsLoading || repLoading;

  if (agentsError) {
    return (
      <PageShell
        title="Reputation Leaderboard"
        description="Top agents ranked by quality score"
      >
        <Card>
          <p className="text-[var(--error)]">Failed to load data: {agentsError.message}</p>
        </Card>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell
        title="Reputation Leaderboard"
        description="Top agents ranked by quality score"
      >
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

  const repMap = new Map(
    reputations?.map((r) => [r.agent_id, r.metrics]) ?? [],
  );

  const completedMap = new Map<string, number>();
  tasks?.forEach((t) => {
    if (t.status === "completed" && t.claimed_by) {
      completedMap.set(t.claimed_by, (completedMap.get(t.claimed_by) ?? 0) + 1);
    }
  });

  // Sort agents by quality_score descending
  const ranked =
    agents
      ?.map((agent) => ({
        agent,
        metrics: repMap.get(agent.id),
        completed: completedMap.get(agent.id) ?? 0,
        provider: (agent.quota_profile as Record<string, string>).provider ?? "unknown",
      }))
      .sort(
        (a, b) =>
          (b.metrics?.quality_score ?? 0) - (a.metrics?.quality_score ?? 0),
      ) ?? [];

  return (
    <PageShell
      title="Reputation Leaderboard"
      description="Top agents ranked by quality score"
    >
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--text-tertiary)]">
                <th className="pb-3 font-medium w-16">#</th>
                <th className="pb-3 font-medium">Agent</th>
                <th className="pb-3 font-medium">Provider</th>
                <th className="pb-3 font-medium text-right">Pass Rate</th>
                <th className="pb-3 font-medium text-right">Quality Score</th>
                <th className="pb-3 font-medium text-right">Tasks Completed</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((row, i) => {
                const rank = i + 1;
                const isTop3 = rank <= 3;
                const rowBg = isTop3
                  ? rank === 1
                    ? "bg-amber-50"
                    : rank === 2
                      ? "bg-neutral-50"
                      : "bg-orange-50"
                  : "";

                return (
                  <tr
                    key={row.agent.id}
                    className={`border-b border-[var(--border)] last:border-0 transition-colors ${rowBg}`}
                  >
                    <td className="py-3">
                      <RankBadge rank={rank} />
                    </td>
                    <td className="py-3">
                      <Link
                        href={`/dashboard/agents/${row.agent.id}`}
                        className="font-medium text-[var(--text-primary)] hover:text-[var(--accent)]"
                      >
                        {row.agent.name}
                      </Link>
                    </td>
                    <td className="py-3">
                      <ProviderBadge provider={row.provider} />
                    </td>
                    <td className="py-3 text-right font-mono text-[var(--text-primary)]">
                      {row.metrics
                        ? `${(row.metrics.pass_rate * 100).toFixed(0)}%`
                        : "—"}
                    </td>
                    <td className="py-3 text-right">
                      <span
                        className={`font-mono font-semibold ${
                          isTop3
                            ? "text-[var(--accent)]"
                            : "text-[var(--text-primary)]"
                        }`}
                      >
                        {row.metrics
                          ? `${(row.metrics.quality_score * 100).toFixed(0)}%`
                          : "—"}
                      </span>
                    </td>
                    <td className="py-3 text-right font-mono text-[var(--text-primary)]">
                      {row.completed}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </PageShell>
  );
}
