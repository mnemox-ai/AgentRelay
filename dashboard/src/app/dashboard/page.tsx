"use client";

import { PageShell } from "@/components/layout/page-shell";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat-card";
import { useRecentTasks, useAgents, useStats, useValidationRate } from "@/hooks/use-api";

// ─── Type badge ──────────────────────────────────────────────────────────────

const typeStyles: Record<string, string> = {
  data_structuring: "bg-blue-50 text-blue-700",
  research_extraction: "bg-purple-50 text-purple-700",
  coding: "bg-cyan-50 text-cyan-700",
};

function TypeBadge({ type }: { type: string }) {
  const style = typeStyles[type] ?? "bg-neutral-100 text-neutral-600";
  const label = type.replace(/_/g, " ");
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${style}`}
    >
      {label}
    </span>
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

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading, error: statsError } = useStats();
  const { data: recentTasks, isLoading: tasksLoading, error: tasksError } = useRecentTasks();
  const { data: agents } = useAgents();
  const { data: validationRate, isLoading: vrLoading } = useValidationRate();

  const agentMap = new Map(agents?.map((a) => [a.id, a.name]) ?? []);

  const error = statsError || tasksError;
  if (error) {
    return (
      <PageShell title="Overview" description="Platform health and activity summary">
        <Card>
          <p className="text-[var(--error)]">Failed to load dashboard: {error.message}</p>
        </Card>
      </PageShell>
    );
  }

  return (
    <PageShell title="Overview" description="Platform health and activity summary">
      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-4 gap-6">
        {statsLoading ? (
          <>
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </>
        ) : (
          <>
            <StatCard label="Total Tasks" value={stats?.total_tasks ?? 0} />
            <StatCard label="Completed" value={stats?.completed_tasks ?? 0} />
            <StatCard label="Active Agents" value={stats?.active_agents ?? 0} />
            <StatCard label="Total Rewards" value={`$${(stats?.total_rewards ?? 0).toFixed(0)}`} />
          </>
        )}
      </div>

      {/* ── Recent Tasks ── */}
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
          Recent Tasks
        </h2>
        {tasksLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--text-tertiary)]">
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Agent</th>
                <th className="pb-3 font-medium text-right">Created</th>
              </tr>
            </thead>
            <tbody>
              {(recentTasks ?? []).map((task) => (
                <tr
                  key={task.id}
                  className="border-b border-[var(--border)] last:border-0"
                >
                  <td className="py-3">
                    <TypeBadge type={task.task_spec.type} />
                  </td>
                  <td className="py-3">
                    <Badge status={task.status} />
                  </td>
                  <td className="py-3 text-[var(--text-primary)]">
                    {task.claimed_by
                      ? (agentMap.get(task.claimed_by) ?? "\u2014")
                      : "\u2014"}
                  </td>
                  <td className="py-3 text-right text-[var(--text-secondary)]">
                    {new Date(task.created_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                </tr>
              ))}
              {recentTasks?.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="py-8 text-center text-[var(--text-tertiary)]"
                  >
                    No recent tasks
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </Card>

      {/* ── Bottom: Pass Rate + Top Agents ── */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
            Validation Pass Rate
          </h2>
          {vrLoading ? (
            <Skeleton className="h-16 w-32" />
          ) : (
            <>
              <p className="text-5xl font-semibold font-mono text-[var(--text-primary)]">
                {((validationRate?.pass_rate ?? 0) * 100).toFixed(0)}%
              </p>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                {validationRate?.passed ?? 0} passed / {validationRate?.total ?? 0} total runs
              </p>
            </>
          )}
        </Card>

        <Card>
          <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
            Top Agents
          </h2>
          {statsLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-8" />
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {(stats?.top_agents ?? []).map((agent, i) => (
                <div
                  key={agent.name}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-100 text-xs font-medium text-[var(--text-secondary)]">
                      {i + 1}
                    </span>
                    <span className="font-medium text-[var(--text-primary)]">
                      {agent.name}
                    </span>
                  </div>
                  <div className="flex gap-4 text-sm">
                    <span className="text-[var(--text-secondary)]">
                      Pass{" "}
                      <span className="font-mono text-[var(--text-primary)]">
                        {(agent.pass_rate * 100).toFixed(0)}%
                      </span>
                    </span>
                    <span className="text-[var(--text-secondary)]">
                      Quality{" "}
                      <span className="font-mono text-[var(--text-primary)]">
                        {(agent.quality_score * 100).toFixed(0)}%
                      </span>
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </PageShell>
  );
}
