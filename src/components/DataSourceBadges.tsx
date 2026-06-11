import { AlertCircle, CheckCircle2, CloudOff, Database, Radio, ShieldAlert } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { ApiStatus, ProvenanceMeta } from '@/src/store';

function sourceLabel(meta: ProvenanceMeta | null | undefined): string {
  if (!meta) return 'Source unknown';
  if (meta.is_fallback) return 'Fallback data';
  switch (meta.source) {
    case 'live':
      return 'Live data';
    case 'generated':
      return 'Demo data';
    case 'mock':
      return 'Mock data';
    case 'cached':
      return 'Cached data';
    case 'fallback':
      return 'Fallback data';
    default:
      return 'Unavailable';
  }
}

function sourceClass(meta: ProvenanceMeta | null | undefined): string {
  if (!meta) return 'bg-zinc-500/10 text-zinc-300 border-zinc-500/20';
  if (meta.is_fallback || meta.source === 'fallback') return 'bg-amber-500/10 text-amber-300 border-amber-500/20';
  if (meta.source === 'live') return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20';
  if (meta.source === 'generated' || meta.source === 'mock') return 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20';
  return 'bg-zinc-500/10 text-zinc-300 border-zinc-500/20';
}

export function DataSourceBadge({ meta }: { meta: ProvenanceMeta | null | undefined }) {
  return (
    <Badge variant="outline" className={sourceClass(meta)}>
      <Database className="w-3 h-3 mr-1" />
      {sourceLabel(meta)}
    </Badge>
  );
}

export function RuntimeModeBadge({ status }: { status: ApiStatus | null }) {
  const mode = status?.data_mode ?? 'unknown';
  const label = mode === 'live' ? 'Live Mode' : mode === 'hybrid' ? 'Hybrid Mode' : mode === 'demo' ? 'Demo Mode' : 'Backend Unknown';
  return (
    <Badge variant="secondary" className="hidden sm:inline-flex bg-teal-500/10 text-teal-300 border-teal-500/20">
      <Radio className="w-3 h-3 mr-1" />
      {label}
    </Badge>
  );
}

export function FallbackNotice({ meta, error }: { meta?: ProvenanceMeta | null; error?: string | null }) {
  if (error) {
    return (
      <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-200 flex items-center gap-2">
        <CloudOff className="w-4 h-4 shrink-0" />
        {error}
      </div>
    );
  }

  if (!meta?.is_fallback) return null;

  return (
    <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-100 flex items-center gap-2">
      <ShieldAlert className="w-4 h-4 shrink-0" />
      {meta.notes}
    </div>
  );
}

export function ApiStatusCard({ status, error }: { status: ApiStatus | null; error: string | null }) {
  const healthy = Boolean(status && !error);
  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardContent className="p-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        {healthy ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertCircle className="w-4 h-4 text-amber-400" />}
        <span>{healthy ? `${status?.service} ${status?.version}` : 'Backend offline or status unavailable'}</span>
        {status ? <span>Data: {status.data_mode}</span> : null}
        {status ? <span>LLM: {status.llm.configured ? 'configured' : 'not configured'}</span> : null}
        {error ? <span className="text-amber-200">{error}</span> : null}
      </CardContent>
    </Card>
  );
}
