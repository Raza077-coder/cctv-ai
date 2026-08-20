import { NavLink, Outlet } from 'react-router-dom';
import { useLiveUpdates } from '../hooks/useLiveUpdates';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/cameras', label: 'Cameras' },
  { to: '/monitor', label: 'Live Monitoring' },
  { to: '/events', label: 'Events' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/settings', label: 'Settings' },
];

export default function Layout() {
  const { connected } = useLiveUpdates();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <NavLink to="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 font-bold text-white">
              CA
            </span>
            <span className="font-semibold tracking-tight">CCTV AI</span>
          </NavLink>
          <nav className="hidden items-center gap-1 md:flex">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm transition ${
                    isActive
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs ${
                connected ? 'bg-emerald-900/50 text-emerald-300' : 'bg-slate-800 text-slate-400'
              }`}
              title="Live WebSocket connection"
            >
              <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              {connected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>
        {/* Mobile nav */}
        <nav className="flex gap-1 overflow-x-auto border-t border-slate-800/60 px-3 py-1.5 md:hidden">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-md px-3 py-1 text-xs ${
                  isActive ? 'bg-slate-800 text-white' : 'text-slate-400'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-600">
        CCTV AI — AI-Powered Video Surveillance & Analytics
      </footer>
    </div>
  );
}
