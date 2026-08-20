import type { ReactNode } from 'react';

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-400" role="status">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-blue-400" />
      <p className="mt-3 text-sm">{label}</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-red-800/50 bg-red-950/30 p-6 text-center" role="alert">
      <p className="text-red-300">⚠️ {message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded-md border border-red-400/50 px-4 py-1.5 text-sm text-red-200 hover:bg-red-900/40"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-10 text-center">
      <p className="text-slate-300">{title}</p>
      {hint && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
    </div>
  );
}

export function Badge({ children, tone = 'slate' }: { children: ReactNode; tone?: string }) {
  const tones: Record<string, string> = {
    slate: 'bg-slate-800 text-slate-300',
    green: 'bg-emerald-900/60 text-emerald-300',
    amber: 'bg-amber-900/60 text-amber-300',
    red: 'bg-red-900/60 text-red-300',
    blue: 'bg-blue-900/60 text-blue-300',
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone] || tones.slate}`}>
      {children}
    </span>
  );
}

export function StatCard({ label, value, sub, tone = 'blue' }: { label: string; value: string | number; sub?: string; tone?: string }) {
  const accents: Record<string, string> = {
    blue: 'text-blue-300',
    green: 'text-emerald-300',
    amber: 'text-amber-300',
    red: 'text-red-300',
    slate: 'text-slate-200',
  };
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 shadow-sm">
      <p className="text-xs uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-1 text-3xl font-semibold ${accents[tone] || accents.blue}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}
