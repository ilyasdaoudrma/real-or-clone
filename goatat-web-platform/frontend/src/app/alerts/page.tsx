'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { api, type AlertItem } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { AlertTriangle, ShieldAlert, CheckCircle2, XCircle, Info, Loader2, Bell } from 'lucide-react';
import Link from 'next/link';

// Mock some alerts if API returns empty for demo purposes
const MOCK_ALERTS: AlertItem[] = [
  {
    id: 'alt-1', analysis_id: 'ana-abc-123', severity: 'high',
    title: 'Clonage vocal détecté (Probabilité: 98%)',
    description: 'Une analyse a révélé de fortes caractéristiques de synthèse vocale.',
    confidence: 0.98, acknowledged: false, dismissed: false,
    created_at: new Date().toISOString(), acknowledged_at: null,
  },
  {
    id: 'alt-2', analysis_id: 'ana-def-456', severity: 'medium',
    title: 'Analyse indéterminée (Bruit de fond)',
    description: 'Le modèle n\'a pas pu déterminer avec certitude l\'authenticité en raison d\'une qualité audio médiocre.',
    confidence: 0.55, acknowledged: true, dismissed: false,
    created_at: new Date(Date.now() - 86400000).toISOString(), acknowledged_at: new Date().toISOString(),
  }
];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'unacknowledged'>('all');

  const load = async () => {
    setLoading(true);
    try {
      let data = await api.listAlerts(filter === 'unacknowledged' ? { acknowledged: false } : undefined);
      // Fallback to mock data if API returns empty array and no real data exists
      if (data.length === 0) {
        data = filter === 'unacknowledged' ? MOCK_ALERTS.filter(a => !a.acknowledged) : MOCK_ALERTS;
      }
      setAlerts(data);
    } catch (e) {
      console.error('Erreur lors du chargement des alertes', e);
      setAlerts(MOCK_ALERTS); // Fallback on error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  const handleAcknowledge = async (id: string) => {
    try {
      // Optomistic UI update
      setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true, acknowledged_at: new Date().toISOString() } : a));
      await api.acknowledgeAlert(id).catch(() => {});
    } catch (e) {
      console.error(e);
    }
  };

  const handleDismiss = async (id: string) => {
    try {
      setAlerts(prev => prev.filter(a => a.id !== id));
      await api.dismissAlert(id).catch(() => {});
    } catch (e) {
      console.error(e);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high': return <ShieldAlert size={20} className="text-rose-500" />;
      case 'medium': return <AlertTriangle size={20} className="text-amber-500" />;
      case 'low': return <Info size={20} className="text-blue-500" />;
      default: return <Bell size={20} className="text-slate-400" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-rose-500/10 border-rose-500/20';
      case 'medium': return 'bg-amber-500/10 border-amber-500/20';
      case 'low': return 'bg-blue-500/10 border-blue-500/20';
      default: return 'bg-slate-500/10 border-slate-500/20';
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-60 overflow-hidden">
        <TopBar title="Alertes de sécurité" />
        <main className="flex-1 overflow-y-auto p-6" style={{ background: '#070D1A' }}>

          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Centre d&apos;alertes</h2>
              <p className="text-slate-400 text-sm">Surveillez les détections de fraude et les activités suspectes</p>
            </div>
            <div className="flex gap-2 p-1 rounded-lg" style={{ background: '#0D172A', border: '1px solid rgba(99,130,188,0.15)' }}>
              <button
                onClick={() => setFilter('unacknowledged')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${filter === 'unacknowledged' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
              >
                Non traitées
              </button>
              <button
                onClick={() => setFilter('all')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${filter === 'all' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
              >
                Toutes
              </button>
            </div>
          </div>

          <div className="space-y-4 max-w-4xl">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 size={24} className="animate-spin text-blue-400" />
              </div>
            ) : alerts.length === 0 ? (
              <div className="glass-card py-16 flex flex-col items-center justify-center text-slate-500">
                <CheckCircle2 size={48} className="mb-4 text-emerald-500/50" />
                <h3 className="text-lg font-medium text-slate-300">Aucune alerte</h3>
                <p className="text-sm mt-1">Votre système est sécurisé.</p>
              </div>
            ) : (
              alerts.map(alert => (
                <div key={alert.id} className={`p-5 rounded-xl border flex gap-4 transition-all ${getSeverityColor(alert.severity)} ${alert.acknowledged ? 'opacity-60' : 'opacity-100'}`}>
                  <div className="mt-1">
                    {getSeverityIcon(alert.severity)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-white font-semibold text-lg">{alert.title}</h3>
                        <p className="text-sm text-slate-400 mt-1">{alert.description}</p>
                      </div>
                      <div className="text-xs text-slate-500">{formatDate(alert.created_at)}</div>
                    </div>
                    
                    <div className="mt-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {alert.analysis_id && (
                          <Link href={`/analysis/${alert.analysis_id}`} className="btn-ghost py-1 px-3 text-xs">
                            Voir l&apos;analyse
                          </Link>
                        )}
                        {alert.confidence !== null && (
                          <span className="text-xs font-medium text-slate-400">
                            Confiance : {(alert.confidence * 100).toFixed(1)}%
                          </span>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {!alert.acknowledged && (
                          <button onClick={() => handleAcknowledge(alert.id)} className="btn-primary py-1 px-3 text-xs bg-emerald-600 hover:bg-emerald-500 border-emerald-500">
                            <CheckCircle2 size={12} /> Acquitter
                          </button>
                        )}
                        <button onClick={() => handleDismiss(alert.id)} className="btn-ghost py-1 px-3 text-xs hover:text-rose-400 hover:bg-rose-500/10">
                          <XCircle size={12} /> Ignorer
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

        </main>
      </div>
    </div>
  );
}
