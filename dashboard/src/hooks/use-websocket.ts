import { useEffect, useRef } from "react";
import { useSWRConfig } from "swr";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

// SWR keys to revalidate per event type
const REVALIDATE_MAP: Record<string, string[]> = {
  task_created: ["/tasks/available", "/dashboard/tasks/recent", "/dashboard/stats"],
  task_claimed: ["/tasks/available", "/dashboard/tasks/recent", "/dashboard/stats"],
  task_completed: ["/tasks/available", "/dashboard/tasks/recent", "/dashboard/stats", "/dashboard/validation-rate"],
  task_failed: ["/tasks/available", "/dashboard/tasks/recent", "/dashboard/stats", "/dashboard/validation-rate"],
};

export function useWebSocket() {
  const { mutate } = useSWRConfig();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as { event: string; data: unknown };
          const keys = REVALIDATE_MAP[msg.event];
          if (keys) {
            keys.forEach((key) => mutate(key));
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        // Reconnect after 3 seconds
        reconnectTimer.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [mutate]);
}
