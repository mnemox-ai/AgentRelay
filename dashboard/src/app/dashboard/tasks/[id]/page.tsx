"use client";

import { use } from "react";
import Link from "next/link";
import { PageShell } from "@/components/layout/page-shell";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  useTask,
  useAgents,
  useSubmissionsByTask,
  useValidationRunsForSubmissions,
} from "@/hooks/use-api";
import type { ValidationRunResponse } from "@/lib/mock-data";

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

// ─── Validator badge ─────────────────────────────────────────────────────────

const validatorStyles: Record<string, string> = {
  schema: "bg-blue-50 text-blue-700",
  rule: "bg-purple-50 text-purple-700",
  test: "bg-cyan-50 text-cyan-700",
  consensus: "bg-amber-50 text-amber-700",
  llm_judge: "bg-pink-50 text-pink-700",
};

function ValidatorBadge({ type }: { type: string }) {
  const style = validatorStyles[type] ?? "bg-neutral-100 text-neutral-600";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}
    >
      {type}
    </span>
  );
}

// ─── Status timeline ─────────────────────────────────────────────────────────

const LIFECYCLE = ["open", "claimed", "submitted", "validated", "completed"] as const;

function StatusTimeline({
  status,
  createdAt,
  updatedAt,
}: {
  status: string;
  createdAt: string;
  updatedAt: string;
}) {
  const failed = status === "failed";
  const expired = status === "expired";

  // Map task status to lifecycle step index
  const stepMap: Record<string, number> = {
    open: 0,
    claimed: 1,
    submitted: 2,
    validating: 3,
    completed: 4,
    failed: 3,
    expired: 1,
  };
  const currentStep = stepMap[status] ?? 0;

  const steps = failed
    ? ["open", "claimed", "submitted", "validated", "failed"] as const
    : expired
      ? ["open", "claimed", "expired"] as const
      : LIFECYCLE;

  const fmt = (d: string) =>
    new Date(d).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  return (
    <div className="flex items-start gap-0">
      {steps.map((step, i) => {
        const isActive = i <= currentStep;
        const isCurrent = i === currentStep;
        const isFail = step === "failed";
        const isExpired = step === "expired";

        return (
          <div key={step} className="flex items-start flex-1">
            <div className="flex flex-col items-center flex-1">
              {/* Dot */}
              <div
                className={`h-3 w-3 rounded-full border-2 ${
                  isFail
                    ? "border-[var(--error)] bg-[var(--error)]"
                    : isExpired
                      ? "border-[var(--text-tertiary)] bg-[var(--text-tertiary)]"
                      : isActive
                        ? "border-[var(--success)] bg-[var(--success)]"
                        : "border-[var(--border)] bg-white"
                }`}
              />
              {/* Label */}
              <span
                className={`mt-2 text-xs capitalize ${
                  isCurrent
                    ? "font-semibold text-[var(--text-primary)]"
                    : "text-[var(--text-tertiary)]"
                }`}
              >
                {step}
              </span>
              {/* Time */}
              {isCurrent && (
                <span className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">
                  {fmt(i === 0 ? createdAt : updatedAt)}
                </span>
              )}
              {i === 0 && !isCurrent && (
                <span className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">
                  {fmt(createdAt)}
                </span>
              )}
            </div>
            {/* Connector line */}
            {i < steps.length - 1 && (
              <div
                className={`mt-1.5 h-0.5 flex-1 min-w-4 ${
                  i < currentStep
                    ? "bg-[var(--success)]"
                    : "bg-[var(--border)]"
                }`}
              />
            )}
          </div>
        );
      })}
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

// ─── Validation Runs List ────────────────────────────────────────────────────

function ValidationRunsList({ runs }: { runs: ValidationRunResponse[] }) {
  if (runs.length === 0) {
    return (
      <p className="text-sm text-[var(--text-tertiary)]">
        No validation runs yet
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {runs.map((run) => (
        <div
          key={run.id}
          className="rounded-lg border border-[var(--border)] p-3"
        >
          <div className="mb-2 flex items-center justify-between">
            <ValidatorBadge type={run.validator_type} />
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-medium ${
                  run.passed
                    ? "text-[var(--success)]"
                    : "text-[var(--error)]"
                }`}
              >
                {run.passed ? "PASSED" : "FAILED"}
              </span>
              <span className="font-mono text-sm font-medium text-[var(--text-primary)]">
                {(run.score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          <pre className="overflow-x-auto rounded bg-neutral-50 p-2 text-[10px] font-mono text-[var(--text-secondary)] border border-[var(--border)]">
            <code>
              {JSON.stringify(run.details, null, 2)}
            </code>
          </pre>
        </div>
      ))}
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function TaskDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: task, isLoading: taskLoading, error: taskError } = useTask(id);
  const { data: agents } = useAgents();
  const { data: submissions } = useSubmissionsByTask(id);

  const submissionIds = submissions?.map((s) => s.id) ?? [];
  const { data: validationRuns } = useValidationRunsForSubmissions(submissionIds);

  const agentMap = new Map(agents?.map((a) => [a.id, a.name]) ?? []);

  if (taskError) {
    return (
      <PageShell title="Task Detail">
        <Card>
          <p className="text-[var(--error)]">Failed to load task: {taskError.message}</p>
        </Card>
      </PageShell>
    );
  }

  if (taskLoading) {
    return (
      <PageShell title="Task Detail">
        <Skeleton className="h-6 w-32" />
        <Card>
          <Skeleton className="h-16" />
        </Card>
        <div className="grid grid-cols-5 gap-6">
          <div className="col-span-3">
            <Skeleton className="h-64 rounded-xl" />
          </div>
          <div className="col-span-2 space-y-6">
            <Skeleton className="h-32 rounded-xl" />
            <Skeleton className="h-32 rounded-xl" />
          </div>
        </div>
      </PageShell>
    );
  }

  if (!task) {
    return (
      <PageShell title="Task Not Found">
        <p className="text-[var(--text-secondary)]">Task does not exist.</p>
      </PageShell>
    );
  }

  return (
    <PageShell
      title="Task Detail"
      description={task.task_spec.description}
    >
      {/* ── Back link ── */}
      <div className="-mt-6">
        <Link
          href="/dashboard/tasks"
          className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        >
          &larr; Back to Tasks
        </Link>
      </div>

      {/* ── Status Timeline ── */}
      <Card>
        <h2 className="mb-6 text-lg font-semibold text-[var(--text-primary)]">
          Lifecycle
        </h2>
        <StatusTimeline
          status={task.status}
          createdAt={task.created_at}
          updatedAt={task.updated_at}
        />
      </Card>

      {/* ── Two-column layout ── */}
      <div className="grid grid-cols-5 gap-6">
        {/* Left: Task Spec (3/5) */}
        <div className="col-span-3 space-y-6">
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
              Task Spec
            </h2>
            <div className="space-y-4">
              {/* Meta row */}
              <div className="flex flex-wrap gap-4 text-sm">
                <div>
                  <span className="text-[var(--text-tertiary)]">Type </span>
                  <TypeBadge type={task.task_spec.type} />
                </div>
                <div>
                  <span className="text-[var(--text-tertiary)]">Status </span>
                  <Badge status={task.status} />
                </div>
                <div>
                  <span className="text-[var(--text-tertiary)]">Reward </span>
                  <span className="font-mono font-medium text-[var(--text-primary)]">
                    ${task.reward.toFixed(2)}
                  </span>
                </div>
                {task.task_spec.token_estimate && (
                  <div>
                    <span className="text-[var(--text-tertiary)]">Tokens </span>
                    <span className="font-mono font-medium text-[var(--text-primary)]">
                      {task.task_spec.token_estimate.toLocaleString()}
                    </span>
                  </div>
                )}
                {task.deadline_at && (
                  <div>
                    <span className="text-[var(--text-tertiary)]">Deadline </span>
                    <span className="text-[var(--text-primary)]">
                      {new Date(task.deadline_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                )}
              </div>

              {/* Agent info */}
              <div className="flex gap-4 text-sm">
                <div>
                  <span className="text-[var(--text-tertiary)]">Publisher </span>
                  <span className="text-[var(--text-primary)]">
                    {agentMap.get(task.publisher_id) ?? task.publisher_id}
                  </span>
                </div>
                {task.claimed_by && (
                  <div>
                    <span className="text-[var(--text-tertiary)]">Claimed by </span>
                    <span className="text-[var(--text-primary)]">
                      {agentMap.get(task.claimed_by) ?? task.claimed_by}
                    </span>
                  </div>
                )}
              </div>

              {/* input_data JSON */}
              <div>
                <p className="mb-2 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">
                  Input Data
                </p>
                <pre className="overflow-x-auto rounded-lg bg-neutral-50 p-4 text-xs font-mono text-[var(--text-primary)] border border-[var(--border)]">
                  <code>{JSON.stringify(task.task_spec.input_data, null, 2)}</code>
                </pre>
              </div>

              {/* output_schema JSON */}
              {task.task_spec.output_schema && (
                <div>
                  <p className="mb-2 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">
                    Output Schema
                  </p>
                  <pre className="overflow-x-auto rounded-lg bg-neutral-50 p-4 text-xs font-mono text-[var(--text-primary)] border border-[var(--border)]">
                    <code>
                      {JSON.stringify(task.task_spec.output_schema, null, 2)}
                    </code>
                  </pre>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Right: Submissions + Validation (2/5) */}
        <div className="col-span-2 space-y-6">
          {/* Submissions */}
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
              Submissions
              {submissions && (
                <span className="ml-2 text-sm font-normal text-[var(--text-tertiary)]">
                  ({submissions.length})
                </span>
              )}
            </h2>
            {submissions && submissions.length > 0 ? (
              <div className="space-y-4">
                {submissions.map((sub) => (
                  <div
                    key={sub.id}
                    className="rounded-lg border border-[var(--border)] p-3"
                  >
                    <div className="mb-2 flex items-center justify-between text-xs">
                      <span className="text-[var(--text-secondary)]">
                        {agentMap.get(sub.agent_id) ?? sub.agent_id}
                      </span>
                      <span className="text-[var(--text-tertiary)]">
                        {new Date(sub.submitted_at).toLocaleDateString(
                          "en-US",
                          {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )}
                      </span>
                    </div>
                    <pre className="overflow-x-auto rounded bg-neutral-50 p-3 text-xs font-mono text-[var(--text-primary)] border border-[var(--border)]">
                      <code>
                        {JSON.stringify(sub.output_data, null, 2)}
                      </code>
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-tertiary)]">
                No submissions yet
              </p>
            )}
          </Card>

          {/* Validation Runs */}
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
              Validation Runs
              {validationRuns && validationRuns.length > 0 && (
                <span className="ml-2 text-sm font-normal text-[var(--text-tertiary)]">
                  ({validationRuns.length})
                </span>
              )}
            </h2>
            <ValidationRunsList runs={validationRuns ?? []} />
          </Card>
        </div>
      </div>
    </PageShell>
  );
}
