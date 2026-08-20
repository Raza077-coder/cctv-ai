import { useEffect, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { api } from '../services/api';
import { ErrorState, Spinner } from '../components/ui';

const PIE_COLORS = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#14b8a6'];

export default function Analytics() {
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof api.summary>> | null>(null);
  const [classes, setClasses] = useState<{ class: string; count: number }[]>([]);
  const [plates, setPlates] = useState<Awaited<ReturnType<typeof api.plates>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const [s, c, p] = await Promise.all([api.summary(), api.classBreakdown(), api.plates({ limit: 20 })]);
      setSummary(s);
      setClasses(c.items);
      setPlates(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load analytics');
    }
  };

  useEffect(() => { load(); }, []);

  if (error && !summary) return <ErrorState message={error} onRetry={load} />;
  if (!summary) return <Spinner label="Loading analytics…" />;

  const cameraBarData = summary.per_camera.map((c) => ({
    name: c.camera_name,
    Events: c.events_24h,
    Alerts: c.alerts_24h,
  }));

  const pieData = classes.length
    ? classes.slice(0, 6).map((c) => ({ name: c.class, value: c.count }))
    : [{ name: 'No detections yet', value: 1 }];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <p className="text-sm text-slate-500">Detection statistics over the last 24 hours.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="mb-4 text-lg font-medium">Events per Camera (24h)</h2>
          {cameraBarData.length === 0 ? (
            <p className="text-sm text-slate-500">No camera data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={cameraBarData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }} />
                <Legend />
                <Bar dataKey="Events" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Alerts" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="mb-4 text-lg font-medium">Detected Classes (24h)</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                {pieData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="mb-3 text-lg font-medium">Recent License Plates</h2>
          {!plates || plates.items.length === 0 ? (
            <p className="text-sm text-slate-500">No plates recognized yet (requires Tesseract OCR).</p>
          ) : (
            <div className="space-y-2">
              {plates.items.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded bg-slate-950 px-3 py-2 text-sm">
                  <span className="font-mono font-semibold text-blue-300">{p.normalized_plate || p.plate_number}</span>
                  <span className="text-xs text-slate-500">
                    cam #{p.camera_id ?? '—'} · {Math.round(p.confidence * 100)}% ·{' '}
                    {new Date(p.created_at).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="mb-3 text-lg font-medium">System Summary</h2>
          <dl className="space-y-2 text-sm">
            {[
              ['Cameras', `${summary.active_cameras}/${summary.total_cameras} active`],
              ['Events (24h)', summary.events_24h],
              ['Active alerts', summary.alerts_active],
              ['People detected', summary.people_detected_24h],
              ['Vehicles detected', summary.vehicles_detected_24h],
              ['Plates detected', summary.plates_detected_24h],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex justify-between border-b border-slate-800/60 pb-2">
                <dt className="text-slate-500">{k}</dt>
                <dd className="font-medium">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
}
