import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useLiveUpdates } from '../hooks/useLiveUpdates';
import { Badge, ErrorState, Spinner, StatCard } from '../components/ui';
import type { Health } from '../types';

export default function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof api.summary>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { connected, frames } = useLiveUpdates();

  const load = async () => {
    setError(null);
    try {
      const [h, s] = await Promise.all([api.health(), api.summary()]);
      setHealth(h);
      setSummary(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard');
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  if (error && !summary) return <ErrorState message={`Cannot reach backend: ${error}`} onRetry={load} />;
  if (!summary) return <Spinner label="Loading dashboard…" />;

  const liveCounts = Object.values(frames).reduce(
    (acc, f) => ({ people: acc.people + f.people, vehicles: acc.vehicles + f.vehicles }),
    { people: 0, vehicles: 0 },
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-slate-500">
            {health?.app} v{health?.version} · DB {health?.database} · Redis {health?.redis}
            {health?.models_loaded?.length ? ` · Model ${health.models_loaded[0]}` : ' · Model not loaded'}
          </p>
        </div>
        <Badge tone={connected ? 'green' : 'red'}>{connected ? '● Live stream' : '○ No live connection'}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Cameras" value={summary.total_cameras} sub={`${summary.active_cameras} active`} />
        <StatCard label="Events (24h)" value={summary.events_24h} tone="amber" />
        <StatCard label="Active Alerts" value={summary.alerts_active} tone="red" />
        <StatCard label="People (live)" value={liveCounts.people} sub={`${summary.people_detected_24h} in 24h`} />
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Vehicles (live)" value={liveCounts.vehicles} sub={`${summary.vehicles_detected_24h} in 24h`} />
        <StatCard label="Plates (24h)" value={summary.plates_detected_24h} tone="blue" />
        <StatCard label="Detections (24h)" value={summary.per_camera.reduce((a, c) => a + c.detections_24h, 0)} tone="slate" />
        <StatCard label="System" value={health?.database === 'ok' ? 'Operational' : 'Degraded'} tone={health?.database === 'ok' ? 'green' : 'red'} />
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="mb-4 text-lg font-medium">Per-Camera Activity (24h)</h2>
        {summary.per_camera.length === 0 ? (
          <p className="text-sm text-slate-500">No cameras configured yet. Add one in Cameras.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-slate-500">
                  <th className="pb-2 pr-4">Camera</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Events</th>
                  <th className="pb-2 pr-4">Alerts</th>
                  <th className="pb-2 pr-4">People</th>
                  <th className="pb-2 pr-4">Vehicles</th>
                </tr>
              </thead>
              <tbody>
                {summary.per_camera.map((c) => (
                  <tr key={c.camera_id} className="border-b border-slate-800/50">
                    <td className="py-2 pr-4 font-medium">{c.camera_name}</td>
                    <td className="py-2 pr-4">
                      <Badge tone={c.camera_id && frames[c.camera_id] ? 'green' : 'slate'}>
                        {c.camera_id && frames[c.camera_id] ? 'live' : '—'}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4">{c.events_24h}</td>
                    <td className="py-2 pr-4">{c.alerts_24h}</td>
                    <td className="py-2 pr-4">{c.people_count}</td>
                    <td className="py-2 pr-4">{c.vehicle_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
