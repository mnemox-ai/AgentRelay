"use client";

import { PageShell } from "@/components/layout/page-shell";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat-card";
import { useTasks, useAgents, useLedger, useReputations } from "@/hooks/use-api";
import { mockSubmissions, mockValidationRuns } from "@/lib/mock-data";

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

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getTaskScore(taskId: string): number | null {
  const subs = mockSubmissions.filter((s) => s.task_id === taskId);
  if (subs.length === 0) return null;
  const runs = mockValidationRuns.filter((v) =>
    subs.some((s) => s.id === v.submission_id),
  );
  if (runs.length === 0) return null;
  return runs.reduce((sum, r) => sum + r.score, 0) / runs.length;
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { data: tasks } = useTasks();
  const { data: agents } = useAgents();
  const { data: ledger } = useLedger();
  const { data: reputations } = useReputations();

  // Stat cards
  const totalTasks = tasks?.length ?? 0;
  const completedTasks =
    tasks?.filter((t) => t.status === "completed").length ?? 0;
  const activeAgents =
    agents?.filter((a) => a.status === "active").length ?? 0;
  const totalRewards =
    ledger
      ?.filter((e) => e.entry_type === "reward")
      .reduce((sum, e) => sum + e.amount, 0) ?? 0;

  // Recent 5 tasks (newest first)
  const recentTasks = tasks
    ? [...tasks]
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() -
            new Date(a.created_at).getTime(),
        )
        .slice(0, 5)
    : [];

  // Agent name lookup
  const agentMap = new Map(agents?.map((a) => [a.id, a.name]) ?? []);

  // Validation pass rate (aggregate)
  const passRate =
    mockValidationRuns.length > 0
      ? mockValidationRuns.filter((v) => v.passed).length /
        mockValidationRuns.length
      : 0;

  // Top 3 agents by quality_score
  const topAgents = reputations
    ? [...reputations]
        .sort((a, b) => b.metrics.quality_score - a.metrics.quality_score)
        .slice(0, 3)
        .map((r) => ({
          name: agentMap.get(r.agent_id) ?? r.agent_id,
          pass_rate: r.metrics.pass_rate,
          quality_score: r.metrics.quality_score,
        }))
    : [];

  return (
    <PageShell title="Overview" description="Platform health and activity summary">
      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-4 gap-6">
        <StatCard label="Total Tasks" value={totalTasks} />
        <StatCard label="Completed" value={completedTasks} />
        <StatCard label="Active Agents" value={activeAgents} />
        <StatCard label="Total Rewards" value={`$${totalRewards.toFixed(0)}`} />
      </div>

      {/* ── Recent Tasks ── */}
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
          Recent Tasks
        </h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--text-tertiary)]">
              <th className="pb-3 font-medium">Type</th>
              <th className="pb-3 font-medium">Status</th>
              <th className="pb-3 font-medium">Agent</th>
              <th className="pb-3 font-medium text-right">Score</th>
              <th className="pb-3 font-medium text-right">Created</th>
            </tr>
          </thead>
          <tbody>
            {recentTasks.map((task) => {
              const score = getTaskScore(task.id);
              return (
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
                  <td className="py-3 text-right font-mono text-[var(--text-primary)]">
                    {score !== null ? `${(score * 100).toFixed(0)}%` : "\u2014"}
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
              );
            })}
          </tbody>
        </table>
      </Card>

      {/* ── Bottom: Pass Rate + Top Agents ── */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
            Validation Pass Rate
          </h2>
          <p className="text-5xl font-semibold font-mono text-[var(--text-primary)]">
            {(passRate * 100).toFixed(0)}%
          </p>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            {mockValidationRuns.filter((v) => v.passed).length} passed /{" "}
            {mockValidationRuns.length} total runs
          </p>
        </Card>

        <Card>
          <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
            Top Agents
          </h2>
          <div className="space-y-4">
            {topAgents.map((agent, i) => (
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
        </Card>
      </div>
    </PageShell>
  );
}
