<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import type { ExtractedJD, RefConfig } from '$lib/jd';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { normalizeText, extractMeta, extractExperienceYears, guessSeniority, findSkills, extractSections, buildReferenceText, formatJD } from '$lib/jd';

  type JDItem = {
    id: string;
    company?: string;
    role?: string;
    location?: string;
    source?: string;
    jd: string;
    extracted?: ExtractedJD | null;
    reference?: string;
    createdAt: number;
    updatedAt: number;
  };

  const defaultRef: RefConfig = {
    includeMeta: true,
    includeSkills: true,
    includeRequirements: true,
    includeResponsibilities: false,
    topSkills: 10,
    topRequirements: 5,
    topResponsibilities: 4,
    maxChars: 800
  };

  let id = '';
  let item: JDItem | null = null;
  let refConfig: RefConfig = { ...defaultRef };
  let useReference = true;
  let expandSkills = false;
  let expandResps = false;
  let expandReqs = false;
  let showRefPreview = false;
  let expandRefPreview = false;
  let refModalBackdropEl: HTMLDivElement;
  let refModalPanelEl: HTMLDivElement;

  function load() {
    try { const raw = $page.params.id; id = raw; } catch {}
    try { const cfg = localStorage.getItem('tf_extract_ref_config'); if (cfg) refConfig = { ...refConfig, ...JSON.parse(cfg) }; } catch {}
    try { const use = localStorage.getItem('tf_extract_use_reference'); useReference = use ? use === 'true' : true; } catch {}
    try { const arr = JSON.parse(localStorage.getItem('tf_jd_items') || '[]') as JDItem[]; item = arr.find(i => i.id === id) || null; } catch {}
  }
  function save() {
    try {
      const arr = JSON.parse(localStorage.getItem('tf_jd_items') || '[]') as JDItem[];
      if (!item) return;
      const idx = arr.findIndex(i => i.id === item!.id);
      if (idx !== -1) arr[idx] = item!; else arr.unshift(item!);
      localStorage.setItem('tf_jd_items', JSON.stringify(arr));
    } catch {}
  }

  onMount(load);

  function clean(t: string) { return formatJD(t); }

  function runExtract() {
    if (!item) return;
    const raw = clean(item.jd || '');
    if (!raw) { item = { ...item, extracted: null, reference: '' }; save(); return; }
    if (raw !== (item.jd || '')) { item = { ...item, jd: raw, updatedAt: Date.now() }; }
    const meta = extractMeta(raw);
    const sections = extractSections(raw);
    const experienceYears = extractExperienceYears(raw);
    const seniority = guessSeniority(raw);
    const skills = findSkills(raw);
    const extracted: ExtractedJD = {
      ...meta,
      location: meta.location,
      experienceYears,
      seniority,
      skills,
      responsibilities: sections.responsibilities,
      requirements: sections.requirements,
      raw,
      when: Date.now()
    };
    const reference = buildReferenceText(extracted, refConfig);
    item = { ...item, extracted, reference, updatedAt: Date.now() };
    save();
    try {
      const actions = JSON.parse(localStorage.getItem('tf_recent_actions') || '[]');
      const entry = { t: `Extracted JD${extracted.title ? ` for "${extracted.title}"` : ''}`, when: new Date().toISOString() };
      localStorage.setItem('tf_recent_actions', JSON.stringify([entry, ...actions].slice(0, 50)));
    } catch {}
  }

  function sendToGenerate() {
    if (!item) return;
    try {
      if (item.extracted) localStorage.setItem('tf_extracted_jd', JSON.stringify(item.extracted));
      localStorage.setItem('tf_generate_use_reference', String(useReference));
      if (useReference && item.reference) localStorage.setItem('tf_generate_reference_text', item.reference);
      // Mark pipeline step
      const raw = localStorage.getItem('tf_pipelines');
      let list = raw ? JSON.parse(raw) : [];
      if (!list.length) {
        const id = crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
        list = [{ id, name: 'Pipeline 1', createdAt: Date.now(), statuses: { extract: 'pending', generate: 'pending', keywords: 'pending', ats: 'pending', export: 'pending', save: 'pending' } }];
        localStorage.setItem('tf_active_pipeline', list[0].id);
      }
      const activeId = localStorage.getItem('tf_active_pipeline') || list[0].id;
      const p = list.find((x: any) => x.id === activeId) || list[0];
      p.statuses.extract = 'complete';
      if (p.statuses.generate !== 'complete') {
        const keys: Array<'extract'|'generate'|'keywords'|'ats'|'export'|'save'> = ['extract','generate','keywords','ats','export','save'];
        for (const k of keys) {
          if (p.statuses[k] !== 'complete') p.statuses[k] = 'pending';
        }
        p.statuses.generate = 'active';
      }
      localStorage.setItem('tf_pipelines', JSON.stringify(list));
    } catch {}
    location.href = '/app/generate';
  }

  $: (() => { try { localStorage.setItem('tf_extract_ref_config', JSON.stringify(refConfig)); } catch {} })();
  $: (() => { try { localStorage.setItem('tf_extract_use_reference', String(useReference)); } catch {} })();
</script>

<svelte:window
  on:keydown={(e: KeyboardEvent) => { if (e.key === 'Escape' && showRefPreview) { showRefPreview = false; } }}
  on:click={(e: MouseEvent) => {
    if (!showRefPreview) return;
    const t = e.target as Node;
    if (refModalPanelEl && refModalPanelEl.contains(t)) return;
    if (refModalBackdropEl && t === refModalBackdropEl) { showRefPreview = false; }
  }}
/>

<section class="space-y-3">
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2">
      <a href="/app/extract" class="inline-flex items-center gap-1 text-xs px-2 py-1 border rounded border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700">
        <Icon name="arrow-left" />
        <span>Back</span>
      </a>
      <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="tag"/> Edit JD</h1>
    </div>
    <div class="flex items-center gap-2">
      {#if item?.extracted}
        <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={() => showRefPreview = !showRefPreview}>{showRefPreview ? 'Hide preview' : 'Preview reference'}</button>
        <button class="text-xs px-2 py-1 rounded border border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20" on:click={sendToGenerate}>Keep this reference</button>
      {/if}
    </div>
  </div>

  {#if item}
    <div class="grid md:grid-cols-2 gap-3">
      <!-- Left: Editor and inputs -->
      <div class="space-y-3">
        <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3">
          <div class="grid sm:grid-cols-3 gap-3 mb-3 text-sm">
            <label class="block">
              <div class="text-xs text-gray-600 dark:text-gray-300 mb-1">Company</div>
              <input class="w-full border rounded px-2 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" placeholder="Company" bind:value={item.company} on:change={(e)=>{item={...item!, company:(e.target as HTMLInputElement).value, updatedAt:Date.now()}; save();}} />
            </label>
            <label class="block">
              <div class="text-xs text-gray-600 dark:text-gray-300 mb-1">Role / Title</div>
              <input class="w-full border rounded px-2 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" placeholder="Role" bind:value={item.role} on:change={(e)=>{item={...item!, role:(e.target as HTMLInputElement).value, updatedAt:Date.now()}; save();}} />
            </label>
            <label class="block">
              <div class="text-xs text-gray-600 dark:text-gray-300 mb-1">Location</div>
              <input class="w-full border rounded px-2 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" placeholder="Location" bind:value={item.location} on:change={(e)=>{item={...item!, location:(e.target as HTMLInputElement).value, updatedAt:Date.now()}; save();}} />
            </label>
          </div>
          <label class="block">
            <div class="text-xs text-gray-600 dark:text-gray-300 mb-1">Job description</div>
            <textarea class="w-full min-h-[260px] border rounded p-3 shadow-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" placeholder="Paste job description..." bind:value={item.jd} on:change={()=>{item={...item!, updatedAt:Date.now()}; save();}}></textarea>
          </label>
          <div class="mt-1 flex items-center justify-between text-xs text-gray-500">
            <div>Updated {new Date(item.updatedAt).toLocaleString()}</div>
            <div class="text-[11px]">{(item.jd || '').length} chars</div>
          </div>
          <div class="mt-2 flex items-center justify-end gap-2">
            <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={()=>{item={...item!, jd: clean(item!.jd), updatedAt:Date.now()}; save();}}>Format</button>
            <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={runExtract}>Extract</button>
          </div>
        </div>
      </div>

  <!-- Right: Extracted details -->
      <div class="space-y-3">
        {#if item.extracted}
        <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3 space-y-2 text-sm">
          <div class="flex items-center justify-between">
            <div class="text-xs text-gray-500">Extracted details</div>
            <div class="text-[11px] text-emerald-700 dark:text-emerald-400">{new Date(item.extracted.when).toLocaleTimeString()}</div>
          </div>
          <div class="grid sm:grid-cols-2 gap-2">
            <div class="border rounded p-2"><div class="text-xs text-gray-500">Title</div><div class="font-medium">{item.extracted.title || '—'}</div></div>
            <div class="border rounded p-2"><div class="text-xs text-gray-500">Company</div><div class="font-medium">{item.extracted.company || '—'}</div></div>
            <div class="border rounded p-2"><div class="text-xs text-gray-500">Location</div><div class="font-medium">{item.extracted.location || '—'}</div></div>
            <div class="border rounded p-2"><div class="text-xs text-gray-500">Seniority</div><div class="font-medium">{item.extracted.seniority || '—'}</div></div>
            <div class="border rounded p-2"><div class="text-xs text-gray-500">Experience</div><div class="font-medium">{item.extracted.experienceYears != null ? `${item.extracted.experienceYears}+ years` : '—'}</div></div>
            <div class="border rounded p-2">
              <div class="text-xs text-gray-500">Skills</div>
              <div class="relative mt-1">
                <div class={expandSkills ? 'max-h-64 overflow-auto pr-1' : 'max-h-16 overflow-hidden'}>
                  <div class="flex flex-wrap gap-1.5">
                    {#each item.extracted.skills as s}
                      <span class="px-2 py-0.5 rounded-full text-[11px] border">{s}</span>
                    {/each}
                  </div>
                </div>
                {#if !expandSkills}
                  <div class="pointer-events-none absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white dark:from-slate-800 to-transparent"></div>
                {/if}
              </div>
              {#if item.extracted.skills.length > 10}
                <div class="mt-1 text-[11px]">
                  <button class="text-blue-600 hover:underline" on:click={() => expandSkills = !expandSkills}>{expandSkills ? 'Collapse' : 'Read more'}</button>
                </div>
              {/if}
            </div>
          </div>
          {#if item.extracted.responsibilities.length}
            <div class="border rounded p-2">
              <div class="text-xs text-gray-500 mb-1">Responsibilities</div>
              <div class="relative">
                <div class={expandResps ? 'max-h-64 overflow-auto pr-1' : 'max-h-24 overflow-hidden'}>
                  <ul class="list-disc pl-5 space-y-1">{#each item.extracted.responsibilities as it}<li>{it}</li>{/each}</ul>
                </div>
                {#if !expandResps}
                  <div class="pointer-events-none absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white dark:from-slate-800 to-transparent"></div>
                {/if}
              </div>
              {#if item.extracted.responsibilities.length}
                <div class="mt-1 text-[11px]"><button class="text-blue-600 hover:underline" on:click={() => expandResps = !expandResps}>{expandResps ? 'Collapse' : 'Read more'}</button></div>
              {/if}
            </div>
          {/if}
          {#if item.extracted.requirements.length}
            <div class="border rounded p-2">
              <div class="text-xs text-gray-500 mb-1">Requirements</div>
              <div class="relative">
                <div class={expandReqs ? 'max-h-64 overflow-auto pr-1' : 'max-h-24 overflow-hidden'}>
                  <ul class="list-disc pl-5 space-y-1">{#each item.extracted.requirements as it}<li>{it}</li>{/each}</ul>
                </div>
                {#if !expandReqs}
                  <div class="pointer-events-none absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white dark:from-slate-800 to-transparent"></div>
                {/if}
              </div>
              {#if item.extracted.requirements.length}
                <div class="mt-1 text-[11px]"><button class="text-blue-600 hover:underline" on:click={() => expandReqs = !expandReqs}>{expandReqs ? 'Collapse' : 'Read more'}</button></div>
              {/if}
            </div>
          {/if}
        </div>
        {:else}
          <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3 text-sm text-gray-600 dark:text-gray-300">
            Run “Extract” to see parsed details and build a reference.
          </div>
        {/if}
      </div>
    </div>

  {#if showRefPreview && item?.extracted}
    <div bind:this={refModalBackdropEl} class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <div bind:this={refModalPanelEl} class="w-[720px] max-w-[95vw] rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-xl">
        <div class="p-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div class="font-medium text-sm">Reference preview</div>
          <div class="flex items-center gap-2">
            <button class="text-[11px] px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={() => (showRefPreview = false)}>Close</button>
          </div>
        </div>
        <div class="p-3 text-sm">
          <div class="relative">
            <div class={expandRefPreview ? 'max-h-[420px] overflow-auto pr-1' : 'max-h-40 overflow-hidden'}>
              <pre class="w-full text-[12px] font-mono whitespace-pre-wrap bg-gray-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-700 rounded p-2">{buildReferenceText(item.extracted, refConfig)}</pre>
            </div>
            {#if !expandRefPreview}
              <div class="pointer-events-none absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-white dark:from-slate-800 to-transparent"></div>
            {/if}
          </div>
          <div class="mt-2 text-[11px] text-right">
            <button class="text-blue-600 hover:underline" on:click={() => (expandRefPreview = !expandRefPreview)}>{expandRefPreview ? 'Collapse' : 'Read more'}</button>
          </div>
        </div>
      </div>
    </div>
  {/if}
  {:else}
    <div class="text-sm text-gray-600 dark:text-gray-400">Not found.</div>
  {/if}
</section>
