"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { useWebSocket } from "@/hooks/use-websocket";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Connect once — revalidates SWR caches on task events for all child pages
  useWebSocket();

  return (
    <>
      <Sidebar />
      {children}
    </>
  );
}
