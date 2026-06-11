import { useState } from 'react';
import { motion } from 'motion/react';
import { Activity, Database, Plug, PlugZap, RefreshCw, Save, ServerCog, Timer, User, LogIn, LogOut } from 'lucide-react';
import { useAppStore } from '@/src/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

export function SettingsView() {
  const { wsConnected, connectWebSocket, disconnectWebSocket, apiStatus, apiStatusError, fetchApiStatus } = useAppStore();
  const [refreshWindow, setRefreshWindow] = useState('30');
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('Quant Analyst');
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  return (
    <div className="flex flex-col h-full w-full px-4 sm:px-8 py-8 max-w-4xl mx-auto overflow-y-auto">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">Settings</h1>
        <p className="text-muted-foreground">Tune your feed behavior and connection preferences.</p>
      </motion.div>

      <div className="space-y-4 pb-20">
        <Card className="glass-panel border-white/5 bg-card/30">
          <CardHeader>
            <CardTitle className="text-lg font-medium flex items-center gap-2">
              <ServerCog className="w-5 h-5 text-teal-400" />
              Pipeline Observability
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">Provider health, cache lifecycle, and ingestion refresh status.</p>
              <Button onClick={fetchApiStatus} variant="outline" className="border-white/10 bg-white/5 hover:bg-white/10">
                <RefreshCw className="w-4 h-4 mr-1" /> Refresh Status
              </Button>
            </div>
            {apiStatusError ? <p className="text-sm text-amber-200">{apiStatusError}</p> : null}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="rounded-lg border border-white/5 bg-black/15 p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                  <Activity className="w-4 h-4" /> Provider Health
                </div>
                <div className="text-sm">Healthy: {apiStatus?.provider_health?.healthy ?? 0}</div>
                <div className="text-sm">Degraded: {apiStatus?.provider_health?.degraded ?? 0}</div>
                <div className="text-sm">Circuit open: {apiStatus?.provider_health?.circuit_open ?? 0}</div>
              </div>
              <div className="rounded-lg border border-white/5 bg-black/15 p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                  <Database className="w-4 h-4" /> Evidence Cache
                </div>
                <div className="text-sm">Backend: {apiStatus?.evidence_cache?.backend ?? 'unknown'}</div>
                <div className="text-sm">Entries: {apiStatus?.evidence_cache?.entries ?? 0}</div>
                <div className="text-sm">TTL: {apiStatus?.evidence_cache?.ttl_seconds ?? 0}s</div>
              </div>
              <div className="rounded-lg border border-white/5 bg-black/15 p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                  <Timer className="w-4 h-4" /> Ingestion
                </div>
                <div className="text-sm">Scheduler: {apiStatus?.ingestion?.scheduler_enabled ? 'enabled' : 'disabled'}</div>
                <div className="text-sm">Interval: {apiStatus?.ingestion?.interval_seconds ?? 0}s</div>
                <div className="text-sm">Last run: {apiStatus?.ingestion?.last_run?.status ?? 'none'}</div>
              </div>
            </div>
            <div className="space-y-2">
              {(apiStatus?.providers ?? []).map((provider) => (
                <div key={provider.name} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/5 bg-black/10 px-3 py-2 text-sm">
                  <span>{provider.name}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={provider.configured ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20' : 'bg-amber-500/10 text-amber-200 border-amber-500/20'}>
                      {provider.configured ? 'configured' : 'not configured'}
                    </Badge>
                    <Badge variant="secondary" className="bg-white/5 text-muted-foreground border-white/5">
                      {provider.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="glass-panel border-white/5 bg-card/30">
          <CardHeader>
            <CardTitle className="text-lg font-medium flex items-center gap-2"><User className="w-5 h-5 text-cyan-400" />Profile & Access</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Display Name" />
              <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant="secondary" className={isLoggedIn ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-zinc-500/10 text-zinc-300 border-zinc-500/20'}>
                {isLoggedIn ? 'Authenticated' : 'Signed Out'}
              </Badge>
              {!isLoggedIn ? (
                <Button onClick={() => setIsLoggedIn(true)} className="bg-teal-500 hover:bg-teal-600 text-white"><LogIn className="w-4 h-4 mr-1" />Sign In</Button>
              ) : (
                <Button onClick={() => setIsLoggedIn(false)} variant="outline" className="border-white/10 bg-white/5 hover:bg-white/10"><LogOut className="w-4 h-4 mr-1" />Sign Out</Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="glass-panel border-white/5 bg-card/30">
          <CardHeader>
            <CardTitle className="text-lg font-medium flex items-center gap-2"><PlugZap className="w-5 h-5 text-teal-400" />Real-Time Connection</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">WebSocket Status</p>
                <p className="text-sm text-muted-foreground">Enable or pause live stream updates.</p>
              </div>
              <Badge variant="secondary" className={wsConnected ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-zinc-500/10 text-zinc-300 border-zinc-500/20'}>
                {wsConnected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button onClick={connectWebSocket} className="bg-teal-500 hover:bg-teal-600 text-white">
                <Plug className="w-4 h-4 mr-1" /> Connect Live
              </Button>
              <Button onClick={disconnectWebSocket} variant="outline" className="border-white/10 bg-white/5 hover:bg-white/10">
                Disconnect
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-panel border-white/5 bg-card/30">
          <CardHeader>
            <CardTitle className="text-lg font-medium flex items-center gap-2"><RefreshCw className="w-5 h-5 text-emerald-400" />Refresh Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="max-w-xs">
              <p className="text-sm text-muted-foreground mb-2">Dashboard refresh window</p>
              <Select value={refreshWindow} onValueChange={setRefreshWindow}>
                <SelectTrigger className="bg-transparent border-white/10">
                  <SelectValue placeholder="Select interval" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="15">15 seconds</SelectItem>
                  <SelectItem value="30">30 seconds</SelectItem>
                  <SelectItem value="60">60 seconds</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button
              onClick={() => setSavedAt(new Date().toLocaleTimeString())}
              variant="outline"
              className="border-white/10 bg-white/5 hover:bg-white/10"
            >
              <Save className="w-4 h-4 mr-1" /> Save Preferences
            </Button>
            {savedAt && <p className="text-xs text-muted-foreground">Saved at {savedAt}</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
