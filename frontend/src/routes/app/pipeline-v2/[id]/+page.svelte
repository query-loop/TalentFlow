<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { getPipelineV2, patchPipelineV2, runPipelineV2, retryJdAnalysis, getPipelineReport, recomputeAtsV2, type PipelineV2 } from '$lib/pipelinesV2';
  let pipe: PipelineV2 | null = null;
  let error: string | null = null;
  $: id = $page.params.id;
  async function load(){ try { pipe = await getPipelineV2(id); } catch(e:any){ error = e?.message || 'Failed to load'; }}

  function getAtsPercent(p: PipelineV2 | null): number | null {
    const ats = p?.artifacts && (p.artifacts as any).ats;
    if (!ats || typeof ats !== 'object') return null;
    if (typeof ats.aggregate === 'number') return Math.max(0, Math.min(100, Math.round(ats.aggregate * 100)));
    if (typeof ats.coverage === 'number') return Math.max(0, Math.min(100, Math.round(ats.coverage)));
    if (typeof ats.percent === 'number') return Math.max(0, Math.min(100, Math.round(ats.percent)));
    if (typeof ats.score === 'number') {
      const v = ats.score;
      return Math.max(0, Math.min(100, Math.round(v <= 1 ? v * 100 : v)));
    }
    return null;
  }

  // Auto-orchestration intentionally disabled: user runs pipeline/report manually.
  let autoRun = false;
  let autoBusy = false;
  let autoNote: string | null = null;
  let autoQueued = false;
  let autoLastKickAt = 0;
  let autoPoll: number | null = null;

  function scheduleAutoKick(note?: string) {
    if (!autoRun || autoQueued) return;
    autoQueued = true;
    if (note) autoNote = note;
    queueMicrotask(async () => {
      autoQueued = false;
      await autoKick();
    });
  }

  function stepStatus(step: string): string {
    const st = (pipe?.statuses as any) || {};
    return st?.[step] || 'pending';
  }

  function hasJd(): boolean {
    const jd = (pipe?.artifacts as any)?.jd;
    if (jd && typeof jd === 'object' && typeof jd.description === 'string' && jd.description.trim()) return true;
    if (pipe?.jdId && pipe.jdId.startsWith('manual:') && pipe.jdId.slice(7).trim()) return true;
    return false;
  }

  function hasProfile(): boolean {
    const p = (pipe?.artifacts as any)?.profile;
    if (p && typeof p === 'object' && p.parsed && typeof p.parsed === 'object') return true;
    return false;
  }

  function hasAts(): boolean {
    const a = (pipe?.artifacts as any)?.ats;
    return !!(a && typeof a === 'object');
  }

  function hasReport(): boolean {
    const r = (pipe?.artifacts as any)?.report;
    return !!(r && typeof r === 'object' && (r.text || r.data));
  }

  async function ensureReport() {
    if (!pipe || hasReport()) return;
    autoNote = 'Generating report…';
    try {
      busy = true;

      // Ensure we have a parsed profile in artifacts (report endpoint relies on artifacts.profile/resume text).
      // This is lightweight and does NOT run the full pipeline.
      if (!hasAts() && hasJd() && (hasProfile() || !!pipe.resumeId || !!(pipe.artifacts as any)?.resume?.text)) {
        try {
          pipe = await recomputeAtsV2(pipe.id);
        } catch {
          // Best-effort: still attempt report generation.
        }
      }

      const rep = await getPipelineReport(pipe.id);
      const reasons = Array.isArray(rep?.reasons) ? rep.reasons : [];
      const sections = rep?.sections && typeof rep.sections === 'object' ? rep.sections : {};
      const text = [
        `Pipeline Report - ${pipe.name}`,
        '',
        `Score: ${rep?.score ?? 'n/a'}`,
        '',
        'Reasons:',
        reasons.length ? reasons.map((r: string) => `- ${r}`).join('\n') : '(none)',
        '',
        ...Object.entries(sections).flatMap(([k, v]) => [`${k}:`, String(v ?? ''), ''])
      ].join('\n');

      const artifacts = { ...(pipe.artifacts || {}), report: { data: rep, text, generatedAt: Date.now() } };
      pipe = await patchPipelineV2(pipe.id, { artifacts });
    } catch (e: any) {
      // Report is best-effort; don't block the rest.
      autoNote = `Report generation failed: ${e?.message || String(e)}`;
    } finally {
      busy = false;
    }
  }

  async function autoKick() {
    if (!autoRun || !pipe || autoBusy) return;

    // Don’t spam the backend.
    const now = Date.now();
    if (now - autoLastKickAt < 2000) return;
    autoLastKickAt = now;

    // If JD failed/blocked, we can't proceed without manual JD.
    const jdSt = stepStatus('jd');
    if (!hasJd() && (jdSt === 'failed' || jdSt === 'blocked')) {
      autoNote = 'JD could not be extracted — paste JD manually to continue.';
      return;
    }

    // If we have JD but pipeline isn’t complete through ATS, run the real backend pipeline.
    const atsSt = stepStatus('ats');
    const shouldRun = hasJd() && (!hasAts() || atsSt !== 'complete');
    if (shouldRun) {
      autoBusy = true;
      autoNote = 'Running pipeline…';
      runLogs = [];
      try {
        const res = await runPipelineV2(pipe.id);
        runLogs = res.log || ['run completed'];
        pipe = res.pipeline;
      } catch (e: any) {
        runLogs = [e?.message || String(e)];
      } finally {
        autoBusy = false;
      }
    }

    // If ATS is ready, create the report automatically.
    if (pipe && hasAts() && stepStatus('ats') === 'complete' && !hasReport()) {
      await ensureReport();
    }

    // Keep the note quiet once everything is ready.
    if (pipe && hasJd() && hasProfile() && hasAts() && hasReport()) {
      autoNote = null;
    }
  }

  onMount(async () => {
    await load();
  });

  let busy = false;

  // ── JD SSE extraction ──────────────────────────────────────────────
  let jdEs: EventSource | null = null;
  let jdStreamForId: string | null = null;
  let jdStatusMessage: string | null = null;
  let jdEta: number | null = null;
  let jdStage: string | null = null;
  let jdProgress: number | null = null;
  let jdFailed: string | null = null;
  let jdTimedOut = false;
  let manualJD = '';
  let savingManual = false;
  let retrying = false;

  // Derived view-model values (must be script-scoped; block-scoped {@const} won’t be visible across elements)
  $: jdObj = (pipe?.artifacts as any)?.jd;
  $: jdReady = !!(jdObj && typeof jdObj === 'object' && typeof jdObj.description === 'string' && jdObj.description.trim());
  $: jdErr = jdObj && typeof jdObj === 'object' ? (jdObj.error || jdObj.blocked_reason) : null;
  $: reportText = (pipe?.artifacts as any)?.report?.text as string | undefined;
  $: atsPct = getAtsPercent(pipe);

  $: if (typeof window !== 'undefined' && pipe && id && !autoBusy) {
    const jdObj = (pipe.artifacts as any)?.jd;
    const jdReady = !!(jdObj && typeof jdObj === 'object' && typeof jdObj.description === 'string' && jdObj.description.trim());
    const canFetch = !!(pipe.jdId && !pipe.jdId.startsWith('manual:'));
    const needsJd = !jdReady;
    const notAlreadyStreaming = jdStreamForId !== id;
    if (needsJd && canFetch && notAlreadyStreaming && !jdEs) {
      jdStreamForId = id;
      try {
        jdEs = new EventSource(`/api/pipelines-v2/${id}/jd/stream`);
        let intentionallyClosed = false;
        jdEs.addEventListener('status', (ev: MessageEvent) => {
          try {
            const p = JSON.parse(ev.data || '{}');
            jdStatusMessage = p.message || null;
            jdEta = typeof p.etaSeconds === 'number' ? p.etaSeconds : null;
            jdStage = p.stage || null;
            jdProgress = typeof p.progress === 'number' ? p.progress : null;
          } catch {}
        });
        jdEs.addEventListener('ready', async () => {
          intentionallyClosed = true;
          try { pipe = await getPipelineV2(id); } catch {}
          jdEs?.close(); jdEs = null; jdStreamForId = null;
          jdStatusMessage = null; jdEta = null; jdStage = null; jdProgress = null;
          // Manual flow: do not auto-run pipeline.
        });
        jdEs.addEventListener('failed', (ev: MessageEvent) => {
          intentionallyClosed = true;
          try { const p = JSON.parse(ev.data || '{}'); jdFailed = p.error || 'Extraction failed'; } catch { jdFailed = 'Extraction failed'; }
          jdEs?.close(); jdEs = null; jdStreamForId = null;
          scheduleAutoKick();
        });
        jdEs.addEventListener('timeout', () => {
          intentionallyClosed = true;
          jdTimedOut = true; jdEs?.close(); jdEs = null; jdStreamForId = null;
          scheduleAutoKick();
        });
        jdEs.addEventListener('error', () => {
          if (intentionallyClosed) { jdEs?.close(); jdEs = null; jdStreamForId = null; }
        });
        jdEs.addEventListener('keepalive', () => {});
      } catch (_) {}
    } else if (!needsJd && jdEs) {
      jdEs.close(); jdEs = null; jdStreamForId = null;
      jdStatusMessage = null; jdEta = null; jdStage = null; jdProgress = null;
      jdFailed = null; jdTimedOut = false;
    }
  }

  onDestroy(() => { if (jdEs) { jdEs.close(); jdEs = null; } jdStreamForId = null; });

  async function saveManualJD() {
    if (!id || !manualJD.trim()) return;
    savingManual = true; error = null;
    try {
      await fetch(`/api/pipelines-v2/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jdId: 'manual:' + manualJD.trim() })
      });
      jdFailed = null; jdTimedOut = false;
      pipe = await getPipelineV2(id);
      // Manual flow: do not auto-run pipeline.
    } catch (e: any) { error = e?.message || String(e); }
    finally { savingManual = false; }
  }

  async function retryExtraction() {
    if (!pipe || !id || retrying) return;
    retrying = true;
    try {
      jdFailed = null; jdTimedOut = false;
      jdStatusMessage = 'Retrying extraction…';
      pipe = await retryJdAnalysis(id);
      pipe = await getPipelineV2(id);
      // Manual flow: do not auto-run pipeline.
    } catch (e: any) { jdFailed = e.message || 'Retry failed'; }
    finally { retrying = false; }
  }

  // Helper to refresh pipeline after patch
  async function refresh() {
    if (!pipe) return;
    pipe = await getPipelineV2(pipe.id);
  }

  // Run full v2 pipeline (agentic)
  let runLogs: string[] = [];
  let runBusy = false;
  async function runFullPipeline() {
    if (!pipe) return;
    runBusy = true; runLogs = [];
    try {
      const res = await runPipelineV2(pipe.id);
      // show logs and refresh
      runLogs = res.log || ["run completed"];
      pipe = res.pipeline;
    } catch (e:any) {
      runLogs = [e?.message || String(e)];
    } finally { runBusy = false; }
  }

  // Download generated resume text (simple TXT download)
  function downloadGenerated() {
    if (!pipe || !(pipe.artifacts && (pipe.artifacts as any).generated)) return;
    const g = (pipe.artifacts as any).generated;
    const text = `${g.summary}\n\nSkills:\n${(g.skills||[]).join(', ')}\n\nExperience:\n${(g.experience||[]).join('\n')}`;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${pipe.name || 'generated_resume'}.txt`; document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  }

  // Simulate pushing to ATS: record push status in artifacts
  async function pushToAts() {
    if (!pipe) return;
    busy = true; error = null;
    try {
      const artifacts = { ...(pipe.artifacts || {}), push: { status: 'pushed', at: Date.now() } };
      await patchPipelineV2(pipe.id, { artifacts });
      await refresh();
    } catch (e:any) { error = e?.message || String(e); }
    finally { busy = false; }
  }
</script>

{#if error}
  <div class="p-6"><div class="border rounded p-4 bg-red-50 text-red-700">{error}</div></div>
{:else if !pipe}
  <div class="p-6"><div class="border rounded p-4">Loading…</div></div>
{:else}
  <div class="p-6 space-y-4">
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <h1 class="text-2xl font-semibold truncate" title={pipe.name}>{pipe.name}</h1>
      </div>
      <div class="flex items-center gap-2">
        <a href="/app/pipelines-v2" class="text-sm text-gray-600 hover:text-gray-800 dark:text-slate-300">All v2 pipelines</a>
        <a href={`/app/pipeline-v2/stats`} class="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"> 
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h3v8H3zM10 8h3v12h-3zM17 4h3v16h-3z" /></svg>
          Stats
        </a>
      </div>
    </div>

    {#if autoNote}
      <div class="border rounded p-3 text-xs bg-slate-50 text-slate-700 dark:bg-slate-900/30 dark:text-slate-200">{autoNote}</div>
    {/if}

    <div class="border rounded-lg bg-white dark:bg-slate-800 divide-y divide-slate-200 dark:divide-slate-700">

      <!-- ── JD ── -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Job Description</span>
          {#if jdReady}
            <span class="text-xs px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300">Ready</span>
          {:else if jdFailed || jdErr || stepStatus('jd') === 'failed' || stepStatus('jd') === 'blocked'}
            <span class="text-xs px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300">Failed</span>
          {:else if jdTimedOut}
            <span class="text-xs px-1.5 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300">Timed out</span>
          {:else}
            <span class="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">Extracting…</span>
          {/if}
        </div>

        {#if jdReady}
          {#if jdObj?.title || pipe.name}
            <div class="text-sm font-medium text-slate-900 dark:text-slate-100">{jdObj?.title || pipe.name}</div>
          {/if}
          {#if jdObj?.company || pipe.company}
            <div class="text-xs text-slate-500 mt-0.5">{jdObj?.company || pipe.company}</div>
          {/if}
          {#if jdObj?.description}
            <div class="mt-2 text-xs text-slate-600 dark:text-slate-300 line-clamp-4 whitespace-pre-wrap">{jdObj.description.slice(0, 300)}{jdObj.description.length > 300 ? '…' : ''}</div>
          {/if}
          <div class="mt-3 flex gap-2 flex-wrap">
            <button class="btn" on:click={retryExtraction} disabled={retrying}>{retrying ? 'Retrying…' : 'Re-extract'}</button>
            <button class="btn btn-primary" on:click={runFullPipeline} disabled={runBusy || autoBusy}>{runBusy ? 'Running…' : 'Run pipeline'}</button>
          </div>
        {:else if jdFailed || jdErr || stepStatus('jd') === 'failed' || stepStatus('jd') === 'blocked'}
          <div class="text-xs text-red-700 dark:text-red-300 break-words mb-2">{jdFailed || String(jdErr || 'JD extraction failed')}</div>
          <div class="text-xs text-slate-500 dark:text-slate-400 mb-2">Paste JD manually to continue the pipeline.</div>
          <textarea class="w-full min-h-24 border rounded p-2 text-xs bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-900 dark:text-slate-100" bind:value={manualJD} placeholder="Paste job description…"></textarea>
          <div class="mt-2 flex gap-2">
            <button class="btn btn-primary" on:click={saveManualJD} disabled={savingManual || !manualJD.trim()}>{savingManual ? 'Saving…' : 'Save JD'}</button>
            <button class="btn" on:click={retryExtraction} disabled={retrying || !(pipe.jdId && !pipe.jdId.startsWith('manual:'))}>{retrying ? 'Retrying…' : 'Retry fetch'}</button>
          </div>
        {:else if jdTimedOut}
          <div class="text-xs text-yellow-700 dark:text-yellow-300 mb-2">Taking longer than expected — paste manually to continue.</div>
          <textarea class="w-full min-h-24 border rounded p-2 text-xs bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-900 dark:text-slate-100" bind:value={manualJD} placeholder="Paste job description…"></textarea>
          <button class="mt-2 btn btn-primary" on:click={saveManualJD} disabled={savingManual || !manualJD.trim()}>{savingManual ? 'Saving…' : 'Save JD'}</button>
        {:else}
          <div class="space-y-1.5">
            {#if !pipe.jdId}
              <div class="text-xs text-slate-500 dark:text-slate-400">No JD found for this pipeline. Paste it to continue.</div>
              <textarea class="w-full min-h-24 border rounded p-2 text-xs bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-900 dark:text-slate-100" bind:value={manualJD} placeholder="Paste job description…"></textarea>
              <button class="mt-2 btn btn-primary" on:click={saveManualJD} disabled={savingManual || !manualJD.trim()}>{savingManual ? 'Saving…' : 'Save JD'}</button>
            {:else}
              <div class="flex items-center gap-2 text-xs text-slate-500">
                <svg class="animate-spin h-3 w-3 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
                <span>{jdStatusMessage || (stepStatus('jd') === 'active' ? 'Extracting…' : 'Waiting…')}</span>
              </div>
            {#if jdEta !== null}<div class="text-xs text-slate-400">~{jdEta}s remaining</div>{/if}
            <details class="text-xs mt-1">
              <summary class="cursor-pointer text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">Paste JD manually instead</summary>
              <textarea class="mt-1 w-full min-h-20 border rounded p-2 bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-900 dark:text-slate-100" bind:value={manualJD} placeholder="Paste job description…"></textarea>
              <button class="mt-1 btn btn-primary" on:click={saveManualJD} disabled={savingManual || !manualJD.trim()}>{savingManual ? 'Saving…' : 'Save JD'}</button>
            </details>
            {/if}
          </div>
        {/if}
      </div>

      <!-- ── Profile ── -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Profile</span>
          {#if (pipe.artifacts as any)?.profile?.parsed}
            <span class="text-xs px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300">Ready</span>
          {:else if stepStatus('profile') === 'active'}
            <span class="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">Processing…</span>
          {:else if stepStatus('profile') === 'failed'}
            <span class="text-xs px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300">Failed</span>
          {/if}
        </div>
        <div class="text-sm text-slate-700 dark:text-slate-200">{(pipe.artifacts as any)?.profile?.parsed?.summary || (pipe.artifacts as any)?.resume?.summary || '—'}</div>
        {#if ((pipe.artifacts as any)?.profile?.parsed?.skills || (pipe.artifacts as any)?.resume?.skills || []).length}
          <div class="mt-1.5 flex flex-wrap gap-1">
            {#each ((pipe.artifacts as any)?.profile?.parsed?.skills || (pipe.artifacts as any)?.resume?.skills || []).slice(0,8) as skill}
              <span class="text-xs px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">{skill}</span>
            {/each}
          </div>
        {/if}
        <div class="mt-3 flex gap-2">
          <button class="btn btn-primary" on:click={runFullPipeline} disabled={runBusy || autoBusy}>{runBusy ? 'Running…' : 'Run pipeline'}</button>
          <button class="btn" on:click={downloadGenerated} disabled={!(pipe.artifacts && (pipe.artifacts as any).generated)}>Download</button>
        </div>
      </div>

      <!-- ── ATS ── -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">ATS Score</span>
          {#if stepStatus('ats') === 'active'}
            <span class="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">Scoring…</span>
          {:else if stepStatus('ats') === 'failed'}
            <span class="text-xs px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300">Failed</span>
          {/if}
        </div>
        <div class="flex items-center justify-between gap-4">
          <div class="text-2xl font-bold text-slate-900 dark:text-slate-100">{atsPct === null ? '—' : `${atsPct}%`}</div>
          <a class="btn" href={`/app/pipeline-v2/${pipe.id}/ats`}>Open ATS</a>
        </div>
        <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">Strengths and weaknesses are shown on the ATS page.</div>
        <div class="flex gap-2">
          <button class="btn btn-primary" on:click={runFullPipeline} disabled={runBusy || autoBusy}>{runBusy ? 'Running…' : 'Run pipeline'}</button>
          <button class="btn" on:click={pushToAts} disabled={busy}>Push to ATS</button>
        </div>
      </div>

      <!-- ── Actions ── -->
      <div class="p-4 flex flex-wrap items-center gap-2">
        <button class="btn" on:click={refresh}>Refresh</button>
        <button class="btn" on:click={ensureReport} disabled={busy || autoBusy}>Generate report</button>
        <a class="btn" href={`/app/pipeline-v2/${pipe.id}/export`}>Export</a>
      </div>
    </div>

    {#if reportText}
      <div class="border rounded-lg bg-white dark:bg-slate-800 p-4">
        <div class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">Report</div>
        <pre class="whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-200">{reportText}</pre>
      </div>
    {/if}

    {#if runLogs && runLogs.length}
      <div class="border rounded-lg bg-black text-white p-4">
        <div class="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">Run logs</div>
        <ul class="text-xs space-y-1 list-disc ml-4">
          {#each runLogs as rl}<li>{rl}</li>{/each}
        </ul>
      </div>
    {/if}
  </div>
{/if}
