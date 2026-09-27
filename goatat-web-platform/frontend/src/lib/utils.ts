import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s}s`;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(dateStr));
}

export function formatDateShort(dateStr: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(dateStr));
}

export function verdictLabel(verdict: string): string {
  switch (verdict) {
    case 'authentic': return 'Authentique probable';
    case 'synthetic': return 'Voix synthétique probable';
    case 'inconclusive': return 'Indéterminé';
    default: return verdict;
  }
}

export function verdictColor(verdict: string): string {
  switch (verdict) {
    case 'authentic': return 'text-emerald-400';
    case 'synthetic': return 'text-rose-400';
    case 'inconclusive': return 'text-amber-400';
    default: return 'text-slate-400';
  }
}

export function verdictBgColor(verdict: string): string {
  switch (verdict) {
    case 'authentic': return 'bg-emerald-500/10 border-emerald-500/30';
    case 'synthetic': return 'bg-rose-500/10 border-rose-500/30';
    case 'inconclusive': return 'bg-amber-500/10 border-amber-500/30';
    default: return 'bg-slate-500/10 border-slate-500/30';
  }
}

export function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'text-rose-400 bg-rose-500/10';
    case 'high': return 'text-orange-400 bg-orange-500/10';
    case 'medium': return 'text-amber-400 bg-amber-500/10';
    case 'low': return 'text-blue-400 bg-blue-500/10';
    default: return 'text-slate-400 bg-slate-500/10';
  }
}
