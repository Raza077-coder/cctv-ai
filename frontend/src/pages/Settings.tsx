import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Badge, ErrorState, Spinner } from '../components/ui';
import type { Health } from '../types';

export default function Settings() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      setHealth(await api.health());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load settings');
    }
  };

  useEffect(() => { load(); }, []);

  if (error && !health) return <ErrorState message={error} onRetry={load} />;
  if (!health) return <Spinner label="Loading settings…" />;

  const save = async () => {
    setSaved(null);
    try {
      setHealth(await api.health());
      setSaved('Health check refreshed');
      setTimeout(() => setSaved(null), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Refresh failed');
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-slate-500">System configuration and health.</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h2 className="mb-4 text-lg font-medium">System Health</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            ['Application', `${health.app} v${health.version}`],
            ['API Status', health.status],
            ['Database', health.database],
            ['Redis', health.redis],
            ['YOLO Model', health.models_loaded[0] || 'not loaded'],
          ].map(([k, v]) => (
            <div key={k} className="rounded-lg bg-slate-950 px-4 py-3">
              <p className="text-xs text-slate-500">{k}</p>
              <p className={`mt-0.5 text-sm font-medium ${v === 'ok' || v === 'running' ? 'text-emerald-300' : ''}`}>{v}</p>
            </div>
          ))}
        </div>
        <button onClick={save} className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500">
          Refresh
        </button>
        {saved && <span className="ml-3 text-sm text-emerald-400">{saved}</span>}
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h2 className="mb-3 text-lg font-medium">Feature Toggles</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(health.features).map(([k, v]) => (
            <Badge key={k} tone={v ? 'green' : 'slate'}>{k.replace(/_/g, ' ')}: {v ? 'enabled' : 'disabled'}</Badge>
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-500">
          Feature toggles are set via environment variables (<code className="text-slate-400">ENABLE_ANPR</code>,{' '}
          <code className="text-slate-400">ENABLE_FACE_RECOGNITION</code>,{' '}
          <code className="text-slate-400">ENABLE_MOTION_DETECTION</code>) and require a backend restart.
        </p>
      </div>
    </div>
  );
}
