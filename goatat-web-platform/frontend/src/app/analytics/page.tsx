'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { api, type AnalyticsData } from '@/lib/api';
import { TrendingUp, Activity, Clock, Zap } from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';

// Demo data for empty states
const DEMO_DAILY = Array.from({ length: 30 }, (_, i) => {
  const d = new Date(); d.setDate(d.getDate() - (29 - i));
  return {
    date: d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }),
    authentic: Math.floor(Math.random() * 12),
    synthetic: Math.floor(Math.random() * 4),
    inconclusive: Math.floor(Math.random() * 2),
  };
});

const PIE_COLORS = ['#10B981', '#F43F5E', '#F59E0B'];

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.analytics(days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [days]);

  const isDemo = data?.is_demo_data !== false;
  const chartData = (data?.daily_counts.length ?? 0) > 0 ? data!.daily_counts : DEMO_DAILY;
  const distribution = data?.verdict_distribution ?? { authentic: 0, synthetic: 0, inconclusive: 0 };
  const totalDist = distribution.authentic + distribution.synthetic + distribution.inconclusive;

  const pieData = [
    { name: 'Authentiques', value: totalDist > 0 ? distribution.authentic : 65 },
    { name: 'Synthétiques', value: totalDist > 0 ? distribution.synthetic : 28 },
    { name: 'Indéterminés', value: totalDist > 0 ? distribution.inconclusive : 7 },
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-60 overflow-hidden">
        <TopBar title="Analytique" />
        <main className="flex-1 overflow-y-auto p-6" style={{ background: '#070D1A' }}>

          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Analytique détaillée</h2>
              <p className="text-slate-400 text-sm">Statistiques d&apos;analyse sur la période sélectionnée</p>
            </div>
            <div className="flex items-center gap-3">
              {isDemo && <span className="demo-badge"><Zap size={9} />Données démo</span>}
              <select
                className="form-input w-40 text-sm"
                value={days}
                onChange={e => setDays(Number(e.target.value))}
              >
                <option value={7}>7 derniers jours</option>
                <option value={30}>30 derniers jours</option>
                <option value={90}>90 derniers jours</option>
              </select>
            </div>
          </div>

          {/* KPI row */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[
              { label: 'Total analyses', value: totalDist || 93, icon: Activity, color: '#2563EB' },
              { label: 'Authentiques', value: distribution.authentic || 65, icon: TrendingUp, color: '#10B981' },
              { label: 'Synthétiques', value: distribution.synthetic || 28, icon: Activity, color: '#F43F5E' },
              { label: 'Latence moy.', value: `${(data?.inference_latency_avg_ms || 842).toFixed(0)} ms`, icon: Clock, color: '#7C3AED' },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="glass-card p-5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-400">{label}</span>
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${color}15` }}>
                    <Icon size={14} style={{ color }} />
                  </div>
                </div>
                <div className="text-2xl font-bold text-white">{value}</div>
              </div>
            ))}
          </div>

          {/* Charts grid */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            {/* Activity area chart */}
            <div className="col-span-2 glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp size={15} className="text-blue-400" />
                <h3 className="text-sm font-semibold text-white">Volume d&apos;analyses par jour</h3>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F43F5E" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#F43F5E" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,130,188,0.08)" />
                  <XAxis dataKey="date" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={false} tickLine={false} interval={4} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#0D172A', border: '1px solid rgba(99,130,188,0.2)', borderRadius: 8 }} />
                  <Area type="monotone" dataKey="authentic" name="Authentiques" stroke="#10B981" fill="url(#ag)" strokeWidth={2} />
                  <Area type="monotone" dataKey="synthetic" name="Synthétiques" stroke="#F43F5E" fill="url(#sg)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Pie */}
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Activity size={15} className="text-purple-400" />
                <h3 className="text-sm font-semibold text-white">Distribution des verdicts</h3>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="45%" innerRadius={50} outerRadius={80} dataKey="value" paddingAngle={3}>
                    {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#0D172A', border: '1px solid rgba(99,130,188,0.2)', borderRadius: 8 }} />
                  <Legend formatter={(v) => <span style={{ color: '#94A3B8', fontSize: 11 }}>{v}</span>} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Bar chart */}
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Activity size={15} className="text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">Activité hebdomadaire détaillée</h3>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={chartData.slice(-14)}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,130,188,0.08)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#0D172A', border: '1px solid rgba(99,130,188,0.2)', borderRadius: 8 }} />
                <Bar dataKey="authentic" name="Authentiques" fill="#10B981" radius={[3,3,0,0]} />
                <Bar dataKey="synthetic" name="Synthétiques" fill="#F43F5E" radius={[3,3,0,0]} />
                <Bar dataKey="inconclusive" name="Indéterminés" fill="#F59E0B" radius={[3,3,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Notice */}
          <div className="mt-4 p-4 rounded-lg"
            style={{ background: 'rgba(37,99,235,0.05)', border: '1px solid rgba(37,99,235,0.12)' }}>
            <p className="text-xs text-slate-500">
              <strong className="text-slate-400">Note : </strong>
              Les métriques de performance du modèle (précision, F1, taux de fausses acceptations) ne sont affichées
              que lorsque des données d&apos;évaluation validées sont disponibles. {isDemo && 'Les données actuelles sont simulées à des fins de démonstration.'}
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
