import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Badge, EmptyState, ErrorState, Spinner } from '../components/ui';
import type { EventItem } from '../types';

const severityTone: Record<string, string> = {
  critical: 'red', high: 'red', medium: 'amber', low: 'amber', info: 'slate',
};

export default function Events() {
  const [items, setItems] = useState<EventItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [typeFilter, setTypeFilter] = useState('');
  const [error, setError] = useState<string | null>(null);

  const load = async (type?: string) => {
    setError(null);
    try {
      const params: Record<string, string | number> = { limit: 100 };
      if (type) params.event_type = type;
      const res = await api.listEvents(params);
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load events');
    }
  };

  useEffect(() => { load(); }, []);

  if (error && !items) return <ErrorState message={error} onRetry={() => load()} />;
  if (!items) return <Spinner label="Loading events…" />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Events</h1>
          <p className="text-sm text-slate-500">{total} total events</p>
        </div>
        <input
          className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm"
          placeholder="Filter by type…"
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); load(e.target.value); }}
        />
      </div>

      {items.length === 0 ? (
        <EmptyState title="No events yet" hint="Events appear here once detection is running." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/80 text-left text-slate-500">
              <tr>
                <th className="px-4 py-2.5">Time</th>
                <th className="px-4 py-2.5">Type</th>
                <th className="px-4 py-2.5">Camera</th>
                <th className="px-4 py-2.5">Severity</th>
                <th className="px-4 py-2.5">Message</th>
                <th className="px-4 py-2.5">Conf.</th>
              </tr>
            </thead>
            <tbody>
              {items.map((ev) => (
                <tr key={ev.id} className="border-t border-slate-800/60">
                  <td className="whitespace-nowrap px-4 py-2 text-xs text-slate-500">
                    {new Date(ev.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-blue-300">{ev.event_type}</td>
                  <td className="px-4 py-2 text-xs">#{ev.camera_id ?? '—'}</td>
                  <td className="px-4 py-2"><Badge tone={severityTone[ev.severity] || 'slate'}>{ev.severity}</Badge></td>
                  <td className="px-4 py-2 text-slate-300">{ev.message}</td>
                  <td className="px-4 py-2 text-xs text-slate-500">{ev.confidence ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
