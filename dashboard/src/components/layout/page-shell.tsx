interface PageShellProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

export function PageShell({ title, description, children }: PageShellProps) {
  return (
    <main className="min-h-screen bg-[var(--bg)] pt-14 md:pt-0 md:ml-56">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8 sm:py-10">
        <div className="mb-12">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            {title}
          </h1>
          {description && (
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              {description}
            </p>
          )}
        </div>
        <div className="space-y-12">{children}</div>
      </div>
    </main>
  );
}
