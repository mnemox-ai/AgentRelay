import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { TaskResponse } from "@/lib/mock-data";

export function useRecentTasks() {
  return useSWR<TaskResponse[]>("/dashboard/tasks/recent", fetcher);
}

export function useTasks() {
  return useSWR<TaskResponse[]>("/tasks/available", fetcher);
}

export function useTask(id: string | undefined) {
  return useSWR<TaskResponse>(id ? `/tasks/${id}` : null, fetcher);
}
