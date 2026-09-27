'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { api, type PaginatedAnalyses, type AnalysisListItem } from '@/lib/api';
import { formatDate, formatDuration, verdictLabel } from '@/lib/utils';
import {
  Search, Filter, Trash2, ExternalLink, ChevronLeft, ChevronRight,
  AlertTriangle, History, Loader2, Download, Zap
} from 'lucide-react';

export default function HistoryPage() {
  const [data, setData] = useState<PaginatedAnalyses | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.listAnalyses({ page, per_page: 15, search: search || undefined, verdict: verdictFilter || undefined });
      setData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, verdictFilter]);

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setPage(1); load(); };

  const handleDelete = async () => {
    if (!deleteId) return;
    setDeleting(true);
    try {
      await api.deleteAnalysis(deleteId);
      setDeleteId(null);
      load();
    } catch (e) {
      console.error(e);
    } finally {
      setDeleting(false);
    }
  };

  const exportCsv = () => {
    if (!data) return;
    const header = 'ID,Fichier,Verdict,Confiance,Durée,Modèle,Date\n';
    const rows = data.items.map(a =>
      `"${a.id}","${a.original_filename}","${a.verdict}","${(a.confidence * 100).toFixed(1)}%","${formatDuration(a.audio_duration_seconds)}","${a.model_name}","${formatDate(a.created_at)}"`
    ).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'goatat-historique.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-60 overflow-hidden">
        <TopBar title="Historique des analyses" />
        <main className="flex-1 overflow-y-auto p-6" style={{ background: '#070D1A' }}>

          {/* Filters */}
          <div className="flex gap-3 mb-6">
            <form onSubmit={handleSearch} className="flex-1 relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                className="form-input pl-9"
                placeholder="Rechercher par nom de fichier..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </form>
            <select
              className="form-input w-48"
              value={verdictFilter}
              onChange={e => { setVerdictFilter(e.target.value); setPage(1); }}
            >
              <option value="">Tous les verdicts</option>
              <option value="authentic">Authentique</option>
              <option value="synthetic">Synthétique</option>
              <option value="inconclusive">Indéterminé</option>
            </select>
            <button onClick={exportCsv} className="btn-ghost">
              <Download size={14} /> Exporter CSV
            </button>
          </div>

          {/* Table */}
          <div className="glass-card overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 size={24} className="animate-spin text-blue-400" />
              </div>
            ) : data?.items.length === 0 ? (
              <div className="flex flex-col items-center py-20 text-slate-500">
                <History size={40} className="mb-3 opacity-20" />
                <p className="font-medium text-slate-400">Aucune analyse trouvée</p>
                <Link href="/verification" className="btn-primary mt-4 text-sm">Commencer une analyse</Link>
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
                      <th>Mode</th>
                      <th>Date</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.items.map((a: AnalysisListItem) => (
                      <tr key={a.id}>
                        <td className="max-w-xs">
                          <div className="font-medium text-slate-200 truncate">{a.original_filename}</div>
                          <div className="text-xs text-slate-500 truncate">{a.id}</div>
                        </td>
                        <td>
                          <span className={`badge verdict-${a.verdict}`}>{verdictLabel(a.verdict)}</span>
                        </td>
                        <td className="text-slate-300">{(a.confidence * 100).toFixed(1)}%</td>
                        <td className="text-slate-400">{formatDuration(a.audio_duration_seconds)}</td>
                        <td>
                          {a.is_demo && <span className="demo-badge"><Zap size={9} />Démo</span>}
                        </td>
                        <td className="text-slate-400 text-xs">{formatDate(a.created_at)}</td>
                        <td>
                          <div className="flex items-center gap-2">
                            <Link href={`/analysis/${a.id}`} className="p-1.5 rounded hover:bg-blue-500/10 text-slate-500 hover:text-blue-400 transition-colors">
                              <ExternalLink size={13} />
                            </Link>
                            <button
                              onClick={() => setDeleteId(a.id)}
                              className="p-1.5 rounded hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 transition-colors"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-slate-500">
                {data.total} analyse{data.total > 1 ? 's' : ''} — Page {data.page} / {data.pages}
              </span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => p - 1)} disabled={page <= 1} className="btn-ghost py-1.5 px-3">
                  <ChevronLeft size={14} />
                </button>
                <button onClick={() => setPage(p => p + 1)} disabled={page >= (data?.pages ?? 1)} className="btn-ghost py-1.5 px-3">
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Delete confirmation modal */}
          {deleteId && (
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
              <div className="glass-card p-6 max-w-sm w-full mx-4">
                <div className="flex items-center gap-3 mb-4">
                  <AlertTriangle size={20} className="text-rose-400" />
                  <h3 className="text-white font-semibold">Supprimer l&apos;analyse ?</h3>
                </div>
                <p className="text-sm text-slate-400 mb-6">
                  Cette action est irréversible. Le fichier audio et les données d&apos;analyse seront définitivement supprimés.
                </p>
                <div className="flex gap-3">
                  <button onClick={() => setDeleteId(null)} className="btn-ghost flex-1 justify-center">Annuler</button>
                  <button onClick={handleDelete} disabled={deleting} className="btn-danger flex-1 justify-center">
                    {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                    Supprimer
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
