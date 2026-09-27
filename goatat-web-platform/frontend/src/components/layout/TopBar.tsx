'use client';

import { Bell, User, Wifi, WifiOff } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export function TopBar({ title }: { title: string }) {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    api.health()
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
  }, []);

  return (
    <header
      className="flex items-center justify-between px-6 py-4 border-b"
      style={{ borderColor: 'rgba(99,130,188,0.12)', background: 'rgba(11,20,38,0.8)', backdropFilter: 'blur(10px)' }}
    >
      <h1 className="text-lg font-semibold text-white">{title}</h1>

      <div className="flex items-center gap-4">
        {/* Backend status */}
        <div className="flex items-center gap-1.5">
          {online === null ? (
            <div className="w-2 h-2 rounded-full bg-slate-400 animate-pulse" />
          ) : online ? (
            <><Wifi size={14} className="text-emerald-400" /><span className="text-xs text-emerald-400">Connecté</span></>
          ) : (
            <><WifiOff size={14} className="text-rose-400" /><span className="text-xs text-rose-400">Hors ligne</span></>
          )}
        </div>

        <div className="w-px h-5 bg-slate-700" />

        <button className="relative p-2 rounded-lg hover:bg-slate-800 transition-colors">
          <Bell size={16} className="text-slate-400" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-rose-500" />
        </button>

        <div className="flex items-center gap-2 pl-2">
          <div className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #2563EB, #7C3AED)' }}>
            <User size={14} className="text-white" />
          </div>
          <div>
            <div className="text-xs font-medium text-white">Utilisateur local</div>
            <div className="text-xs text-slate-500">Mode démo</div>
          </div>
        </div>
      </div>
    </header>
  );
}
