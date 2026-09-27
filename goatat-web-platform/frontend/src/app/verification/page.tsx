'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { api, type AnalysisResult } from '@/lib/api';
import { formatFileSize, formatDuration, verdictLabel, formatDate } from '@/lib/utils';
import {
  Upload, Mic, Play, Square, Trash2, AlertTriangle, CheckCircle2,
  XCircle, HelpCircle, Loader2, FileAudio, ChevronDown, Zap, Info
} from 'lucide-react';

type Tab = 'upload' | 'record';
type RecordState = 'idle' | 'requesting' | 'recording' | 'stopped' | 'error';

const SUPPORTED_EXTS = ['.wav', '.mp3', '.flac', '.m4a', '.ogg', '.opus', '.webm'];

const STAGE_LABELS = [
  { key: 'upload', label: 'Envoi de l\'audio' },
  { key: 'preprocess', label: 'Prétraitement audio' },
  { key: 'inference', label: 'Inférence du modèle' },
  { key: 'results', label: 'Génération des résultats' },
];

function VerdictDisplay({ result }: { result: AnalysisResult }) {
  const isAuthentic = result.verdict === 'authentic';
  const isSynthetic = result.verdict === 'synthetic';
  const isInconclusive = result.verdict === 'inconclusive';

  const color = isAuthentic ? '#10B981' : isSynthetic ? '#F43F5E' : '#F59E0B';
  const Icon = isAuthentic ? CheckCircle2 : isSynthetic ? XCircle : HelpCircle;
  const bgClass = isAuthentic ? 'rgba(16,185,129,0.08)' : isSynthetic ? 'rgba(244,63,94,0.08)' : 'rgba(245,158,11,0.08)';
  const borderColor = isAuthentic ? 'rgba(16,185,129,0.25)' : isSynthetic ? 'rgba(244,63,94,0.25)' : 'rgba(245,158,11,0.25)';

  return (
    <div className="mt-6 space-y-4">
      {/* Main verdict */}
      <div className="rounded-xl p-6" style={{ background: bgClass, border: `1px solid ${borderColor}` }}>
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full flex items-center justify-center" style={{ background: `${color}20` }}>
            <Icon size={28} style={{ color }} />
          </div>
          <div className="flex-1">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Verdict d'analyse</div>
            <div className="text-2xl font-bold text-white">{verdictLabel(result.verdict)}</div>
            <div className="text-sm mt-1" style={{ color }}>
              Confiance : {(result.confidence * 100).toFixed(1)}%
            </div>
          </div>
          {result.is_demo && (
            <span className="demo-badge self-start"><Zap size={9} /> Démo</span>
          )}
        </div>

        {/* Probability bars */}
        {result.authentic_probability !== null && (
          <div className="mt-5 space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-emerald-400 font-medium">Probabilité authentique</span>
                <span className="text-emerald-300">{((result.authentic_probability ?? 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${(result.authentic_probability ?? 0) * 100}%`, background: 'linear-gradient(90deg, #10B981, #059669)' }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-rose-400 font-medium">Probabilité synthétique</span>
                <span className="text-rose-300">{((result.synthetic_probability ?? 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${(result.synthetic_probability ?? 0) * 100}%`, background: 'linear-gradient(90deg, #F43F5E, #E11D48)' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: 'Modèle', value: result.model_name },
          { label: 'Version', value: result.model_version },
          { label: 'Mode d\'inférence', value: result.inference_mode },
          { label: 'Temps d\'inférence', value: `${result.inference_time_ms.toFixed(0)} ms` },
          { label: 'Durée audio', value: formatDuration(result.audio_duration_seconds) },
          { label: 'Taille du fichier', value: formatFileSize(result.file_size_bytes) },
          { label: 'Fréquence d\'échantillonnage', value: `${result.sample_rate} Hz` },
          { label: 'Date d\'analyse', value: formatDate(result.created_at) },
        ].map(({ label, value }) => (
          <div key={label} className="glass-card p-3">
            <div className="text-xs text-slate-500 mb-1">{label}</div>
            <div className="text-sm text-slate-200 font-medium truncate">{value}</div>
          </div>
        ))}
      </div>

      {/* Warning */}
      <div className="p-4 rounded-lg flex items-start gap-3" style={{ background: 'rgba(37,99,235,0.05)', border: '1px solid rgba(37,99,235,0.15)' }}>
        <AlertTriangle size={14} className="text-blue-400 mt-0.5 shrink-0" />
        <p className="text-xs text-slate-500">
          <strong className="text-slate-400">Avertissement : </strong>
          Ce résultat est généré par un modèle de machine learning.
          {result.is_demo && ' En mode démonstration, les prédictions sont simulées et ne reflètent pas les performances réelles du modèle.'}
          {' '}Il ne constitue pas une preuve juridique de l'authenticité ou de la synthèse vocale.
        </p>
      </div>

      {/* Link to full details */}
      <a href={`/analysis/${result.id}`} className="btn-ghost w-full justify-center">
        <Info size={14} /> Voir l&apos;analyse détaillée
      </a>
    </div>
  );
}

export default function VerificationPage() {
  const [tab, setTab] = useState<Tab>('upload');
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStage, setAnalysisStage] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Recording
  const [recordState, setRecordState] = useState<RecordState>('idle');
  const [recordDuration, setRecordDuration] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!SUPPORTED_EXTS.includes(ext)) {
      setError(`Format non supporté: ${ext}. Formats acceptés: ${SUPPORTED_EXTS.join(', ')}`);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError('Fichier trop grand (maximum 50 Mo)');
      return;
    }
    setError(null);
    setResult(null);
    setSelectedFile(file);
  }, []);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const startRecording = async () => {
    setRecordState('requesting');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mr;
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setRecordedBlob(blob);
        setRecordedUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach(t => t.stop());
      };
      mr.start(100);
      setRecordState('recording');
      setRecordDuration(0);
      timerRef.current = setInterval(() => setRecordDuration(d => d + 1), 1000);
    } catch (err: unknown) {
      setRecordState('error');
      setError('Accès au microphone refusé. Vérifiez les permissions du navigateur.');
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    if (timerRef.current) clearInterval(timerRef.current);
    setRecordState('stopped');
  };

  const discardRecording = () => {
    setRecordedBlob(null);
    setRecordedUrl(null);
    setRecordState('idle');
    setRecordDuration(0);
    setResult(null);
    setError(null);
  };

  const analyze = async () => {
    const fileToAnalyze = tab === 'upload' ? selectedFile : recordedBlob
      ? new File([recordedBlob], `enregistrement-${Date.now()}.webm`, { type: 'audio/webm' })
      : null;

    if (!fileToAnalyze) return;

    setAnalyzing(true);
    setResult(null);
    setError(null);
    setAnalysisStage(0);

    try {
      // Simulate staged progress
      for (let s = 0; s < STAGE_LABELS.length; s++) {
        setAnalysisStage(s);
        if (s < 3) await new Promise(r => setTimeout(r, 400));
      }
      const res = await api.analyzeAudio(fileToAnalyze);
      setResult(res);
    } catch (e: unknown) {
      setError((e as Error).message || 'Erreur lors de l\'analyse');
    } finally {
      setAnalyzing(false);
      setAnalysisStage(0);
    }
  };

  const canAnalyze = tab === 'upload' ? !!selectedFile : recordState === 'stopped' && !!recordedBlob;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-60 overflow-hidden">
        <TopBar title="Vérification vocale" />
        <main className="flex-1 overflow-y-auto p-6" style={{ background: '#070D1A' }}>

          <div className="max-w-3xl mx-auto">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-white mb-1">Analyser une voix</h2>
              <p className="text-slate-400 text-sm">
                Détectez si un enregistrement audio est authentique ou potentiellement synthétique ou cloné.
              </p>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-6 p-1 rounded-lg" style={{ background: '#0D172A', border: '1px solid rgba(99,130,188,0.15)' }}>
              {[
                { key: 'upload' as Tab, label: 'Importer un fichier audio', icon: Upload },
                { key: 'record' as Tab, label: 'Enregistrer en direct', icon: Mic },
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => { setTab(key); setResult(null); setError(null); }}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all"
                  style={{
                    background: tab === key ? 'linear-gradient(135deg, #2563EB, #1D4ED8)' : 'transparent',
                    color: tab === key ? 'white' : '#94A3B8',
                  }}
                >
                  <Icon size={14} />
                  {label}
                </button>
              ))}
            </div>

            {/* Upload tab */}
            {tab === 'upload' && (
              <div className="space-y-4">
                <div
                  className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <FileAudio size={32} className="mx-auto mb-3 text-slate-500" />
                  <p className="text-slate-300 font-medium mb-1">
                    Glissez-déposez un fichier audio ou cliquez pour parcourir
                  </p>
                  <p className="text-xs text-slate-500">
                    Formats acceptés : WAV, MP3, FLAC, M4A, OGG, OPUS, WEBM — Max 50 Mo
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={SUPPORTED_EXTS.join(',')}
                    className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                  />
                </div>

                {selectedFile && (
                  <div className="glass-card p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg flex items-center justify-center"
                        style={{ background: 'rgba(37,99,235,0.1)' }}>
                        <FileAudio size={16} className="text-blue-400" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">{selectedFile.name}</div>
                        <div className="text-xs text-slate-400">{formatFileSize(selectedFile.size)}</div>
                      </div>
                    </div>
                    <button onClick={() => { setSelectedFile(null); setResult(null); }} className="btn-ghost p-2">
                      <Trash2 size={14} />
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Record tab */}
            {tab === 'record' && (
              <div className="space-y-4">
                <div className="glass-card p-8 text-center">
                  <div className="relative inline-block mb-6">
                    <div
                      className={`w-24 h-24 rounded-full flex items-center justify-center cursor-pointer transition-all ${recordState === 'recording' ? 'pulse-record' : ''}`}
                      style={{
                        background: recordState === 'recording'
                          ? 'rgba(244,63,94,0.2)'
                          : 'rgba(37,99,235,0.1)',
                        border: `2px solid ${recordState === 'recording' ? '#F43F5E' : '#2563EB'}`,
                      }}
                      onClick={recordState === 'idle' ? startRecording : recordState === 'recording' ? stopRecording : undefined}
                    >
                      <Mic size={36} style={{ color: recordState === 'recording' ? '#F43F5E' : '#2563EB' }} />
                    </div>
                  </div>

                  <div className="text-4xl font-mono font-bold text-white mb-2">
                    {String(Math.floor(recordDuration / 60)).padStart(2, '0')}:{String(recordDuration % 60).padStart(2, '0')}
                  </div>

                  <div className="text-sm text-slate-400 mb-6">
                    {recordState === 'idle' && 'Cliquez sur le microphone pour commencer l\'enregistrement'}
                    {recordState === 'requesting' && 'Demande d\'accès au microphone...'}
                    {recordState === 'recording' && 'Enregistrement en cours — cliquez pour arrêter'}
                    {recordState === 'stopped' && 'Enregistrement terminé'}
                    {recordState === 'error' && <span className="text-rose-400">Erreur de microphone</span>}
                  </div>

                  <div className="flex justify-center gap-3">
                    {recordState === 'idle' && (
                      <button onClick={startRecording} className="btn-primary"><Mic size={14} /> Commencer</button>
                    )}
                    {recordState === 'recording' && (
                      <button onClick={stopRecording} className="btn-danger"><Square size={14} /> Arrêter</button>
                    )}
                    {recordState === 'stopped' && (
                      <button onClick={discardRecording} className="btn-ghost"><Trash2 size={14} /> Réenregistrer</button>
                    )}
                  </div>
                </div>

                {recordedUrl && (
                  <div className="glass-card p-4">
                    <div className="text-xs text-slate-400 mb-2">Aperçu de l&apos;enregistrement</div>
                    <audio src={recordedUrl} controls className="w-full" style={{ filter: 'invert(0.85) hue-rotate(170deg)' }} />
                  </div>
                )}
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="mt-4 p-4 rounded-lg flex items-center gap-3"
                style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.2)' }}>
                <AlertTriangle size={14} className="text-rose-400" />
                <span className="text-sm text-rose-300">{error}</span>
              </div>
            )}

            {/* Analysis progress */}
            {analyzing && (
              <div className="mt-6 glass-card p-5">
                <div className="flex items-center gap-3 mb-4">
                  <Loader2 size={16} className="text-blue-400 animate-spin" />
                  <span className="text-sm font-medium text-white">Analyse en cours...</span>
                </div>
                <div className="space-y-2">
                  {STAGE_LABELS.map((stage, idx) => (
                    <div key={stage.key} className="flex items-center gap-3">
                      <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${idx < analysisStage ? 'bg-emerald-500' : idx === analysisStage ? 'bg-blue-500' : 'bg-slate-700'}`}>
                        {idx < analysisStage ? '✓' : idx === analysisStage ? <Loader2 size={10} className="animate-spin" /> : ''}
                      </div>
                      <span className={`text-sm ${idx === analysisStage ? 'text-white' : idx < analysisStage ? 'text-emerald-400' : 'text-slate-500'}`}>
                        {stage.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Analyze button */}
            {!analyzing && !result && (
              <button
                onClick={analyze}
                disabled={!canAnalyze}
                className="btn-primary w-full justify-center mt-6 py-3 text-base"
              >
                <Mic size={18} /> Analyser la voix
              </button>
            )}

            {/* Result */}
            {result && <VerdictDisplay result={result} />}

            {/* New analysis button after result */}
            {result && !analyzing && (
              <button
                onClick={() => { setResult(null); setSelectedFile(null); setRecordedBlob(null); setRecordedUrl(null); setRecordState('idle'); }}
                className="btn-ghost w-full justify-center mt-4"
              >
                Nouvelle analyse
              </button>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
