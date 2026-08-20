import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Badge, EmptyState, ErrorState, Spinner } from '../components/ui';
import type { AlertItem } from '../types';

const severityTone: Record<string, string> = {
  critical: 'red', high: 'red', medium: 'amber', low: 'amber', info: 'slate',
};
const statusTone: Record<string, string> = {
  active: 'red', acknowledged: 'amber', resolved: 'green',
};

export default function Alerts() {
  const [items, setItems] = useState<AlertItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [error, setError] = useState<string | null>(null);

  const load = async (st?: string) => {
    setError(null);
    try {
      const params: Record<string, string | number> = { limit: 100 };
      if (st) params.status = st;
      const res = await api.listAlerts(params);
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load alerts');
    }
  };

  useEffect(() => { load(); }, []);

  const changeStatus = async (id: number, st: string) => {
    try {
      await api.ackAlert(id, st);
      await load(statusFilter);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed');
    }
  };

  if (error && !items) return <ErrorState message={error} onRetry={() => load()} />;
  if (!items) return <Spinner label="Loading alerts…" />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Alerts</h1>
          <p className="text-sm text-slate-500">{total} alerts</p>
        </div>
        <select
          className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); load(e.target.value); }}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      {items.length === 0 ? (
        <EmptyState title="No alerts" hint="Smart alerts (motion, zone, crowd, plates, unknown face) appear here." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {items.map((a) => (
            <div key={a.id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <Badge tone={severityTone[a.severity] || 'slate'}>{a.severity}</Badge>
                    <Badge tone={statusTone[a.status] || 'slate'}>{a.status}</Badge>
                  </div>
                  <h3 className="mt-2 font-medium">{a.title}</h3>
                  <p className="mt-0.5 text-sm text-slate-400">{a.message}</p>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                <span>Camera #{a.camera_id ?? '—'} · {new Date(a.created_at).toLocaleString()}</span>
                {a.status === 'active' && (
                  <div className="flex gap-2">
                    <button onClick={() => changeStatus(a.id, 'acknowledged')} className="rounded border border-slate-700 px-2 py-1 hover:bg-slate-800">
                      Acknowledge
                    </button>
                    <button onClick={() => changeStatus(a.id, 'resolved')} className="rounded border border-emerald-700 px-2 py-1 text-emerald-300 hover:bg-emerald-950">
                      Resolve
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
