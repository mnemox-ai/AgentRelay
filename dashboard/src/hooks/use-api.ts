import useSWR from "swr";
import { fetcher } from "@/lib/api";
import {
  type AgentResponse,
  type TaskResponse,
  type SubmissionResponse,
  type ValidationRunResponse,
  type ReputationResponse,
  type LedgerEntry,
  mockAgents,
  mockTasks,
  mockSubmissions,
  mockValidationRuns,
  mockReputationSnapshots,
  mockLedgerEntries,
  getMockAgent,
  getMockTask,
  getMockSubmissionsByTask,
  getMockValidationsBySubmission,
  getMockReputationByAgent,
  getMockLedgerByAgent,
} from "@/lib/mock-data";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

function useMockOrFetch<T>(key: string, mockData: T) {
  return useSWR<T>(
    key,
    USE_MOCK ? () => Promise.resolve(mockData) : fetcher<T>,
  );
}

// ─── Agents ────────────────────────────────────────────────────────────────

export function useAgents() {
  return useMockOrFetch<AgentResponse[]>("/agents", mockAgents);
}

export function useAgent(id: string | undefined) {
  return useMockOrFetch<AgentResponse | undefined>(
    id ? `/agents/${id}` : "",
    id ? getMockAgent(id) : undefined,
  );
}

// ─── Tasks ─────────────────────────────────────────────────────────────────

export function useTasks() {
  return useMockOrFetch<TaskResponse[]>("/tasks/available", mockTasks);
}

export function useTask(id: string | undefined) {
  return useMockOrFetch<TaskResponse | undefined>(
    id ? `/tasks/${id}` : "",
    id ? getMockTask(id) : undefined,
  );
}

// ─── Submissions ───────────────────────────────────────────────────────────

export function useSubmissions() {
  return useMockOrFetch<SubmissionResponse[]>("/submissions", mockSubmissions);
}

export function useSubmissionsByTask(taskId: string | undefined) {
  return useMockOrFetch<SubmissionResponse[]>(
    taskId ? `/tasks/${taskId}/submissions` : "",
    taskId ? getMockSubmissionsByTask(taskId) : [],
  );
}

// ─── Validation Runs ───────────────────────────────────────────────────────

export function useValidationRuns(submissionId: string | undefined) {
  return useMockOrFetch<ValidationRunResponse[]>(
    submissionId ? `/submissions/${submissionId}/validation` : "",
    submissionId ? getMockValidationsBySubmission(submissionId) : [],
  );
}

// ─── Reputation ────────────────────────────────────────────────────────────

export function useReputations() {
  return useMockOrFetch<ReputationResponse[]>("/reputation", mockReputationSnapshots);
}

export function useReputation(agentId: string | undefined) {
  return useMockOrFetch<ReputationResponse | undefined>(
    agentId ? `/reputation/${agentId}` : "",
    agentId ? getMockReputationByAgent(agentId) : undefined,
  );
}

// ─── Ledger ────────────────────────────────────────────────────────────────

export function useLedger() {
  return useMockOrFetch<LedgerEntry[]>("/ledger", mockLedgerEntries);
}

export function useLedgerByAgent(agentId: string | undefined) {
  return useMockOrFetch<LedgerEntry[]>(
    agentId ? `/ledger/${agentId}` : "",
    agentId ? getMockLedgerByAgent(agentId) : [],
  );
}
