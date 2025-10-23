<script lang="ts">
  import StepFooterV2 from '$lib/components/StepFooterV2.svelte';
  import { page } from '$app/stores';
  import { getPipelineV2, retryJdAnalysis, type PipelineV2 } from '$lib/pipelinesV2';
  // Icon is only needed in certain blocks; keep import in case other elements use it later
  import Icon from '$lib/Icon.svelte';
  
  $: id = $page.params.id;
  let pipe: PipelineV2 | null = null;
  let error: string | null = null;
  let loading = true;
  let es: EventSource | null = null;
  let sseStarted = false;
  let statusMessage: string | null = null;
  let eta: number | null = null;
  let stage: string | null = null;
  let progress: number | null = null;
  let failed: string | null = null;
  let manualJD: string = '';
  let savingManual = false;

  let retrying = false;
  async function retryExtraction() {
    if (!pipe || !id || retrying) return;
    retrying = true;
    try {
      // Reset states
      failed = null;
      timedOut = false;
      statusMessage = 'Retrying extraction...';
      eta = null;
      stage = null;
      progress = null;

      // Call retry endpoint
      pipe = await retryJdAnalysis(id);

      // Reload to get updated status
      await loadPipeline();
    } catch (e: any) {
      failed = e.message || 'Retry failed';
    } finally {
      retrying = false;
    }
  }

  let timedOut = false;
  
  async function loadPipeline() {
    if (!id) return;
    try {
      loading = true;
      error = null;
      pipe = await getPipelineV2(id);
    } catch (e: any) {
      error = e.message || 'Failed to load pipeline';
    } finally {
      loading = false;
    }
  }
  
  $: if (id) loadPipeline();

  function formatJd(text: string): string {
    if (!text) return '';
    // Normalize multiple blank lines and trim
    const normalized = text.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
    return normalized;
  }
  
  // Track stream per pipeline ID to prevent reconnections
  let streamForId: string | null = null;

  $: if (typeof window !== 'undefined' && pipe && id) {
    const needsJd = !(pipe.artifacts && (pipe.artifacts as any).jd);
    const notAlreadyStreaming = streamForId !== id;
    
    if (needsJd && notAlreadyStreaming && !es) {
      // Start SSE stream once for this pipeline ID
      streamForId = id;
      try {
        es = new EventSource(`/api/pipelines-v2/${id}/jd/stream`);
        
        // Flag to prevent reconnection after intentional close
        let intentionallyClosed = false;
        
        es.addEventListener('status', (ev: MessageEvent) => {
          try {
            const payload = JSON.parse(ev.data || '{}');
            statusMessage = payload.message || null;
            eta = typeof payload.etaSeconds === 'number' ? payload.etaSeconds : null;
            stage = payload.stage || null;
            progress = typeof payload.progress === 'number' ? payload.progress : null;
          } catch {}
        });
        
        es.addEventListener('ready', async () => {
          intentionallyClosed = true;
          try { pipe = await getPipelineV2(id); } catch {}
          es?.close(); es = null; streamForId = null;
          statusMessage = null; eta = null; stage = null; progress = null;
        });
        
        es.addEventListener('failed', (ev: MessageEvent) => {
          intentionallyClosed = true;
          try { const p = JSON.parse(ev.data || '{}'); failed = p.error || 'Job failed'; } catch { failed = 'Job failed'; }
          es?.close(); es = null; streamForId = null;
        });
        
        es.addEventListener('timeout', () => {
          intentionallyClosed = true;
          timedOut = true; es?.close(); es = null; streamForId = null;
        });
        
        // Handle errors to prevent auto-reconnection after intentional close
        es.addEventListener('error', (err) => {
          if (intentionallyClosed) {
            // Don't reconnect if we intentionally closed
            es?.close(); es = null; streamForId = null;
          }
          // Otherwise, EventSource will auto-reconnect with exponential backoff
        });
        
        // Optional: keepalive no-op to keep connection active
        es.addEventListener('keepalive', () => {});
      } catch (_) {
        // ignore
      }
    } else if (!needsJd && es) {
      // JD is complete, close stream
      es.close(); es = null; streamForId = null;
      statusMessage = null; eta = null; stage = null; progress = null;
      failed = null; timedOut = false;
    }
  }

  // Cleanup on destroy
  import { onDestroy } from 'svelte';
  onDestroy(() => { if (es) { es.close(); es = null; } streamForId = null; });

  // no manual analyze action; background processing happens automatically on creation
</script>

{#if loading}
  <div class="text-sm text-slate-600 dark:text-slate-400">Loading…</div>
{:else if error}
  <div class="border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 rounded-lg p-4">
    <div class="flex items-center gap-2 text-red-800 dark:text-red-200">
      <Icon name="alert-circle" size={16} />
      <span class="font-medium">Error loading pipeline</span>
    </div>
    <p class="text-red-700 dark:text-red-300 text-sm mt-1">{error}</p>
  </div>
{:else if pipe}
  <div class="space-y-4">
    <div class="border rounded-lg p-4 bg-white dark:bg-slate-800">
      <h2 class="text-base font-semibold text-slate-900 dark:text-slate-100 mb-3">Job Description</h2>
      {#if pipe.artifacts && (pipe.artifacts as any).jd}
        {#if (pipe.artifacts as any).jd.title || pipe.name}
          <div class="text-sm font-medium text-slate-900 dark:text-slate-100">{(pipe.artifacts as any).jd.title || pipe.name}</div>
        {/if}
        {#if (pipe.artifacts as any).jd.company || pipe.company}
          <div class="text-xs text-slate-600 dark:text-slate-400 mb-3">{(pipe.artifacts as any).jd.company || pipe.company}</div>
        {/if}
        {#if (pipe.artifacts as any).jd.description}
          <pre class="whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-200 bg-slate-50 dark:bg-slate-700 rounded p-3">{formatJd((pipe.artifacts as any).jd.description)}</pre>
        {/if}
        {#if (pipe.artifacts as any).jd.extraction_metadata}
          <div class="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded text-xs">
            <div class="font-medium text-blue-800 dark:text-blue-200 mb-2">Extraction Details</div>
            <div class="grid grid-cols-2 gap-2 text-blue-700 dark:text-blue-300">
              <div><span class="font-medium">Method:</span> {(pipe.artifacts as any).jd.extraction_metadata.method || 'unknown'}</div>
              <div><span class="font-medium">Quality:</span> {((pipe.artifacts as any).jd.extraction_metadata.quality_score || 0) * 100}%</div>
              {#if (pipe.artifacts as any).jd.extraction_metadata.html_length}
                <div><span class="font-medium">Content Size:</span> {(pipe.artifacts as any).jd.extraction_metadata.html_length} chars</div>
              {/if}
              {#if (pipe.artifacts as any).jd.extraction_metadata.has_structured_data}
                <div><span class="font-medium">Structured Data:</span> Yes</div>
              {/if}
              {#if (pipe.artifacts as any).jd.extraction_metadata.source_domain}
                <div><span class="font-medium">Source:</span> {(pipe.artifacts as any).jd.extraction_metadata.source_domain}</div>
              {/if}
              {#if (pipe.artifacts as any).jd.extraction_metadata.timestamp}
                <div><span class="font-medium">Extracted:</span> {new Date((pipe.artifacts as any).jd.extraction_metadata.timestamp * 1000).toLocaleString()}</div>
              {/if}
            </div>
          </div>
        {/if}
        <div class="mt-3 flex gap-2">
          <button
            class="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
            on:click={retryExtraction}
            disabled={retrying}
          >
            <Icon name="refresh" size={12} />
            {retrying ? 'Retrying...' : 'Retry Extraction'}
          </button>
        </div>
      {:else if failed}
        <div class="border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 rounded p-3 text-sm text-red-800 dark:text-red-200">
          <div class="font-medium mb-1">Job failed</div>
          <div class="text-xs break-words">{failed}</div>
          <div class="mt-3 text-slate-800 dark:text-slate-200">
            <div class="text-xs mb-1">If the website blocks automated fetches, paste the job description below and save:</div>
            <textarea class="w-full min-h-32 border rounded p-2 bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-900 dark:text-slate-100" bind:value={manualJD} placeholder="Paste job description text here..."></textarea>
            <div class="mt-2 flex items-center gap-2">
              <button class="px-3 py-1.5 rounded bg-blue-600 text-white disabled:opacity-50" on:click={saveManualJD} disabled={savingManual || !manualJD.trim()}>{savingManual ? 'Saving…' : 'Save JD'}</button>
            </div>
          </div>
        </div>
      {:else if timedOut}
        <div class="border border-yellow-200 bg-yellow-50 dark:bg-yellow-900/20 dark:border-yellow-800 rounded p-3 text-sm text-yellow-800 dark:text-yellow-200">
          <div class="font-medium mb-1">Taking longer than expected</div>
          <div class="text-xs">You can stay on this page or come back later; we’ll load the extracted content as soon as it’s ready.</div>
        </div>
      {:else}
        <div class="space-y-2">
          <div class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <svg class="animate-spin h-4 w-4 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path></svg>
            <span>{statusMessage || 'Processing job description…'}</span>
          </div>
          {#if progress !== null}
            <div class="w-full bg-slate-100 dark:bg-slate-700 rounded h-2 overflow-hidden">
              <div class="bg-slate-500 h-2" style={`width: ${Math.max(0, Math.min(100, progress))}%`}></div>
            </div>
          {/if}
          {#if eta !== null}
            <div class="text-xs text-slate-500 dark:text-slate-400">Estimated time remaining: ~{eta}s</div>
          {/if}
        </div>
      {/if}
    </div>
    
    <!-- Resume Attachment preview removed per request: JD page will no longer show resume attachments -->
  </div>

  <StepFooterV2 current="jd" pipelineId={id} />
{/if}
