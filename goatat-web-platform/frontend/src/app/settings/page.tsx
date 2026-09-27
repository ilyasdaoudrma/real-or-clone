'use client';

import { useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { Save, Settings as SettingsIcon, Shield, Database, Cpu, Globe } from 'lucide-react';

export default function SettingsPage() {
  const [saving, setSaving] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => setSaving(false), 800);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-60 overflow-hidden">
        <TopBar title="Paramètres" />
        <main className="flex-1 overflow-y-auto p-6" style={{ background: '#070D1A' }}>

          <div className="max-w-3xl">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-white mb-1">Paramètres du système</h2>
              <p className="text-slate-400 text-sm">Configurez l&apos;application GOATAT et les préférences de sécurité</p>
            </div>

            <div className="space-y-6">
              {/* General Settings */}
              <div className="glass-card p-6">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-3">
                  <SettingsIcon size={18} className="text-blue-400" />
                  <h3 className="text-lg font-semibold text-white">Général</h3>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Nom de l&apos;organisation</label>
                    <input type="text" className="form-input" defaultValue="GOATAT Security" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Langue de l&apos;interface</label>
                    <select className="form-input">
                      <option value="fr">Français</option>
                      <option value="en">English</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Model & Inference */}
              <div className="glass-card p-6">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-3">
                  <Cpu size={18} className="text-purple-400" />
                  <h3 className="text-lg font-semibold text-white">Modèle d&apos;inférence</h3>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Modèle actif</label>
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 font-mono text-sm">
                      XLS-R 300M (Custom Fine-tuned)
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-4 rounded-lg" style={{ background: 'rgba(37,99,235,0.05)' }}>
                    <div>
                      <div className="text-white font-medium">Seuil de sensibilité synthétique</div>
                      <div className="text-xs text-slate-400">Définit à partir de quelle probabilité l&apos;audio est marqué comme synthétique</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <input type="range" min="0" max="100" defaultValue="75" className="w-32 accent-blue-500" />
                      <span className="text-blue-400 font-mono text-sm w-8">0.75</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Security Alerts */}
              <div className="glass-card p-6">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-3">
                  <Shield size={18} className="text-emerald-400" />
                  <h3 className="text-lg font-semibold text-white">Règles d&apos;alerte</h3>
                </div>
                
                <div className="space-y-3">
                  {[
                    { label: 'Créer une alerte pour chaque détection synthétique confirmée (>90%)', default: true },
                    { label: 'Alerter en cas de qualité audio insuffisante', default: false },
                    { label: 'Notification par email pour les alertes de priorité haute', default: true },
                  ].map((setting, i) => (
                    <label key={i} className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-800/50 cursor-pointer transition-colors">
                      <input type="checkbox" defaultChecked={setting.default} className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-900" />
                      <span className="text-sm text-slate-300">{setting.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-8">
                <button className="btn-ghost">Réinitialiser</button>
                <button onClick={handleSave} disabled={saving} className="btn-primary">
                  {saving ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save size={16} />}
                  {saving ? 'Enregistrement...' : 'Enregistrer les modifications'}
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
