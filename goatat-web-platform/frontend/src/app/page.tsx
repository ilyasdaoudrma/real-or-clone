'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { api, type DashboardStats, type AnalysisListItem } from '@/lib/api';
import { formatDate, formatDuration, verdictLabel } from '@/lib/utils';
import {
  Activity, AlertTriangle, CheckCircle2, Mic, Plus, RefreshCw,
  ShieldAlert, TrendingUp, XCircle, Zap
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, ResponsiveContainer, Legend
} from 'recharts';

const COLORS = { authentic: '#10B981', synthetic: '#F43F5E', inconclusive: '#F59E0B' };

// Demo chart data for empty states
const DEMO_CHART = Array.from({ length: 14 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (13 - i));
  return {
    date: d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }),
    authentic: Math.floor(Math.random() * 8),
    synthetic: Math.floor(Math.random() * 3),
  };
});

function KpiCard({
  title, value, icon: Icon, color, subtitle
}: {
  title: string; value: string | number; icon: React.ElementType; color: string; subtitle?: string;
}) {
  return (
    <div className="glass-card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-400 font-medium">{title}</span>
        <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${color}15` }}>
          <Icon size={18} style={{ color }} />
        </div>
      </div>
      <div>
        <div className="text-3xl font-bold text-white">{value}</div>
        {subtitle && <div className="text-xs text-slate-500 mt-1">{subtitle}</div>}
      </div>
    </div>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const cls = `badge verdict-${verdict}`;
  return <span className={cls}>{verdictLabel(verdict)}</span>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.dashboardStats();
      setStats(data);
    } catch (e: unknown) {
      setError((e as Error).message || 'Erreur de connexion au backend');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const total = stats?.total_analyses ?? 0;
  const authentic = stats?.authentic_count ?? 0;
  const synthetic = stats?.synthetic_count ?? 0;
  const inconclusive = stats?.inconclusive_count ?? 0;

  const pieData = [
    { name: 'Authentiques', value: authentic, color: COLORS.authentic },
    { name: 'Synthétiques', value: synthetic, color: COLORS.synthetic },
    { name: 'Indéterminés', value: inconclusive, color: COLORS.inconclusive },
  ].filter(d => d.value > 0);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-60 overflow-hidden">
        <TopBar title="Tableau de bord" />
        <main className="flex-1 overflow-y-auto p-6" style={{ background: '#070D1A' }}>

          {error && (
            <div className="mb-6 p-4 rounded-lg flex items-center gap-3"
              style={{ background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.25)' }}>
              <AlertTriangle size={16} className="text-rose-400" />
              <div>
                <div className="text-sm font-medium text-rose-300">Backend non disponible</div>
                <div className="text-xs text-rose-400/70">{error} — Démarrez le backend: <code>python run.py</code></div>
              </div>
              <button onClick={load} className="ml-auto btn-ghost text-xs py-1.5 px-3">
                <RefreshCw size={12} /> Réessayer
              </button>
            </div>
          )}

          {/* Hero header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">
                Bienvenue sur <span className="gradient-text">GOATAT</span>
              </h2>
              <p className="text-slate-400 text-sm">Plateforme de détection de voix synthétiques et d&apos;authentification vocale</p>
            </div>
            <div className="flex gap-3">
              <button onClick={load} className="btn-ghost" disabled={loading}>
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                Actualiser
              </button>
              <Link href="/verification" className="btn-primary">
                <Plus size={16} /> Nouvelle analyse
              </Link>
            </div>
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <KpiCard
              title="Total des analyses"
              value={loading ? '—' : total}
              icon={Activity}
              color="#2563EB"
              subtitle={total === 0 ? 'Aucune analyse encore' : undefined}
            />
            <KpiCard
              title="Voix authentiques"
              value={loading ? '—' : authentic}
              icon={CheckCircle2}
              color="#10B981"
              subtitle={total > 0 ? `${Math.round((authentic / total) * 100)}% du total` : undefined}
            />
            <KpiCard
              title="Voix synthétiques"
              value={loading ? '—' : synthetic}
              icon={XCircle}
              color="#F43F5E"
              subtitle={total > 0 ? `${Math.round((synthetic / total) * 100)}% du total` : undefined}
            />
            <KpiCard
              title="Alertes actives"
              value={loading ? '—' : stats?.suspicious_alerts ?? 0}
              icon={ShieldAlert}
              color="#7C3AED"
              subtitle="Alertes non acquittées"
            />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            {/* Activity chart */}
            <div className="col-span-2 glass-card p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <TrendingUp size={16} className="text-blue-400" />
                  <h3 className="text-sm font-semibold text-white">Activité d&apos;analyse</h3>
                </div>
                <span className="demo-badge"><Zap size={9} /> Données démo</span>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={DEMO_CHART}>
                  <defs>
                    <linearGradient id="authGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="synthGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F43F5E" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#F43F5E" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,130,188,0.1)" />
                  <XAxis dataKey="date" tick={{ fill: '#64748B', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#0D172A', border: '1px solid rgba(99,130,188,0.2)', borderRadius: 8, color: '#E2E8F0' }}
                  />
                  <Area type="monotone" dataKey="authentic" name="Authentiques" stroke="#10B981" fill="url(#authGrad)" strokeWidth={2} />
                  <Area type="monotone" dataKey="synthetic" name="Synthétiques" stroke="#F43F5E" fill="url(#synthGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Distribution pie */}
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Activity size={16} className="text-purple-400" />
                <h3 className="text-sm font-semibold text-white">Distribution des verdicts</h3>
              </div>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} dataKey="value" paddingAngle={3}>
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: '#0D172A', border: '1px solid rgba(99,130,188,0.2)', borderRadius: 8 }} />
                    <Legend formatter={(value) => <span style={{ color: '#94A3B8', fontSize: 12 }}>{value}</span>} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex flex-col items-center justify-center h-44 text-slate-500">
                  <Activity size={32} className="mb-2 opacity-30" />
                  <p className="text-sm">Aucune analyse</p>
                  <p className="text-xs text-slate-600 mt-1">Commencez une analyse vocale</p>
                </div>
              )}
            </div>
          </div>

          {/* Recent analyses */}
          <div className="glass-card">
            <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: 'rgba(99,130,188,0.12)' }}>
              <div className="flex items-center gap-2">
                <Mic size={15} className="text-blue-400" />
                <h3 className="text-sm font-semibold text-white">Analyses récentes</h3>
              </div>
              <Link href="/history" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
                Voir tout →
              </Link>
            </div>
            {loading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3].map(i => <div key={i} className="skeleton h-10" />)}
              </div>
            ) : stats?.recent_analyses.length === 0 ? (
              <div className="flex flex-col items-center py-16 text-slate-500">
                <Mic size={40} className="mb-3 opacity-20" />
                <p className="font-medium text-slate-400">Aucune analyse pour l&apos;instant</p>
                <p className="text-sm mt-1 text-slate-600">Importez un fichier audio ou enregistrez votre voix</p>
                <Link href="/verification" className="btn-primary mt-4 text-sm">
                  <Plus size={14} /> Commencer une analyse
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Fichier</th>
                      <th>Verdict</th>
                      <th>Confiance</th>
                      <th>Durée</th>
                      <th>Date</th>
                      <th>Mode</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats?.recent_analyses.map((a: AnalysisListItem) => (
                      <tr key={a.id}>
                        <td className="font-medium text-slate-200 max-w-xs truncate">{a.original_filename}</td>
                        <td><VerdictBadge verdict={a.verdict} /></td>
                        <td className="text-slate-300">{(a.confidence * 100).toFixed(1)}%</td>
                        <td className="text-slate-400">{formatDuration(a.audio_duration_seconds)}</td>
                        <td className="text-slate-400 text-xs">{formatDate(a.created_at)}</td>
                        <td>
                          {a.is_demo && <span className="demo-badge"><Zap size={9} />Démo</span>}
                        </td>
                        <td>
                          <Link href={`/analysis/${a.id}`} className="text-xs text-blue-400 hover:text-blue-300">
                            Détails →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Footer disclaimer */}
          <div className="mt-6 p-4 rounded-lg flex items-start gap-3"
            style={{ background: 'rgba(37,99,235,0.05)', border: '1px solid rgba(37,99,235,0.15)' }}>
            <AlertTriangle size={14} className="text-blue-400 mt-0.5 shrink-0" />
            <p className="text-xs text-slate-500">
              <strong className="text-slate-400">Avertissement : </strong>
              Les résultats de ce système sont générés par un modèle de machine learning et constituent une aide à la décision,
              pas une preuve juridique. En mode démonstration, les prédictions sont simulées et ne reflètent pas les performances réelles du modèle.
            </p>
          </div>

        </main>
      </div>
    </div>
  );
}
