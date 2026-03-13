import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { AgentResponse } from "@/lib/mock-data";

export function useAgents() {
  return useSWR<AgentResponse[]>("/agents", fetcher);
}

export function useAgent(id: string | undefined) {
  return useSWR<AgentResponse>(id ? `/agents/${id}` : null, fetcher);
}
