<script lang="ts">
  import { listPipelinesV2, createPipelineV2, patchPipelineV2, deletePipelineV2, getPipelineReport, recomputeAtsV2, type PipelineV2 } from '$lib/pipelinesV2';
  import { onMount } from 'svelte';
  import Icon from '$lib/Icon.svelte';
  let items: PipelineV2[] = [];
  let loading = false; let error: string | null = null;
  // no periodic polling; we fetch on demand

  // Modal state
  let showCreate = false;
  const form = { name: '', jdUrl: '', jdDoc: '' };
  // JD import state
  let jdImporting = false;
  let importedJd: any = null;
  let importedJdId: string | null = null;
  
  // Resume upload state
  let resumeFile: File | null = null;
  let resumeUploading = false;
  let resumeText: string = '';
  let resumeId: string | null = null;
  // Removed sample data support
  
  function resetForm() {
    form.name = '';
    form.jdUrl = '';
    form.jdDoc = '';
    resumeFile = null;
    resumeText = '';
    resumeId = null;
    error = null;
    // reset imported JD state
    jdImporting = false;
    importedJd = null;
    importedJdId = null;
  }
  
  function openCreateModal() {
    resetForm();
    showCreate = true;
  }

  // Import a JD URL via backend to make it available immediately
  async function importJdUrl(url: string) {
    if (!url || !/^https?:\/\//.test(url)) return;
    if (importedJd && importedJd.sourceUrl === url) return;
    jdImporting = true; importedJd = null; importedJdId = null; error = null;
    try {
      const resp = await fetch('/api/jd/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      if (!resp.ok) throw new Error('Failed to import JD');
      const data = await resp.json();
      importedJd = data; importedJdId = data.id;
      if (data.descriptionRaw) form.jdDoc = data.descriptionRaw;
    } catch (e:any) {
      error = e?.message || 'Failed to import JD';
    } finally {
      jdImporting = false;
    }
  }

  // Edit modal state
  let showEdit = false; let editTarget: PipelineV2 | null = null;
  const editForm = { name: '', jdUrl: '', notes: '' };

  // Snapshot modal state (compact snapshot shown when clicking View)
  let showSnapshot = false;
  let snapshotTarget: PipelineV2 | null = null;
  let snapshotReport: any = null;
  let snapshotLoading = false;
  let snapshotError: string | null = null;
  let snapshotAtsPct: number | null = null;
  $: snapshotAtsPct = snapshotTarget ? getAtsPercent(snapshotTarget) : null;

  async function openSnapshot(p: PipelineV2) {
    snapshotTarget = p;
    snapshotReport = null;
    snapshotError = null;
    showSnapshot = true;
    snapshotLoading = true;
    try {
      // Load last report from backend and show ATS artifacts if present
      const r = await getPipelineReport(p.id);
      snapshotReport = r;
    } catch (e:any) {
      snapshotError = e?.message || 'Failed to load report';
    } finally {
      snapshotLoading = false;
    }
  }

  // Compute a friendly status label and CSS classes for a given step.
  function getSmartStatus(step: string, raw: string, artifacts: any, prevStatus?: string) {
    const clsBase = 'text-[11px] px-2 py-1 rounded-full border';
    const artifactsPresent = artifacts && typeof artifacts === 'object';

    // Helper to produce result
    const res = (label: string, kind: 'complete'|'active'|'pending'|'failed'|'waiting') => {
      const cls = kind === 'complete' ? `${clsBase} border-emerald-300 text-emerald-700 bg-emerald-50/40`
                : kind === 'active' ? `${clsBase} border-indigo-300 text-indigo-700 bg-indigo-50/40`
                : kind === 'failed' ? `${clsBase} border-rose-300 text-rose-700 bg-rose-50/20`
                : kind === 'waiting' ? `${clsBase} border-slate-300 text-slate-700 bg-slate-50/30`
                : `${clsBase} border-slate-200 text-slate-600`;
      return { label, class: cls };
    };

    // If an explicit artifact exists for this step, treat as complete
    if (artifactsPresent && artifacts[step]) {
      return res('Complete', 'complete');
    }

    // Common artifact mappings
    if (artifactsPresent && step === 'intake' && (artifacts.resume || artifacts.intake)) return res('Complete', 'complete');
    if (artifactsPresent && step === 'jd' && (artifacts.jd || artifacts.intake?.jd)) return res('Complete', 'complete');
    if (artifactsPresent && step === 'profile' && artifacts.profile) return res('Complete', 'complete');
    if (artifactsPresent && step === 'ats' && artifacts.ats) return res('Complete', 'complete');

    // Map raw statuses
    if (raw === 'complete') return res('Complete', 'complete');
    if (raw === 'active') return res('In progress', 'active');
    if (raw === 'failed') return res('Failed', 'failed');

    // raw is 'pending' -> try to infer
    if (raw === 'pending') {
      // If previous step is complete, this is likely 'Waiting'
      if (prevStatus === 'complete') return res('Waiting', 'waiting');
      // If no previous progress, mark as 'Not started'
      return res('Not started', 'pending');
    }

    return res(raw || 'Unknown', 'pending');
  }

  // Compute overall progress and current step summary
  // Full pipeline-v2 order for snapshot display (used by computeSmartSummary)
  const fullV2Order = ['intake','jd','profile','gaps','differentiators','draft','compliance','ats','benchmark'];

  function computeSmartSummary(pipeline: PipelineV2 | null) {
    if (!pipeline) return { completed: 0, total: 0, pct: 0, currentStep: '—', currentSmart: { label: '—', class: '' } };
    const order = fullV2Order;
    const artifacts = pipeline.artifacts || {};
    const statuses = (pipeline.statuses || {}) as any;
    let completed = 0;
    for (const step of order) {
      if ((artifacts && artifacts[step]) || statuses[step] === 'complete') completed++;
    }
    const total = order.length;
    const pct = Math.round((completed / Math.max(1, total)) * 100);

    // find current active or first non-complete
    let currentStep: string | undefined = order.find(s => statuses[s] === 'active');
    if (!currentStep) currentStep = order.find(s => statuses[s] !== 'complete');
    if (!currentStep) currentStep = order[order.length - 1];
    const prevIndex = Math.max(0, order.indexOf(currentStep) - 1);
    const prev = order[prevIndex] ? (statuses[order[prevIndex]] || 'pending') : undefined;
    const currentSmart = getSmartStatus(currentStep, statuses[currentStep] || 'pending', artifacts, prev);
    return { completed, total, pct, currentStep, currentSmart };
  }

  // Helper to get summary in template without {@const}
  function getSummary(pipeline: PipelineV2 | null) {
    return computeSmartSummary(pipeline);
  }

  // Helper to read a single step status in template without {@const}
  function getStepStatus(pipeline: PipelineV2 | null, step: any) {
    return (pipeline && (pipeline.statuses as any) && (pipeline.statuses as any)[step.key]) || 'pending';
  }
  
  // Reactive snapshot summary computed from snapshotTarget
  let snapshotSummary: { completed: number; total: number; pct: number; currentStep: string; currentSmart: any } = { completed: 0, total: 0, pct: 0, currentStep: '—', currentSmart: { label: '—', class: '' } };
  $: snapshotSummary = computeSmartSummary(snapshotTarget);

  let atsFillBusy = false;
  async function load(){
    try {
      items = await listPipelinesV2();
      error = null;
      // Best-effort: fill ATS for most recent items so the dashboard shows the latest ATS.
      queueMicrotask(() => { void fillRecentMissingAts(); });
    }
    catch(e:any){ error = e?.message || 'Failed to fetch pipelines'; }
  }
  onMount(() => { load(); });

  function canComputeAts(p: PipelineV2): boolean {
    const a: any = (p.artifacts || {}) as any;
    const jd = a.jd;
    const jdText = (jd && typeof jd === 'object')
      ? (jd.description || jd.descriptionRaw || (jd.extracted && (jd.extracted.description || jd.extracted.descriptionRaw || jd.extracted.raw || jd.extracted.text)))
      : null;
    const hasJd = Boolean((jdText && String(jdText).trim()) || (p.jdId && String(p.jdId).startsWith('manual:') && String(p.jdId).slice('manual:'.length).trim()));

    const hasProfile = Boolean(a.profile && typeof a.profile === 'object' && a.profile.parsed);
    const hasResume = Boolean(
      hasProfile ||
      (a.resume && typeof a.resume === 'object' && a.resume.text) ||
      (p.resumeId && String(p.resumeId).trim())
    );

    return hasJd && hasResume;
  }

  async function fillRecentMissingAts() {
    if (atsFillBusy) return;
    atsFillBusy = true;
    try {
      const recent = (items || []).slice(0, 6);
      const candidates = recent.filter((p) => getAtsPercent(p) === null && canComputeAts(p));
      for (const p of candidates) {
        try {
          const updated = await recomputeAtsV2(p.id);
          items = items.map((it) => (it.id === updated.id ? updated : it));
          if (snapshotTarget?.id === updated.id) snapshotTarget = updated;
        } catch {
          // ignore (missing JD/resume, or backend errors)
        }
      }
    } finally {
      atsFillBusy = false;
    }
  }

  async function handleResumeUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    if (!input.files || !input.files[0]) return;
    
    const file = input.files[0];
    resumeFile = file;
    resumeUploading = true;
    error = null;
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/resume/parse-file', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error('Failed to parse resume');
      
      const data = await response.json();
      resumeId = data.id;
      resumeText = data.text || '';
    } catch(e: any) {
      error = e?.message || 'Failed to upload resume';
      resumeFile = null;
    } finally {
      resumeUploading = false;
    }
  }
  
  async function createWithConfig(){
    if (loading) return; loading = true; error=null;
    try {
      const baseName = (form.name || '').trim() || 'Untitled v2';
      
      // Determine JD source: prefer URL, else manual pasted text.
      // Note: /api/jd/import currently returns a mock id (jd_*) that is not fetchable later,
      // so we must NOT persist that id as pipeline.jdId.
      let jdSource = form.jdUrl?.trim() || undefined;
      if (!jdSource && form.jdDoc?.trim()) jdSource = 'manual:' + form.jdDoc.trim();
      
      const p = await createPipelineV2({ 
        name: baseName, 
        jdId: jdSource,
        resumeId: resumeId || undefined
      });
      
      // Store intake data and resume as artifacts
      const artifacts: any = { 
        intake: { 
          jdSource: form.jdUrl ? 'url' : 'document'
        } 
      };

      // If we imported the JD earlier, attach its extracted content immediately
      if (importedJd) {
        const extracted = importedJd.extracted && typeof importedJd.extracted === 'object' ? importedJd.extracted : null;
        const reqs = Array.isArray(extracted?.requirements) ? extracted.requirements : [];
        artifacts.jd = {
          url: importedJd.sourceUrl || form.jdUrl?.trim() || 'manual',
          title: extracted?.title || baseName,
          description: importedJd.descriptionRaw || form.jdDoc?.trim() || '',
          key_requirements: reqs,
          extracted,
          importedAt: Date.now(),
        };
      }
      
      if (resumeId && resumeText) {
        artifacts.resume = {
          id: resumeId,
          text: resumeText,
          filename: resumeFile?.name || 'resume',
          uploadedAt: Date.now()
        };
      }
      
      await patchPipelineV2(p.id, { artifacts });
      window.location.href = `/app/pipeline-v2/${p.id}`;
    } catch(e:any){ error = e?.message || 'Failed to create pipeline'; }
    finally { loading = false; showCreate = false; }
  }

  function openEdit(p: PipelineV2) {
    editTarget = p;
    editForm.name = p.name || '';
    editForm.jdUrl = p.jdId || '';
    const n = (p.artifacts && (p.artifacts as any).intake && (p.artifacts as any).intake.notes) || '';
    editForm.notes = n;
    showEdit = true; error = null;
  }

  async function removePipeline(p: PipelineV2){
    if (loading) return;
    const ok = window.confirm(`Delete pipeline "${p.name}"? This cannot be undone.`);
    if (!ok) return;
    loading = true; error=null;
    try {
      await deletePipelineV2(p.id);
      // Refresh list
      await load();
    } catch(e:any){ error = e?.message || 'Failed to delete pipeline'; }
    finally { loading = false; }
  }

  async function saveEdit(){
    if (!editTarget) return;
    if (loading) return; loading = true; error=null;
    try {
      const patch: any = {
        name: (editForm.name||'').trim() || editTarget.name,
        jdId: (editForm.jdUrl||'').trim() || null,
        artifacts: { intake: { notes: editForm.notes || '' } }
      };
      const updated = await patchPipelineV2(editTarget.id, patch);
      // Update local list
      items = items.map(it => it.id === updated.id ? updated : it);
      showEdit = false; editTarget = null;
    } catch(e:any){ error = e?.message || 'Failed to save changes'; }
    finally { loading = false; }
  }

  function getAtsPercent(p: PipelineV2): number | null {
    const ats = p?.artifacts && (p.artifacts as any).ats;
    if (!ats || typeof ats !== 'object') return null;
    if (typeof ats.aggregate === 'number') return Math.max(0, Math.min(100, Math.round(ats.aggregate * 100)));
    if (typeof ats.coverage === 'number') return Math.max(0, Math.min(100, Math.round(ats.coverage)));
    if (typeof ats.score === 'number') {
      const v = ats.score;
      return Math.max(0, Math.min(100, Math.round(v <= 1 ? v * 100 : v)));
    }
    return null;
  }

  function getKeywordsFoundCount(p: PipelineV2): number | null {
    const ats = p?.artifacts && (p.artifacts as any).ats;
    if (!ats || typeof ats !== 'object') return null;
    const arr = Array.isArray(ats.matched_keywords) ? ats.matched_keywords : (Array.isArray(ats.matched) ? ats.matched : null);
    return Array.isArray(arr) ? arr.length : null;
  }

  function getKeywordsMissingCount(p: PipelineV2): number | null {
    const ats = p?.artifacts && (p.artifacts as any).ats;
    if (!ats || typeof ats !== 'object') return null;
    const arr = Array.isArray(ats.missing_keywords) ? ats.missing_keywords : (Array.isArray(ats.missing) ? ats.missing : null);
    return Array.isArray(arr) ? arr.length : null;
  }

  function getLastReportScore(p: PipelineV2): number | null {
    const rep = p?.artifacts && (p.artifacts as any).report;
    const data = rep && typeof rep === 'object' ? (rep.data || null) : null;
    const score = data && typeof data === 'object' ? (data.score ?? null) : null;
    return typeof score === 'number' ? score : null;
  }

  function getLastReportAt(p: PipelineV2): string | null {
    const rep = p?.artifacts && (p.artifacts as any).report;
    const ts = rep && typeof rep === 'object' ? (rep.generatedAt ?? null) : null;
    return typeof ts === 'number' ? new Date(ts).toLocaleString() : null;
  }

  let reportBusyById: Record<string, boolean> = {};
  async function generateReportFor(p: PipelineV2) {
    if (!p?.id || reportBusyById[p.id]) return;
    reportBusyById = { ...reportBusyById, [p.id]: true };
    try {
      // If ATS/profile is missing but JD+resume exist, compute ATS first so report generation is reliable.
      if (getAtsPercent(p) === null && canComputeAts(p)) {
        try {
          const updatedForAts = await recomputeAtsV2(p.id);
          items = items.map(it => it.id === updatedForAts.id ? updatedForAts : it);
        } catch {}
      }

      const rep = await getPipelineReport(p.id);
      const reasons = Array.isArray(rep?.reasons) ? rep.reasons : [];
      const sections = rep?.sections && typeof rep.sections === 'object' ? rep.sections : {};
      const text = [
        `Pipeline Report - ${p.name}`,
        '',
        `Score: ${rep?.score ?? 'n/a'}`,
        '',
        'Reasons:',
        reasons.length ? reasons.map((r: string) => `- ${r}`).join('\n') : '(none)',
        '',
        ...Object.entries(sections).flatMap(([k, v]) => [`${k}:`, String(v ?? ''), ''])
      ].join('\n');

      const artifacts = { ...(p.artifacts || {}), report: { data: rep, text, generatedAt: Date.now() } };
      const updated = await patchPipelineV2(p.id, { artifacts });
      items = items.map(it => it.id === updated.id ? updated : it);
    } catch (e: any) {
      error = e?.message || 'Failed to generate report';
    } finally {
      reportBusyById = { ...reportBusyById, [p.id]: false };
    }
  }

</script>

<section class="space-y-4">
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold flex items-center gap-2">Pipelines v2</h1>
    <div class="flex items-center gap-2">
      <a
        href="/app/pipeline-v2/stats"
        class="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-blue-600 text-white border border-blue-700 shadow-sm hover:bg-blue-700 transition"
        title="View extraction statistics"
      >
        <Icon name="layers" size={14} />
        Stats
      </a>
      <button
        on:click={() => load()}
        class="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-white/30 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-800 dark:text-gray-100 shadow-sm hover:bg-white/50 dark:hover:bg-white/20 transition disabled:opacity-60"
        disabled={loading}
        title="Refresh list"
      >
        Refresh
      </button>
      <button
        on:click={openCreateModal}
        class="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-800 dark:text-gray-100 shadow-sm hover:bg-white/60 dark:hover:bg-white/20 transition disabled:opacity-60"
        disabled={loading}
      >
        New pipeline
      </button>
    </div>
  </div>

  {#if error}
    <div class="text-sm text-red-600">{error}</div>
  {/if}

  {#if loading}
    <div>Loading…</div>
  {:else if !items.length}
    <div class="text-gray-600 dark:text-gray-400">No pipelines yet.</div>
  {:else}
    <ul class="grid gap-3">
      {#each items as p}
        <li class="relative border rounded-lg p-3 bg-white/80 backdrop-blur-sm dark:bg-slate-800/70 border-slate-200 dark:border-slate-700">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="font-medium truncate">{p.name}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap mt-0.5">{new Date(p.createdAt).toLocaleString()}</div>
              <div class="text-xs text-slate-600 dark:text-slate-400 mt-1">
                ATS: {getAtsPercent(p) === null ? '—' : `${getAtsPercent(p)}%`}
                {#if getKeywordsFoundCount(p) !== null}
                  <span class="ml-2">• Keywords found: {getKeywordsFoundCount(p)}</span>
                {/if}
                {#if getKeywordsMissingCount(p) !== null}
                  <span class="ml-2">• Missing: {getKeywordsMissingCount(p)}</span>
                {/if}
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Progress: {getSummary(p).pct}% • {getSummary(p).currentStep} • {getSummary(p).currentSmart.label}
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Last report: {getLastReportScore(p) === null ? '—' : `${getLastReportScore(p)}%`}
                {#if getLastReportAt(p)}
                  <span class="ml-2">• {getLastReportAt(p)}</span>
                {/if}
              </div>
            </div>
          </div>

          <div class="mt-3 flex items-center justify-end gap-3">
              <button
                class="inline-flex items-center text-xs px-2.5 py-1.5 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-800 dark:text-gray-100 shadow-sm hover:bg-white/60 dark:hover:bg-white/20 transition disabled:opacity-60"
                on:click|stopPropagation={() => generateReportFor(p)}
                disabled={!!reportBusyById[p.id]}
                title="Generate and save report"
              >
                {reportBusyById[p.id] ? 'Generating…' : 'Generate report'}
              </button>
              <a
                href={`/app/pipeline-v2/${p.id}`}
                class="inline-flex items-center text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-blue-600 text-white border border-blue-700 shadow-sm hover:bg-blue-700 transition"
                title="Open overview"
              >Open</a>
              <button
                class="inline-flex items-center text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-800 dark:text-gray-100 shadow-sm hover:bg-white/60 dark:hover:bg-white/20 transition"
                on:click|stopPropagation={() => openSnapshot(p)}
                title="Quick view"
              >View</button>
              <button
                class="inline-flex items-center justify-center w-8 h-8 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-white/60 dark:hover:bg-white/20"
                on:click={() => openEdit(p)}
                title="Edit"
              >
                <Icon name="edit" size={16} />
              </button>
              <button
                class="inline-flex items-center justify-center w-8 h-8 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300 hover:bg-white/60 dark:hover:bg-white/20 disabled:opacity-50"
                on:click={() => removePipeline(p)}
                title="Delete"
                disabled={loading}
              >
                <Icon name="trash" size={16} />
              </button>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
  {#if showCreate}
    <!-- Modal overlay -->
    <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-40" on:click={() => { showCreate=false; resetForm(); }}></div>
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="w-full max-w-4xl my-8 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-2xl" on:click|stopPropagation>
        <!-- Header -->
        <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-slate-800 dark:to-slate-800 rounded-t-xl">
          <div>
            <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Create New Pipeline</h2>
            <p class="text-xs text-slate-600 dark:text-slate-400 mt-0.5">Set up your resume and job description analysis</p>
          </div>
          <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition" on:click={() => { showCreate=false; resetForm(); }}>
            <Icon name="x" size={20} />
          </button>
        </div>
        
        <!-- Content - Two Column Layout -->
        <div class="p-6 max-h-[calc(100vh-16rem)] overflow-y-auto">
          {#if error}
            <div class="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
              <Icon name="alert-circle" size={16} />
              {error}
            </div>
          {/if}
          
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Left Column: Basic Info -->
            <div class="space-y-4">
              <div>
                <h3 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                  <Icon name="info" size={16} />
                  Pipeline Information
                </h3>
                <div class="space-y-3">
                  <label class="block">
                    <span class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">Pipeline Name *</span>
                    <input 
                      class="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" 
                      bind:value={form.name} 
                      placeholder="e.g., Senior Backend Engineer at TechCorp" 
                    />
                  </label>
                </div>
              </div>
              
              <!-- Resume Upload -->
              <div>
                <h3 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                  <Icon name="file-text" size={16} />
                  Resume Upload
                </h3>
                <div class="space-y-3">
                  <label class="block">
                    <span class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">Upload Resume (PDF or DOCX)</span>
                    <div class="relative">
                      <input 
                        type="file" 
                        accept=".pdf,.docx,.doc" 
                        class="w-full text-sm border border-slate-300 dark:border-slate-600 rounded-lg cursor-pointer
                               file:mr-4 file:py-2 file:px-4 file:rounded-l-lg file:border-0 
                               file:text-sm file:font-medium file:cursor-pointer
                               file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 
                               dark:file:bg-blue-900/30 dark:file:text-blue-300 dark:hover:file:bg-blue-900/50
                               bg-white dark:bg-slate-800 transition" 
                        on:change={handleResumeUpload}
                        disabled={resumeUploading}
                      />
                    </div>
                  </label>
                  
                  {#if resumeUploading}
                    <div class="text-xs text-blue-600 dark:text-blue-400 flex items-center gap-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <svg class="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path></svg>
                      <span>Uploading and parsing resume...</span>
                    </div>
                  {/if}
                  
                  {#if resumeFile && resumeId}
                    <div class="text-xs text-green-600 dark:text-green-400 flex items-center gap-2 p-2 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                      <Icon name="check" size={14} />
                      <span class="font-medium">{resumeFile.name}</span>
                      <span class="text-green-500 dark:text-green-500">• Uploaded successfully</span>
                    </div>
                  {/if}
                </div>
              </div>
            </div>
            
            <!-- Right Column: JD Source -->
            <div class="space-y-4">
              <div>
                <h3 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                  <Icon name="building" size={16} />
                  Job Description Source
                </h3>
                <div class="space-y-3">
                  <label class="block">
                    <span class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">JD URL (Optional)</span>
                    <div class="flex items-center gap-2">
                      <input 
                        class="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" 
                        bind:value={form.jdUrl} 
                        placeholder="https://jobs.lever.co/company/job-id" 
                        on:blur={() => importJdUrl(form.jdUrl?.trim())}
                      />
                      {#if jdImporting}
                        <div class="text-xs text-slate-500">Importing…</div>
                      {:else if importedJdId}
                        <div class="text-xs text-green-600 flex items-center gap-1">
                          <Icon name="check" size={14} /> Imported
                        </div>
                      {/if}
                    </div>
                  </label>
                  {#if form.jdUrl?.trim()}
                  <div class="text-xs mt-1">
                    <a class="inline-flex items-center gap-1 text-blue-600 hover:underline" href={form.jdUrl} target="_blank" rel="noopener noreferrer">
                      <Icon name="external-link" size={12} /> Open JD link
                    </a>
                  </div>
                  {/if}
                  
                  <div class="relative">
                    <div class="absolute inset-0 flex items-center">
                      <div class="w-full border-t border-slate-300 dark:border-slate-600"></div>
                    </div>
                    <div class="relative flex justify-center text-xs">
                      <span class="px-2 bg-white dark:bg-slate-900 text-slate-500">OR</span>
                    </div>
                  </div>
                  
                  <label class="block">
                    <span class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">Paste JD Text</span>
                    <textarea 
                      class="w-full border rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition font-mono"
                      bind:value={form.jdDoc} 
                      placeholder="Paste the job description here..."
                      rows="12"
                      disabled={!!form.jdUrl?.trim()}
                    ></textarea>
                  </label>
                  
                  {#if form.jdUrl?.trim()}
                    <div class="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5 p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                      <Icon name="info" size={12} />
                      <span>URL takes precedence over pasted text</span>
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          </div>
          
          
        </div>
        
        <!-- Footer -->
        <div class="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50 rounded-b-xl">
          <div class="text-xs text-slate-500 dark:text-slate-400">
            {#if resumeFile && (form.jdUrl?.trim() || form.jdDoc?.trim())}
              <span class="text-green-600 dark:text-green-400 flex items-center gap-1">
                <Icon name="check" size={14} />
                Ready to create
              </span>
            {:else}
              <span>Upload resume and provide JD to continue</span>
            {/if}
          </div>
          <div class="flex items-center gap-3">
            <button 
              class="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition" 
              on:click={() => { showCreate=false; resetForm(); }}
            >
              Cancel
            </button>
            <button 
              class="px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg shadow-blue-500/30 flex items-center gap-2" 
              disabled={loading || !resumeFile || (!form.jdUrl?.trim() && !form.jdDoc?.trim())} 
              on:click={createWithConfig}
            >
              {#if loading}
                <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path></svg>
                Creating...
              {:else}
                <Icon name="arrow-right" size={16} />
                Create Pipeline
              {/if}
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}

  {#if showEdit && editTarget}
    <!-- Edit modal overlay -->
    <div class="fixed inset-0 bg-black/40 z-40" on:click={() => { showEdit=false; editTarget=null; }}></div>
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="w-full max-w-lg rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-lg" on:click|stopPropagation>
        <div class="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div class="font-medium">Edit pipeline</div>
          <button class="text-sm text-gray-500" on:click={() => { showEdit=false; editTarget=null; }}>✕</button>
        </div>
        <div class="p-4 space-y-3">
          <label class="block">
            <span class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Name</span>
            <input class="w-full border rounded px-2 py-1.5 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" bind:value={editForm.name} />
          </label>
          <label class="block">
            <span class="block text-xs text-gray-600 dark:text-gray-400 mb-1">JD URL or ID</span>
            <input class="w-full border rounded px-2 py-1.5 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" bind:value={editForm.jdUrl} />
          </label>
          <label class="block">
            <span class="block text-xs text-gray-600 dark:text-gray-400 mb-1">Notes</span>
            <textarea class="w-full border rounded px-2 py-1.5 min-h-24 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" bind:value={editForm.notes} placeholder="Optional notes for this pipeline..."></textarea>
          </label>
        </div>
        <div class="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex items-center gap-2 justify-end">
          <button class="px-3 py-1.5 rounded border" on:click={() => { showEdit=false; editTarget=null; }}>Cancel</button>
          <button class="px-3 py-1.5 rounded bg-blue-600 text-white disabled:opacity-50" disabled={loading} on:click={saveEdit}>{loading? 'Saving…' : 'Save changes'}</button>
        </div>
      </div>
    </div>
  {/if}
  
  {#if showSnapshot && snapshotTarget}
    <div class="fixed inset-0 bg-black/40 z-40" on:click={() => { showSnapshot=false; snapshotTarget=null; snapshotReport=null; }}></div>
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="w-full max-w-sm md:max-w-md max-h-[calc(100vh-8rem)] overflow-y-auto rounded-lg border bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 shadow-lg p-4" on:click|stopPropagation>
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-sm font-semibold">{snapshotTarget.name}</div>
            <div class="text-xs text-slate-500">Progress snapshot</div>
          </div>
          <button class="text-sm text-slate-400 hover:text-slate-600" on:click={() => { showSnapshot=false; snapshotTarget=null; snapshotReport=null; }}>✕</button>
        </div>

        <div class="mt-3 text-xs space-y-2">
          <div class="mt-2">
            <div class="text-xs text-slate-600 mb-1">ATS</div>
            <div class="text-sm font-semibold">{snapshotAtsPct === null ? '—' : `${snapshotAtsPct}%`}</div>
          </div>

          <div class="mt-3">
            <div class="text-xs text-slate-600 mb-1">Last Report</div>
            {#if snapshotLoading}
              <div class="text-xs text-slate-500">Loading…</div>
            {:else if snapshotError}
              <div class="text-xs text-amber-600">{snapshotError}</div>
            {:else if snapshotReport}
              <div class="text-sm font-medium">Score: {snapshotReport.score}%</div>
              <div class="text-xs text-slate-500">{(snapshotReport.reasons || []).join('; ')}</div>
            {:else}
              <div class="text-xs text-slate-500">No report available</div>
            {/if}
          </div>

          <div class="mt-3 flex items-center justify-end gap-2">
            <a class="text-xs text-blue-600 hover:underline" href={`/app/pipeline-v2/${snapshotTarget.id}`}>Open full</a>
          </div>
        </div>
      </div>
    </div>
  {/if}
</section>
