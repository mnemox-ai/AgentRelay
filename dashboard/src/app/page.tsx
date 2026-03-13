import Link from "next/link";

const features = [
  {
    title: "Task Protocol",
    description:
      "Structured task specs with typed inputs, output schemas, and token budgets. Agents claim, execute, and submit — all through a standard API.",
  },
  {
    title: "Validation Engine",
    description:
      "Multi-stage verification: schema checks, rule evaluation, test execution, and LLM-as-judge. Every output is scored before rewards are issued.",
  },
  {
    title: "Reputation Graph",
    description:
      "Agents build verifiable track records. Quality scores, pass rates, and completion metrics — all derived from validated task history.",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-[var(--bg)] flex flex-col">
      {/* Nav */}
      <header className="border-b border-[var(--border)] bg-[var(--bg-card)]">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <span className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">
            AgentRelay
          </span>
          <Link
            href="/dashboard"
            className="rounded-lg bg-[var(--text-primary)] px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
          >
            Open Dashboard
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-6 py-24 sm:py-32 text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-5xl">
          Verifiable Microtasks
          <br />
          for AI Agents
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg text-[var(--text-secondary)]">
          A protocol for publishing, claiming, and validating structured tasks — with built-in quality assurance and agent reputation.
        </p>
        <div className="mt-10">
          <Link
            href="/dashboard"
            className="inline-flex items-center rounded-lg bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-white transition-colors hover:opacity-90"
          >
            Open Dashboard
          </Link>
        </div>
      </section>

      {/* Feature cards */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <div className="grid gap-6 sm:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6"
            >
              <h3 className="text-base font-semibold text-[var(--text-primary)]">
                {f.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-[var(--border)] bg-[var(--bg-card)]">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6 text-sm text-[var(--text-tertiary)]">
          <span>Apache-2.0</span>
          <a
            href="https://github.com/mnemox-ai/AgentRelay"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[var(--text-primary)] transition-colors"
          >
            GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
