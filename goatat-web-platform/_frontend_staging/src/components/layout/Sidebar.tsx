'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home, Mic, History, Users, BarChart3, Bell, Settings, ShieldCheck, Zap
} from 'lucide-react';

const navItems = [
  { href: '/', label: 'Accueil', icon: Home },
  { href: '/verification', label: 'Vérification vocale', icon: Mic },
  { href: '/history', label: 'Historique', icon: History },
  { href: '/profiles', label: 'Profils vocaux', icon: Users },
  { href: '/analytics', label: 'Analytique', icon: BarChart3 },
  { href: '/alerts', label: 'Alertes', icon: Bell },
  { href: '/settings', label: 'Paramètres', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-60 flex flex-col z-30"
      style={{ background: '#0B1426', borderRight: '1px solid rgba(99,130,188,0.12)' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b" style={{ borderColor: 'rgba(99,130,188,0.12)' }}>
        <div className="relative">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #2563EB, #7C3AED)' }}>
            <ShieldCheck size={20} className="text-white" />
          </div>
          <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2"
            style={{ borderColor: '#0B1426' }} />
        </div>
        <div>
          <div className="text-sm font-bold text-white tracking-wide">GOATAT</div>
          <div className="text-xs text-slate-400 font-medium">Real or Clone</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`nav-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={16} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t" style={{ borderColor: 'rgba(99,130,188,0.12)' }}>
        <div className="flex items-center gap-2 px-2 py-2 rounded-lg"
          style={{ background: 'rgba(37,99,235,0.08)' }}>
          <Zap size={12} className="text-blue-400" />
          <span className="text-xs text-blue-300 font-medium">Mode Démonstration</span>
        </div>
        <p className="text-xs text-slate-500 mt-2 px-2">
          Authenticate the voice.<br />Protect trust.
        </p>
      </div>
    </aside>
  );
}
