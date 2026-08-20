import { useEffect, useRef, useState } from 'react';
import type { LiveFrameStats } from '../types';

const WS_BASE = import.meta.env.VITE_WS_BASE || (() => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws`;
})();

/**
 * Subscribe to live WebSocket updates from the backend.
 * Returns the latest frame stats (keyed by camera) and connection state.
 */
export function useLiveUpdates() {
  const [connected, setConnected] = useState(false);
  const [frames, setFrames] = useState<Record<number, LiveFrameStats>>({});
  const [lastMessage, setLastMessage] = useState<{ kind: string; data: unknown; ts: string } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let closed = false;

    const connect = () => {
      if (closed) return;
      const ws = new WebSocket(WS_BASE);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!closed) retryTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.kind === 'pong') return;
          setLastMessage(msg);
          if (msg.kind === 'frame_stats' && msg.data?.camera_id != null) {
            setFrames((prev) => ({ ...prev, [msg.data.camera_id]: msg.data }));
          }
        } catch {
          /* ignore malformed */
        }
      };

      // keepalive
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 20000);
      ws.addEventListener('close', () => clearInterval(ping));
    };

    connect();
    return () => {
      closed = true;
      if (retryTimer) clearTimeout(retryTimer);
      wsRef.current?.close();
    };
  }, []);

  return { connected, frames, lastMessage };
}
