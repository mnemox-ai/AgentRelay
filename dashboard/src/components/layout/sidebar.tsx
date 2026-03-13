"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const navItems = [
  { label: "Overview", href: "/dashboard" },
  { label: "Tasks", href: "/dashboard/tasks" },
  { label: "Agents", href: "/dashboard/agents" },
  { label: "Reputation", href: "/dashboard/reputation" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [apiKey, setApiKey] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);

  const navContent = (
    <>
      <div className="px-6 py-8">
        <span className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">
          AgentRelay
        </span>
      </div>

      <nav className="flex-1 px-3">
        {navItems.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={`block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-[var(--bg)] text-[var(--text-primary)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg)] hover:text-[var(--text-primary)]"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[var(--border)] px-4 py-4">
        <label className="block text-xs font-medium text-[var(--text-tertiary)] mb-2">
          API Key
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Enter API key"
          className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
        />
      </div>
    </>
  );

  return (
    <>
      {/* Mobile top bar */}
      <div className="fixed top-0 left-0 right-0 z-40 flex items-center justify-between border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 md:hidden">
        <span className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">
          AgentRelay
        </span>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg)] hover:text-[var(--text-primary)]"
          aria-label="Toggle menu"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            {mobileOpen ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
              />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile slide-out sidebar */}
      <aside
        className={`fixed left-0 top-0 z-50 h-screen w-56 border-r border-[var(--border)] bg-[var(--bg-card)] flex flex-col transition-transform duration-200 md:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {navContent}
      </aside>

      {/* Desktop sidebar */}
      <aside className="fixed left-0 top-0 h-screen w-56 border-r border-[var(--border)] bg-[var(--bg-card)] flex-col hidden md:flex">
        {navContent}
      </aside>
    </>
  );
}
