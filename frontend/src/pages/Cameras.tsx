import { FormEvent, useEffect, useState } from 'react';
import { api } from '../services/api';
import { Badge, ErrorState, Spinner } from '../components/ui';
import type { Camera } from '../types';

const EMPTY = {
  name: '',
  source_type: 'rtsp' as Camera['source_type'],
  source_url: '',
  location: '',
  enabled: true,
};

export default function Cameras() {
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setError(null);
    try {
      setCameras(await api.listCameras());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load cameras');
    }
  };

  useEffect(() => { load(); }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.source_url) return;
    setBusy(true);
    setError(null);
    try {
      await api.createCamera(form);
      setForm(EMPTY);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create camera');
    } finally {
      setBusy(false);
    }
  };

  const toggleDetection = async (cam: Camera) => {
    try {
      if (cam.status === 'running') {
        await api.stopDetection(cam.id);
      } else {
        await api.startDetection(cam.id);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Detection control failed');
    }
  };

  const remove = async (cam: Camera) => {
    if (!window.confirm(`Delete camera "${cam.name}"?`)) return;
    try {
      await api.deleteCamera(cam.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  if (error && !cameras) return <ErrorState message={error} onRetry={load} />;
  if (!cameras) return <Spinner label="Loading cameras…" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Cameras</h1>
        <p className="text-sm text-slate-500">Add webcam, video file, or RTSP sources.</p>
      </div>

      {error && <ErrorState message={error} />}

      <form onSubmit={submit} className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="mb-3 text-lg font-medium">Add Camera</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <input
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            placeholder="Name (e.g. Parking Lot)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <select
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            value={form.source_type}
            onChange={(e) => setForm({ ...form, source_type: e.target.value as Camera['source_type'] })}
          >
            <option value="rtsp">RTSP stream</option>
            <option value="file">Video file</option>
            <option value="webcam">Webcam</option>
          </select>
          <input
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm md:col-span-2"
            placeholder={form.source_type === 'webcam' ? 'Camera index (0 = default webcam)' : 'Source URL (rtsp://… or /path/to/video.mp4)'}
            value={form.source_url}
            onChange={(e) => setForm({ ...form, source_url: e.target.value })}
            required
          />
          <input
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            placeholder="Location (optional)"
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
          />
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
            />
            Enabled
          </label>
        </div>
        <button
          type="submit"
          disabled={busy}
          className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
        >
          {busy ? 'Adding…' : 'Add Camera'}
        </button>
      </form>

      <div className="grid gap-4 md:grid-cols-2">
        {cameras.length === 0 && (
          <div className="md:col-span-2 rounded-lg border border-slate-800 p-8 text-center text-sm text-slate-500">
            No cameras yet. Add one above to begin.
          </div>
        )}
        {cameras.map((cam) => (
          <div key={cam.id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-medium">{cam.name}</h3>
                <p className="mt-0.5 text-xs text-slate-500">{cam.source_type} · {cam.location || 'no location'}</p>
              </div>
              <Badge tone={cam.status === 'running' ? 'green' : cam.status === 'error' ? 'red' : 'slate'}>
                {cam.status}
              </Badge>
            </div>
            <p className="mt-3 truncate rounded bg-slate-950 px-2 py-1 font-mono text-xs text-slate-500">
              {cam.source_url}
            </p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => toggleDetection(cam)}
                className={`rounded-md px-3 py-1.5 text-sm ${
                  cam.status === 'running'
                    ? 'bg-red-700 text-white hover:bg-red-600'
                    : 'bg-emerald-700 text-white hover:bg-emerald-600'
                }`}
              >
                {cam.status === 'running' ? 'Stop' : 'Start Detection'}
              </button>
              <button
                onClick={() => remove(cam)}
                className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-800"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
