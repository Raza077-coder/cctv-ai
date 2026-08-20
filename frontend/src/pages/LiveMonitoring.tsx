import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useLiveUpdates } from '../hooks/useLiveUpdates';
import { Badge, ErrorState, Spinner } from '../components/ui';
import type { Camera } from '../types';

export default function LiveMonitoring() {
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { connected, frames } = useLiveUpdates();

  useEffect(() => {
    api.listCameras().then(setCameras).catch((e) => setError(e instanceof Error ? e.message : 'load failed'));
  }, []);

  if (error && !cameras) return <ErrorState message={error} />;
  if (!cameras) return <Spinner label="Loading cameras…" />;

  const active = cameras.filter((c) => c.status === 'running');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Live Monitoring</h1>
          <p className="text-sm text-slate-500">
            Real-time detection stats streamed over WebSocket ·{' '}
            {connected ? 'connected' : 'disconnected — retrying…'}
          </p>
        </div>
        <Badge tone={connected ? 'green' : 'red'}>{active.length} running</Badge>
      </div>

      {active.length === 0 ? (
        <div className="rounded-lg border border-slate-800 p-12 text-center">
          <p className="text-slate-400">No cameras currently running detection.</p>
          <p className="mt-1 text-sm text-slate-500">Start detection from the Cameras page — live stats will appear here.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {active.map((cam) => {
            const live = frames[cam.id];
            return (
              <div key={cam.id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">{cam.name}</h3>
                  <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" /> LIVE
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                  <div className="rounded-lg bg-slate-950 p-3">
                    <p className="text-2xl font-semibold text-blue-300">{live?.people ?? 0}</p>
                    <p className="text-xs text-slate-500">People</p>
                  </div>
                  <div className="rounded-lg bg-slate-950 p-3">
                    <p className="text-2xl font-semibold text-amber-300">{live?.vehicles ?? 0}</p>
                    <p className="text-xs text-slate-500">Vehicles</p>
                  </div>
                  <div className="rounded-lg bg-slate-950 p-3">
                    <p className="text-2xl font-semibold text-slate-300">{live?.fps ?? 0}</p>
                    <p className="text-xs text-slate-500">FPS</p>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                  <span>Motion: {live?.motion ? 'detected' : 'none'}</span>
                  <span>Crowd: {live?.crowd_level ?? '—'}</span>
                </div>
                {live && live.alerts.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {live.alerts.slice(0, 4).map((a, i) => (
                      <div key={i} className="rounded bg-red-950/40 px-2 py-1 text-xs text-red-300">
                        {a.message}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
