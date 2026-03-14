import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type {
  SubmissionResponse,
  ValidationRunResponse,
  LedgerEntry,
} from "@/lib/mock-data";

// Re-export from separate hook files
export { useAgents, useAgent } from "./use-agents";
export { useTasks, useTask, useRecentTasks } from "./use-tasks";
export { useStats, useValidationRate } from "./use-stats";
export { useWebSocket } from "./use-websocket";

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

// ─── Reputation (from /dashboard/agents/top) ─────────────────────────────

interface TopAgentResponse {
  id: string;
  name: string;
  quality_score: number;
  total_submissions: number;
  pass_rate: number;
}

interface ReputationEntry {
  agent_id: string;
  metrics: {
    quality_score: number;
    pass_rate: number;
    total_submissions: number;
  };
}

export function useReputations() {
  return useSWR<ReputationEntry[]>("reputation-from-top", async () => {
    const agents = await fetcher<TopAgentResponse[]>("/dashboard/agents/top");
    return agents.map((a) => ({
      agent_id: a.id,
      metrics: {
        quality_score: a.quality_score / 100,
        pass_rate: a.pass_rate,
        total_submissions: a.total_submissions,
      },
    }));
  });
}

export function useReputation(agentId: string | undefined) {
  return useSWR<ReputationEntry>(
    agentId ? `reputation-${agentId}` : null,
    async () => {
      const data = await fetcher<TopAgentResponse>(`/dashboard/agents/${agentId}/reputation`);
      return {
        agent_id: agentId!,
        metrics: {
          quality_score: (data.quality_score ?? 0) / 100,
          pass_rate: data.pass_rate ?? 0,
          total_submissions: data.total_submissions ?? 0,
        },
      };
    },
  );
}

// ─── Ledger ────────────────────────────────────────────────────────────────

export function useLedger() {
  // No flat /ledger endpoint
  return useSWR<LedgerEntry[]>(null, fetcher);
}

export function useLedgerByAgent(agentId: string | undefined) {
  return useSWR<LedgerEntry[]>(
    agentId ? `/dashboard/agents/${agentId}/ledger` : null,
    fetcher,
  );
}
