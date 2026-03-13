"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/page-shell";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTasks, useAgents } from "@/hooks/use-api";

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

// ─── Difficulty badge ────────────────────────────────────────────────────────

const difficultyStyles: Record<string, string> = {
  easy: "bg-emerald-50 text-emerald-700",
  medium: "bg-amber-50 text-amber-700",
  hard: "bg-red-50 text-red-700",
};

function DifficultyBadge({ level }: { level: string }) {
  const style = difficultyStyles[level] ?? "bg-neutral-100 text-neutral-600";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${style}`}
    >
      {level}
    </span>
  );
}

// ─── Filter tabs ─────────────────────────────────────────────────────────────

const TABS = ["all", "open", "claimed", "completed", "failed"] as const;
type Tab = (typeof TABS)[number];

// ─── Skeleton ────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-neutral-200 ${className ?? ""}`}
    />
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function TasksPage() {
  const [activeTab, setActiveTab] = useState<Tab>("all");
  const router = useRouter();
  const { data: tasks, isLoading, error } = useTasks();
  const { data: agents } = useAgents();

  const agentMap = new Map(agents?.map((a) => [a.id, a.name]) ?? []);

  if (error) {
    return (
      <PageShell title="Tasks" description="Browse and filter all tasks">
        <Card>
          <p className="text-[var(--error)]">Failed to load tasks: {error.message}</p>
        </Card>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell title="Tasks" description="Browse and filter all tasks">
        <Skeleton className="h-10 w-96" />
        <Card>
          <div className="space-y-3">
            {[...Array(8)].map((_, i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        </Card>
      </PageShell>
    );
  }

  const filteredTasks = tasks
    ? activeTab === "all"
      ? tasks
      : tasks.filter((t) => t.status === activeTab)
    : [];

  const sorted = [...filteredTasks].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <PageShell title="Tasks" description="Browse and filter all tasks">
      {/* ── Filter Tabs ── */}
      <div className="flex gap-1 rounded-lg bg-neutral-100 p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium capitalize transition-colors ${
              activeTab === tab
                ? "bg-white text-[var(--text-primary)] shadow-sm"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            {tab}
            {tasks && (
              <span className="ml-1.5 text-xs text-[var(--text-tertiary)]">
                {tab === "all"
                  ? tasks.length
                  : tasks.filter((t) => t.status === tab).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tasks Table ── */}
      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--text-tertiary)]">
              <th className="pb-3 font-medium">Type</th>
              <th className="pb-3 font-medium">Status</th>
              <th className="pb-3 font-medium">Difficulty</th>
              <th className="pb-3 font-medium text-right">Token Est.</th>
              <th className="pb-3 font-medium text-right">Reward</th>
              <th className="pb-3 font-medium">Agent</th>
              <th className="pb-3 font-medium text-right">Created</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((task) => (
              <tr
                key={task.id}
                onClick={() =>
                  router.push(`/dashboard/tasks/${task.id}`)
                }
                className="border-b border-[var(--border)] last:border-0 cursor-pointer hover:bg-neutral-50 transition-colors"
              >
                <td className="py-3">
                  <TypeBadge type={task.task_spec.type} />
                </td>
                <td className="py-3">
                  <Badge status={task.status} />
                </td>
                <td className="py-3">
                  <DifficultyBadge
                    level={
                      (task.task_spec.token_estimate ?? 0) > 4000
                        ? "hard"
                        : (task.task_spec.token_estimate ?? 0) > 2000
                          ? "medium"
                          : "easy"
                    }
                  />
                </td>
                <td className="py-3 text-right font-mono text-[var(--text-primary)]">
                  {task.task_spec.token_estimate?.toLocaleString() ?? "\u2014"}
                </td>
                <td className="py-3 text-right font-mono text-[var(--text-primary)]">
                  ${task.reward.toFixed(0)}
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
            {sorted.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="py-8 text-center text-[var(--text-tertiary)]"
                >
                  No tasks found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </PageShell>
  );
}
