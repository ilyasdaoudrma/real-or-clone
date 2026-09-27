'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { api, type AnalysisResult } from '@/lib/api';
import { formatDate, formatDuration, formatFileSize, verdictLabel } from '@/lib/utils';
import {
  ArrowLeft, CheckCircle2, XCircle, HelpCircle, Loader2,
  AlertTriangle, Download, Activity, Zap, Info
} from 'lucide-react';

export default function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.getAnalysis(id)
      .then(setAnalysis)
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [id]);

  const downloadJson = () => {
    if (!analysis) return;
    const blob = new Blob([JSON.stringify(analysis, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `goatat-analyse-${id}.json`; a.click();
  };

  const VerdictIcon = analysis?.verdict === 'authentic' ? CheckCircle2
    : analysis?.verdict === 'synthetic' ? XCircle : HelpCircle;
  const verdictColor = analysis?.verdict === 'authentic' ? '#10B981'
    : analysis?.verdict === 'synthetic' ? '#F43F5E' : '#F59E0B';

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-60 overflow-hidden">
        <TopBar title="Analyse détaillée" />
        <main className="flex-1 overflow-y-auto p-6" style={{ background: '#070D1A' }}>

          <Link href="/history" className="btn-ghost inline-flex mb-6 text-sm">
            <ArrowLeft size={14} /> Retour à l&apos;historique
          </Link>

          {loading && (
            <div className="flex items-center justify-center py-20">
              <Loader2 size={28} className="animate-spin text-blue-400" />
            </div>
          )}

          {error && (
            <div className="p-5 rounded-xl flex items-center gap-3"
              style={{ background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.25)' }}>
              <AlertTriangle size={18} className="text-rose-400" />
              <div>
                <div className="text-rose-300 font-medium">Analyse introuvable</div>
                <div className="text-rose-400/70 text-sm">{error}</div>
              </div>
            </div>
          )}

          {analysis && (
            <div className="max-w-4xl space-y-5">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white mb-1">{analysis.original_filename}</h2>
                  <div className="text-xs text-slate-500 font-mono">ID: {analysis.id}</div>
                </div>
                <div className="flex gap-3">
                  {analysis.is_demo && <span className="demo-badge self-start"><Zap size={9} />Démo</span>}
                  <button onClick={downloadJson} className="btn-ghost text-sm">
                    <Download size={14} /> Télécharger JSON
                  </button>
                </div>
              </div>

              {/* Verdict card */}
              <div className="glass-card p-6">
                <div className="flex items-center gap-4 mb-5">
                  <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: `${verdictColor}20` }}>
                    <VerdictIcon size={32} style={{ color: verdictColor }} />
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Verdict</div>
                    <div className="text-2xl font-bold text-white">{verdictLabel(analysis.verdict)}</div>
                    <div className="text-sm mt-1" style={{ color: verdictColor }}>
                      Indice de confiance : {(analysis.confidence * 100).toFixed(2)}%
                    </div>
                  </div>
                </div>

                {/* Probability bars */}
                {analysis.authentic_probability !== null && (
                  <div className="space-y-3 border-t pt-5" style={{ borderColor: 'rgba(99,130,188,0.15)' }}>
                    <div>
                      <div className="flex justify-between text-xs mb-1.5">
                        <span className="text-emerald-400 font-medium">Voix authentique</span>
                        <span className="text-emerald-300 font-mono">{((analysis.authentic_probability ?? 0) * 100).toFixed(3)}%</span>
                      </div>
                      <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${(analysis.authentic_probability ?? 0) * 100}%`, background: 'linear-gradient(90deg,#10B981,#059669)' }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1.5">
                        <span className="text-rose-400 font-medium">Voix synthétique</span>
                        <span className="text-rose-300 font-mono">{((analysis.synthetic_probability ?? 0) * 100).toFixed(3)}%</span>
                      </div>
                      <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${(analysis.synthetic_probability ?? 0) * 100}%`, background: 'linear-gradient(90deg,#F43F5E,#E11D48)' }} />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Audio player */}
              <div className="glass-card p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Activity size={15} className="text-blue-400" />
                  <h3 className="text-sm font-semibold text-white">Lecteur audio</h3>
                </div>
                <audio
                  src={api.audioUrl(analysis.filename)}
                  controls
                  className="w-full"
                  style={{ filter: 'invert(0.85) hue-rotate(170deg)' }}
                />
              </div>

              {/* Spectrogram */}
              {analysis.spectrogram_path && (
                <div className="glass-card p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <Activity size={15} className="text-purple-400" />
                    <h3 className="text-sm font-semibold text-white">Mel-Spectrogramme</h3>
                  </div>
                  <img
                    src={api.spectrogramUrl(analysis.id)}
                    alt="Spectrogramme"
                    className="w-full rounded-lg"
                    style={{ border: '1px solid rgba(99,130,188,0.15)' }}
                  />
                  <p className="text-xs text-slate-500 mt-2">
                    Représentation temps-fréquence de l&apos;audio analysé (échelle Mel, 128 banques de fréquences).
                  </p>
                </div>
              )}

              {/* Raw scores */}
              {analysis.raw_scores && (
                <div className="glass-card p-5">
                  <h3 className="text-sm font-semibold text-white mb-3">Scores bruts du modèle</h3>
                  <pre className="text-xs text-slate-300 overflow-x-auto p-3 rounded-lg"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(99,130,188,0.1)' }}>
                    {JSON.stringify(analysis.raw_scores, null, 2)}
                  </pre>
                </div>
              )}

              {/* Metadata grid */}
              <div className="glass-card p-5">
                <h3 className="text-sm font-semibold text-white mb-4">Métadonnées de l&apos;analyse</h3>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Modèle', value: analysis.model_name },
                    { label: 'Version du modèle', value: analysis.model_version },
                    { label: 'Mode d\'inférence', value: analysis.inference_mode },
                    { label: 'Temps d\'inférence', value: `${analysis.inference_time_ms.toFixed(1)} ms` },
                    { label: 'Durée audio', value: formatDuration(analysis.audio_duration_seconds) },
                    { label: 'Taille du fichier', value: formatFileSize(analysis.file_size_bytes) },
                    { label: 'Fréquence d\'échantillonnage', value: `${analysis.sample_rate} Hz` },
                    { label: 'Horodatage', value: formatDate(analysis.created_at) },
                    { label: 'Mode démo', value: analysis.is_demo ? 'Oui' : 'Non' },
                  ].map(({ label, value }) => (
                    <div key={label} className="p-3 rounded-lg" style={{ background: 'rgba(0,0,0,0.2)' }}>
                      <div className="text-xs text-slate-500 mb-1">{label}</div>
                      <div className="text-sm text-slate-200 font-medium">{value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Disclaimer */}
              <div className="p-4 rounded-lg flex items-start gap-3"
                style={{ background: 'rgba(37,99,235,0.05)', border: '1px solid rgba(37,99,235,0.15)' }}>
                <Info size={14} className="text-blue-400 mt-0.5 shrink-0" />
                <p className="text-xs text-slate-500">
                  <strong className="text-slate-400">Explication technique : </strong>
                  Le modèle XLS-R (wav2vec 2.0) analyse les caractéristiques acoustiques de bas niveau extraites de l&apos;audio.
                  La probabilité de synthèse reflète la vraisemblance que ces caractéristiques correspondent à un signal généré par un système de synthèse vocale.
                  {analysis.is_demo && ' En mode démonstration, ces valeurs sont simulées.'}
                  {' '}Un résultat élevé indique une corrélation avec des patterns de voix synthétique — ce n&apos;est pas une preuve définitive.
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
