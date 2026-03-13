import useSWR from "swr";
import { fetcher } from "@/lib/api";

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
  return useSWR<DashboardStats>("/dashboard/stats", fetcher);
}

export function useValidationRate() {
  return useSWR<ValidationRateResponse>("/dashboard/validation-rate", fetcher);
}
