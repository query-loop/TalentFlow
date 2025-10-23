<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getPipelineV2, patchPipelineV2, runPipelineV2, type PipelineV2 } from '$lib/pipelinesV2';
  let pipe: PipelineV2 | null = null;
  let error: string | null = null;
  $: id = $page.params.id;
  async function load(){ try { pipe = await getPipelineV2(id); } catch(e:any){ error = e?.message || 'Failed to load'; }}
  onMount(load);
  
  const v2Steps = [
    { key: 'intake', label: 'Intake' },
    { key: 'jd', label: 'JD' },
    { key: 'profile', label: 'Profile' },
    { key: 'analysis', label: 'Analysis' },
    { key: 'ats', label: 'ATS' },
    { key: 'actions', label: 'Actions' },
    { key: 'export', label: 'Export' }
  ];

  const stepDetails: Record<string, { desc: string; implemented: string[] }> = {
    intake: { desc: 'Collect intake data: JD source, resume upload, notes.', implemented: ['Resume upload & parsing', 'JD URL or pasted text', 'Artifacts stored on pipeline'] },
    jd: { desc: 'Process job description into consumable blocks.', implemented: ['Fetch JD from URL', 'Parse text into sections', 'Store JD artifact'] },
    profile: { desc: 'Build candidate profile from resume & JD.', implemented: ['Extract skills/summary', 'Associate resume artifact'] },
    analysis: { desc: 'Analyze JD vs profile, surface gaps and recommendations.', implemented: ['Keyword tally', 'Suggested highlights', 'Store analysis notes'] },
    ats: { desc: 'Run ATS compatibility scan and tips.', implemented: ['ATS scoring', 'Formatting tips', 'Save last score locally'] },
    actions: { desc: 'Suggested actions and integrations.', implemented: ['Generate resume', 'Copy/download', 'Integration hooks'] },
    export: { desc: 'Export final artifacts (PDF/DOCX).', implemented: ['Placeholder export flows', 'Apply theme to output'] }
  };

  let busy = false;

  // Helper to refresh pipeline after patch
  async function refresh() {
    if (!pipe) return;
    pipe = await getPipelineV2(pipe.id);
  }

  // Run ATS scan using available resume text or JD text
  async function runAtsScan() {
    if (!pipe) return;
    busy = true; error = null;
    try {
      let text = '';
      if (pipe.artifacts && (pipe.artifacts as any).resume && (pipe.artifacts as any).resume.text) {
        text = (pipe.artifacts as any).resume.text;
      } else if (pipe.jdId && pipe.jdId.startsWith('manual:')) {
        text = pipe.jdId.replace(/^manual:/, '');
      } else if (pipe.artifacts && (pipe.artifacts as any).jd && (pipe.artifacts as any).jd.description) {
        text = (pipe.artifacts as any).jd.description as string;
      }
      if (!text || !text.trim()) throw new Error('No resume or JD text available for ATS scan');

      const res = await fetch('/api/mock/ats', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ text }) });
      if (!res.ok) throw new Error('ATS endpoint failed');
      const data = await res.json();

      // Patch pipeline artifacts with ATS result
      const artifacts = { ...(pipe.artifacts || {}), ats: { score: data.score, tips: data.tips, ranAt: Date.now() } };
      await patchPipelineV2(pipe.id, { artifacts });
      await refresh();
    } catch (e:any) {
      error = e?.message || String(e);
    } finally { busy = false; }
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
      await refresh();
    } catch (e:any) {
      runLogs = [e?.message || String(e)];
    } finally { runBusy = false; }
  }

  // Generate tailored resume snippet using mock generate endpoint
  async function runGenerate() {
    if (!pipe) return;
    busy = true; error = null;
    try {
      // prefer JD text from artifacts or manual jdId
      let jobText = '';
      if (pipe.artifacts && (pipe.artifacts as any).jd && (pipe.artifacts as any).jd.description) jobText = (pipe.artifacts as any).jd.description as string;
      else if (pipe.jdId && pipe.jdId.startsWith('manual:')) jobText = pipe.jdId.replace(/^manual:/, '');
      if (!jobText || !jobText.trim()) throw new Error('No JD text available to generate from');

      const res = await fetch('/api/mock/generate', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ job: jobText }) });
      if (!res.ok) throw new Error('Generate endpoint failed');
      const data = await res.json();

      const gen = { summary: data.summary, skills: data.skills, experience: data.experience, generatedAt: Date.now() };
      const artifacts = { ...(pipe.artifacts || {}), generated: gen };
      await patchPipelineV2(pipe.id, { artifacts });
      await refresh();
    } catch (e:any) {
      error = e?.message || String(e);
    } finally { busy = false; }
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
        <div class="text-sm text-slate-500 mt-1">Pipeline overview · <span class="font-mono">{pipe.id}</span></div>
      </div>
      <div class="flex items-center gap-2">
        <a href="/app/pipelines-v2" class="text-sm text-gray-600 hover:text-gray-800 dark:text-slate-300">All v2 pipelines</a>
        <a href={`/app/pipeline-v2/stats`} class="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"> 
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h3v8H3zM10 8h3v12h-3zM17 4h3v16h-3z" /></svg>
          Stats
        </a>
      </div>
    </div>
    <div class="border rounded-lg p-4 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
      <div class="flex items-center justify-between gap-4">
        <div>
          <div class="text-xs text-slate-600">ID: <span class="font-mono text-xs text-slate-700 dark:text-slate-300">{pipe.id}</span></div>
          <div class="text-sm text-slate-600 mt-1">Use the step navigation above to move through the pipeline.</div>
        </div>
        <div class="text-sm text-slate-700 dark:text-slate-200">
          {#if pipe.statuses}
            {@const completed = Object.values(pipe.statuses).filter(s => s === 'complete').length}
            {@const total = Object.keys(pipe.statuses).length || 7}
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-sm">
              <span class="text-xs text-slate-500">Steps</span>
              <span class="font-medium">{completed}/{total}</span>
            </div>
          {/if}
        </div>
      </div>
    </div>
    <div class="mt-4 grid gap-3">
      <div class="flex items-center gap-3">
        <button class="btn btn-primary" on:click={runFullPipeline} disabled={runBusy || busy}> {runBusy ? 'Running…' : 'Run full pipeline'} </button>
        <button class="btn" on:click={refresh}>Refresh</button>
      </div>
      {#each v2Steps as s, i}
        <div class="border rounded p-3 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class={`w-6 h-6 rounded-full flex items-center justify-center text-sm ${pipe.statuses && (pipe.statuses as any)[s.key] === 'complete' ? 'bg-emerald-600 text-white' : (pipe.statuses && (pipe.statuses as any)[s.key] === 'active' ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-slate-700 text-gray-800 dark:text-gray-200')}`}>{i+1}</div>
              <div>
                <div class="font-medium">{s.label}</div>
                <div class="text-xs text-gray-500">{stepDetails[s.key].desc}</div>
              </div>
            </div>
            <div class="text-xs text-gray-500">{(pipe.statuses && (pipe.statuses as any)[s.key]) || 'pending'}</div>
          </div>
          <div class="mt-2 text-sm">
            <div class="font-medium text-xs mb-1">Implemented</div>
            <ul class="list-disc ml-4 text-xs space-y-1">
              {#each stepDetails[s.key].implemented as feat}
                <li>{feat}</li>
              {/each}
            </ul>
          </div>
        </div>
        {#if s.key === 'actions' && pipe?.artifacts?.generated}
          <div class="mt-2 text-xs text-gray-600">Generated preview: {(pipe.artifacts as any).generated.resume_text?.slice(0,200) || '(none)'}</div>
        {/if}
      {/each}
      {#if runLogs && runLogs.length}
        <div class="border rounded p-3 bg-black text-white mt-4">
          <div class="font-medium">Run logs</div>
          <ul class="text-xs mt-2 list-disc ml-4">
            {#each runLogs as rl}
              <li>{rl}</li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
  </div>
{/if}
