const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const MODEL_NAME = 'meta-llama/Meta-Llama-3-8B';
const LLM_UNAVAILABLE_UNTIL_KEY = 'q_belief_net_hf_llm_unavailable_until';
const LLM_UNAVAILABLE_REASON_KEY = 'q_belief_net_hf_llm_unavailable_reason';
const LLM_HARD_LOCK_KEY = 'q_belief_net_hf_llm_hard_lock';
const LEGACY_KEYS = [
  'q_belief_net_llm_unavailable_until',
  'q_belief_net_llm_unavailable_reason',
  'q_belief_net_llm_hard_lock',
];
const KNOWN_TICKERS = new Set([
  'NVDA', 'TSLA', 'AAPL', 'AMD', 'MSFT', 'META', 'AMZN', 'GOOGL', 'PLTR', 'SMCI',
  'COIN', 'MARA', 'JPM', 'UNH', 'XOM', 'V', 'JNJ', 'WMT', 'PG', 'MA',
]);

let llmUnavailableUntil = 0;
let llmUnavailableReason = '';
let llmHardLocked = false;

function buildApiUrl(path: string): string {
  if (!apiBaseUrl) return path;
  return `${apiBaseUrl}${path}`;
}

function readStoredCooldown(): void {
  if (typeof window === 'undefined') {
    return;
  }

  for (const key of LEGACY_KEYS) {
    window.localStorage.removeItem(key);
  }

  const hardLock = window.localStorage.getItem(LLM_HARD_LOCK_KEY);
  const storedUntil = window.localStorage.getItem(LLM_UNAVAILABLE_UNTIL_KEY);
  const storedReason = window.localStorage.getItem(LLM_UNAVAILABLE_REASON_KEY);
  const parsedUntil = storedUntil ? Number(storedUntil) : 0;

  llmHardLocked = hardLock === 'true';

  if (llmHardLocked) {
    llmUnavailableUntil = Number.POSITIVE_INFINITY;
    llmUnavailableReason = storedReason || 'Hugging Face quota exhausted';
    return;
  }

  if (Number.isFinite(parsedUntil) && parsedUntil > Date.now()) {
    llmUnavailableUntil = parsedUntil;
    llmUnavailableReason = storedReason || 'Hugging Face quota exhausted';
  }
}

function storeCooldown(until: number, reason: string, hardLock = false): void {
  llmUnavailableUntil = hardLock ? Number.POSITIVE_INFINITY : until;
  llmUnavailableReason = reason;
  llmHardLocked = hardLock;

  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(LLM_UNAVAILABLE_UNTIL_KEY, String(llmUnavailableUntil));
  window.localStorage.setItem(LLM_UNAVAILABLE_REASON_KEY, reason);
  window.localStorage.setItem(LLM_HARD_LOCK_KEY, String(hardLock));
}

readStoredCooldown();

function extractTickers(question: string): string[] {
  const matches = question.toUpperCase().match(/\b[A-Z]{2,5}\b/g) ?? [];
  return [...new Set(matches.filter((token) => KNOWN_TICKERS.has(token)))].slice(0, 3);
}

function buildFallbackResponse(question: string): string {
  const tickers = extractTickers(question);
  const lowered = question.toLowerCase();

  if (tickers.length > 0) {
    const tickerList = tickers.join(', ');
    return `I am using local fallback analysis. For ${tickerList}, inspect belief score, attention, sentiment, coherence, fragility, narrative clusters, and evidence provenance before drawing a product-level interpretation. This is not financial advice.`;
  }

  if (lowered.includes('fall') || lowered.includes('drop') || lowered.includes('down')) {
    return 'I am using local fallback analysis. A belief-signal starting point is to check whether attention rose, sentiment weakened, coherence fragmented, or fragility increased. This prototype does not provide buy/sell recommendations.';
  }

  if (lowered.includes('ai') || lowered.includes('tech') || lowered.includes('semiconductor')) {
    return 'I am using local fallback analysis. For AI and tech names, compare attention intensity, narrative coherence, source agreement, and fragility across tickers rather than treating belief scores as price predictions.';
  }

  return 'I am using local fallback analysis. Ask about a ticker or sector and I can explain belief signals such as attention, sentiment, velocity, coherence, fragility, evidence count, and provenance.';
}

export async function queryMarketLLM(question: string): Promise<string> {
  if (llmHardLocked || llmUnavailableUntil > Date.now()) {
    return buildFallbackResponse(question);
  }

  try {
    const systemPrompt = `You are Q-Belief Net's belief-signal assistant.
Explain market belief signals such as attention, sentiment, velocity, coherence, fragility, narrative clusters, evidence count, and provenance.
Do not provide financial advice, price targets, trading instructions, or buy/sell recommendations.
Clearly state when data is demo-generated or prototype-only.
Keep responses concise and focused on interpretive belief analytics, not stock price truth.`;

    const response = await fetch(buildApiUrl('/api/llm'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        model: MODEL_NAME,
        system_prompt: systemPrompt,
      }),
    });

    const payload = await response.json() as {
      response?: string;
      error?: { message?: string } | string;
    };

    if (!response.ok) {
      const errorMessage = typeof payload.error === 'object'
        ? payload.error?.message || 'Unknown model error'
        : payload.error || `Request failed with status ${response.status}`;
      throw new Error(errorMessage);
    }

    return payload.response?.trim() || 'Unable to generate response. Please try again.';
  } catch (error) {
    const status = (error as { status?: number; code?: number; message?: string })?.status ?? (error as { code?: number })?.code;
    const message = (error as { message?: string })?.message ?? '';
    const isQuotaError = status === 429 || message.toLowerCase().includes('quota') || message.toLowerCase().includes('rate limit');

    if (isQuotaError) {
      storeCooldown(Number.POSITIVE_INFINITY, 'Hugging Face quota exhausted', true);
      console.warn('Hugging Face quota exhausted; switching to local fallback until manually reset.');
      return buildFallbackResponse(question);
    }

    console.warn('LLM query error; using local fallback:', error);
    storeCooldown(Date.now() + 60_000, 'Hugging Face unavailable', false);
    return buildFallbackResponse(question);
  }
}

export function isLLMConfigured(): boolean {
  return true;
}

export function getLLMStatus(): string {
  if (llmHardLocked) {
    return llmUnavailableReason || 'quota-exhausted';
  }

  if (llmUnavailableUntil > Date.now()) {
    return llmUnavailableReason || 'temporarily-unavailable';
  }

  if (typeof window !== 'undefined') {
    window.localStorage.removeItem(LLM_UNAVAILABLE_UNTIL_KEY);
    window.localStorage.removeItem(LLM_UNAVAILABLE_REASON_KEY);
  }

  return 'available';
}

export function resetLLMFallback(): void {
  llmUnavailableUntil = 0;
  llmUnavailableReason = '';
  llmHardLocked = false;

  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.removeItem(LLM_UNAVAILABLE_UNTIL_KEY);
  window.localStorage.removeItem(LLM_UNAVAILABLE_REASON_KEY);
  window.localStorage.removeItem(LLM_HARD_LOCK_KEY);
}
