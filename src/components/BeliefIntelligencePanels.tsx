import { AlertTriangle, Activity, Database, FileText, Gauge, Layers3, RadioTower, ShieldAlert, Timer, TrendingUp } from 'lucide-react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataSourceBadge, FallbackNotice } from '@/src/components/DataSourceBadges';
import type { BeliefDelta, BeliefHistoryPoint, BeliefSnapshot, ProvenanceMeta } from '@/src/store';

function percent(value: number): string {
  return `${Math.round(value)}%`;
}

function ratio(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function sentimentClass(sentiment: string): string {
  if (sentiment === 'positive') return 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20';
  if (sentiment === 'negative') return 'text-rose-300 bg-rose-500/10 border-rose-500/20';
  return 'text-amber-200 bg-amber-500/10 border-amber-500/20';
}

export function BeliefScoreCard({ snapshot, meta }: { snapshot: BeliefSnapshot; meta: ProvenanceMeta | null }) {
  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-medium flex flex-wrap items-center gap-2">
          <Gauge className="w-5 h-5 text-teal-400" />
          Belief Intelligence
          <DataSourceBadge meta={meta ?? snapshot.meta} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-end gap-5">
          <div>
            <div className="text-sm text-muted-foreground">Belief Score</div>
            <div className="text-5xl font-semibold tracking-tight text-gradient">{snapshot.belief.score}</div>
          </div>
          <div className="space-y-1">
            <div className="text-lg font-medium">{snapshot.belief.label}</div>
            <p className="text-sm text-muted-foreground max-w-xl">
              Q-Belief Net analyzes market belief signals, not stock price truth.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-lg border border-white/5 bg-black/15 p-3">
            <div className="text-xs text-muted-foreground">Velocity</div>
            <div className="text-xl font-medium">{snapshot.belief.velocity > 0 ? '+' : ''}{snapshot.belief.velocity.toFixed(1)}</div>
          </div>
          <div className="rounded-lg border border-white/5 bg-black/15 p-3">
            <div className="text-xs text-muted-foreground">Coherence</div>
            <div className="text-xl font-medium">{ratio(snapshot.belief.coherence)}</div>
          </div>
          <div className="rounded-lg border border-white/5 bg-black/15 p-3">
            <div className="text-xs text-muted-foreground">Fragility</div>
            <div className="text-xl font-medium">{ratio(snapshot.belief.fragility)}</div>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          This prototype does not provide financial advice. Scores are interpretive signals, not buy/sell recommendations.
        </p>
      </CardContent>
    </Card>
  );
}

export function BeliefBreakdownPanel({ snapshot }: { snapshot: BeliefSnapshot }) {
  const rows = [
    ['Attention', snapshot.breakdown.attention, 'Volume and intensity of belief evidence.'],
    ['Sentiment', snapshot.breakdown.sentiment, 'Weighted tone across evidence.'],
    ['Momentum', snapshot.breakdown.momentum, 'Recent change in belief formation.'],
    ['Source agreement', snapshot.breakdown.source_agreement, 'How aligned source categories are.'],
    ['Volatility', snapshot.breakdown.volatility, 'How unstable the evidence tone is.'],
    ['Evidence depth', snapshot.breakdown.evidence_depth, 'Breadth of available evidence.'],
  ] as const;

  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader>
        <CardTitle className="text-lg font-medium flex items-center gap-2">
          <Activity className="w-5 h-5 text-emerald-400" />
          Signal Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {rows.map(([label, value, description]) => (
          <div key={label}>
            <div className="flex justify-between gap-3 mb-2">
              <span className="text-sm text-muted-foreground">{label}</span>
              <span className="text-sm font-medium">{percent(value)}</span>
            </div>
            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-teal-400 rounded-full" style={{ width: `${value}%` }} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">{description}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function NarrativeClustersPanel({ snapshot }: { snapshot: BeliefSnapshot }) {
  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader>
        <CardTitle className="text-lg font-medium flex items-center gap-2">
          <Layers3 className="w-5 h-5 text-cyan-400" />
          Narrative Clusters
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {snapshot.narratives.slice(0, 5).map((cluster) => (
          <div key={cluster.id} className="rounded-lg border border-white/5 bg-black/15 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-medium text-sm">{cluster.title}</div>
              <Badge variant="outline" className={sentimentClass(cluster.sentiment)}>{cluster.sentiment}</Badge>
            </div>
            <div className="mt-2 h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-cyan-400 rounded-full" style={{ width: `${cluster.strength * 100}%` }} />
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {cluster.keywords.map((keyword) => (
                <Badge key={keyword} variant="secondary" className="bg-white/5 text-muted-foreground border-white/5">
                  {keyword}
                </Badge>
              ))}
            </div>
            <p className="mt-2 text-xs text-muted-foreground line-clamp-2">{cluster.representative_evidence}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function EvidencePanel({ snapshot }: { snapshot: BeliefSnapshot }) {
  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader>
        <CardTitle className="text-lg font-medium flex items-center gap-2">
          <FileText className="w-5 h-5 text-amber-300" />
          Evidence
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {snapshot.evidence.slice(0, 6).map((item) => (
          <div key={item.id} className="rounded-lg border border-white/5 bg-black/15 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <Badge variant="outline" className="bg-cyan-500/10 text-cyan-200 border-cyan-500/20">
                {item.source_name}
              </Badge>
              <span className="text-xs text-muted-foreground">sentiment {item.sentiment.toFixed(2)}</span>
            </div>
            <p className="text-sm leading-relaxed">{item.text}</p>
            <p className="text-xs text-muted-foreground mt-2">{item.note}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function BeliefExplanationPanel({ snapshot }: { snapshot: BeliefSnapshot }) {
  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader>
        <CardTitle className="text-lg font-medium flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-teal-400" />
          Why This Score Exists
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-relaxed">{snapshot.explanation.summary}</p>
        <div className="space-y-2">
          {snapshot.explanation.drivers.map((driver) => (
            <div key={driver} className="text-sm text-muted-foreground flex gap-2">
              <TrendingUp className="w-4 h-4 text-teal-400 mt-0.5 shrink-0" />
              <span>{driver}</span>
            </div>
          ))}
        </div>
        {snapshot.explanation.warnings.map((warning) => (
          <div key={warning} className="text-sm text-amber-100 flex gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 p-2">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{warning}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function BeliefHistoryChart({ history }: { history: BeliefHistoryPoint[] }) {
  const chartData = history.map((point) => ({
    ...point,
    fragility: Math.round(point.fragility * 100),
  }));

  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader>
        <CardTitle className="text-lg font-medium">Belief History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[220px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="timestamp" hide />
              <YAxis domain={[0, 100]} stroke="rgba(255,255,255,0.2)" fontSize={12} />
              <Tooltip
                contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                labelFormatter={(label) => new Date(String(label)).toLocaleDateString()}
              />
              <Line type="monotone" dataKey="score" stroke="#2dd4bf" strokeWidth={3} dot={false} name="Belief Score" />
              <Line type="monotone" dataKey="fragility" stroke="#fb7185" strokeWidth={2} dot={false} name="Fragility" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

export function BeliefDeltaTicker({ delta }: { delta: BeliefDelta | null }) {
  if (!delta) return null;
  const positive = delta.delta >= 0;
  return (
    <div className={`rounded-lg border px-3 py-2 text-sm flex items-center gap-2 ${positive ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-100' : 'border-rose-500/20 bg-rose-500/10 text-rose-100'}`}>
      <RadioTower className="w-4 h-4 shrink-0" />
      <span>{delta.symbol} belief {positive ? 'rose' : 'fell'} {Math.abs(delta.delta)} points. {delta.reason}</span>
    </div>
  );
}

export function BeliefFallbackNotice({ meta, error }: { meta: ProvenanceMeta | null; error: string | null }) {
  return <FallbackNotice meta={meta} error={error} />;
}

export function EvidenceSourceMixPanel({ snapshot }: { snapshot: BeliefSnapshot }) {
  const mix = snapshot.source_mix ?? {};
  const entries = [
    ['Live', mix.live ?? 0, 'text-emerald-300'],
    ['Cached', mix.cached ?? 0, 'text-sky-300'],
    ['Synthetic', mix.synthetic ?? 0, 'text-cyan-300'],
    ['Fallback', mix.fallback ?? 0, 'text-amber-300'],
  ] as const;

  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader>
        <CardTitle className="text-lg font-medium flex items-center gap-2">
          <Database className="w-5 h-5 text-cyan-400" />
          Source Mix
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3">
        {entries.map(([label, value, color]) => (
          <div key={label} className="rounded-lg border border-white/5 bg-black/15 p-3">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className={`text-2xl font-semibold ${color}`}>{value}</div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function FreshnessIndicator({ snapshot }: { snapshot: BeliefSnapshot }) {
  const freshness = snapshot.freshness_summary;
  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader>
        <CardTitle className="text-lg font-medium flex items-center gap-2">
          <Timer className="w-5 h-5 text-emerald-400" />
          Freshness
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex justify-between gap-3">
          <span className="text-muted-foreground">Latest</span>
          <span>{freshness?.latest_timestamp ? new Date(freshness.latest_timestamp).toLocaleString() : 'Unknown'}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span className="text-muted-foreground">Fresh items</span>
          <span>{freshness?.fresh_item_count ?? 0}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span className="text-muted-foreground">Stale items</span>
          <span>{freshness?.stale_item_count ?? 0}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span className="text-muted-foreground">Cache hits</span>
          <span>{freshness?.cache_hit_count ?? 0}</span>
        </div>
      </CardContent>
    </Card>
  );
}

export function ProviderStatusPanel({ snapshot }: { snapshot: BeliefSnapshot }) {
  const providers = snapshot.provider_results ?? [];
  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader>
        <CardTitle className="text-lg font-medium">Providers</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {providers.length === 0 ? (
          <p className="text-sm text-muted-foreground">No provider results were returned.</p>
        ) : providers.map((provider) => (
          <div key={`${provider.provider}-${provider.status}`} className="rounded-lg border border-white/5 bg-black/15 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium text-sm">{provider.provider}</span>
              <Badge variant="outline" className={provider.status === 'ok' ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20' : provider.status === 'cached' ? 'bg-sky-500/10 text-sky-300 border-sky-500/20' : 'bg-amber-500/10 text-amber-200 border-amber-500/20'}>
                {provider.status}
              </Badge>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {provider.is_live ? 'Live provider evidence' : provider.is_cached ? 'Cached provider result' : provider.is_fallback ? 'Fallback provider result' : 'Demo or unavailable provider result'}
            </p>
            {provider.errors.map((error) => (
              <p key={error.code} className="mt-1 text-xs text-amber-200">{error.message}</p>
            ))}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function EvidenceTrustPanel({ snapshot }: { snapshot: BeliefSnapshot }) {
  const warnings = snapshot.warnings ?? snapshot.evidence_bundle?.warnings ?? [];
  const fallback = (snapshot.source_mix?.fallback ?? 0) > 0 || snapshot.meta.is_fallback;
  return (
    <Card className="glass-panel border-white/5 bg-card/30">
      <CardHeader>
        <CardTitle className="text-lg font-medium flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-300" />
          Evidence Trust
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className={`rounded-lg border p-3 ${fallback ? 'border-amber-500/20 bg-amber-500/10 text-amber-100' : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-100'}`}>
          {fallback ? 'Fallback evidence is being used and is visible in the source mix.' : 'No fallback was reported for this snapshot.'}
        </div>
        {warnings.length > 0 ? warnings.map((warning) => (
          <p key={warning} className="text-xs text-muted-foreground">{warning}</p>
        )) : (
          <p className="text-xs text-muted-foreground">No provider warnings were reported.</p>
        )}
      </CardContent>
    </Card>
  );
}
