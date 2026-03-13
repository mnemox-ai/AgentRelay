import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type {
  SubmissionResponse,
  ValidationRunResponse,
  ReputationResponse,
  LedgerEntry,
} from "@/lib/mock-data";

// Re-export from separate hook files
export { useAgents, useAgent } from "./use-agents";
export { useTasks, useTask, useRecentTasks } from "./use-tasks";
export { useStats, useValidationRate } from "./use-stats";

// ─── Submissions ───────────────────────────────────────────────────────────

export function useSubmissions() {
  return useSWR<SubmissionResponse[]>("/submissions", fetcher);
}

export function useSubmissionsByTask(taskId: string | undefined) {
  return useSWR<SubmissionResponse[]>(
    taskId ? `/tasks/${taskId}/submissions` : null,
    fetcher,
  );
}

// ─── Validation Runs ───────────────────────────────────────────────────────

export function useValidationRuns(submissionId: string | undefined) {
  return useSWR<ValidationRunResponse[]>(
    submissionId ? `/submissions/${submissionId}/validation` : null,
    fetcher,
  );
}

export function useValidationRunsForSubmissions(submissionIds: string[]) {
  const key =
    submissionIds.length > 0
      ? `validation-runs:${[...submissionIds].sort().join(",")}`
      : null;
  return useSWR<ValidationRunResponse[]>(key, async () => {
    const results = await Promise.all(
      submissionIds.map((id) =>
        fetcher<ValidationRunResponse[]>(`/submissions/${id}/validation`),
      ),
    );
    return results.flat();
  });
}

// ─── Reputation ────────────────────────────────────────────────────────────

export function useReputations() {
  return useSWR<ReputationResponse[]>("/reputation", fetcher);
}

export function useReputation(agentId: string | undefined) {
  return useSWR<ReputationResponse>(
    agentId ? `/reputation/${agentId}` : null,
    fetcher,
  );
}

// ─── Ledger ────────────────────────────────────────────────────────────────

export function useLedger() {
  return useSWR<LedgerEntry[]>("/ledger", fetcher);
}

export function useLedgerByAgent(agentId: string | undefined) {
  return useSWR<LedgerEntry[]>(
    agentId ? `/ledger/${agentId}` : null,
    fetcher,
  );
}
