import useSWR from "swr";
import { fetcher } from "@/lib/api";

interface RawStats {
  total_tasks: number;
  completed_tasks: number;
  active_agents: number;
  total_rewards: number;
}

interface TopAgent {
  id: string;
  name: string;
  pass_rate: number;
  quality_score: number;
  total_submissions: number;
}

export interface DashboardStats {
  total_tasks: number;
  completed_tasks: number;
  active_agents: number;
  total_rewards: number;
  top_agents: Array<{
    name: string;
    pass_rate: number;
    quality_score: number;
  }>;
}

export interface ValidationRateResponse {
  pass_rate: number;
  passed: number;
  total: number;
}

export function useStats() {
  return useSWR<DashboardStats>("dashboard-combined", async () => {
    const [stats, topAgents] = await Promise.all([
      fetcher<RawStats>("/dashboard/stats"),
      fetcher<TopAgent[]>("/dashboard/agents/top"),
    ]);
    return {
      ...stats,
      top_agents: topAgents.map((a) => ({
        name: a.name,
        pass_rate: a.pass_rate,
        quality_score: a.quality_score / 100, // API returns 0-100, frontend expects 0-1
      })),
    };
  });
}

export function useValidationRate() {
  return useSWR<ValidationRateResponse>("/dashboard/validation-rate", fetcher);
}
