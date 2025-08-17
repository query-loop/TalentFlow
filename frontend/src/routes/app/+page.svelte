<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { onMount } from 'svelte';
  let backendOk = false;
  let endpoints: Array<{ method: string; path: string; description: string }>= [];
  let companiesTop: Array<{ name: string; matchScore: number; roles: string[]; reason: string }>= [];
  // extended type when fetched now includes logo + metrics in mock
  let loading = true;
  let err = '';
  // Theme removed: use default light styles

  // Lightweight metrics (from localStorage when available)
  let endpointsCount = 0;
  let companiesCount = 0;
  let lastGeneratedAt: string | null = null;
  let lastAtsScore: number | null = null;
  let lastKeywordsCount: number | null = null;
  let recent: Array<{ t: string; when: string }>= [];
  // Recent generated resumes (from generate page)
  type SavedResume = { id: string; name: string; when: number; job?: string; result: { summary?: string; skills?: string[]; experience?: string[] } };
  let recentResumes: SavedResume[] = [];
  // Quick tasks config and drag-sort state
  type QuickTask = { id: string; label: string; href: string; icon: any };
  let quickTasks: QuickTask[] = [
  { id: 'extract',  label: 'Extract a JD',     href: '/app/extract',  icon: 'tag' },
    { id: 'generate', label: 'Generate a resume', href: '/app/generate', icon: 'sparkles' },
    { id: 'ats',      label: 'Check ATS score',   href: '/app/ats',      icon: 'shield-check' },
    { id: 'keywords', label: 'Run keyword analysis', href: '/app/keywords', icon: 'tag' },
    { id: 'themes',   label: 'Choose a theme',    href: '/app/themes',   icon: 'palette' }
  ];
  let draggingTaskId: string | null = null;
  function saveQuickTasksOrder() {
    const ids = quickTasks.map(q => q.id);
    localStorage.setItem('tf_quick_tasks_order', JSON.stringify(ids));
  }
  function loadQuickTasksOrder() {
    try {
      const raw = localStorage.getItem('tf_quick_tasks_order');
      if (!raw) return;
      const order = JSON.parse(raw) as string[];
      const map = new Map(quickTasks.map((q, idx) => [q.id, { q, idx }]));
      quickTasks = order
        .map(id => map.get(id)?.q)
        .filter(Boolean) as QuickTask[];
      // Append any new tasks not in saved order
      const remaining = [...map.values()].filter(v => !order.includes(v.q.id)).sort((a,b) => a.idx - b.idx).map(v => v.q);
      if (remaining.length) quickTasks = [...quickTasks, ...remaining];
    } catch {}
  }
  function onDragStart(e: DragEvent, id: string) {
    draggingTaskId = id;
    e.dataTransfer?.setData('text/plain', id);
    e.dataTransfer?.setDragImage?.(document.createElement('div'), 0, 0);
  }
  function onDragOver(e: DragEvent) { e.preventDefault(); }
  function onDrop(e: DragEvent, overId: string) {
    e.preventDefault();
    const src = draggingTaskId || e.dataTransfer?.getData('text/plain');
    if (!src || src === overId) return;
    const from = quickTasks.findIndex(q => q.id === src);
    const to = quickTasks.findIndex(q => q.id === overId);
    if (from === -1 || to === -1) return;
    const copy = [...quickTasks];
    const [moved] = copy.splice(from, 1);
    copy.splice(to, 0, moved);
    quickTasks = copy;
    saveQuickTasksOrder();
    draggingTaskId = null;
  }

  // Group recent activity by local day
  type RecentGroup = { date: string; items: { t: string; when: string }[] };
  let groupedRecent: RecentGroup[] = [];
  function regroupRecent() {
    const groups = new Map<string, { t: string; when: string }[]>();
    for (const r of (recent || []).slice(0, 20).sort((a,b) => +new Date(b.when) - +new Date(a.when))) {
      const key = new Date(r.when).toLocaleDateString();
      const arr = groups.get(key) || [];
      arr.push(r);
      groups.set(key, arr);
    }
    groupedRecent = Array.from(groups.entries()).map(([date, items]) => ({ date, items }));
  }

  // Trim activity text to a very short summary (1 sentence, strict length)
  function trimRecentText(text: string): string {
    const clean = (text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return '';
    const maxChars = 120;
    const firstSent = clean.split(/(?<=[.!?])\s+/)[0] || clean;
    let out = firstSent;
    if (out.length > maxChars) {
      out = out.slice(0, maxChars).replace(/\s+\S*$/, '').trimEnd() + '…';
    }
    return out;
  }

  // Pipeline state
  type StepKey = 'extract' | 'generate' | 'keywords' | 'ats' | 'export' | 'save';
  type StepStatus = 'pending' | 'active' | 'complete';
  type PipelineStep = { key: StepKey; label: string; icon: any; link: string; desc: string };
  const pipelineSteps: PipelineStep[] = [
    { key: 'extract',  label: 'Extract JD', icon: 'tag',          link: '/app/extract',   desc: 'Paste or upload job description' },
    { key: 'generate', label: 'Generate',   icon: 'sparkles',     link: '/app/generate',  desc: 'Create a theme-aware draft' },
    { key: 'keywords', label: 'Keywords',   icon: 'tag',          link: '/app/keywords',  desc: 'Analyze terms and gaps' },
    { key: 'ats',      label: 'ATS',        icon: 'shield-check', link: '/app/ats',       desc: 'Score and get tips' },
    { key: 'export',   label: 'Export',     icon: 'layers',       link: '/app/themes',    desc: 'Export to PDF/DOCX' },
    { key: 'save',     label: 'Save',       icon: 'folder',       link: '/app/library',   desc: 'Store in your Library' }
  ];
  type PipelineInstance = {
    id: string;
    name: string;
    createdAt: number;
    statuses: Record<StepKey, StepStatus>;
  };
  let pipelines: PipelineInstance[] = [];
  let activePipelineId: string | null = null;
  let recentPipelines: PipelineInstance[] = [];
  // UI state for expand/collapse of the recent pipelines section
  let pipelinesExpanded = true;
  function togglePipelines() {
    pipelinesExpanded = !pipelinesExpanded;
  }

  function defaultStatuses(): Record<StepKey, StepStatus> {
    return { extract: 'active', generate: 'pending', keywords: 'pending', ats: 'pending', export: 'pending', save: 'pending' };
  }
  function getActivePipeline(): PipelineInstance | null {
    return pipelines.find(p => p.id === activePipelineId) || null;
  }
  function setActivePipeline(id: string) {
    activePipelineId = id;
    localStorage.setItem('tf_active_pipeline', id);
  }

  function loadPipelines() {
    try {
      const raw = localStorage.getItem('tf_pipelines');
      pipelines = raw ? JSON.parse(raw) : [];
    } catch { pipelines = []; }
    if (!pipelines.length) {
      const first: PipelineInstance = { id: crypto.randomUUID?.() || String(Date.now()), name: 'Pipeline 1', createdAt: Date.now(), statuses: defaultStatuses() };
      pipelines = [first];
      activePipelineId = first.id;
      savePipelines();
    }
    const savedActive = localStorage.getItem('tf_active_pipeline');
    if (savedActive && pipelines.some(p => p.id === savedActive)) activePipelineId = savedActive;
    if (!activePipelineId) activePipelineId = pipelines[0]?.id || null;
  }
  function savePipelines() {
    localStorage.setItem('tf_pipelines', JSON.stringify(pipelines));
  }
  function firstIncompleteIndex(statuses: Record<StepKey, StepStatus>) {
    return pipelineSteps.findIndex(s => statuses[s.key] !== 'complete');
  }
  function ensureSingleActive(statuses: Record<StepKey, StepStatus>) {
    const idx = firstIncompleteIndex(statuses);
    (Object.keys(statuses) as StepKey[]).forEach(k => statuses[k] = statuses[k] === 'complete' ? 'complete' : 'pending');
    if (idx >= 0) statuses[pipelineSteps[idx].key] = 'active';
  }
  function applyAutoCompletionFromSignals(statuses: Record<StepKey, StepStatus>) {
    // Heuristics from existing localStorage metrics
    if (lastGeneratedAt) statuses.generate = 'complete';
    if (lastKeywordsCount && lastKeywordsCount > 0) statuses.keywords = 'complete';
    if (lastAtsScore !== null) statuses.ats = 'complete';
    ensureSingleActive(statuses);
  }
  function markActiveCompleteAndNext() {
    const p = getActivePipeline();
    if (!p) return;
    const idx = pipelineSteps.findIndex(s => p.statuses[s.key] === 'active');
    if (idx === -1) return;
    p.statuses[pipelineSteps[idx].key] = 'complete';
    const nextIdx = pipelineSteps.slice(idx + 1).findIndex(s => p.statuses[s.key] !== 'complete');
    if (nextIdx !== -1) {
      (Object.keys(p.statuses) as StepKey[]).forEach(k => p.statuses[k] = p.statuses[k] === 'complete' ? 'complete' : 'pending');
      p.statuses[pipelineSteps[idx + 1 + nextIdx].key] = 'active';
    }
    savePipelines();
  }
  function resetPipeline() {
    const p = getActivePipeline();
    if (!p) return;
    p.statuses = defaultStatuses();
    savePipelines();
  }
  function newPipeline() {
    const id = crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
    const name = `Pipeline ${pipelines.length + 1}`;
    const p: PipelineInstance = { id, name, createdAt: Date.now(), statuses: defaultStatuses() };
    pipelines = [p, ...pipelines];
    setActivePipeline(id);
    savePipelines();
  }
  function progressOf(statuses: Record<StepKey, StepStatus>) {
    const completed = pipelineSteps.filter(s => statuses[s.key] === 'complete').length;
    const total = pipelineSteps.length;
    const percent = Math.round((completed / total) * 100);
    return { completed, total, percent };
  }

  // Derive top 3 most recent pipelines
  $: recentPipelines = pipelines.length ? [...pipelines].sort((a,b) => b.createdAt - a.createdAt).slice(0,3) : [];

  onMount(async () => {
    try {
      const [endRes, compRes] = await Promise.allSettled([
        fetch('/api/endpoints'),
        fetch('/api/mock/companies')
      ]);
      if (endRes.status === 'fulfilled') {
        backendOk = endRes.value.ok;
        endpoints = backendOk ? await endRes.value.json() : [];
        endpointsCount = endpoints.length;
      }
      if (compRes.status === 'fulfilled' && compRes.value.ok) {
        companiesTop = await compRes.value.json();
        companiesCount = companiesTop.length;
      }
    } catch (e: any) { err = e?.message ?? String(e); }

  // Theme removed
    lastGeneratedAt = localStorage.getItem('tf_last_generated_at');
    const ats = localStorage.getItem('tf_last_ats_score');
    lastAtsScore = ats ? Number(ats) : null;
    const kw = localStorage.getItem('tf_last_keywords_count');
    lastKeywordsCount = kw ? Number(kw) : null;
    try { recent = JSON.parse(localStorage.getItem('tf_recent_actions') || '[]'); } catch {}
  // Load recent resumes
  try { recentResumes = (JSON.parse(localStorage.getItem('tf_recent_resumes') || '[]') as SavedResume[]).slice(0,25); } catch {}
  loadQuickTasksOrder();
  regroupRecent();

  // Pipelines initialize
  loadPipelines();
  // Apply heuristics to the active pipeline only
  const ap = getActivePipeline();
  if (ap) {
    applyAutoCompletionFromSignals(ap.statuses);
    savePipelines();
  }

    loading = false;
  });

  $: regroupRecent();

  function openInGenerator(r: SavedResume) {
    try { localStorage.setItem('tf_selected_resume', JSON.stringify(r)); } catch {}
    location.href = '/app/generate';
  }
</script>

<section class="space-y-8">
  <!-- Hero -->
  <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
    <div>
      <h1 class="text-2xl font-semibold flex items-center gap-2"><Icon name="home"/> Resume Curation</h1>
      <p class="text-sm text-gray-600 dark:text-gray-300">Generate, analyze, and refine resumes tailored to each job.</p>
    </div>
  </div>

  

  <!-- Metrics -->
  <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3">
      <div class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400"><Icon name="building" size={14}/> Companies you top at</div>
      <div class="text-xl font-semibold">{loading ? '…' : companiesCount || '—'}</div>
    </div>
    <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3">
      <div class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400"><Icon name="clock" size={14}/> Last generated</div>
      <div class="text-xl font-semibold">{lastGeneratedAt ? new Date(lastGeneratedAt).toLocaleString() : '—'}</div>
    </div>
    <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3">
      <div class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400"><Icon name="shield-check" size={14}/> Last ATS score</div>
      <div class="text-xl font-semibold">{lastAtsScore !== null ? `${lastAtsScore}%` : '—'}</div>
    </div>
    <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3">
      <div class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400"><Icon name="tag" size={14}/> Keywords found</div>
      <div class="text-xl font-semibold">{lastKeywordsCount ?? '—'}</div>
    </div>
  </div>

  <!-- Pipelines (recent 3, fixed layout, no scroll) -->
  <div id="pipelines" class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm text-gray-700 dark:text-gray-200">Recent curation pipelines</div>
      <div class="flex items-center gap-2">
        <a href="/app/pipelines" class="inline-flex items-center text-xs px-2.5 py-1 border border-slate-200 dark:border-slate-700 rounded hover:bg-gray-50 dark:hover:bg-slate-700 transition">Show all</a>
        <button class="inline-flex items-center justify-center w-7 h-7 border border-slate-200 dark:border-slate-700 rounded hover:bg-gray-50 dark:hover:bg-slate-700 transition"
                aria-label="Toggle recent curation pipelines"
                aria-expanded={pipelinesExpanded}
                on:click={togglePipelines}>
          <span class={`transition ${pipelinesExpanded ? 'rotate-90' : ''}`}><Icon name="arrow-right" size={12} /></span>
        </button>
      </div>
    </div>
    {#if pipelinesExpanded}
      {#if recentPipelines.length}
        <div class="grid gap-3">
          {#each recentPipelines as p (p.id)}
            <div class="border rounded-lg p-3 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
              <div class="flex items-center justify-between mb-1">
                <div class="font-medium truncate">{p.name}</div>
              </div>
              <div class="mt-2 flex items-center gap-3">
                <div class="flex items-center gap-2 flex-1 flex-wrap overflow-visible whitespace-normal pr-1">
                  {#each pipelineSteps as s, i (s.key)}
                    {@const st = p.statuses[s.key]}
                    <div class="relative group">
                      <div class={`whitespace-nowrap inline-flex items-center gap-2 px-2.5 py-1.5 rounded-full border text-xs transition cursor-default select-none ${st === 'complete' ? 'border-emerald-300 text-emerald-700 dark:border-emerald-700 dark:text-emerald-300 bg-emerald-50/40 dark:bg-emerald-900/20' : st === 'active' ? 'border-indigo-300 text-indigo-700 dark:border-indigo-700 dark:text-indigo-300 bg-indigo-50/40 dark:bg-indigo-900/20' : 'border-slate-200 text-gray-700 dark:border-slate-700 dark:text-gray-200'} hover:bg-gray-50/70 dark:hover:bg-slate-700/40`}>
                        <span class={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] ${st === 'complete' ? 'bg-emerald-600 text-white' : st === 'active' ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300'}`}>{i+1}</span>
                        <span class="font-medium">{s.label}</span>
                      </div>
                      <!-- Hover card (hover-only info, non-clickable) -->
                      <div class="absolute left-0 top-full mt-2 z-30 invisible opacity-0 group-hover:visible group-hover:opacity-100 transition min-w-[220px] max-w-[280px] p-3 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow pointer-events-none">
                        <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Step {i+1}</div>
                        <div class="font-medium mb-1">{s.label}</div>
                        <div class="text-sm text-gray-700 dark:text-gray-200">{s.desc}</div>
                        <div class="mt-2"><span class={`text-[10px] px-1.5 py-0.5 rounded ${st === 'complete' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : st === 'active' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300' : 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-gray-300'}`}>{st === 'complete' ? 'Complete' : st === 'active' ? 'In progress' : 'Pending'}</span></div>
                      </div>
                    </div>
                    {#if i < pipelineSteps.length - 1}
                      <span class="text-gray-400 dark:text-gray-500"><Icon name="arrow-right" size={14}/></span>
                    {/if}
                  {/each}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 select-none">
                  Hover a step to see details
                </div>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="text-sm text-gray-600 dark:text-gray-400">No pipelines yet.</div>
      {/if}
    {/if}
  </div>

  <!-- Recent generated resumes -->
  <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm text-gray-700 dark:text-gray-200">Recent generated resumes</div>
      {#if recentResumes && recentResumes.length > 3}
        <div class="flex items-center gap-2">
          <a href="/app/resumes" class="inline-flex items-center text-xs px-2.5 py-1 border border-slate-200 dark:border-slate-700 rounded hover:bg-gray-50 dark:hover:bg-slate-700 transition">Show all</a>
        </div>
      {/if}
    </div>
    {#if recentResumes && recentResumes.length}
      <ul class="divide-y divide-slate-200 dark:divide-slate-700">
        {#each recentResumes.slice(0,5) as r}
          <li class="py-2 flex items-center gap-3">
            <div class="flex-1 min-w-0">
              <div class="font-medium truncate">{r.name}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">{new Date(r.when).toLocaleString()}</div>
            </div>
            <div class="flex items-center gap-2">
              <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={() => openInGenerator(r)}>View</button>
              {#if (r.result && (r.result.summary || r.result.skills || r.result.experience))}
                <a href="/app/generate" class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700">Edit</a>
              {/if}
            </div>
          </li>
        {/each}
      </ul>
    {:else}
      <div class="text-sm text-gray-600 dark:text-gray-400">
        No resumes generated yet.
        <a href="/app/generate" class="text-blue-600 hover:underline">Generate your first resume</a>.
      </div>
    {/if}
  </div>

  <!-- Top companies you top at (moved below pipelines) -->
  {#if companiesTop.length}
  <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm text-gray-700 dark:text-gray-200">Top companies you top at</div>
      <a href="/app/companies" class="text-xs text-blue-600 hover:underline">View all</a>
    </div>
    <ul class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {#each companiesTop.slice(0,4) as c}
        <li class="border rounded-lg p-3 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-2 min-w-0">
              {#if (c as any).logo}
                <img src={(c as any).logo} alt={c.name} class="w-6 h-6 rounded bg-white border border-slate-200 object-contain" />
              {/if}
              <div class="font-medium truncate">{c.name}</div>
            </div>
            <div class="text-sm"><span class="font-semibold">{c.matchScore}%</span></div>
          </div>
          <div class="text-xs text-gray-600 dark:text-gray-300 mt-1 truncate">{c.reason}</div>
          <div class="mt-2 h-1.5 bg-gray-100 dark:bg-slate-700 rounded overflow-hidden">
            <div class="h-full bg-indigo-600" style={`width:${c.matchScore}%`}></div>
          </div>
        </li>
      {/each}
    </ul>
  </div>
  {/if}

  
  <!-- Two-column: Quick tasks vs Activity & Tips -->
  <div class="grid md:grid-cols-2 gap-4">
    <div class="space-y-3">
      <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
        <div class="px-4 py-2 border-b border-slate-200 dark:border-slate-700 text-sm text-gray-600 dark:text-gray-400 flex items-center justify-between">
          <span>Quick tasks</span>
          <span class="text-xs text-gray-500">Drag to reorder</span>
        </div>
        <div class="p-3 grid sm:grid-cols-2 gap-2">
          {#each quickTasks as q (q.id)}
            <a href={q.href}
               draggable="true"
               on:dragstart={(e) => onDragStart(e, q.id)}
               on:dragover={onDragOver}
               on:drop={(e) => onDrop(e, q.id)}
               class={`flex items-center justify-between gap-2 border border-slate-200 dark:border-slate-700 rounded p-2 hover:bg-gray-50 dark:hover:bg-slate-700 transition ${draggingTaskId === q.id ? 'opacity-70' : ''}`}>
              <span class="flex items-center gap-2 min-w-0">
                <Icon name={q.icon as any} />
                <span class="truncate">{q.label}</span>
              </span>
              <span class="text-gray-400 cursor-grab select-none">⋮⋮</span>
            </a>
          {/each}
        </div>
      </div>
    </div>
    <div class="space-y-3">
      <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
        <div class="px-4 py-2 border-b border-slate-200 dark:border-slate-700 text-sm text-gray-600 dark:text-gray-400">Recent activity</div>
        <div class="p-3 text-sm">
          {#if groupedRecent.length}
            <div class="space-y-3">
              {#each groupedRecent as g}
                <div>
                  <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{g.date}</div>
                  <ul class="relative pl-4 border-l border-slate-200 dark:border-slate-700">
        {#each g.items.slice(0, 10) as r}
                      <li class="relative py-1">
                        <span class="absolute -left-1 top-2 w-2 h-2 rounded-full bg-indigo-600"></span>
                        <div class="flex items-center justify-between gap-3">
          <div class="pr-2 text-gray-800 dark:text-gray-200">{trimRecentText(r.t)}</div>
                          <div class="text-[11px] text-gray-500 dark:text-gray-400 whitespace-nowrap">{new Date(r.when).toLocaleTimeString()}</div>
                        </div>
                      </li>
                    {/each}
                  </ul>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-gray-600 dark:text-gray-400">No recent actions yet.</div>
          {/if}
        </div>
      </div>
      <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
        <div class="px-4 py-2 border-b border-slate-200 dark:border-slate-700 text-sm text-gray-600 dark:text-gray-400">Tips</div>
        <div class="p-3 grid sm:grid-cols-2 lg:grid-cols-3 gap-2 text-sm">
          <div class="flex items-start gap-2 border border-slate-200 dark:border-slate-700 rounded p-2 bg-white dark:bg-slate-800">
            <Icon name="sparkles" />
            <span class="text-gray-700 dark:text-gray-200">Use action verbs and quantify achievements.</span>
          </div>
          <div class="flex items-start gap-2 border border-slate-200 dark:border-slate-700 rounded p-2 bg-white dark:bg-slate-800">
            <Icon name="tag" />
            <span class="text-gray-700 dark:text-gray-200">Align keywords from the JD to your resume.</span>
          </div>
          <div class="flex items-start gap-2 border border-slate-200 dark:border-slate-700 rounded p-2 bg-white dark:bg-slate-800">
            <Icon name="shield-check" />
            <span class="text-gray-700 dark:text-gray-200">Keep formatting simple for ATS parsers.</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- System status (compact) -->
  <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
    <div class="px-4 py-2 border-b border-slate-200 dark:border-slate-700 text-sm text-gray-600 dark:text-gray-400">System status</div>
    <div class="p-4 text-sm">
      {#if loading}
        Checking...
      {:else}
        {#if backendOk}
          <div class="text-emerald-700 dark:text-emerald-400">Backend connected. {endpoints.length} endpoints available.</div>
        {:else}
          <div class="text-red-700 dark:text-red-400">Backend not reachable. {err}</div>
        {/if}
      {/if}
    </div>
  </div>
</section>

<style>
  /* Hide scrollbar but keep element scrollable */
  .no-scrollbar {
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE 10+ */
  }
  .no-scrollbar::-webkit-scrollbar {
    display: none; /* Safari and Chrome */
  }
</style>
