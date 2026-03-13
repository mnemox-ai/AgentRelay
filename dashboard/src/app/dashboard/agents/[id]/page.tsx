"use client";

import { use } from "react";
import Link from "next/link";
import { PageShell } from "@/components/layout/page-shell";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat-card";
import {
  useAgent,
  useReputation,
  useLedgerByAgent,
  useTasks,
} from "@/hooks/use-api";

// ─── Skeleton ────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-neutral-200 ${className ?? ""}`}
    />
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function AgentProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: agent, isLoading, error } = useAgent(id);
  const { data: reputation } = useReputation(id);
  const { data: ledger } = useLedgerByAgent(id);
  const { data: tasks } = useTasks();

  if (error) {
    return (
      <PageShell title="Agent Profile">
        <Card>
          <p className="text-[var(--error)]">Failed to load agent: {error.message}</p>
        </Card>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell title="Agent Profile">
        <Skeleton className="h-6 w-32" />
        <Card>
          <Skeleton className="h-24" />
        </Card>
        <div className="grid grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-6">
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
      </PageShell>
    );
  }

  if (!agent) {
    return (
      <PageShell title="Agent Not Found">
        <p className="text-[var(--text-secondary)]">Agent does not exist.</p>
      </PageShell>
    );
  }

  const provider = (agent.quota_profile as Record<string, string>).provider ?? "—";
  const model = (agent.quota_profile as Record<string, string>).model ?? "—";
  const metrics = reputation?.metrics;
  const qualityScore = metrics ? (metrics.quality_score * 100).toFixed(0) : "—";

  // Total earned from ledger
  const totalEarned = ledger?.reduce((sum, e) => sum + e.amount, 0) ?? 0;

  // Recent tasks for this agent (claimed_by or publisher_id)
  const agentTasks = tasks
    ? [...tasks]
        .filter((t) => t.claimed_by === id || t.publisher_id === id)
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        )
        .slice(0, 10)
    : [];

  const fmt = (d: string) =>
    new Date(d).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  return (
    <PageShell title="Agent Profile" description={agent.name}>
      {/* ── Back link ── */}
      <div className="-mt-6">
        <Link
          href="/dashboard/agents"
          className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        >
          &larr; Back to Agents
        </Link>
      </div>

      {/* ── Hero ── */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
              {agent.name}
            </h2>
            <div className="mt-2 flex items-center gap-2">
              <span className="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-[var(--text-secondary)] capitalize">
                {provider}
              </span>
              <span className="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-mono text-[var(--text-secondary)]">
                {model}
              </span>
              <Badge status={agent.status} />
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-[var(--text-tertiary)]">Quality Score</p>
            <p className="text-5xl font-semibold font-mono text-[var(--text-primary)]">
              {qualityScore}
              {qualityScore !== "—" && (
                <span className="text-2xl text-[var(--text-tertiary)]">%</span>
              )}
            </p>
          </div>
        </div>
      </Card>

      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-4 gap-6">
        <StatCard
          label="Pass Rate"
          value={metrics ? `${(metrics.pass_rate * 100).toFixed(0)}%` : "—"}
        />
        <StatCard
          label="Avg Latency"
          value={metrics ? `${metrics.avg_latency_seconds.toFixed(0)}s` : "—"}
        />
        <StatCard
          label="Token Efficiency"
          value={metrics ? `${(metrics.token_efficiency * 100).toFixed(0)}%` : "—"}
        />
        <StatCard
          label="Total Earned"
          value={`$${totalEarned.toFixed(2)}`}
        />
      </div>

      {/* ── Two-column: Recent Tasks + Ledger ── */}
      <div className="grid grid-cols-2 gap-6">
        {/* Left: Recent Tasks */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
            Recent Tasks
            <span className="ml-2 text-sm font-normal text-[var(--text-tertiary)]">
              ({agentTasks.length})
            </span>
          </h2>
          {agentTasks.length > 0 ? (
            <div className="space-y-3">
              {agentTasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-[var(--text-primary)]">
                      {task.task_spec.description}
                    </p>
                    <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
                      {fmt(task.created_at)}
                    </p>
                  </div>
                  <div className="ml-3 flex-shrink-0">
                    <Badge status={task.status} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-tertiary)]">No tasks yet</p>
          )}
        </Card>

        {/* Right: Ledger */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
            Ledger
            <span className="ml-2 text-sm font-normal text-[var(--text-tertiary)]">
              ({ledger?.length ?? 0})
            </span>
          </h2>
          {ledger && ledger.length > 0 ? (
            <div className="space-y-3">
              {[...ledger]
                .sort(
                  (a, b) =>
                    new Date(b.created_at).getTime() -
                    new Date(a.created_at).getTime(),
                )
                .map((entry) => (
                  <div
                    key={entry.id}
                    className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2"
                  >
                    <div>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          entry.entry_type === "reward"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-red-50 text-red-700"
                        }`}
                      >
                        {entry.entry_type}
                      </span>
                      <span className="ml-2 text-xs text-[var(--text-tertiary)]">
                        {fmt(entry.created_at)}
                      </span>
                    </div>
                    <span
                      className={`font-mono text-sm font-medium ${
                        entry.amount >= 0
                          ? "text-[var(--success)]"
                          : "text-[var(--error)]"
                      }`}
                    >
                      {entry.amount >= 0 ? "+" : ""}
                      ${entry.amount.toFixed(2)}
                    </span>
                  </div>
                ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-tertiary)]">
              No ledger entries
            </p>
          )}
        </Card>
      </div>
    </PageShell>
  );
}
