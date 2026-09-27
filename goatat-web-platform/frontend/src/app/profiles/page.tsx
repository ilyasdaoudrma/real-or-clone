'use client';

import { useEffect, useState, useRef } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { api, type VoiceProfile } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { Users, Plus, ShieldCheck, FileAudio, Trash2, Mic, Upload, X, Loader2 } from 'lucide-react';

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);

  // Form states
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [consentGiven, setConsentGiven] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Audio enroll state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadProfiles = async () => {
    setLoading(true);
    try {
      // Mock data in case backend isn't ready
      const data = await api.listProfiles().catch(() => [
        {
          id: 'vp-demo-1', display_name: 'Directeur Financier (Demo)', description: 'Profil de protection pour le DAF',
          has_embedding: true, consent_given: true, consent_timestamp: new Date().toISOString(),
          is_experimental: false, created_at: new Date().toISOString()
        }
      ]);
      setProfiles(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadProfiles(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consentGiven) return;
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append('display_name', displayName);
      fd.append('description', description);
      fd.append('consent_given', 'true');
      
      await api.createProfile(fd).catch(e => console.error(e));
      setIsCreateModalOpen(false);
      setDisplayName('');
      setDescription('');
      setConsentGiven(false);
      loadProfiles();
    } finally {
      setSubmitting(false);
    }
  };

  const handleEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !selectedProfileId) return;
    setSubmitting(true);
    try {
      await api.enrollVoice(selectedProfileId, selectedFile).catch(e => console.error(e));
      setIsEnrollModalOpen(false);
      setSelectedFile(null);
      setSelectedProfileId(null);
      loadProfiles();
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Voulez-vous vraiment supprimer ce profil ? Toutes les empreintes vocales seront détruites.')) return;
    try {
      await api.deleteProfile(id).catch(e => console.error(e));
      loadProfiles();
    } catch (e) {}
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-60 overflow-hidden">
        <TopBar title="Profils vocaux protégés" />
        <main className="flex-1 overflow-y-auto p-6" style={{ background: '#070D1A' }}>

          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Gestion des profils (Anti-Usurpation)</h2>
              <p className="text-slate-400 text-sm">
                Créez des profils vocaux pour les personnes à risque (VIP, cadres) afin de détecter les usurpations.
              </p>
            </div>
            <button onClick={() => setIsCreateModalOpen(true)} className="btn-primary">
              <Plus size={16} /> Nouveau profil
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-20"><Loader2 size={24} className="animate-spin text-blue-400" /></div>
          ) : profiles.length === 0 ? (
            <div className="glass-card py-16 flex flex-col items-center justify-center text-slate-500">
              <Users size={48} className="mb-4 text-blue-500/30" />
              <h3 className="text-lg font-medium text-slate-300">Aucun profil enregistré</h3>
              <p className="text-sm mt-1 mb-4">Enregistrez une voix légitime pour vous protéger contre le clonage ciblé.</p>
              <button onClick={() => setIsCreateModalOpen(true)} className="btn-ghost">Créer le premier profil</button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {profiles.map(profile => (
                <div key={profile.id} className="glass-card p-5 relative group">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center border border-slate-700">
                        <Users size={20} className="text-blue-400" />
                      </div>
                      <div>
                        <h3 className="text-white font-semibold truncate max-w-[150px]" title={profile.display_name}>{profile.display_name}</h3>
                        <p className="text-xs text-slate-500">Créé le {formatDate(profile.created_at).split(' ')[0]}</p>
                      </div>
                    </div>
                    <button onClick={() => handleDelete(profile.id)} className="text-slate-600 hover:text-rose-400 transition-colors">
                      <Trash2 size={16} />
                    </button>
                  </div>
                  
                  {profile.description && <p className="text-sm text-slate-400 mb-4 line-clamp-2">{profile.description}</p>}
                  
                  <div className="flex items-center gap-2 mb-5">
                    {profile.has_embedding ? (
                      <span className="badge bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                        <ShieldCheck size={12} className="mr-1" /> Voix protégée
                      </span>
                    ) : (
                      <span className="badge bg-amber-500/10 text-amber-400 border-amber-500/20">
                        <ShieldCheck size={12} className="mr-1" /> En attente d'empreinte
                      </span>
                    )}
                    {profile.consent_given && (
                      <span className="badge bg-blue-500/10 text-blue-400 border-blue-500/20" title="Consentement RGPD validé">
                        Consentement OK
                      </span>
                    )}
                  </div>
                  
                  <button 
                    onClick={() => { setSelectedProfileId(profile.id); setIsEnrollModalOpen(true); }}
                    className="w-full btn-ghost justify-center text-xs"
                  >
                    <Mic size={14} /> {profile.has_embedding ? 'Mettre à jour l\'empreinte' : 'Ajouter une empreinte vocale'}
                  </button>
                </div>
              ))}
            </div>
          )}

        </main>
      </div>

      {/* Modal Creation */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card w-full max-w-md mx-4 overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white">Nouveau profil vocal</h3>
              <button onClick={() => setIsCreateModalOpen(false)} className="text-slate-400 hover:text-white"><X size={20} /></button>
            </div>
            <form onSubmit={handleCreate} className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Nom ou identifiant</label>
                <input required value={displayName} onChange={e => setDisplayName(e.target.value)} type="text" className="form-input" placeholder="ex: PDG Jean Dupont" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Description (Optionnel)</label>
                <textarea value={description} onChange={e => setDescription(e.target.value)} className="form-input" rows={3} placeholder="Détails additionnels..." />
              </div>
              <div className="p-4 rounded-lg bg-blue-900/10 border border-blue-500/20 mt-2">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input required checked={consentGiven} onChange={e => setConsentGiven(e.target.checked)} type="checkbox" className="mt-1 w-4 h-4 rounded border-slate-600 bg-slate-900 text-blue-500" />
                  <span className="text-sm text-slate-300">
                    <strong className="text-blue-400 block mb-1">Consentement explicite (RGPD)</strong>
                    Je confirme avoir obtenu l'accord explicite de cette personne pour enregistrer et analyser son empreinte vocale biométrique dans le but exclusif de prévention des fraudes.
                  </span>
                </label>
              </div>
              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => setIsCreateModalOpen(false)} className="btn-ghost">Annuler</button>
                <button type="submit" disabled={submitting || !consentGiven} className="btn-primary">
                  {submitting ? <Loader2 size={16} className="animate-spin" /> : 'Créer le profil'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Enrollment */}
      {isEnrollModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card w-full max-w-md mx-4 overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white">Ajouter une empreinte vocale</h3>
              <button onClick={() => { setIsEnrollModalOpen(false); setSelectedFile(null); }} className="text-slate-400 hover:text-white"><X size={20} /></button>
            </div>
            <form onSubmit={handleEnroll} className="p-5 space-y-4">
              <p className="text-sm text-slate-400 mb-4">
                Uploadez un fichier audio clair contenant uniquement la voix de cette personne (minimum 10 secondes recommandées).
              </p>
              
              <div 
                className="drop-zone cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <FileAudio size={32} className="mx-auto mb-3 text-slate-500" />
                <p className="text-slate-300 font-medium mb-1">
                  {selectedFile ? selectedFile.name : 'Cliquez pour sélectionner un fichier'}
                </p>
                <p className="text-xs text-slate-500">
                  {selectedFile ? `${(selectedFile.size / 1024 / 1024).toFixed(2)} Mo` : 'WAV, MP3, M4A'}
                </p>
                <input 
                  ref={fileInputRef} type="file" accept=".wav,.mp3,.m4a,.flac" className="hidden" 
                  onChange={e => e.target.files && setSelectedFile(e.target.files[0])} 
                />
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => { setIsEnrollModalOpen(false); setSelectedFile(null); }} className="btn-ghost">Annuler</button>
                <button type="submit" disabled={submitting || !selectedFile} className="btn-primary">
                  {submitting ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />} 
                  {submitting ? 'Extraction en cours...' : 'Extraire l\'empreinte'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
